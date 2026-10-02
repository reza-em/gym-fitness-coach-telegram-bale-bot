"""SQLite (WAL) storage: one connection per thread, explicit transactions, tiny helpers."""
import os, json, threading, sqlite3
from contextlib import contextmanager
import config, util

_path = config.DB_PATH
_local = threading.local()

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
"""

def now(): return util.now()

def set_path(p):
    global _path
    _path = p; close_all()

def close_all():
    c = getattr(_local, "c", None)
    if c:
        try: c[1].close()
        except Exception: pass
    _local.c = None

def _migrate(cn):
    """Idempotent upgrades. v2: users.sex ('m'/'f'); every existing user (e.g. Tester) becomes male."""
    cols = {r[1] for r in cn.execute("PRAGMA table_info(users)").fetchall()}
    if "sex" not in cols:
        cn.execute("ALTER TABLE users ADD COLUMN sex TEXT NOT NULL DEFAULT 'm'")
    cn.execute("UPDATE users SET sex='m' WHERE sex IS NULL OR sex NOT IN ('m','f')")

def conn():
    c = getattr(_local, "c", None)
    if c and c[0] == _path: return c[1]
    if c:
        try: c[1].close()
        except Exception: pass
    d = os.path.dirname(_path)
    if d: os.makedirs(d, exist_ok=True)
    new = not os.path.exists(_path)
    cn = sqlite3.connect(_path, timeout=30, isolation_level=None, check_same_thread=False)
    cn.row_factory = sqlite3.Row
    cn.execute("PRAGMA journal_mode=WAL"); cn.execute("PRAGMA synchronous=NORMAL"); cn.execute("PRAGMA busy_timeout=30000")
    cn.executescript(SCHEMA)
    _migrate(cn)
    if new:
        try: os.chmod(_path, 0o600)
        except OSError: pass
    _local.c = (_path, cn); _local.depth = 0
    return cn

@contextmanager
def tx():
    cn = conn(); depth = getattr(_local, "depth", 0)
    if depth:
        _local.depth = depth + 1
        try: yield cn
        finally: _local.depth -= 1
        return
    cn.execute("BEGIN IMMEDIATE"); _local.depth = 1
    try:
        yield cn; cn.execute("COMMIT")
    except BaseException:
        cn.execute("ROLLBACK"); raise
    finally:
        _local.depth = 0

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
