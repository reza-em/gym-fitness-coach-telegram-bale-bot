"""Daily workout view, set logging (weight x reps with quick buttons / typed input), double-progression suggestions, PRs, week view."""
import json, datetime as dt
import config, db, util, program as P, exdata as X, nutrition as N
import core as C, ui
from core import btn, kb, send, show
from util import esc, fnum, grid

# ---------------------------------------------------------------- helpers
def active_workout(uid):
    w = db.q1("SELECT * FROM workouts WHERE user_id=? AND finished=0 ORDER BY id DESC LIMIT 1", (uid,))
    if w: w["plan"] = json.loads(w["plan"])
    return w

def get_workout(uid, wid):
    w = db.q1("SELECT * FROM workouts WHERE id=? AND user_id=?", (wid, uid))
    if w: w["plan"] = json.loads(w["plan"])
    return w

def save_plan(w): db.ex("UPDATE workouts SET plan=? WHERE id=?", (json.dumps(w["plan"], ensure_ascii=False), w["id"]))

def done_sets(uid, wid, eid): return db.q("SELECT * FROM sets WHERE user_id=? AND workout_id=? AND ex=? ORDER BY setno", (uid, wid, eid))

def next_session_idx(u, week):
    done = {w["sidx"] for w in P.week_workouts_done(u, week)}
    for i in range(P.n_sessions(u)):
        if i not in done: return i
    return None

def rest_label(sec): return f"{sec // 60}:{sec % 60:02d} دقیقه" if sec >= 60 and sec % 60 else (f"{sec // 60} دقیقه" if sec >= 60 else f"{sec} ثانیه")

def item_line(it, w=None, done=None):
    nm = X.ex_name(it["ex"])
    s = f"{nm}: {it['sets']}×{it['lo']}–{it['hi']}"
    if done is not None: s = ("✅ " if done >= it["sets"] else (f"🔸{done}/{it['sets']} " if done else "▫️ ")) + s
    return s

# ---------------------------------------------------------------- today
def today(uid, mid=None):
    u = ui.U(uid)
    w = active_workout(uid)
    if w:
        return session_view(uid, mid, w, resumed=True)
    d = util.today(u["tz"]); week = P.week_of(u, d)
    sidx = next_session_idx(u, week)
    ph = P.phase_for_user(u, week)
    if sidx is None:
        nxt_week = week + 1; s, _e = P.week_range(u, nxt_week)
        return show(uid, mid, f"🎉 همهٔ جلسه‌های هفتهٔ {week} را انجام دادی! استراحت و غذا و خواب کافی = رشد.\nهفتهٔ بعد از {util.dlabel(s)} شروع می‌شود ({P.phase_for_user(u, nxt_week)['name']}).",
                    kb([[btn("📅 برنامه", "w:week"), btn("📊 پیشرفت", "p:menu")], ui.menu_row()]))
    sess = P.build_session(u, week, sidx)
    lines = [f"🏋️ <b>{sess['title']}</b> — جلسهٔ {sidx + 1} از {P.n_sessions(u)} (هفتهٔ {week})", f"📍 {ph['name']} | RIR هدف: {ph['rir']} | حدود {sess['minutes']} دقیقه"]
    if not P.is_train_day(u, d):
        lines.append("ℹ️ امروز طبق برنامه روز استراحته؛ ولی اگر آماده‌ای می‌توانی همین جلسه را بزنی.")
    lines.append("")
    for i, it in enumerate(sess["items"]): lines.append(f"{i + 1}. " + item_line(it))
    lines.append("")
    lines.append("🔥 گرم‌کردن عمومی ~۵–۸ دقیقه (دوچرخه/تردمیل + چرخش شانه و ران) + ست‌های گرم‌کن قبل از حرکت‌های سنگین (ربات خودش وزنه‌ها را می‌گوید).")
    lines.append(f"\n💡 {ph['note']}")
    for n in sess["notes"]: lines.append("🩹 " + n)
    if sess["dropped"]: lines.append("⏱ برای جا شدن در " + str(u["sess_min"]) + " دقیقه حذف شد: " + "، ".join(X.ex_name(e) for e in sess["dropped"] if e in X.EX))
    return show(uid, mid, "\n".join(lines), kb([[btn("▶️ شروع تمرین", f"w:start:{sidx}")], [btn("📅 برنامهٔ هفته", "w:week"), btn("🏠 منو", "m:menu")]]))

def start(uid, mid, sidx):
    u = ui.U(uid)
    if active_workout(uid): return today(uid, mid)
    d = util.today(u["tz"]); week = P.week_of(u, d)
    sess = P.build_session(u, week, sidx)
    items = sess["items"]
    for it in items:
        sg = P.suggest(u, it["ex"], it, week)
        it.update(sug_w=sg["w"], why=sg["why"], last=sg["last"], skipped=False)
    plan = dict(title=sess["title"], items=items, notes=sess["notes"], prs=[], phase=sess["phase"], rir=sess["rir"])
    wid = db.ex("INSERT INTO workouts(user_id,day,week,sidx,title,plan,started,deload) VALUES(?,?,?,?,?,?,?,?)",
                (uid, d.isoformat(), week, sidx, sess["title"], json.dumps(plan, ensure_ascii=False), util.now(), 1 if P.phase_for_user(u, week)["key"] == "deload" else 0)).lastrowid
    return session_view(uid, mid, get_workout(uid, wid))

# ---------------------------------------------------------------- session list
def session_view(uid, mid, w, resumed=False):
    u = ui.U(uid); plan = w["plan"]; rows = []; lines = [f"🏋️ <b>{plan['title']}</b>" + (" (ادامه)" if resumed else ""), f"{plan['phase']} | RIR {plan['rir']}", ""]
    total = 0
    for i, it in enumerate(plan["items"]):
        n = len(done_sets(uid, w["id"], it["ex"])); total += n
        mark = "⏭" if it.get("skipped") else ("✅" if n >= it["sets"] else (f"🔸{n}/{it['sets']}" if n else "▫️"))
        lines.append(f"{i + 1}. {mark} {X.ex_name(it['ex'])} — {it['sets']}×{it['lo']}–{it['hi']}")
        rows.append([btn(f"{mark} {i + 1}. {X.ex_name(it['ex'])}", f"x:{w['id']}:{i}")])
    lines.append(f"\nمجموع ست‌های ثبت‌شده: {total}")
    rows.append([btn("🏁 پایان تمرین", f"wf:{w['id']}"), btn("🏠 منو", "m:menu")])
    db.set_await(uid, None)
    return show(uid, mid, "\n".join(lines), kb(rows))

# ---------------------------------------------------------------- exercise card
def state(uid):
    aw, d = db.get_await(uid)
    return d if aw == "set" else {}

def card(uid, mid, w, i, show_howto=None, w_override=None, prefix=""):
    u = ui.U(uid); plan = w["plan"]; it = plan["items"][i]; eid = it["ex"]; ex = X.EX[eid]
    sets = done_sets(uid, w["id"], eid); n = len(sets)
    st = state(uid); cur_w = w_override if w_override is not None else (st.get("w") if st.get("wid") == w["id"] and st.get("i") == i else None)
    if cur_w is None:
        cur_w = sets[-1]["w"] if sets else it.get("sug_w")
    if show_howto is None: show_howto = (n == 0)
    db.set_await(uid, "set", {"wid": w["id"], "i": i, "w": cur_w})
    lines = ([prefix, ""] if prefix else []) + [f"🏋️ <b>{ex['fa']}</b> ({i + 1}/{len(plan['items'])}) — {ex['eq']}",
             f"🎯 {it['sets']} ست × {it['lo']}–{it['hi']} تکرار | RIR {it['rir']} | استراحت ≈ {rest_label(ex['rest'])}"]
    if it.get("sug_w") is not None:
        lines.append(f"💡 پیشنهاد وزنه: <b>{fnum(it['sug_w'])} کیلو</b> — {it['why']}")
    else:
        lines.append(f"💡 {it['why']}")
    if it.get("last"): lines.append(f"📜 دفعهٔ قبل: {it['last']}")
    if n == 0 and ex["kind"] == "c" and it.get("sug_w"):
        wu = P.warmup_sets(it["sug_w"], ex["inc"])
        if wu: lines.append("🔥 گرم‌کردن: " + "، ".join(f"{fnum(a)}×{b}" for a, b in wu) + " (استراحت کوتاه)")
    if show_howto: lines.append(f"\n📝 {ex['how']}")
    if sets:
        lines.append("\n✅ ست‌های ثبت‌شده:")
        for s in sets: lines.append(f"   {s['setno']}) {fnum(s['w'])} کیلو × {s['reps']}")
    complete = n >= it["sets"]
    lines.append(f"⚖️ وزنهٔ انتخاب‌شده: {fnum(cur_w) if cur_w is not None else '؟'} کیلو")
    if complete: lines.append(f"\n🎉 {it['sets']} ست کامل شد. برو حرکت بعدی (یا ست اضافه بزن).")
    else: lines.append(f"\nست {n + 1} از {it['sets']}: وزنه {fnum(cur_w) if cur_w is not None else '؟'} کیلو — تعداد تکرار را بزن یا بنویس (مثل <code>20x10</code>).")
    wid = w["id"]; inc = ex["inc"]
    rows = [[btn(f"➖ {fnum(inc)}", f"xj:{wid}:{i}:-1"), btn(f"{fnum(cur_w) if cur_w is not None else '؟'} کیلو ✏️", f"xc:{wid}:{i}"), btn(f"➕ {fnum(inc)}", f"xj:{wid}:{i}:1")],
            [btn(str(q), f"xw:{wid}:{i}:{q}") for q in config.WEIGHT_QUICK]]
    lo = max(1, it["lo"] - 3); reps = list(range(lo, min(30, it["hi"] + 3) + 1))[:12]
    rows += grid([btn(f"{r}", f"xr:{wid}:{i}:{r}") for r in reps], 6)
    rows.append([btn("↩️ حذف آخرین ست", f"xu:{wid}:{i}"), btn("ℹ️ آموزش", f"xh:{wid}:{i}"), btn("🔁 جایگزین", f"xa:{wid}:{i}")])
    rows.append([btn("🎬 ویدیو / آموزش", f"xv:{eid}"), btn("💡 نکات بیشتر", f"xm:{eid}")])
    nxt_i = i + 1 if i + 1 < len(plan["items"]) else None
    nav = [btn("📋 لیست", f"xl:{wid}")]
    if nxt_i is not None: nav.insert(0, btn("⏭ حرکت بعدی", f"x:{wid}:{nxt_i}"))
    else: nav.insert(0, btn("🏁 پایان تمرین", f"wf:{wid}"))
    rows.append(nav)
    return show(uid, mid, "\n".join(lines), kb(rows))

def _w(uid, wid):
    w = get_workout(uid, wid)
    return w if w and not w["finished"] else None

def log_set(uid, mid, wid, i, weight, reps):
    w = _w(uid, wid)
    if not w: return send(uid, "این تمرین بسته شده؛ از «تمرین امروز» ادامه بده.")
    u = ui.U(uid); it = w["plan"]["items"][i]; eid = it["ex"]
    if weight is None: return send(uid, "اول وزنه را انتخاب کن (دکمه‌های ۵ تا ۲۵ یا ➕/➖ یا ✏️).")
    n = len(done_sets(uid, wid, eid))
    if n >= 15: return send(uid, "تعداد ست‌های این حرکت زیاده؛ برو حرکت بعدی 🙂")
    msgs = P.record_set(u, wid, eid, n + 1, weight, reps)
    if msgs: w["plan"].setdefault("prs", []).extend(msgs); save_plan(w)
    hint = ""
    inc = X.EX[eid]["inc"]
    if reps >= it["hi"]: hint = f"\n⬆️ به سقف {it['hi']} رسیدی؛ اگر RIR هنوز بالای {it['rir']} بود، ست بعد را {fnum(inc)} کیلو سنگین‌تر بزن."
    elif reps < it["lo"]: hint = f"\n⬇️ زیر {it['lo']} تکرار بود؛ اگر سخت بود ست بعد را {fnum(inc)} کیلو سبک‌تر کن."
    if msgs: hint += "\n" + "\n".join(msgs)
    db.set_await(uid, "set", {"wid": wid, "i": i, "w": weight})
    pre = f"✅ ثبت شد: {fnum(weight)} × {reps}{hint}\n⏱ استراحت پیشنهادی: {rest_label(X.EX[eid]['rest'])}"
    return card(uid, mid, get_workout(uid, wid), i, show_howto=False, prefix=pre)

# ---------------------------------------------------------------- callbacks
def cb(uid, mid, p):
    k = p[0]
    if k == "w":
        if p[1] == "today": return today(uid, mid)
        if p[1] == "start": return start(uid, mid, int(p[2]))
        if p[1] == "week": return week_view(uid, mid, int(p[2]) if len(p) > 2 else None)
    wid = int(p[1]) if len(p) > 1 and p[1].isdigit() else None
    if k == "xl":
        w = _w(uid, wid); return session_view(uid, mid, w, True) if w else today(uid, mid)
    w = _w(uid, wid) if wid else None
    if k in ("x", "xj", "xw", "xr", "xc", "xu", "xh", "xa", "xa2", "wf", "wff") and not w:
        return send(uid, "این تمرین بسته شده؛ از «تمرین امروز» ادامه بده.")
    if k == "x": return card(uid, mid, w, int(p[2]))
    i = int(p[2]) if len(p) > 2 and p[2].isdigit() else 0
    if k == "xw": return card(uid, mid, w, i, w_override=float(p[3]), show_howto=False)
    if k == "xj":
        it = w["plan"]["items"][i]; inc = X.EX[it["ex"]]["inc"]; cur = state(uid).get("w")
        if cur is None: cur = it.get("sug_w") or 0
        return card(uid, mid, w, i, w_override=max(0, cur + int(p[3]) * inc), show_howto=False)
    if k == "xr":
        return log_set(uid, mid, wid, i, state(uid).get("w") if state(uid).get("wid") == wid and state(uid).get("i") == i else w["plan"]["items"][i].get("sug_w"), int(p[3]))
    if k == "xc":
        db.set_await(uid, "wcustom", {"wid": wid, "i": i}); return show(uid, mid, f"وزنهٔ «{X.ex_name(w['plan']['items'][i]['ex'])}» را به کیلو بنویس (مثلاً 22.5):")
    if k == "xh": return card(uid, mid, w, i, show_howto=True)
    if k == "xu":
        eid = w["plan"]["items"][i]["ex"]; last = db.q1("SELECT id FROM sets WHERE user_id=? AND workout_id=? AND ex=? ORDER BY id DESC LIMIT 1", (uid, wid, eid))
        if last:
            db.ex("DELETE FROM sets WHERE id=?", (last["id"],)); P.recompute_prs(uid, eid)
        return card(uid, mid, w, i, show_howto=False)
    if k == "xa":
        it = w["plan"]["items"][i]; alts = [a for a in X.EX[it["ex"]]["alts"] if a != it["ex"]]
        inj = {x for x in ui.U(uid)["injuries"].split(",") if x}
        alts = [a for a in alts if not (X.EX[a]["avoid"] & inj)] or alts
        rows = [[btn(X.ex_name(a), f"xa2:{wid}:{i}:{a}")] for a in alts] + [[btn("⏭ این حرکت را رد کن", f"xa2:{wid}:{i}:skip")], [btn("◀️ برگشت", f"x:{wid}:{i}")]]
        return show(uid, mid, f"جایگزین «{X.ex_name(it['ex'])}» (مثلاً دستگاه پر است یا درد داری):", kb(rows))
    if k == "xa2":
        it = w["plan"]["items"][i]; a = p[3]
        if a == "skip":
            it["skipped"] = True; save_plan(w); return session_view(uid, mid, get_workout(uid, wid), True)
        if a not in X.EX: return
        u = ui.U(uid); week = w["week"]; ph = P.phase_for_user(u, week)
        it["sets"], it["lo"], it["hi"] = P.item_scheme(u, ph, a); it["ex"] = a
        sg = P.suggest(u, a, it, week, wid)
        it.update(sug_w=sg["w"], why=sg["why"], last=sg["last"]); save_plan(w)
        db.set_await(uid, None); return card(uid, mid, get_workout(uid, wid), i)
    if k == "wf":
        total = sum(len(done_sets(uid, wid, it["ex"])) for it in w["plan"]["items"])
        planned = sum(it["sets"] for it in w["plan"]["items"] if not it.get("skipped"))
        if total == 0:
            return show(uid, mid, "هنوز هیچ ستی ثبت نکردی. تمرین را لغو کنم؟", kb([[btn("🗑 لغو تمرین", f"wff:{wid}:x"), btn("◀️ ادامه", f"xl:{wid}")]]))
        if total < planned:
            return show(uid, mid, f"{planned - total} ست از برنامه مانده. تمرین را همین‌جا تمام کنم؟", kb([[btn("🏁 بله، تمام", f"wff:{wid}:y"), btn("◀️ ادامه", f"xl:{wid}")]]))
        return finish(uid, mid, w)
    if k == "wff":
        if p[2] == "x":
            db.ex("DELETE FROM workouts WHERE id=?", (wid,)); db.set_await(uid, None); return show(uid, mid, "تمرین لغو شد.", kb([ui.menu_row()]))
        return finish(uid, mid, w)

def finish(uid, mid, w):
    u = ui.U(uid); wid = w["id"]
    total = db.val("SELECT COUNT(*) FROM sets WHERE workout_id=?", (wid,), 0)
    vol = P.workout_volume(uid, wid)
    db.ex("UPDATE workouts SET finished=1, finished_ts=? WHERE id=?", (util.now(), wid))
    db.set_await(uid, None)
    mins = max(1, (util.now() - (w["started"] or util.now())) // 60)
    lines = [f"🏁 <b>تمرین تمام شد!</b> {w['plan']['title']}", f"⏱ حدود {mins} دقیقه | {total} ست | حجم کل: {fnum(vol, 0)} کیلو"]
    prs = w["plan"].get("prs") or []
    if prs: lines += [""] + prs
    ts = __import__("diet").today_supp(ui.U(uid)); rows = []
    to_do = []
    if u["gainer_on"] and u["gainer_kcal"] and ts.get("gainer", (0, 0))[0] < u["gainer_n"]: to_do.append("گینر (۱ سروینگ، تا یک ساعت بعد از تمرین)"); rows.append(btn("✅ گینر خوردم", "s:log:gainer"))
    if u["creatine_on"] and N.creatine_ok(u) and not ts.get("creatine"): to_do.append(f"کراتین {fnum(u['creatine_g'])} گرم با آب"); rows.append(btn("✅ کراتین خوردم", "s:log:creatine"))
    lines.append("\n🍽 بعد از تمرین: یک وعدهٔ پروتئین + کربوهیدرات بخور" + (" و " + " و ".join(to_do) if to_do else "") + ". امشب خواب ۷–۹ ساعت 😴")
    week = w["week"]; nx = next_session_idx(ui.U(uid), week)
    kb_rows = ([rows] if rows else []) + [[btn("📊 پیشرفت", "p:menu"), btn("🏠 منو", "m:menu")]]
    return show(uid, mid, "\n".join(lines), kb(kb_rows))

# ---------------------------------------------------------------- typed input
def on_text(uid, aw, d, text):
    if aw == "wcustom":
        v = util.parse_num(text, 0, 500)
        if v is None: return send(uid, "یک عدد کیلوگرم بنویس (مثلاً 22.5).")
        w = _w(uid, d["wid"]); 
        if not w: return send(uid, "این تمرین بسته شده.")
        return card(uid, None, w, d["i"], w_override=v, show_howto=False)
    if aw == "set":
        w = _w(uid, d.get("wid"))
        if not w: db.set_await(uid, None); return False
        parsed = P.parse_set_text(text, d.get("w"))
        if not parsed:
            if util.parse_num(text, 0, 500) is not None and not d.get("w"):
                return card(uid, None, w, d["i"], w_override=util.parse_num(text), show_howto=False)
            return False
        wt, reps = parsed
        return log_set(uid, None, d["wid"], d["i"], wt, reps)
    return False

# ---------------------------------------------------------------- week view
def roadmap(u):
    return ("🗺 <b>نقشهٔ ۸ هفته</b>\n• هفتهٔ ۱–۲: سازگاری (RIR 3–4، وزنهٔ سبک، ست کم)\n• هفتهٔ ۳–۶: ساخت حجم (RIR 2–3 ← 1–2، افزایش تدریجی وزنه و ست)\n"
            "• هفتهٔ ۷–۸: تشدید (۶–۱۰ تکرار، وزنه‌های سنگین‌تر)\n• هفتهٔ ۹: هفتهٔ سبک (دیلود) و بعد دور بعدی با وزنه‌های بالاتر")

def week_view(uid, mid=None, week=None):
    u = ui.U(uid); cur = P.week_of(u); week = week or cur; week = max(1, week)
    s, e = P.week_range(u, week); ph = P.phase_for_user(u, week)
    done = {w["sidx"] for w in P.week_workouts_done(u, week)}
    lines = [f"📅 <b>هفتهٔ {week}</b> ({util.jdate(s)} تا {util.jdate(e)}){' ← این هفته' if week == cur else ''}", f"{ph['name']} | RIR {ph['rir']}",
             "روزها: " + "، ".join(util.WEEKDAYS[d] for d in sorted(P.train_days(u), key=util.WEEK_ORDER.index)), ""]
    for i in range(P.n_sessions(u)):
        sess = P.build_session(u, week, i)
        lines.append(("✅ " if i in done else "▫️ ") + f"<b>{sess['title']}</b> (~{sess['minutes']} دقیقه)")
        for it in sess["items"]: lines.append("   • " + item_line(it))
    if week == 9 or ph["key"] == "deload": lines.append("\n🌿 هفتهٔ سبک: حجم و شدت کمتر برای ریکاوری.")
    lines.append("\n" + roadmap(u))
    nav = []
    if week > 1: nav.append(btn("◀️ قبلی", f"w:week:{week - 1}"))
    nav.append(btn("بعدی ▶️", f"w:week:{week + 1}"))
    return show(uid, mid, "\n".join(lines), kb([nav, [btn("🏋️ تمرین امروز", "w:today"), btn("🏠 منو", "m:menu")]]))

def prs_view(uid, mid=None):
    rows = db.q("SELECT * FROM prs WHERE user_id=? AND kind='e1rm' ORDER BY val DESC", (uid,))
    if not rows: return show(uid, mid, "هنوز رکوردی ثبت نشده. اولین ست‌هایت مبنای مقایسه می‌شوند 💪", kb([ui.menu_row()]))
    mx = {r["ex"]: r for r in db.q("SELECT * FROM prs WHERE user_id=? AND kind='max_w'", (uid,))}
    lines = ["🏆 <b>رکوردهای من</b>", ""]
    for r in rows:
        m = mx.get(r["ex"]); lines.append(f"• {X.ex_name(r['ex'])}: ۱RM تخمینی {fnum(r['val'])} کیلو ({fnum(r['w'])}×{r['reps']}, {util.jdate(util.parse_day(r['day']))})" + (f" | سنگین‌ترین: {fnum(m['val'])}" if m else ""))
    return show(uid, mid, "\n".join(lines), kb([ui.menu_row()]))
