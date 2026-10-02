#!/usr/bin/env python3
"""Bale adapter tests (mocked HTTP; no token, no network): URL, Markdown conversion, request adaptation, unsupported methods, skipping without a token,
per-platform files. Run: ./venv/bin/python test_bale.py"""
import os, sys, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["FITNESS_PLATFORM"] = "bale"; os.environ["FITNESS_BALE_BOT_TOKEN"] = "222:BALE-TEST-TOKEN-XYZ"; os.environ["FITNESS_TELEGRAM_BOT_TOKEN"] = "111:TG-TEST-TOKEN-XYZ"
os.environ["FITNESS_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "b.db")
sys.path.insert(0, HERE)
import plat, balefmt, core as C, db, util, diet, nutrition as N
PASS = FAIL = 0
def ok(c, n):
    global PASS, FAIL
    if c: PASS += 1
    else: FAIL += 1; print("FAIL:", n)

P = plat.PLAT
ok(P.name == "bale" and P.api.startswith("https://tapi.bale.ai/bot222:"), "Bale API base tapi.bale.ai")
ok(P.db_path.endswith("b.db") and P.lock_name == "bot_bale.lock" and P.log_name == "bale.log" and P.claim and not P.profile, "own lock/log, claim code, no profile API")
ok(C.link("x") == "https://ble.ir/x", "ble.ir links")
class R:
    def __init__(s, j, code=200): s._j, s.status_code = j, code
    def json(s): return s._j
calls = []
C.sess.post = lambda url, data=None, files=None, timeout=None: (calls.append((url, data, files)), R({"ok": True, "result": {"message_id": 7}}))[1]
C.call("sendMessage", {"chat_id": 5, "text": "<b>سلام</b> 15x12 a_b *x*", "parse_mode": "HTML", "reply_markup": json.dumps({"inline_keyboard": [[{"text": "a", "callback_data": "x", "style": "p"}]]})})
url, data, _ = calls[-1]
ok(url.startswith("https://tapi.bale.ai/bot222:") and url.endswith("/sendMessage") and "parse_mode" not in data and data["text"].startswith("*سلام*") and "style" not in data["reply_markup"], "sendMessage adapted for Bale")
ok("<b>" not in data["text"] and "∗x∗" in data["text"], "stray markdown neutralised")
n = len(calls)
for meth in ("setMyName", "setMyDescription", "setMyShortDescription"):
    try: C.call(meth, {"name": "x"}); ok(False, meth)
    except C.ApiError: pass
ok(len(calls) == n, "unsupported profile methods are never sent to Bale")
C.call("setMyCommands", {"commands": "[]"}); ok(len(calls) == n + 1, "setMyCommands is sent")
C.call("answerCallbackQuery", {"callback_query_id": "1234"}); ok(len(calls) == n + 1, "old-client callback ids are not answered")
C.call("sendPhoto", {"chat_id": 1, "caption": "<b>c</b>", "parse_mode": "HTML"}, {"photo": ("c.png", b"x", "image/png")})
ok(calls[-1][2] and "photo" in calls[-1][2] and calls[-1][1]["caption"] == "*c*", "sendPhoto: multipart photo kept, caption converted")
C.call("sendDocument", {"chat_id": 1}, {"document": ("a.zip", b"x")}); ok("document" in calls[-1][2], "sendDocument works")
import json as _j
C.call("sendMediaGroup", {"chat_id": 1, "media": _j.dumps([{"type": "photo", "media": "attach://f0", "caption": "<b>x</b>", "parse_mode": "HTML"}, {"type": "photo", "media": "attach://f1"}])},
       {"f0": ("a.jpg", b"1", "image/jpeg"), "f1": ("b.jpg", b"2", "image/jpeg")})
mg = _j.loads(calls[-1][1]["media"])
ok(mg[0]["caption"] == "*x*" and "parse_mode" not in mg[0] and set(calls[-1][2]) == {"f0", "f1"}, "sendMediaGroup: caption converted, files attached (exercise photo album)")
# real texts from the bot convert cleanly
u = dict(sex="m", weight=60, height=185, age=28, activity=1.6, surplus=450, protein_gk=2.0, gainer_on=1, gainer_kcal=570, gainer_prot=25, gainer_n=1, tz="Asia/Tehran", train_days="5,6,1,2", id=1, gainer_name="x", gainer_g=150, creatine_on=1, creatine_g=5)
txt = diet.day_text(u, 0)
d, _ = C.bale_prepare("sendMessage", {"chat_id": 1, "text": util.rtl(txt), "parse_mode": "HTML"}, None)
ok("<" not in d["text"] and "&" not in d["text"] and len(d["text"]) <= 4096, "meal plan converts to Bale text without HTML")
# platform-specific skipping
env = {k: v for k, v in os.environ.items() if k not in ("FITNESS_BALE_BOT_TOKEN", "FITNESS_TELEGRAM_BOT_TOKEN")}
env["FITNESS_PLATFORM"] = "bale"
r = subprocess.run([sys.executable, "bot.py"], cwd=HERE, env=env, capture_output=True, text=True, timeout=60)
ok(r.returncode == 0 and "FITNESS_BALE_BOT_TOKEN is not set" in r.stderr, "bot.py without the Bale token exits 0 with a message")
env["FITNESS_PLATFORM"] = "telegram"
r = subprocess.run([sys.executable, "bot.py"], cwd=HERE, env=env, capture_output=True, text=True, timeout=60)
ok(r.returncode == 1 and "FITNESS_TELEGRAM_BOT_TOKEN" in r.stderr, "telegram without its token fails loudly")
r = subprocess.run(["bash", "run.sh"], cwd=HERE, env=dict(env, FITNESS_DB_PATH=""), capture_output=True, text=True, timeout=30)
ok(r.returncode != 0 and "not set" in (r.stdout + r.stderr), "run.sh with no tokens starts nothing")
r = subprocess.run([sys.executable, "-c", "import plat"], env=dict(env, FITNESS_PLATFORM="nope"), cwd=HERE, capture_output=True, text=True)
ok(r.returncode == 1, "unknown FITNESS_PLATFORM rejected")
print(f"{PASS} passed, {FAIL} failed"); sys.exit(1 if FAIL else 0)
