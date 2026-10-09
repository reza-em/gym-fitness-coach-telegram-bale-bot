"""Storage: SQLite (WAL) locally, or Turso / libSQL when TURSO_DATABASE_URL(_BALE) is set (serverless).
One connection per (thread, database), explicit transactions, tiny helpers.

Which database is used is decided per call from the active platform (plat.PLAT), so one serverless process can
serve Telegram and Bale with two separate databases:
  * set_path(p) override (tests)           -> local SQLite file p
  * PLAT.turso_url set (libsql://..., https://..., or file:/path for a local libSQL file) -> libSQL client
  * otherwise                              -> local SQLite file PLAT.db_path (fitness.db / fitness_bale.db)
FITNESS_DB_DRIVER=libsql forces the libSQL client for local files too (used by the tests)."""
import os, json, time, threading, sqlite3, logging
from contextlib import contextmanager
import config, util, plat

log = logging.getLogger("bot")
_path = None                     # explicit override (set_path); None -> per-platform target
_local = threading.local()
_schema_done = set()             # targets whose schema/migrations ran in this process
_schema_lock = threading.Lock()
REMOTE_IDLE_RECONNECT = 4.0      # Turso/Hrana streams expire after ~10 s idle: open a fresh (cheap, lazy) connection before that

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT, name TEXT, created INTEGER, last_seen INTEGER,
  onboarded INTEGER NOT NULL DEFAULT 0, ack INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0, is_admin INTEGER NOT NULL DEFAULT 0,
  awaiting TEXT, adata TEXT, tz TEXT NOT NULL DEFAULT 'Asia/Tehran', can_dm INTEGER NOT NULL DEFAULT 1,
  sex TEXT NOT NULL DEFAULT 'm', age INTEGER, height REAL, weight REAL, start_w REAL, best_w REAL, goal_w REAL, target_w REAL, target_days INTEGER NOT NULL DEFAULT 56,
  break_months INTEGER, days_pw INTEGER NOT NULL DEFAULT 4, plan_type TEXT NOT NULL DEFAULT 'ul', train_days TEXT NOT NULL DEFAULT '5,6,1,2',
  sess_min INTEGER NOT NULL DEFAULT 60, injuries TEXT NOT NULL DEFAULT '', activity REAL NOT NULL DEFAULT 1.55, kidney INTEGER NOT NULL DEFAULT 0,
  start_date TEXT, surplus INTEGER NOT NULL DEFAULT 450, protein_gk REAL NOT NULL DEFAULT 2.0, deload_week INTEGER NOT NULL DEFAULT 0,
  gainer_on INTEGER NOT NULL DEFAULT 0, gainer_name TEXT, gainer_g REAL, gainer_kcal REAL, gainer_prot REAL, gainer_n INTEGER NOT NULL DEFAULT 1,
  creatine_on INTEGER NOT NULL DEFAULT 0, creatine_g REAL NOT NULL DEFAULT 5, creatine_start TEXT,
  last_adjust TEXT, last_checkin_week INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ref_weights(user_id INTEGER NOT NULL, ex TEXT NOT NULL, w REAL NOT NULL, PRIMARY KEY(user_id, ex));
CREATE TABLE IF NOT EXISTS weights(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, kg REAL NOT NULL, ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_weights ON weights(user_id, day);
CREATE TABLE IF NOT EXISTS measures(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL, cm REAL NOT NULL, ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_measures ON measures(user_id, kind, day);
CREATE TABLE IF NOT EXISTS workouts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, week INTEGER NOT NULL, sidx INTEGER NOT NULL,
  title TEXT, plan TEXT, started INTEGER, finished INTEGER NOT NULL DEFAULT 0, finished_ts INTEGER, deload INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_workouts ON workouts(user_id, day);
CREATE TABLE IF NOT EXISTS sets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, workout_id INTEGER NOT NULL, ex TEXT NOT NULL, setno INTEGER NOT NULL,
  w REAL NOT NULL, reps INTEGER NOT NULL, ts INTEGER, day TEXT
);
CREATE INDEX IF NOT EXISTS ix_sets_ex ON sets(user_id, ex, id);
CREATE INDEX IF NOT EXISTS ix_sets_w ON sets(workout_id);
CREATE TABLE IF NOT EXISTS prs(user_id INTEGER NOT NULL, ex TEXT NOT NULL, kind TEXT NOT NULL, val REAL NOT NULL, w REAL, reps INTEGER, day TEXT, PRIMARY KEY(user_id, ex, kind));
CREATE TABLE IF NOT EXISTS supp(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL, amount REAL, ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_supp ON supp(user_id, day);
CREATE TABLE IF NOT EXISTS water(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, ml INTEGER NOT NULL, ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_water ON water(user_id, day);
CREATE TABLE IF NOT EXISTS reminders(user_id INTEGER NOT NULL, kind TEXT NOT NULL, times TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, kind));
CREATE TABLE IF NOT EXISTS rem_sent(user_id INTEGER NOT NULL, key TEXT NOT NULL, day TEXT NOT NULL, PRIMARY KEY(user_id, key));
CREATE TABLE IF NOT EXISTS checkins(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, week INTEGER, day TEXT, kg REAL, fatigue INTEGER, pain INTEGER, adherence INTEGER,
  rate REAL, action TEXT, kcal_change INTEGER NOT NULL DEFAULT 0, ts INTEGER
);
CREATE TABLE IF NOT EXISTS activity(day TEXT NOT NULL, user_id INTEGER NOT NULL, PRIMARY KEY(day, user_id));
CREATE TABLE IF NOT EXISTS updates_seen(update_id INTEGER PRIMARY KEY, ts INTEGER NOT NULL);
"""

def now(): return util.now()

def set_path(p):
    global _path
    _path = p; close_all()

def target():
    """-> (kind, location, auth_token) for the active platform."""
    if _path: return ("libsql" if os.environ.get("FITNESS_DB_DRIVER") == "libsql" else "sqlite", _path, "")
    P = plat.current()
    if P.turso_url:
        u = P.turso_url
        if u.startswith("file:"): return ("libsql", u[5:], "")
        return ("remote", u, P.turso_token)
    if plat.SERVERLESS and os.environ.get("TURSO_DATABASE_URL") and P.is_bale:
        raise RuntimeError("TURSO_DATABASE_URL_BALE is not set (the Bale bot needs its own Turso database)")
    return ("libsql" if os.environ.get("FITNESS_DB_DRIVER") == "libsql" else "sqlite", P.db_path, "")

def _conns():
    d = getattr(_local, "conns", None)
    if d is None: d = _local.conns = {}
    return d

def close_all():
    for key, c in list(_conns().items()):
        if key[0] == "sqlite":
            try: c["cn"].close()
            except Exception: pass
        # libSQL connections are just dropped (Connection.close() on a remote connection panics in libsql 0.1.x)
    _conns().clear()

# ---------------- libSQL adapter (sqlite3-like rows: r[0], r["col"], dict(r)) ----------------
class Row(tuple):
    """Tuple row that also supports r["col"], keys() and dict(r) like sqlite3.Row."""
    __slots__ = ()
    _cols = ()
    def keys(self): return list(self._cols)
    def __getitem__(self, k):
        if isinstance(k, str): return tuple.__getitem__(self, self._cols.index(k))
        return tuple.__getitem__(self, k)

def _row_class(cols):
    return type("Row", (Row,), {"__slots__": (), "_cols": cols})

class _LCur:
    def __init__(self, cur):
        self._cur = cur
        desc = cur.description or ()
        self._cls = _row_class(tuple(d[0] for d in desc)) if desc else None
    def _wrap(self, r): return None if r is None else (self._cls(r) if self._cls else r)
    def fetchone(self): return self._wrap(self._cur.fetchone())
    def fetchall(self): return [self._wrap(r) for r in self._cur.fetchall()]
    def __iter__(self): return iter(self.fetchall())
    @property
    def rowcount(self): return self._cur.rowcount
    @property
    def lastrowid(self): return self._cur.lastrowid
    @property
    def description(self): return self._cur.description

def split_sql(script):
    """Split a simple ';'-separated script (no ';' inside literals/triggers - true for SCHEMA) into statements."""
    return [x.strip() for x in script.split(";") if x.strip()]

def _transient(e):
    m = str(e).lower()
    return any(w in m for w in ("stream_expired", "stream has expired", "baton", "connection reset", "connection refused", "timed out", "broken pipe", "error sending request"))

class _LConn:
    """Wraps a libsql Connection: sqlite3-like rows, and a fresh connection when the remote stream may have expired."""
    def __init__(self, kind, loc, token):
        self.kind, self.loc, self.token = kind, loc, token
        self.cn = None; self.last = 0.0; self.depth = 0
    def _open(self):
        import libsql
        if self.kind == "remote": self.cn = libsql.connect(database=self.loc, auth_token=self.token, isolation_level=None)
        else: self.cn = libsql.connect(self.loc, isolation_level=None)
    def _get(self):
        if self.cn is None or (self.kind == "remote" and self.depth == 0 and time.time() - self.last > REMOTE_IDLE_RECONNECT):
            self._open()
        return self.cn
    def execute(self, sql, args=()):
        cn = self._get()
        try:
            cur = cn.execute(sql, tuple(args))
        except Exception as e:
            if self.kind != "remote" or self.depth or not _transient(e): raise
            log.info("libsql: reconnecting after %s", type(e).__name__)
            self._open(); cur = self.cn.execute(sql, tuple(args))
        self.last = time.time()
        return _LCur(cur)
    def executescript(self, script):
        # Remote: run statement by statement. libsql's remote executescript re-serialises multi-statement scripts and
        # upper-cases keyword-like identifiers (a column `key` became `KEY`, `action` -> `ACTION`), which breaks r["key"].
        if self.kind == "remote":
            for stmt in split_sql(script): self.execute(stmt)
            return
        self._get().executescript(script)
        self.last = time.time()
    def close(self): self.cn = None

def _migrate(cn):
    """Idempotent upgrades. v4: users.body_cat. v3: users.macro_target. v2: users.sex ('m'/'f'); every existing user (e.g. Tester) becomes male."""
    cols = {r[1] for r in cn.execute("PRAGMA table_info(users)").fetchall()}
    if "sex" not in cols:
        cn.execute("ALTER TABLE users ADD COLUMN sex TEXT NOT NULL DEFAULT 'm'")
    cn.execute("UPDATE users SET sex='m' WHERE sex IS NULL OR sex NOT IN ('m','f')")
    if "macro_target" not in cols:      # v3: pinned target weight from the 🧮 calories & macros calculator (macros.py)
        cn.execute("ALTER TABLE users ADD COLUMN macro_target REAL")
    if "body_cat" not in cols:          # v4: 📂 body-type override 'fat'/'lean'/'fit' (NULL = automatic from BMI + goal, programs_db.py)
        cn.execute("ALTER TABLE users ADD COLUMN body_cat TEXT")

def _ensure_schema(key, cn):
    if key in _schema_done: return
    with _schema_lock:
        if key in _schema_done: return
        cn.executescript(SCHEMA)
        _migrate(cn)
        _schema_done.add(key)

def _entry():
    key = target(); conns = _conns()
    c = conns.get(key)
    if c: return c
    kind, loc, token = key
    if kind == "remote":
        cn = _LConn(kind, loc, token)
    else:
        d = os.path.dirname(loc)
        if d: os.makedirs(d, exist_ok=True)
        new = not os.path.exists(loc)
        if kind == "libsql":
            cn = _LConn(kind, loc, token)
            cn.execute("PRAGMA journal_mode=WAL"); cn.execute("PRAGMA busy_timeout=30000")
        else:
            cn = sqlite3.connect(loc, timeout=30, isolation_level=None, check_same_thread=False)
            cn.row_factory = sqlite3.Row
            cn.execute("PRAGMA journal_mode=WAL"); cn.execute("PRAGMA synchronous=NORMAL"); cn.execute("PRAGMA busy_timeout=30000")
        if new:
            try: os.chmod(loc, 0o600)
            except OSError: pass
    if kind == "remote": _ensure_schema(key, cn)            # once per process (each statement is a network round trip)
    else: cn.executescript(SCHEMA); _migrate(cn)             # local file: every new connection (cheap; the file may be new)
    c = conns[key] = {"cn": cn, "depth": 0}
    return c

def conn(): return _entry()["cn"]

@contextmanager
def tx():
    c = _entry(); cn = c["cn"]
    if c["depth"]:
        c["depth"] += 1
        try: yield cn
        finally: c["depth"] -= 1
        return
    cn.execute("BEGIN IMMEDIATE"); c["depth"] = 1
    if isinstance(cn, _LConn): cn.depth = 1
    try:
        yield cn; cn.execute("COMMIT")
    except BaseException:
        try: cn.execute("ROLLBACK")
        except Exception: pass
        raise
    finally:
        c["depth"] = 0
        if isinstance(cn, _LConn): cn.depth = 0

def q(sql, args=()): return [dict(r) for r in conn().execute(sql, args).fetchall()]
def q1(sql, args=()):
    r = conn().execute(sql, args).fetchone(); return dict(r) if r else None
def val(sql, args=(), default=None):
    r = conn().execute(sql, args).fetchone()
    return default if r is None or r[0] is None else r[0]
def ex(sql, args=()): return conn().execute(sql, args)

def meta_get(key, default=None):
    r = conn().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    if r is None: return default
    try: return json.loads(r[0])
    except Exception: return default

def meta_set(key, value):
    conn().execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))

def init():
    conn()
    with tx():
        if meta_get("schema_version") is None: meta_set("schema_version", 1)

# ---- users ----
def get_user(uid): return q1("SELECT * FROM users WHERE id=?", (uid,))

def touch_user(frm, private=True):
    """-> (user dict, is_new). Creates the row on first contact."""
    uid = frm["id"]; name = " ".join(x for x in (frm.get("first_name"), frm.get("last_name")) if x)[:60]
    u = get_user(uid); new = u is None
    with tx():
        if new:
            ex("INSERT INTO users(id,username,name,created,last_seen) VALUES(?,?,?,?,?)", (uid, frm.get("username"), name, now(), now()))
        else:
            ex("UPDATE users SET username=?, name=?, last_seen=?, can_dm=1 WHERE id=?", (frm.get("username"), name, now(), uid))
        ex("INSERT OR IGNORE INTO activity(day,user_id) VALUES(?,?)", (util.today("Asia/Tehran").isoformat(), uid))
    return get_user(uid), new

_USER_COLS = None
def update_user(uid, **kw):
    global _USER_COLS
    if not kw: return
    if _USER_COLS is None: _USER_COLS = {r[1] for r in conn().execute("PRAGMA table_info(users)").fetchall()}
    bad = set(kw) - _USER_COLS
    if bad: raise KeyError("unknown user column(s): %s" % ", ".join(sorted(bad)))
    ex("UPDATE users SET " + ",".join(f"{k}=?" for k in kw) + " WHERE id=?", (*kw.values(), uid))

def set_await(uid, kind, data=None):
    update_user(uid, awaiting=kind, adata=json.dumps(data, ensure_ascii=False) if data is not None else None)

def get_await(uid):
    u = get_user(uid)
    if not u or not u["awaiting"]: return None, {}
    try: d = json.loads(u["adata"]) if u["adata"] else {}
    except Exception: d = {}
    return u["awaiting"], d

def is_admin(uid):
    u = get_user(uid)
    return bool(u and u["is_admin"]) or (uid == config.OWNER_ID and not __import__("plat").PLAT.claim)

def is_banned(uid):
    u = get_user(uid); return bool(u and u["banned"])

# ---- webhook idempotency (Telegram/Bale re-deliver an update when our response is slow or not 200) ----
def claim_update(update_id):
    """True the first time this update_id is seen for the active platform's database, False for a re-delivery."""
    if update_id is None: return True
    cur = ex("INSERT OR IGNORE INTO updates_seen(update_id, ts) VALUES(?,?)", (int(update_id), now()))
    return (cur.rowcount or 0) > 0

def prune_updates(keep_days=3):
    ex("DELETE FROM updates_seen WHERE ts < ?", (now() - keep_days * 86400,))
