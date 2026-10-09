#!/usr/bin/env python3
"""Offline test of the Vercel webhook app (api/index.py) with a fake Telegram/Bale API (no network, no real token).
Both platforms run in ONE process (like on Vercel) with separate databases.
   .venv/bin/python test_serverless.py                                   (local SQLite files)
   SERVERLESS_TEST_STORAGE=libsql .venv/bin/python test_serverless.py    (libSQL client on local files: TURSO_DATABASE_URL=file:...)
   SERVERLESS_TEST_STORAGE=remote TEST_LIBSQL_URL=http://127.0.0.1:8089 TEST_LIBSQL_URL_BALE=http://127.0.0.1:8090 ...
                                                                          (libSQL remote protocol against local `sqld` servers)"""
import os, sys, json, tempfile, datetime as dt
TMP = tempfile.mkdtemp(prefix="fit-sl-")
MODE = os.environ.get("SERVERLESS_TEST_STORAGE", "sqlite")
for k in ("FITNESS_DB_PATH", "FITNESS_PLATFORM", "TURSO_DATABASE_URL", "TURSO_DATABASE_URL_BALE", "FITNESS_DB_DRIVER"): os.environ.pop(k, None)
os.environ.update(FITNESS_SERVERLESS="1", FITNESS_DATA_DIR=TMP, OWNER_ID="100000001",
                  FITNESS_TELEGRAM_BOT_TOKEN="123456:FAKE-TG-TOKEN-abcdefghijklmnop", FITNESS_BALE_BOT_TOKEN="222:FAKE-BALE-TOKEN-ABCDEF",
                  TELEGRAM_WEBHOOK_SECRET="tg-secret-123", BALE_WEBHOOK_SECRET="bale-secret-456", CRON_SECRET="cron-secret-789")
if MODE == "libsql":
    os.environ["TURSO_DATABASE_URL"] = "file:" + os.path.join(TMP, "tg_libsql.db")
    os.environ["TURSO_DATABASE_URL_BALE"] = "file:" + os.path.join(TMP, "bale_libsql.db")
elif MODE == "remote":
    os.environ["TURSO_DATABASE_URL"] = os.environ["TEST_LIBSQL_URL"]; os.environ["TURSO_DATABASE_URL_BALE"] = os.environ["TEST_LIBSQL_URL_BALE"]
    os.environ["TURSO_AUTH_TOKEN"] = "local-dev"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.index import app
import plat, db, util, bot, core as C, logging
logging.getLogger().setLevel(logging.WARNING)

PASS = FAIL = 0
def ok(cond, name):
    global PASS, FAIL
    if cond: PASS += 1
    else: FAIL += 1; print("FAIL:", name)

SENT = []; NEXT = [1000]
def fake_call(method, data_=None, files=None, timeout=60):
    P = plat.current(); d = dict(data_ or {})
    if P.is_bale: d, files = C.bale_prepare(method, d, files)       # what really goes to tapi.bale.ai
    SENT.append((P.name, method, d)); NEXT[0] += 1
    if method == "getMe": return {"id": 999, "username": "FitTestBot", "is_bot": True}
    if method in ("sendMessage", "sendPhoto", "sendDocument", "editMessageText", "sendAnimation"): return {"message_id": NEXT[0], "chat": {"id": d.get("chat_id")}}
    if method == "sendMediaGroup": return [{"message_id": NEXT[0]}]
    return True
C.call = fake_call; bot.call = fake_call

TEHRAN = dt.timezone(dt.timedelta(hours=3, minutes=30))
CLOCK = [dt.datetime(2026, 10, 2, 12, 0, tzinfo=TEHRAN).timestamp()]
util.set_clock(lambda: CLOCK[0])

cl = app.test_client()
import random
_B = random.randint(10**6, 10**9)               # fresh ids so re-runs against a persistent (remote) DB do not collide
UPD = {"telegram": _B, "bale": _B}
def post(platform, up, secret=None, headers=None):
    if platform == "telegram":
        h = {"X-Telegram-Bot-Api-Secret-Token": secret if secret is not None else "tg-secret-123"}; h.update(headers or {})
        return cl.post("/api/tg", json=up, headers=h)
    return cl.post("/api/bale/" + (secret if secret is not None else "bale-secret-456"), json=up, headers=headers or {})
def msg(platform, uid, text, uid_=None):
    UPD[platform] += 1
    return {"update_id": UPD[platform], "message": {"message_id": 5000 + UPD[platform], "from": {"id": uid, "first_name": "Tester", "username": "u%d" % uid},
            "chat": {"id": uid, "type": "private"}, "date": 1, "text": text}}
def cbq(platform, uid, data, mid=777):
    UPD[platform] += 1
    return {"update_id": UPD[platform], "callback_query": {"id": "9cb%d" % UPD[platform], "from": {"id": uid, "first_name": "Tester"}, "data": data,
            "message": {"message_id": mid, "chat": {"id": uid, "type": "private"}}}}
def say(p, uid, text): r = post(p, msg(p, uid, text)); assert r.status_code == 200, (r.status_code, r.data); return r
def press(p, uid, data): r = post(p, cbq(p, uid, data)); assert r.status_code == 200, (r.status_code, r.data); return r
def mark(): return len(SENT)
def out(since, p=None):
    t = []
    for pn, m, d in SENT[since:]:
        if p and pn != p: continue
        if m in ("sendMessage", "editMessageText"): t.append(d.get("text", ""))
        elif m in ("sendPhoto", "sendDocument", "sendAnimation"): t.append(d.get("caption", ""))
    return "\n".join(t)
def datas(since, p=None):
    for pn, m, d in reversed(SENT[since:]):
        if (p is None or pn == p) and d.get("reply_markup"):
            try: return [b.get("callback_data") for row in json.loads(d["reply_markup"])["inline_keyboard"] for b in row if b.get("callback_data")]
            except Exception: return []
    return []
def user(p, uid):
    with plat.use(p): return db.get_user(uid)

print("== storage mode:", MODE)
# ---------------- health + auth
r = cl.get("/api/health"); j = r.get_json()
ok(r.status_code == 200 and j["platforms"] == {"telegram": True, "bale": True}, "health ok, both tokens seen")
ok("123456:FAKE" not in r.get_data(as_text=True) and "secret" not in r.get_data(as_text=True), "health leaks no secrets")
ok(post("telegram", msg("telegram", 1, "/start"), secret="").status_code == 401, "telegram: missing secret header -> 401")
ok(post("telegram", msg("telegram", 1, "/start"), secret="wrong").status_code == 401, "telegram: wrong secret header -> 401")
ok(post("bale", msg("bale", 1, "/start"), secret="wrong").status_code == 401, "bale: wrong path secret -> 401")
ok(cl.post("/api/bale", json={}).status_code == 401, "bale: no path secret -> 401")
ok(cl.get("/api/tg").status_code == 405, "GET on webhook not allowed")
ok(cl.get("/api/cron/tick").status_code == 401, "cron without secret -> 401")
ok(cl.get("/api/cron/tick", headers={"Authorization": "Bearer nope"}).status_code == 401, "cron with wrong secret -> 401")
ok(len(SENT) == 0, "rejected requests sent nothing")
ok(post("telegram", "not json").status_code == 400, "malformed body -> 400")

# ---------------- /start on both platforms, same numeric user id -> separate databases
TG = BA = random.randint(10**6, 10**9)          # same numeric id on both platforms on purpose
m = mark(); say("telegram", TG, "/start")
ok("هشدار پزشکی" in out(m, "telegram") and "ob:ack" in datas(m, "telegram"), "telegram /start -> disclaimer + ack button")
ok(all(pn == "telegram" for pn, _m, _d in SENT[m:]) and any(d.get("parse_mode") == "HTML" for _p, _m, d in SENT[m:]), "telegram replies use HTML on the telegram API")
m = mark(); say("bale", BA, "/start")
ok("ob:ack" in datas(m, "bale") and all(pn == "bale" for pn, _m, _d in SENT[m:]), "bale /start -> ack button, routed to the bale API")
ok(not any("parse_mode" in d for _p, _m, d in SENT[m:]), "bale replies carry no parse_mode (markdown conversion)")

# ---------------- duplicate delivery (Telegram retry) is ignored
up = msg("telegram", TG, "/help"); up["update_id"] = _B - 1; m = mark()
r1 = post("telegram", up); n1 = len(SENT) - m; r2 = post("telegram", up)
ok(r1.status_code == 200 and r2.status_code == 200 and n1 >= 1 and len(SENT) - m == n1, "same update_id twice -> handled once, both 200")
ok(post("bale", dict(up)).status_code == 200 and len(SENT) - m > n1, "same update_id on the OTHER platform is a different update")

# ---------------- onboarding (generic driver: press the first forward button / answer numbers)
def onboard(p, uid, sex="m"):
    press(p, uid, "ob:ack"); press(p, uid, "ob:sex:" + sex)
    answers = iter(["28", "180", "70", "75", "80", "80", "80"])
    for _ in range(40):
        u = user(p, uid)
        if u["onboarded"]: return True
        m = mark()
        aw = u["awaiting"] or ""
        last = [d for d in datas(0, p) if d and d.startswith("ob:") and "back" not in d and d != "ob:ack" and not d.startswith("ob:inj:")]
        if aw.startswith("ob:") and aw[3:] in ("age", "height", "weight", "goal_w", "best_w", "target_w", "gainer_amt") or not last:
            say(p, uid, next(answers, "80"))
        else:
            press(p, uid, last[0])
        if os.environ.get('DBG'): print('  step', aw, last[:3], '->', (out(m, p) or '')[:70].replace('\n',' '), datas(m, p)[:4])
        if len(SENT) == m: return False
    return user(p, uid)["onboarded"] == 1
ok(onboard("telegram", TG), "telegram onboarding completes via webhook")
ok(onboard("bale", BA, "f"), "bale onboarding completes via webhook")
ok(user("telegram", TG)["sex"] == "m" and user("bale", BA)["sex"] == "f", "per-platform data kept apart (same user id, different profiles)")

# ---------------- menus after onboarding
for p, uid in (("telegram", TG), ("bale", BA)):
    m = mark(); say(p, uid, "/macros"); txt = out(m, p)
    ok(txt and any((d or "").startswith("mc:") for d in datas(m, p)), p + ": /macros shows the calculator with mc: buttons")
    first_mc = [d for d in datas(m, p) if d.startswith("mc:c:")]
    if first_mc:
        m = mark(); press(p, uid, first_mc[0]); ok("کالری" in out(m, p) or "kcal" in out(m, p), p + ": macro card for a target weight")
    m = mark(); say(p, uid, "/bodytype")
    ok(any((d or "").startswith("bt:") for d in datas(m, p)), p + ": /bodytype menu with bt: buttons")
    m = mark(); press(p, uid, "bt:sec:food"); ok(len(out(m, p)) > 50, p + ": body-type food section")
    m = mark(); say(p, uid, "/progress"); ok(any(me in ("sendPhoto", "sendMessage", "editMessageText") for _pn, me, _d in SENT[m:]), p + ": /progress (chart) answered")
    m = mark(); say(p, uid, "/today"); ok(len(out(m, p)) > 0, p + ": /today answered")

# ---------------- cron tick (reminders) for both platforms
CLOCK[0] = dt.datetime(2026, 10, 3, 13, 5, tzinfo=TEHRAN).timestamp()      # 13:05 Tehran: water reminder (13:00) due
H = {"Authorization": "Bearer cron-secret-789"}
m = mark(); r = cl.get("/api/cron/tick?platform=all", headers=H); j = r.get_json()
ok(r.status_code == 200 and isinstance(j["result"]["telegram"], dict) and isinstance(j["result"]["bale"], dict), "cron tick ok for both platforms: %s" % j)
ok(j["result"]["telegram"]["sent"] >= 1 and j["result"]["bale"]["sent"] >= 1, "due reminders sent on both platforms")
ok(any(pn == "telegram" and me == "sendMessage" and d.get("chat_id") == TG for pn, me, d in SENT[m:]) and any(pn == "bale" and me == "sendMessage" for pn, me, d in SENT[m:]), "reminders went to the right APIs")
m = mark(); r = cl.post("/api/cron/tick?platform=telegram", headers={"X-Cron-Secret": "cron-secret-789"})
ok(r.status_code == 200 and r.get_json()["result"]["telegram"]["sent"] == 0 and not [1 for _p, me, _d in SENT[m:] if me == "sendMessage"], "second tick: nothing re-sent (POST + X-Cron-Secret works)")
ok(cl.get("/api/cron/tick?platform=xx", headers=H).status_code == 400, "bad platform -> 400")

# ---------------- schema column names survive the storage backend (remote executescript used to upper-case `key`)
for p in ("telegram", "bale"):
    with plat.use(p):
        cols = {t: [d[0] for d in db.conn().execute("SELECT * FROM %s LIMIT 0" % t).description] for t in ("meta", "rem_sent", "checkins")}
    ok("key" in cols["meta"] and "key" in cols["rem_sent"] and "action" in cols["checkins"], p + ": lower-case column names kept (%s)" % MODE)

# ---------------- no background threads were started by the app
import threading
ok(not [t for t in threading.enumerate() if t.name == "scheduler"], "no scheduler thread in serverless mode")
alltext = json.dumps(SENT, ensure_ascii=False)
ok("FAKE-TG-TOKEN" not in alltext and "FAKE-BALE-TOKEN" not in alltext, "tokens never in outgoing payloads")
print("%d passed, %d failed  [serverless/%s]" % (PASS, FAIL, MODE))
sys.exit(1 if FAIL else 0)
