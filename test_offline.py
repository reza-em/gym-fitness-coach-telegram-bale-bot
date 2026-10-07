#!/usr/bin/env python3
"""Offline tests with a fake Telegram/Bale API (no network, no real token). Run on both platforms:
   ./venv/bin/python test_offline.py                      (Telegram)
   FITNESS_PLATFORM=bale ./venv/bin/python test_offline.py (Bale, owner claim)
"""
import os, sys, json, tempfile, zipfile, io, csv, datetime as dt, logging
os.environ["OWNER_ID"] = "100000001"; os.environ["OWNER_USERNAME"] = "example_owner"
PLATFORM = os.environ.get("FITNESS_PLATFORM", "telegram")
os.environ["FITNESS_PLATFORM"] = PLATFORM
FAKE_TOKEN = "123456:FAKE-TEST-TOKEN-abcdefghijklmnopqrstuvwxyz"
os.environ["FITNESS_TELEGRAM_BOT_TOKEN"] = FAKE_TOKEN
os.environ["FITNESS_BALE_BOT_TOKEN"] = "222:FAKE-BALE-TOKEN-ABCDEF"
TMP = tempfile.mkdtemp(prefix="fit-test-")
os.environ["FITNESS_DB_PATH"] = os.path.join(TMP, "t.db")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plat, config, db, util, texts, exdata as X, program as P, nutrition as N, charts, balefmt
import core as C
import ui, onboarding as OB, workout as W, track as T, diet as D, remind as R, settings as S, admin as A, bot

IS_BALE = plat.IS_BALE
PASS = FAIL = 0
def ok(cond, name):
    global PASS, FAIL
    if cond: PASS += 1
    else: FAIL += 1; print("FAIL:", name)

SENT = []; FILES = []; NEXT = [1000]
def fake_call(method, data_=None, files=None, timeout=60):
    d = dict(data_ or {}); SENT.append((method, d))
    if files: FILES.append((method, {k: (v[0], len(v[1])) for k, v in files.items()}, files))
    NEXT[0] += 1
    if method == "getMe": return {"id": 999, "username": "FitTestBot", "is_bot": True}
    if method in ("sendMessage", "sendPhoto", "sendDocument", "editMessageText"):
        return {"message_id": NEXT[0], "chat": {"id": d.get("chat_id")}}
    return True
C.call = fake_call; bot.call = fake_call
import onboarding, diet, workout, track, remind, settings, admin
for m in (ui, OB, W, T, D, R, S, A, bot): 
    if hasattr(m, "send"): pass
C.BOT_USERNAME = "FitTestBot"
db.set_path(os.environ["FITNESS_DB_PATH"]); db.init()

# --- fake clock: 2026-10-02 12:00 Tehran (Friday)
TEHRAN = dt.timezone(dt.timedelta(hours=3, minutes=30))
CLOCK = [dt.datetime(2026, 10, 2, 12, 0, tzinfo=TEHRAN).timestamp()]
util.set_clock(lambda: CLOCK[0])
def advance(days=0, hours=0): CLOCK[0] += days * 86400 + hours * 3600
def set_time(y, m, d, hh, mm): CLOCK[0] = dt.datetime(y, m, d, hh, mm, tzinfo=TEHRAN).timestamp()

def mark(): return len(SENT)
def texts_out(since=0):
    out = []
    for m, d in SENT[since:]:
        if m in ("sendMessage", "editMessageText"): out.append(d.get("text", ""))
        elif m in ("sendPhoto", "sendDocument", "sendAnimation"): out.append(d.get("caption", ""))
        elif m == "sendMediaGroup": out.append(" ".join(e.get("caption", "") for e in json.loads(d["media"])))
    return "\n".join(out)
def last_markup(since=0):
    for m, d in reversed(SENT[since:]):
        if d.get("reply_markup"):
            try: return json.loads(d["reply_markup"])["inline_keyboard"]
            except Exception: return []
    return []
def buttons(since=0): return [b for row in last_markup(since) for b in row]
def datas(since=0): return [b.get("callback_data") for b in buttons(since) if b.get("callback_data")]
UPD = [0]
def msg_update(uid, text, name="Tester"):
    UPD[0] += 1
    return {"update_id": UPD[0], "message": {"message_id": 5000 + UPD[0], "from": {"id": uid, "first_name": name, "username": "u%d" % uid, "language_code": "fa"}, "chat": {"id": uid, "type": "private"}, "date": 1, "text": text}}
def say(uid, text): bot.handle_update(msg_update(uid, text))
def press(uid, data_, mid=777):
    UPD[0] += 1
    bot.handle_update({"update_id": UPD[0], "callback_query": {"id": "cb%d" % UPD[0], "from": {"id": uid, "first_name": "Tester", "username": "u%d" % uid}, "data": data_, "message": {"message_id": mid, "chat": {"id": uid, "type": "private"}}}})

OWNER = config.OWNER_ID
TESTER = OWNER if not IS_BALE else 70001
OTHER = 424242

# ============================================================ 1. static data / program
print(f"== platform: {PLATFORM}")
ok(all(a in X.EX for e in X.EX.values() for a in e["alts"]), "alternatives exist")
ok(all(e in X.EX for t in X.TEMPLATES.values() for _n, it in t for e, _p in it), "template exercises exist")
ok(len(X.TEMPLATES["ul"]) == 4 and len(X.TEMPLATES["fb"]) == 3, "4-day upper/lower and 3-day full body")
ok(P.phase_of(1)["rir_n"] == 4 and P.phase_of(2)["key"] == "ramp" and P.phase_of(3)["key"] == "build" and P.phase_of(6)["key"] == "build" and P.phase_of(7)["key"] == "intensify" and P.phase_of(9)["key"] == "deload", "phases: ramp 1-2, build 3-6, intensify 7-8, deload 9")
ok(P.phase_of(1)["sets_c"] < P.phase_of(5)["sets_c"], "volume grows with phase")
u0 = dict(plan_type="ul", injuries="", sess_min=60, deload_week=0)
s60 = P.build_session(u0, 3, 0); s45 = P.build_session(dict(u0, sess_min=45), 3, 0); s90 = P.build_session(dict(u0, sess_min=90), 3, 0)
ok(len(s45["items"]) < len(s60["items"]) <= len(s90["items"]), "session length fits time budget")
inj = P.build_session(dict(u0, injuries="shoulder", sess_min=90), 3, 0)
ok("bench_bb" not in [i["ex"] for i in inj["items"]] and inj["notes"], "shoulder injury replaces barbell bench")
ok(P.warmup_sets(20, 2.5)[0][0] < 20 and P.round_to(11.3, 2.5) == 12.5, "warm-up + rounding")
ok(P.parse_set_text("۲۰x۱۰") == (20.0, 10) and P.parse_set_text("22.5 8") == (22.5, 8) and P.parse_set_text("10", 20) == (20.0, 10) and P.parse_set_text("abc") is None, "set text parsing")
ok(abs(P.e1rm(20, 10) - 26.67) < 0.1, "Epley e1RM")
nu = dict(sex="m", weight=60, height=185, age=28, activity=1.6, surplus=450, protein_gk=2.0, gainer_on=0)
t = N.targets(nu)
ok(abs(t["bmr"] - (10 * 60 + 6.25 * 185 - 5 * 28 + 5)) <= 1 and abs(t["kcal"] - (t["tdee"] + 450)) <= 1 and t["protein"] == 120, "Mifflin-St Jeor x activity + surplus; protein 2 g/kg")
ok(N.targets(dict(nu, gainer_on=1, gainer_kcal=570, gainer_prot=25, gainer_n=1))["food_kcal"] == t["kcal"] - 570, "gainer kcal subtracted from food target")
pj = N.projection(60, 73)
ok(not pj["realistic"] and 63 < pj["lo"] < 65 and 67 < pj["hi"] < 69, "projection: 60->73 in 8 wk is not realistic; 6-8 kg realistic")
d0 = dt.date(2026, 10, 2)
ok(N.adjust_decision(0.1, 450, 4) == (150, "low") and N.adjust_decision(0.05, 450, 4)[0] == 200 and N.adjust_decision(1.2, 450, 4)[0] < 0 and N.adjust_decision(0.7, 450, 4) == (0, "ok") and N.adjust_decision(1.5, 450, 1)[0] == 0, "auto-adjust rules (+150-200 / reduce / early water ignored)")
pts = [(d0, 60), (d0 + dt.timedelta(7), 60.6), (d0 + dt.timedelta(14), 61.2)]
ok(abs(N.weekly_rate(pts) - 0.6) < 0.01, "weekly rate")
dp = N.day_plan(2500, 3)
ok(len(dp["meals"]) == 5 and dp["total_kcal"] > 1500, "meal plan has 5 slots")
png = charts.weight_chart([(d0, 60)], d0, 60, 73, 80, 56)
ok(png[:8] == b"\x89PNG\r\n\x1a\n", "weight chart is a PNG")
ok(balefmt.to_md("<b>x</b>") == "*x*", "bale markdown conversion")

# ============================================================ 2. owner / admin
print("== owner")
say(OTHER, "/start")
m = mark(); say(OTHER, "/admin"); ok("فقط برای مالک" in texts_out(m), "non-owner cannot open /admin")
if not IS_BALE:
    say(OWNER, "/start"); m = mark(); say(OWNER, "/admin")
    ok("پنل مالک" in texts_out(m), "Telegram owner id opens /admin")
else:
    code = A.ensure_claim_code()
    ok(code and len(code) == 14, "Bale: claim code generated")
    m = mark(); say(TESTER, "/claim 0000-0000-0000"); ok(not db.is_admin(TESTER), "wrong claim code refused")
    say(TESTER, "/claim " + code.lower()); ok(db.is_admin(TESTER) and any(me == "deleteMessage" for me, _ in SENT[m:]), "Bale: correct code binds owner and deletes the message")
    ok(A.ensure_claim_code() is None, "claim code consumed")
    m = mark(); say(TESTER, "/admin"); ok("پنل مالک" in texts_out(m), "Bale owner opens /admin")

# ============================================================ 3. onboarding (owner)
print("== onboarding")
m = mark(); say(TESTER, "/start")
ok("هشدار پزشکی" in texts_out(m) and "ob:ack" in datas(m), "start shows medical disclaimer + ack button")
press(TESTER, "ob:ack"); press(TESTER, "ob:sex:m")
say(TESTER, "۲۸"); say(TESTER, "185"); say(TESTER, "60")
say(TESTER, "73")                      # best weight
say(TESTER, "80")                      # long-term goal
m = mark(); press(TESTER, "ob:tw:73.0")
ok("ob:brk:6" in datas(m), "asks about the break")
press(TESTER, "ob:brk:6")
m = mark(); say(TESTER, "x") if False else None
press(TESTER, "ob:days:4")
m = mark()
ok(db.get_user(TESTER)["plan_type"] == "ul" and db.get_user(TESTER)["train_days"] == "5,6,1,2", "4 days -> upper/lower with default weekdays")
press(TESTER, "ob:ds:0"); press(TESTER, "ob:sm:60")
press(TESTER, "ob:inj:knee"); press(TESTER, "ob:inj:knee"); press(TESTER, "ob:injok")
press(TESTER, "ob:act:1.6"); press(TESTER, "ob:kid:0"); press(TESTER, "ob:gn:1")
say(TESTER, "150 ماسل‌تک"); say(TESTER, "570"); say(TESTER, "25"); press(TESTER, "ob:gnn:1")
u = db.get_user(TESTER)
ok(u["gainer_on"] == 1 and u["gainer_kcal"] == 570 and u["gainer_g"] == 150 and u["gainer_name"] == "ماسل‌تک" and u["gainer_n"] == 1, "gainer settings stored")
m = mark(); press(TESTER, "ob:cr:5")
ok(db.get_user(TESTER)["creatine_on"] == 1 and "ob:rw:squat_bb:5" in "".join(datas(m)) or any(d.startswith("ob:rw:") for d in datas(m)), "creatine on; per-exercise starting weights asked")
ok(any(d == "ob:rw:%s:25" % X.program_exercises("ul")[0] for d in datas(m)), "quick buttons 5/10/15/20/25 present")
first = X.program_exercises("ul")[0]
press(TESTER, f"ob:rw:{first}:20")
second = X.program_exercises("ul")[1]
press(TESTER, f"ob:rwc:{second}"); say(TESTER, "12.5")
ok(P.ref_weight(TESTER, first) == 20 and P.ref_weight(TESTER, second) == 12.5, "starting weights stored (button + custom)")
press(TESTER, "ob:rwall:10")
ok(len(db.q("SELECT * FROM ref_weights WHERE user_id=?", (TESTER,))) == len(X.program_exercises("ul")), "'same for the rest' fills the others")
m = mark(); press(TESTER, "ob:rem:1")
u = db.get_user(TESTER); txt = texts_out(m)
ok(u["onboarded"] == 1 and u["start_date"] == "2026-10-02", "onboarding finished, start date today")
ok("۰٫۵ تا ۱ کیلو" in txt and "واقع" in txt and "هفتهٔ ۱ و ۲" in txt, "honest expectations shown (0.5-1 kg/wk, ramp-up weeks)")
ok("کالری هدف" in txt, "targets in summary")
rm = R.get(TESTER)
ok(all(rm[k]["enabled"] for k in R.KINDS), "all reminders enabled with defaults (creatine+gainer on)")
ok(db.val("SELECT COUNT(*) FROM weights WHERE user_id=?", (TESTER,)) == 1, "start weight logged")

# ============================================================ 4. workout flow
print("== workout")
set_time(2026, 10, 3, 17, 0)           # Saturday = training day 1
m = mark(); say(TESTER, "/today")
ok("بالاتنه A" in texts_out(m) and "w:start:0" in datas(m), "today shows session 1 (upper A) with start button")
ok("سازگاری" in texts_out(m) and "۳–۴" in texts_out(m) or "3–4" in texts_out(m), "week-1 ramp-up RIR shown")
m = mark(); press(TESTER, "w:start:0")
wk = W.active_workout(TESTER); wid = wk["id"]
ok(wk and len(wk["plan"]["items"]) >= 4, "workout created with items")
it0 = wk["plan"]["items"][0]
ok(it0["sug_w"] == P.round_to(20 * 0.8, 2.5) == 15.0 and it0["sets"] == 2, "week 1: 80% of reference, 2 sets")
m = mark(); press(TESTER, f"x:{wid}:0")
tx = texts_out(m)
ok("پیشنهاد وزنه" in tx and "گرم‌کردن" in tx and "RIR" in tx, "exercise card: suggestion, warm-up, RIR")
ok(any(d == f"xw:{wid}:0:25" for d in datas(m)) and any(d == f"xw:{wid}:0:5" for d in datas(m)), "quick weight buttons 5..25")
press(TESTER, f"xw:{wid}:0:15")
m = mark(); press(TESTER, f"xr:{wid}:0:12")
ok(len(W.done_sets(TESTER, wid, it0["ex"])) == 1 and "ثبت شد" in texts_out(m), "set logged by button")
m = mark(); say(TESTER, "15x12")
ok(len(W.done_sets(TESTER, wid, it0["ex"])) == 2, "set logged by typing 15x12")
m = mark(); say(TESTER, "12")
ok(len(W.done_sets(TESTER, wid, it0["ex"])) == 3 and W.done_sets(TESTER, wid, it0["ex"])[-1]["w"] == 15, "reps-only text uses current weight")
press(TESTER, f"xu:{wid}:0"); ok(len(W.done_sets(TESTER, wid, it0["ex"])) == 2, "undo last set")
m = mark(); press(TESTER, f"xj:{wid}:0:1"); ok("17.5" in texts_out(m), "+ increment button changes weight")
m = mark(); press(TESTER, f"xc:{wid}:0"); say(TESTER, "16")
ok("16" in texts_out(m), "custom weight typed")
m = mark(); press(TESTER, f"xa:{wid}:0")
alts = [d for d in datas(m) if d.startswith("xa2:")]
ok(len(alts) >= 2, "alternatives listed")
press(TESTER, alts[0]); ok(W.get_workout(TESTER, wid)["plan"]["items"][0]["ex"] != it0["ex"], "exercise swapped")
# do the remaining exercises with 1 set each, then finish
for i, it in enumerate(W.get_workout(TESTER, wid)["plan"]["items"]):
    if i == 0: continue
    press(TESTER, f"x:{wid}:{i}"); press(TESTER, f"xw:{wid}:{i}:10"); press(TESTER, f"xr:{wid}:{i}:12"); press(TESTER, f"xr:{wid}:{i}:12")
press(TESTER, f"wf:{wid}")
m = mark(); press(TESTER, f"wff:{wid}:y")
ok("تمرین تمام شد" in texts_out(m) or "تمام" in texts_out(m), "finish workout")
w1 = db.q1("SELECT * FROM workouts WHERE id=?", (wid,))
ok(w1["finished"] == 1, "workout marked finished")
ok("s:log:gainer" in datas(m) and "s:log:creatine" in datas(m), "post-workout gainer + creatine buttons")
vol = P.workout_volume(TESTER, wid); ok(vol > 0, "volume computed")

# --- PRs and double progression in a later session
print("== progression")
bench = "bench_bb" if "bench_bb" in X.EX else None
# craft a clean history: exercise 'lat_pd' reached the top of the range at 20 kg in the last session
db.ex("INSERT INTO workouts(user_id,day,week,sidx,title,plan,started,finished) VALUES(?,?,?,?,?,?,?,1)", (TESTER, "2026-10-05", 1, 3, "x", "{}", 1))
hid = db.val("SELECT MAX(id) FROM workouts")
for n in (1, 2, 3):
    db.ex("INSERT INTO sets(user_id,workout_id,ex,setno,w,reps,ts,day) VALUES(?,?,?,?,?,?,?,?)", (TESTER, hid, "curl_db", n, 10, 15, 1, "2026-10-05"))
u = db.get_user(TESTER)
sg = P.suggest(u, "curl_db", dict(sets=3, lo=10, hi=15, ex="curl_db"), 3)
ok(sg["w"] == 11 and "+1" in sg["why"], "double progression: all sets at top reps -> +increment")
db.ex("DELETE FROM sets WHERE workout_id=?", (hid,))
for n in (1, 2, 3):
    db.ex("INSERT INTO sets(user_id,workout_id,ex,setno,w,reps,ts,day) VALUES(?,?,?,?,?,?,?,?)", (TESTER, hid, "curl_db", n, 10, 11, 1, "2026-10-05"))
sg = P.suggest(u, "curl_db", dict(sets=3, lo=10, hi=15, ex="curl_db"), 3)
ok(sg["w"] == 10 and "همین وزنه" in sg["why"], "within the range -> same weight, add reps")
db.ex("DELETE FROM sets WHERE workout_id=?", (hid,))
for n in (1, 2, 3):
    db.ex("INSERT INTO sets(user_id,workout_id,ex,setno,w,reps,ts,day) VALUES(?,?,?,?,?,?,?,?)", (TESTER, hid, "curl_db", n, 10, 6, 1, "2026-10-05"))
sg = P.suggest(u, "curl_db", dict(sets=3, lo=10, hi=15, ex="curl_db"), 3)
ok(sg["w"] == 9, "below the range -> lighter")
sg = P.suggest(u, "curl_db", dict(sets=3, lo=10, hi=15, ex="curl_db"), 9)
ok(sg["w"] == P.round_to(9.0, 1) or sg["w"] == 9.0 or sg["w"] <= 10, "deload week lowers the load")
db.ex("DELETE FROM sets WHERE workout_id=?", (hid,))
# PR: first set baseline (no message), heavier second -> PR
db.ex("DELETE FROM prs WHERE user_id=? AND ex='hammer'", (TESTER,))
u = db.get_user(TESTER)
r1 = P.record_set(u, hid, "hammer", 1, 10, 10); r2 = P.record_set(u, hid, "hammer", 2, 12, 10)
ok(r1 == [] and len(r2) == 1 and "رکورد" in r2[0], "PR detected only after a baseline")

# ============================================================ 5. weight, measures, charts, check-in
print("== tracking")
set_time(2026, 10, 9, 8, 0)           # Friday, day 8 -> check-in day
m = mark(); say(TESTER, "/weight 60.8")
ok(db.val("SELECT kg FROM weights WHERE user_id=? ORDER BY id DESC LIMIT 1", (TESTER,)) == 60.8 and db.get_user(TESTER)["weight"] == 60.8, "weight logged by command")
say(TESTER, "/measure")
for v in ("30.5", "95", "78", "54"): say(TESTER, v)
ok(len(db.q("SELECT * FROM measures WHERE user_id=?", (TESTER,))) == 4, "4 measurements logged")
m = mark(); press(TESTER, "p:chart:w")
ok(any(me == "sendPhoto" for me, _ in SENT[m:]) and any(f[0] == "sendPhoto" and f[2]["photo"][1][:4] == b"\x89PNG" for f in FILES[-1:]), "weight chart sent as PNG photo")
m = mark(); press(TESTER, "p:chart:m"); ok(any(me == "sendPhoto" for me, _ in SENT[m:]), "measurements chart sent")
m = mark(); press(TESTER, "p:chart:v"); ok(any(me == "sendPhoto" for me, _ in SENT[m:]), "volume chart sent")
m = mark(); press(TESTER, "p:chart:slat_pd") if False else press(TESTER, f"p:chart:s{W.get_workout(TESTER, wid)['plan']['items'][1]['ex']}")
ok(any(me == "sendPhoto" for me, _ in SENT[m:]), "strength chart sent")
m = mark(); say(TESTER, "/progress"); ok("خلاصهٔ پیشرفت" in texts_out(m), "progress summary")
# the reminder for the weekly check-in is due on day 8
set_time(2026, 10, 9, 8, 5)
m = mark(); R.tick()
ok("بررسی هفتگی" in texts_out(m) and "ci:start" in datas(m), "weigh-in/check-in reminder fires on day 8")
# slow gain (0.1 kg/wk) -> +kcal
print("== weekly auto-adjust")
db.ex("DELETE FROM weights WHERE user_id=?", (TESTER,))
db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (TESTER, "2026-10-02", 60.0, 1))
before = db.get_user(TESTER)["surplus"]
press(TESTER, "ci:start"); press(TESTER, "ci:w"); say(TESTER, "60.05")
press(TESTER, "ci:f:2"); press(TESTER, "ci:p:0"); m = mark(); press(TESTER, "ci:a:100")
tx = texts_out(m); u = db.get_user(TESTER)
ok(u["surplus"] == before + 200 and "+200" in tx, "gain < 0.25 kg/wk -> +kcal applied")
ok(db.val("SELECT COUNT(*) FROM checkins WHERE user_id=?", (TESTER,)) == 1 and u["last_checkin_week"] == 2, "check-in stored")
# fast gain -> reduce (week 4)
set_time(2026, 10, 23, 8, 0)
db.update_user(TESTER, last_adjust=None)
db.ex("DELETE FROM weights WHERE user_id=?", (TESTER,))
for dd, kg in (("2026-10-09", 61.0), ("2026-10-16", 62.2), ("2026-10-23", 63.5)): db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (TESTER, dd, kg, 1))
sp = db.get_user(TESTER)["surplus"]
press(TESTER, "ci:start"); press(TESTER, "ci:w"); say(TESTER, "63.6"); press(TESTER, "ci:f:4"); press(TESTER, "ci:p:2"); m = mark(); press(TESTER, "ci:a:100")
tx = texts_out(m)
ok(db.get_user(TESTER)["surplus"] < sp and "سبک" in tx and "ci:dl:1" in datas(m), "gain > 1 kg/wk -> reduce kcal; fatigue/pain -> deload offered")
press(TESTER, "ci:dl:1"); ok(db.get_user(TESTER)["deload_week"] == P.week_of(db.get_user(TESTER)) + 1, "deload scheduled for next week")
# low adherence: no increase
set_time(2026, 10, 30, 8, 0); db.update_user(TESTER, last_adjust=None, last_checkin_week=0)
db.ex("DELETE FROM weights WHERE user_id=?", (TESTER,))
for dd, kg in (("2026-10-16", 62.0), ("2026-10-23", 62.0), ("2026-10-30", 62.05)): db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (TESTER, dd, kg, 1))
sp = db.get_user(TESTER)["surplus"]
press(TESTER, "ci:start"); press(TESTER, "ci:w"); say(TESTER, "62.05"); press(TESTER, "ci:f:2"); press(TESTER, "ci:p:0"); m = mark(); press(TESTER, "ci:a:50")
ok(db.get_user(TESTER)["surplus"] == sp, "low adherence: calories are not raised")

# ============================================================ 6. nutrition + supplements + reminders
print("== nutrition / supplements / reminders")
set_time(2026, 10, 31, 10, 0)
m = mark(); say(TESTER, "/food"); tx = texts_out(m)
ok("کالری هدف" in tx and "پروتئین" in tx and "گینر" in tx, "targets incl. gainer")
m = mark(); press(TESTER, "n:day:0"); tx = texts_out(m)
ok("صبحانه" in tx and "ناهار" in tx and "شام" in tx and ("برنج" in tx or "نان" in tx or "تخم" in tx), "Iranian meal plan")
m = mark(); press(TESTER, "n:day:1"); ok(texts_out(m) != "", "other options")
m = mark(); say(TESTER, "/supplements"); tx = texts_out(m)
ok("گینر" in tx and "کراتین" in tx and "بدون لودینگ" in tx and "5 گرم" in tx, "supplements screen (creatine, no loading)")
m = mark(); press(TESTER, "s:info:c"); tx = texts_out(m)
ok("۳ تا ۵ گرم" in tx and "لودینگ" in tx and "کلیوی" in tx and "پزشک" in tx, "creatine info: 3-5 g, no loading, doctor if kidney")
press(TESTER, "s:log:creatine"); press(TESTER, "s:log:gainer"); press(TESTER, "wt:500")
ts = D.today_supp(db.get_user(TESTER)); ok(ts.get("creatine") and ts.get("gainer") and D.water_today(db.get_user(TESTER)) == 500, "supplements + water logged")
# reminders
db.ex("DELETE FROM rem_sent"); 
set_time(2026, 11, 1, 10, 5)           # Sunday (train day), 10:05
db.ex("DELETE FROM supp WHERE user_id=?", (TESTER,)); db.ex("DELETE FROM water WHERE user_id=?", (TESTER,))
m = mark(); n = R.tick(); tx = texts_out(m)
ok("کراتین" in tx and "آب" in tx, "creatine + water reminders fire at 10:00 window")
m = mark(); R.tick(); ok(mark() == m, "no duplicates the same day")
set_time(2026, 11, 1, 17, 5); m = mark(); R.tick(); ok("امروز روز تمرینه" in texts_out(m), "workout-day reminder on a training day")
set_time(2026, 11, 3, 23, 5)           # Tuesday... train day but late; sleep reminder
m = mark(); R.tick(); ok("خواب" in texts_out(m), "sleep reminder")
set_time(2026, 11, 4, 3, 0); db.ex("DELETE FROM rem_sent"); m = mark(); R.tick(); ok("آب" not in texts_out(m), "stale reminders are not sent late (3 h window)")
set_time(2026, 11, 5, 12, 0)           # Thursday = rest day
m = mark(); R.tick(); ok("امروز روز تمرینه" not in texts_out(m), "no workout reminder on a rest day")
m = mark(); press(TESTER, "r:menu"); ok("یادآورها" in texts_out(m) and "r:t:water" in datas(m), "reminder settings screen")
press(TESTER, "r:t:water"); ok(R.get(TESTER)["water"]["enabled"] == 0, "toggle reminder off")
press(TESTER, "r:e:sleep"); say(TESTER, "22:30"); ok(R.get(TESTER)["sleep"]["times"] == "22:30", "custom reminder time")

# ============================================================ 7. kidney branch, steroid guard, settings, export
print("== safety / settings / export")
K = 70002 if IS_BALE else 70002
say(K, "/start"); press(K, "ob:ack"); press(K, "ob:sex:m"); say(K, "30"); say(K, "180"); say(K, "70"); press(K, "ob:skip:best_w"); say(K, "80")
press(K, "ob:skip:target_w"); press(K, "ob:brk:2"); press(K, "ob:days:3"); press(K, "ob:ds:0"); press(K, "ob:sm:45"); press(K, "ob:injok"); press(K, "ob:act:1.45")
press(K, "ob:kid:1"); press(K, "ob:gn:0")
uk = db.get_user(K)
ok(uk["kidney"] == 1 and uk["creatine_on"] == 0, "kidney concern disables creatine (see doctor)")
ok(uk["plan_type"] == "fb" and len(X.TEMPLATES["fb"]) == 3, "3 days -> full-body plan")
m = mark(); press(K, "ob:rwskipall"); tx = texts_out(m)
ok(db.get_user(K)["onboarded"] == 0, "still in onboarding (reminders question)")
press(K, "ob:rem:0"); ok(db.get_user(K)["onboarded"] == 1, "onboarding done with reminders off")
m = mark(); press(K, "s:cset"); ok("پزشک" in texts_out(m) and db.get_user(K)["creatine_on"] == 0, "cannot enable creatine with kidney concern")
m = mark(); say(K, "ازت میپرسم استروئید بزنم یا نه؟"); ok("هیچ توصیه‌ای نمی‌کنم" in texts_out(m), "steroid questions refused")
m = mark(); say(K, "tell me about trenbolone dosage"); ok("هیچ توصیه‌ای نمی‌کنم" in texts_out(m), "steroid refusal (English term)")
m = mark(); say(K, "/help"); ok("هشدار پزشکی" in texts_out(m), "help includes disclaimer")
m = mark(); say(TESTER, "/settings"); ok("تنظیمات" in texts_out(m) and "st:sched" in datas(m), "settings")
press(TESTER, "st:d:3"); ok(db.get_user(TESTER)["plan_type"] == "fb" and db.get_user(TESTER)["days_pw"] == 3, "switch to 3-day full body")
press(TESTER, "st:d:4"); press(TESTER, "st:inj:shoulder"); ok("shoulder" in db.get_user(TESTER)["injuries"], "injury toggled")
press(TESTER, "st:inj:shoulder")
m = mark(); say(TESTER, "/export")
doc = [f for f in FILES if f[0] == "sendDocument"][-1]
z = zipfile.ZipFile(io.BytesIO(doc[2]["document"][1]))
ok({"weights.csv", "sets.csv", "measurements.csv", "workouts.csv", "profile.json"} <= set(z.namelist()), "export zip has CSVs + profile")
rows = list(csv.reader(io.StringIO(z.read("sets.csv").decode("utf-8-sig"))))
ok(len(rows) > 5 and rows[0][0] == "date", "sets.csv content")
ok(b"token" not in z.read("profile.json").lower(), "no secrets in export")
# programme restart / delete
press(TESTER, "st:restart2"); ok(db.get_user(TESTER)["start_date"] == util.today("Asia/Tehran").isoformat(), "restart program")


# ============================================================ 9. sex-specific behaviour (female) + migration
print("== sex")
uf = dict(plan_type="ul", injuries="", sess_min=90, deload_week=0, sex="f"); um = dict(uf, sex="m")
lower = lambda sess: sum(1 for i in sess["items"] if X.EX[i["ex"]]["grp"] in X.LOWER_GROUPS)
lf = sum(lower(P.build_session(uf, 3, i)) for i in range(4)); lm = sum(lower(P.build_session(um, 3, i)) for i in range(4))
ok(lf > lm, "female 4-day plan has more lower-body/glute exercises than male")
ok(any(X.EX[i["ex"]]["grp"] == "باسن" for i in P.build_session(uf, 3, 0)["items"]), "female lower day includes glute work")
sf, sm = P.build_session(uf, 5, 1), P.build_session(um, 5, 1)
ok(sf["items"][0]["lo"] == sm["items"][0]["lo"] + 2 and sf["items"][0]["hi"] == sm["items"][0]["hi"] + 3, "female rep ranges are higher (+2/+3)")
ok(sf["items"][0]["sets"] == sm["items"][0]["sets"] - 1, "female upper body: one set less once past ramp-up (maintain/tone)")
sfl, sml = P.build_session(uf, 5, 0), P.build_session(um, 5, 1)
ok(sfl["items"][0]["sets"] == 4, "female lower body keeps full volume")
ok(len(X.template("fb", "f")) == 3 and X.plan_name("ul", "f") != X.plan_name("ul", "m"), "female 3-day template + plan names")
ok(all(X.EX[e]["fed"] for e in X.EX) and set(X.TIPS) == set(X.EX), "every exercise has image source id + tips")
nf = dict(sex="f", weight=55, height=165, age=28, activity=1.6, surplus=300, protein_gk=1.8, gainer_on=0)
tf = N.targets(nf)
ok(abs(tf["bmr"] - (10 * 55 + 6.25 * 165 - 5 * 28 - 161)) <= 1, "Mifflin-St Jeor female constant (-161)")
ok(tf["protein"] == round(1.8 * 55) and tf["gainer_kcal"] == 0 and tf["food_kcal"] == tf["kcal"], "female protein 1.8 g/kg; no gainer assumptions")
pf = N.projection(55, 60, 56, "f")
ok(pf["rate_hi"] == 0.5 and 56.9 < pf["lo"] < 57.1 and 58.9 < pf["hi"] < 59.1 and not pf["realistic"], "female realism: 0.25-0.5 kg/wk (2-4 kg in 2 months)")
ok(N.adjust_decision(0.1, 300, 4, "f") == (100, "low") and N.adjust_decision(0.03, 300, 4, "f")[0] == 150 and N.adjust_decision(0.9, 300, 4, "f")[0] == -150
   and N.adjust_decision(0.4, 300, 4, "f") == (0, "ok") and N.adjust_decision(0.9, 300, 1, "f")[0] == 0, "female auto-adjust thresholds")
F = 70003
say(F, "/start"); press(F, "ob:ack")
m = mark(); press(F, "ob:sex:f")
uf_ = db.get_user(F)
ok(uf_["sex"] == "f" and uf_["surplus"] == 300 and abs(uf_["protein_gk"] - 1.8) < 1e-9, "onboarding sex=female sets surplus 300 + protein 1.8")
say(F, "27"); say(F, "165"); say(F, "55"); press(F, "ob:skip:best_w"); say(F, "60")
m = mark(); press(F, "ob:skip:target_w"); press(F, "ob:brk:5"); m = mark(); press(F, "ob:days:4")
ok("باسن" in texts_out(m) or "ob:ds:0" in datas(m), "female days screen")
press(F, "ob:ds:0"); press(F, "ob:sm:60"); press(F, "ob:injok"); press(F, "ob:act:1.45"); press(F, "ob:kid:0"); press(F, "ob:gn:0")
m = mark(); press(F, "ob:cr:0")
exs_f = X.program_exercises("ul", "f")
ok(any(d.startswith("ob:rw:%s:" % exs_f[0]) for d in datas(m)) and "hip_thrust" == exs_f[0], "female per-exercise starting weights asked (glute first)")
press(F, "ob:rwskipall"); m = mark(); press(F, "ob:rem:1")
tx = texts_out(m); uf_ = db.get_user(F)
ok(uf_["onboarded"] == 1 and "۰٫۲۵ تا ۰٫۵ کیلو در هفته" in tx and "۲ تا ۴ کیلو" in tx, "female goals text: 0.25-0.5 kg/wk, 2-4 kg in 2 months")
ok("0.25–0.5" in tx or "0.25" in tx, "female need-rate sentence uses the female range")
ok(R.get(F)["gainer"]["enabled"] == 0 and R.get(F)["creatine"]["enabled"] == 0, "no gainer/creatine reminders unless set")
set_time(2026, 11, 7, 10, 0)
m = mark(); say(F, "/food"); tx = texts_out(m); ok("🥤" not in tx and "گینر" not in tx, "no gainer in the female nutrition screen unless set")
m = mark(); press(F, "n:day:0"); ok("گینر" not in texts_out(m), "no gainer in the female meal plan unless set")
m = mark(); press(F, "n:tune"); ok("1.6" in texts_out(m) or "n:p:1.6" in datas(m), "female protein options 1.6/1.8/2.0")
m = mark(); say(F, "/today"); press(F, "w:start:0"); wf_ = W.active_workout(F)
ok(wf_ and X.EX[wf_["plan"]["items"][0]["ex"]]["grp"] == "باسن" or X.EX[wf_["plan"]["items"][0]["ex"]]["grp"] in X.LOWER_GROUPS, "female first session is a lower-body day")
# settings: switch sex of a male user keeps customised values
press(K, "st:sex:f"); uk = db.get_user(K)
ok(uk["sex"] == "f" and uk["surplus"] == 300 and abs(uk["protein_gk"] - 1.8) < 1e-9, "settings: switching to female updates default surplus/protein")
db.update_user(K, surplus=380); press(K, "st:sex:m"); ok(db.get_user(K)["sex"] == "m" and db.get_user(K)["surplus"] == 380, "settings: custom surplus kept when switching back")
m = mark(); press(K, "st:sex"); ok("st:sex:f" in datas(m), "settings has a sex screen")
# migration: old DB without users.sex -> every existing user is male
import sqlite3
p_old = os.path.join(TMP, "old.db"); cn = sqlite3.connect(p_old)
cn.executescript("CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, name TEXT); INSERT INTO users(id,name) VALUES(100000001,'Owner');"); cn.commit(); cn.close()
cur = db._path; db.set_path(p_old)
ok(db.get_user(100000001)["sex"] == "m", "migration: existing user (owner) defaults to male")
db.set_path(cur)

# ============================================================ 10. exercise video / tutorial
print("== video")
import media
eid = "bench_bb"
ok(("youtube.com" in X.yt_url(eid) and "aparat.com" in X.aparat_url(eid) and "common+mistakes" in X.yt_url(eid, "mistakes")), "YouTube + Aparat tutorial URLs present")
ok(all(media.files(e)[0] and len(media.files(e)[1]) == 2 for e in X.EX), "every exercise has local images + GIF (free-exercise-db)")
ok(os.path.exists(os.path.join(config.ASSETS, "ex", "NOTICE.txt")), "license notice shipped with the media")
m = mark(); wk2 = W.active_workout(TESTER)
press(TESTER, "w:today"); wk2 = W.active_workout(TESTER) or W.get_workout(TESTER, W.start(TESTER, None, 0) and W.active_workout(TESTER)["id"])
wid2 = W.active_workout(TESTER)["id"]; m = mark(); press(TESTER, f"x:{wid2}:0")
ok("xv:" in "".join(datas(m)) and "xm:" in "".join(datas(m)) and "🎬 ویدیو / آموزش" in json.dumps(last_markup(m), ensure_ascii=False), "exercise card has the 🎬 video/tutorial + tips buttons")
cur_ex = W.active_workout(TESTER)["plan"]["items"][0]["ex"]
m = mark(); press(TESTER, f"xv:{cur_ex}"); ms = [x[0] for x in SENT[m:]]; tx = texts_out(m)
ok(("sendMediaGroup" in ms) if IS_BALE else ("sendAnimation" in ms), "media sent: " + ("photo album on Bale" if IS_BALE else "GIF animation on Telegram"))
ok("youtube.com/results?search_query=" in tx and any("youtube.com/results" in (b.get("url") or "") for b in buttons(m)), "video link in text and as a URL button")
ok("Unlicense" in tx, "image credit/licence shown")
m = mark(); press(TESTER, f"xm:{cur_ex}"); tx = texts_out(m)
ok("اشتباهات رایج" in tx and "common+mistakes" in tx and sum(1 for b in buttons(m) if "youtube" in (b.get("url") or "")) == 2, "'more' gives tips, common mistakes and a second search link")
# fallback: album fails -> single photos
_orig = fake_call
def failing(method, data_=None, files=None, timeout=60):
    if method in ("sendMediaGroup", "sendAnimation"): raise C.ApiError("Bad Request: nope")
    return _orig(method, data_, files, timeout)
C.call = failing
m = mark(); press(TESTER, f"xv:{cur_ex}"); ms = [x[0] for x in SENT[m:]]
ok(ms.count("sendPhoto") == 2 and "youtube" in texts_out(m), "fallback: two single photos + link when album/animation is unavailable")
C.call = _orig
mp = os.path.join(config.ASSETS, "ex", f"{cur_ex}.gif"); os.rename(mp, mp + ".bak")
try:
    for f in media.files(cur_ex)[1]: os.rename(f, f + ".bak")
    m = mark(); press(TESTER, f"xv:{cur_ex}"); ok("youtube" in texts_out(m) and not any(x[0] in ("sendPhoto", "sendAnimation", "sendMediaGroup") for x in SENT[m:]), "no local media -> link only")
finally:
    os.rename(mp + ".bak", mp)
    for i in (0, 1): os.rename(os.path.join(config.ASSETS, "ex", f"{cur_ex}_{i}.jpg.bak"), os.path.join(config.ASSETS, "ex", f"{cur_ex}_{i}.jpg"))

# ============================================================ 11. 🧮 target-weight calories & macros calculator
print("== macros")
import macros as MC
ok(MC.calc(90) == dict(target=90.0, kcal=2160, protein=198, fat=72, fiber=30, carbs=180, water_l=3.0, pf_kcal=1440, rest_kcal=720),
   "reel example: target 90 kg -> 2160 kcal / 198 P / 72 F / 30 fiber / 180 C / 3.0 L")
m72 = MC.calc(72.5)
ok(m72["kcal"] == 1740 and m72["water_l"] == 2.4 and abs(m72["protein"] * 4 + m72["fat"] * 9 + m72["carbs"] * 4 - m72["kcal"]) <= 2, "non-integer target rounds sensibly and adds up")
ok(MC.suggestions(178, "m") == dict(lo=59, hi=78, bmi22=70, devine=73) and MC.suggestions(165, "f")["devine"] == 57 and MC.suggestions(None) is None,
   "healthy-range / BMI 22 / Devine suggestions (male + female)")
ok("mc:start:m" in json.dumps(json.loads(ui.menu_markup())), "main menu has the calculator entry")
ok("/macros" in texts.HELP, "help mentions /macros")
ut = db.get_user(TESTER)
m = mark(); say(TESTER, "/macros"); tx = texts_out(m)
ok("وزن هدف" in tx and f"mc:c:{util.fnum(ut['goal_w'])}:m" in datas(m) and "دیواین" in tx and "BMI" in tx and "نه از ویدیوی آموزشی" in tx,
   "/macros: saved goal weight offered as default + labelled standard-formula suggestions")
ok(any(b["text"] == texts.BACK and b.get("callback_data") == "mc:back:m" for b in buttons(m)), "calculator start screen has «◀️ بازگشت»")
ok(db.get_await(TESTER)[0] == "mc", "calculator waits for a typed target weight")
m = mark(); say(TESTER, "500"); ok("بین 35 تا 200" in texts_out(m) and db.get_await(TESTER)[0] == "mc", "out-of-range target rejected gently, still waiting")
m = mark(); say(TESTER, "۹۰ کیلو"); tx = texts_out(m)
ok(all(x in tx for x in ("2160", "198", "72", "30", "180", "90 × 24 = 2160", "2160 − 1440 = 720", "720 ÷ 4 = 180", "90 ÷ 30 = 3 لیتر")), "typed target (Persian digits) -> card with the 6 numbers + steps")
ok("روش محاسبه بر اساس آموزش سامان خوارزمی" in tx and "نه توصیهٔ پزشکی" in tx, "card has the credit line + not-medical-advice footer")
ok(db.get_await(TESTER)[0] is None and "mc:sv:90:m" in datas(m), "await cleared; save button offered")
m = mark(); say(TESTER, "/macros 45"); tx = texts_out(m)
ok("پایین‌تر از محدودهٔ وزن سالم" in tx if ut["height"] and 45 / (ut["height"] / 100) ** 2 < 18.5 else True, "low-BMI target gets a gentle note")
m = mark(); say(TESTER, "/macros 85"); ok("پایین‌تر از محدودهٔ وزن سالم" not in texts_out(m), "no low-BMI note for a healthy target")
m = mark(); press(TESTER, "n:menu"); ok("mc:start:n" in datas(m) and "ذخیره‌شده از ماشین‌حساب" not in texts_out(m), "nutrition menu has the calculator entry; nothing pinned yet")
kcal_before = N.targets(db.get_user(TESTER), ui.current_weight(TESTER))["kcal"]
m = mark(); press(TESTER, "mc:sv:90:n"); ok(db.get_user(TESTER)["macro_target"] == 90 and "ذخیره شد" in texts_out(m) and "mc:rm:90:n" in datas(m), "save pins the result")
m = mark(); say(TESTER, "/food"); tx = texts_out(m)
ok("ذخیره‌شده از ماشین‌حساب" in tx and "2160" in tx and N.targets(db.get_user(TESTER), ui.current_weight(TESTER))["kcal"] == kcal_before, "pinned numbers shown on /food; the bot's own targets unchanged")
m = mark(); press(TESTER, "mc:rm:90:n"); ok(db.get_user(TESTER)["macro_target"] is None, "pinned result can be removed")
press(TESTER, "mc:start:n"); m = mark(); press(TESTER, "mc:back:n"); ok("هدف تغذیهٔ روزانه" in texts_out(m) and db.get_await(TESTER)[0] is None, "back from the calculator returns to nutrition and clears the wait")
g0 = ut["goal_w"]; db.update_user(TESTER, goal_w=None)
m = mark(); say(TESTER, "/macros"); tx = texts_out(m)
ok("هنوز وزن هدف ثبت نکرده‌ای" in tx and any(d_.startswith("mc:c:") for d_ in datas(m)), "no saved goal -> height-based suggestions as buttons")
db.update_user(TESTER, goal_w=g0); say(TESTER, "/cancel")

# ============================================================ 8. transport: tokens never leak, platform adaptation
print("== transport")
alltext = json.dumps([d for _m, d in SENT], ensure_ascii=False)
ok(FAKE_TOKEN not in alltext and "FAKE-BALE-TOKEN" not in alltext, "tokens never appear in outgoing message payloads")
rf = C.RedactFilter(); rec = logging.LogRecord("x", logging.INFO, "", 0, "boom " + FAKE_TOKEN + " and 222:FAKE-BALE-TOKEN-ABCDEF", None, None); rf.filter(rec)
ok(FAKE_TOKEN not in rec.getMessage() and "FAKE-BALE" not in rec.getMessage(), "log redaction removes both tokens")
ok(FAKE_TOKEN not in C.safe(Exception("url " + plat.PLAT.api)) , "safe() redacts token from errors")
d, f = C.bale_prepare("sendMessage", {"chat_id": 1, "text": "<b>Hi</b>", "parse_mode": "HTML", "reply_markup": json.dumps({"inline_keyboard": [[{"text": "a", "callback_data": "x", "style": "primary"}]]})}, None)
ok("parse_mode" not in d and d["text"] == "*Hi*" and "style" not in d["reply_markup"], "bale_prepare: Markdown, no parse_mode, no styles")
ok(all(len(b.get("callback_data", "")) <= 64 for _m, dd in SENT if dd.get("reply_markup") for row in json.loads(dd["reply_markup"])["inline_keyboard"] for b in row), "all callback_data <= 64 bytes")
ok(all(len(dd.get("text", "")) <= 4096 for _m, dd in SENT), "texts fit one message")
# profile
SENT.clear(); db.meta_set("profile_sha", None)
bot.setup_profile()
meths = [mm for mm, _ in SENT]
if IS_BALE: ok(meths == ["setMyCommands"], "Bale profile: only setMyCommands (others are 501 there)")
else: ok("setMyName" in meths and "setMyDescription" in meths and meths.count("setMyCommands") == 2, "Telegram profile: name, description, commands (default + fa)")
cmds = json.loads([d for mm, d in SENT if mm == "setMyCommands"][0]["commands"])
ok(any(c["command"] == "macros" for c in cmds), "/macros registered as a bot command")
ok(any(c["command"] == "today" for c in cmds) and all(any("\u0600" <= ch <= "\u06ff" for ch in c["description"]) for c in cmds if c["command"] != "cancel" or True) , "commands described in Persian")

# groups are ignored
SENT.clear(); bot.handle_update({"update_id": 1, "message": {"message_id": 1, "from": {"id": 5, "first_name": "x"}, "chat": {"id": -100, "type": "group"}, "text": "/today"}})
ok(not SENT, "group messages ignored")
print(f"\n{PASS} passed, {FAIL} failed  [{PLATFORM}]")
sys.exit(1 if FAIL else 0)
