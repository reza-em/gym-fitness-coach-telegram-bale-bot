#!/usr/bin/env python3
"""Copy the polling bot's SQLite databases into Turso (libSQL) for the serverless deployment.

    # stop the polling bot first (./stop.sh) so nothing is written during the copy, then:
    export TURSO_DATABASE_URL=libsql://fitness-telegram-<org>.turso.io   TURSO_AUTH_TOKEN=...      # never commit these
    export TURSO_DATABASE_URL_BALE=libsql://fitness-bale-<org>.turso.io  [TURSO_AUTH_TOKEN_BALE=...]
    .venv/bin/python scripts/migrate_sqlite_to_turso.py --platform telegram --src fitness.db
    .venv/bin/python scripts/migrate_sqlite_to_turso.py --platform bale     --src fitness_bale.db

What it does: snapshots the source with SQLite's online-backup API (the live file is opened read-only and never
modified), creates the bot schema on the target (same SCHEMA/migrations as db.py), copies every table with
multi-row INSERT OR REPLACE in transactions, then compares row counts. It refuses to write into a target that
already has users unless --wipe (fresh copy: empties the target tables first) or --force (upsert). --dry-run only prints what would be copied. Secrets are never printed."""
import os, sys, argparse, sqlite3, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import db  # noqa: E402  (SCHEMA + _migrate)

ENV = {"telegram": ("TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"), "bale": ("TURSO_DATABASE_URL_BALE", "TURSO_AUTH_TOKEN_BALE")}
SKIP_TABLES = {"sqlite_sequence", "sqlite_stat1", "updates_seen"}
BATCH = 100

def mask(url):
    return url.split("?")[0]

def snapshot(src):
    if not os.path.exists(src): sys.exit("source not found: %s" % src)
    tmp = os.path.join(tempfile.mkdtemp(prefix="fit-migrate-"), "snapshot.db")
    s = sqlite3.connect("file:%s?mode=ro" % os.path.abspath(src), uri=True, timeout=30)
    d = sqlite3.connect(tmp)
    s.backup(d); s.close(); d.close()
    return tmp

def connect_target(platform, url_arg):
    import libsql
    url_env, tok_env = ENV[platform]
    url = (url_arg or os.environ.get(url_env, "")).strip()
    token = (os.environ.get(tok_env) or os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
    if not url: sys.exit("%s is not set (or pass --url)" % url_env)
    if url.startswith("file:"):
        return url, libsql.connect(url[5:], isolation_level=None)
    if not token: sys.exit("%s / TURSO_AUTH_TOKEN is not set" % tok_env)
    return url, libsql.connect(database=url, auth_token=token, isolation_level=None)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=("telegram", "bale"), required=True)
    ap.add_argument("--src", required=True, help="source SQLite file (fitness.db / fitness_bale.db)")
    ap.add_argument("--url", help="target URL (default: from the platform's TURSO_DATABASE_URL* env var)")
    ap.add_argument("--force", action="store_true", help="allow writing into a target that already has users (rows are upserted)")
    ap.add_argument("--wipe", action="store_true", help="DELETE all rows in the target tables first (re-sync a fresh copy at switchover)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    snap = snapshot(a.src)
    s = sqlite3.connect(snap); s.row_factory = sqlite3.Row
    tables = [r[0] for r in s.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if r[0] not in SKIP_TABLES]
    counts = {t: s.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in tables}
    print("source %s: %s" % (a.src, ", ".join("%s=%d" % kv for kv in counts.items())))
    if a.dry_run: print("dry run: nothing written"); return

    url, t = connect_target(a.platform, a.url)
    print("target:", mask(url))
    for stmt in db.split_sql(db.SCHEMA): t.execute(stmt)     # one by one (remote executescript mangles `key` -> `KEY`)
    db._migrate(t)
    existing = t.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing and not (a.force or a.wipe): sys.exit("target already has %d users - refusing (use --wipe for a fresh copy, or --force to upsert)" % existing)
    if a.wipe:
        for tb in tables + ["updates_seen"]:
            try: t.execute('DELETE FROM "%s"' % tb)
            except Exception: pass
        print("target tables wiped")

    t0 = time.time()
    for tb in tables:
        try: tcols = [d[0].lower() for d in t.execute('SELECT * FROM "%s" LIMIT 0' % tb).description]
        except Exception: tcols = []
        if not tcols: print("  skip %s (not in target schema)" % tb); continue
        scols = [r[1] for r in s.execute('PRAGMA table_info("%s")' % tb).fetchall()]
        cols = [c for c in scols if c.lower() in tcols]
        rows = s.execute('SELECT %s FROM "%s"' % (",".join('"%s"' % c for c in cols), tb)).fetchall()
        collist = ",".join('"%s"' % c for c in cols); one = "(" + ",".join("?" * len(cols)) + ")"
        t.execute("BEGIN")
        try:
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i + BATCH]
                args = [v for r in chunk for v in tuple(r)]
                t.execute('INSERT OR REPLACE INTO "%s"(%s) VALUES %s' % (tb, collist, ",".join([one] * len(chunk))), tuple(args))
            t.execute("COMMIT")
        except BaseException:
            try: t.execute("ROLLBACK")
            except Exception: pass
            raise
        print("  %-12s %6d rows" % (tb, len(rows)))
    bad = []
    for tb in tables:
        n = t.execute('SELECT COUNT(*) FROM "%s"' % tb).fetchone()[0]
        if n < counts[tb]: bad.append("%s: %d < %d" % (tb, n, counts[tb]))
    os.remove(snap)
    if bad: sys.exit("row count mismatch: " + "; ".join(bad))
    print("done in %.1fs - row counts verified" % (time.time() - t0))

if __name__ == "__main__":
    main()
