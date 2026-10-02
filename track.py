"""Bodyweight + measurements, weekly check-in with auto-adjust, progress summary, charts, data export."""
import io, csv, json, zipfile, datetime as dt
import config, db, util, nutrition as N, program as P, exdata as X, charts
import core as C, ui
from core import btn, kb, send, show
from util import esc, fnum, sgn

MEAS = [("arm", "💪 دور بازو"), ("chest", "🫁 دور سینه"), ("waist", "📏 دور کمر"), ("thigh", "🦵 دور ران")]

# ---------------------------------------------------------------- weight
def menu(uid, mid=None):
    u = ui.U(uid); w = ui.current_weight(uid); pts = ui.weight_points(uid)
    lines = ["⚖️ <b>وزن و اندازه‌ها</b>", f"وزن فعلی: <b>{fnum(w)}</b> کیلو | شروع: {fnum(u['start_w'])} ({sgn(w - u['start_w'])})", f"هدف ۲ ماهه: {fnum(u['target_w'])} | بلندمدت: {fnum(u['goal_w'])}"]
    r = N.weekly_rate(pts)
    if r is not None: lines.append(f"روند اخیر: {sgn(r, 2)} کیلو در هفته")
    ms = []
    for k, lab in MEAS:
        x = db.q1("SELECT cm, day FROM measures WHERE user_id=? AND kind=? ORDER BY day DESC, id DESC LIMIT 1", (uid, k))
        if x: ms.append(f"{lab[2:]}: {fnum(x['cm'])}")
    if ms: lines.append("آخرین اندازه‌ها (سانتی‌متر): " + " | ".join(ms))
    return show(uid, mid, "\n".join(lines), kb([[btn("⚖️ ثبت وزن", "t:w"), btn("📏 ثبت اندازه‌ها", "t:m")], [btn("✅ بررسی هفتگی", "ci:start"), btn("📈 نمودار وزن", "p:chart:w")], ui.menu_row()]))

def weight_prompt(uid, mid=None, ctx=None):
    last = ui.current_weight(uid) or 60
    db.set_await(uid, "weigh", {"ctx": ctx})
    rows = [[btn(f"{fnum(last - 0.5)}", f"t:wl:{last - 0.5}"), btn(f"{fnum(last)}", f"t:wl:{last}"), btn(f"{fnum(last + 0.5)}", f"t:wl:{last + 0.5}"), btn(f"{fnum(last + 1)}", f"t:wl:{last + 1}")]]
    rows.append([btn("◀️ بازگشت", "t:menu")])
    return show(uid, mid, "⚖️ وزن امروزت را بنویس (کیلو، مثلاً 61.4) یا یکی از دکمه‌ها را بزن.\n<i>بهترین زمان: صبح، بعد از دستشویی و قبل از صبحانه.</i>", kb(rows))

def log_weight(uid, kg, mid=None, ctx=None):
    u = ui.U(uid); day = util.today(u["tz"]).isoformat()
    prev = db.q1("SELECT kg FROM weights WHERE user_id=? AND day<? ORDER BY day DESC, id DESC LIMIT 1", (uid, day))
    db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (uid, day, kg, util.now()))
    ui.sync_weight(uid); db.set_await(uid, None)
    if ctx == "ci":
        return ci_after_weight(uid, kg, mid)
    msg = f"✅ وزن {fnum(kg)} کیلو ثبت شد."
    if prev: msg += f" ({sgn(kg - prev['kg'])} نسبت به آخرین ثبت قبلی)"
    t = N.targets(ui.U(uid))
    msg += f"\nکالری هدف با این وزن: {t['kcal']} kcal"
    return show(uid, mid, msg, kb([[btn("📈 نمودار", "p:chart:w"), btn("⚖️ منو", "t:menu")]]))

# ---------------------------------------------------------------- measurements
def meas_start(uid, mid=None):
    return meas_ask(uid, mid, 0)

def meas_ask(uid, mid, i):
    if i >= len(MEAS):
        db.set_await(uid, None); return show(uid, mid, "✅ اندازه‌ها ثبت شد. هر ۲–۴ هفته یک‌بار کافیه.", kb([[btn("📈 نمودار اندازه‌ها", "p:chart:m"), btn("⚖️ منو", "t:menu")]]))
    k, lab = MEAS[i]; db.set_await(uid, "meas", {"i": i})
    last = db.q1("SELECT cm FROM measures WHERE user_id=? AND kind=? ORDER BY day DESC, id DESC LIMIT 1", (uid, k))
    return show(uid, mid, f"{lab} را به سانتی‌متر بنویس" + (f" (قبلی: {fnum(last['cm'])})" if last else "") + "\n<i>همیشه در یک نقطه و حالت ریلکس اندازه بگیر.</i>",
                kb([[btn("⏭ ردکردن", f"t:ms:{i + 1}"), btn("✖️ پایان", "t:menu")]]))

def on_text(uid, aw, d, text):
    if aw == "weigh":
        v = util.parse_num(text, 30, 250)
        if v is None: return send(uid, "وزن معتبر نیست؛ مثلاً 61.4 بنویس.")
        return log_weight(uid, v, ctx=d.get("ctx"))
    if aw == "meas":
        i = d["i"]; v = util.parse_num(text, 5, 250)
        if v is None: return send(uid, "عدد سانتی‌متر معتبر نیست (مثلاً 34.5).")
        db.ex("INSERT INTO measures(user_id,day,kind,cm,ts) VALUES(?,?,?,?,?)", (uid, util.today(ui.U(uid)["tz"]).isoformat(), MEAS[i][0], v, util.now()))
        return meas_ask(uid, None, i + 1)
    return False

# ---------------------------------------------------------------- weekly check-in
def ci_start(uid, mid=None):
    u = ui.U(uid); wk = P.week_of(u)
    return show(uid, mid, f"✅ <b>بررسی هفتگی</b> (هفتهٔ {wk})\nاول وزن امروزت را ثبت کن (صبح و ناشتا بهتره).", kb([[btn("⚖️ ثبت وزن", "ci:w")]]))

def ci_after_weight(uid, kg, mid=None):
    db.set_await(uid, "ci", {"kg": kg})
    return send(uid, f"وزن {fnum(kg)} ثبت شد ✅\nامروز/این هفته چقدر خسته یا کوفته‌ای؟ (۱ = سرحال، ۵ = خیلی خسته)", kb([[btn(str(i), f"ci:f:{i}") for i in range(1, 6)]]))

def ci_cb(uid, mid, p):
    k = p[1]
    if k == "start": return ci_start(uid, mid)
    if k == "w": return weight_prompt(uid, mid, ctx="ci")
    if k == "dl":
        u = ui.U(uid); wk = P.week_of(u)
        if p[2] == "1":
            db.update_user(uid, deload_week=wk + 1)
            return show(uid, mid, "🌿 باشه؛ هفتهٔ بعد را سبک (دیلود) می‌کنم: ست‌ها و وزنه‌ها کمتر.", kb([ui.menu_row()]))
        return show(uid, mid, "باشه، برنامه عادی ادامه دارد. اگر خستگی یا درد ادامه‌دار شد، دیلود را در /settings فعال کن.", kb([ui.menu_row()]))

    aw, d = db.get_await(uid)
    if aw != "ci": return ci_start(uid, mid)
    if k == "f":
        d["f"] = int(p[2]); db.set_await(uid, "ci", d)
        return show(uid, mid, "مفصل یا کمرت درد داشت؟", kb([[btn("نه", "ci:p:0"), btn("کمی کوفتگی عضله", "ci:p:1")], [btn("درد مفصل/تاندون", "ci:p:2")]]))
    if k == "p":
        d["p"] = int(p[2]); db.set_await(uid, "ci", d)
        return show(uid, mid, "این هفته چقدر طبق برنامهٔ غذایی (کالری هدف) خوردی؟", kb([[btn("≈ ۱۰۰٪", "ci:a:100"), btn("≈ ۷۵٪", "ci:a:75"), btn("≈ ۵۰٪ یا کمتر", "ci:a:50")]]))
    if k == "a":
        d["a"] = int(p[2]); return ci_result(uid, mid, d)
def ci_result(uid, mid, d):
    u = ui.U(uid); wk = P.week_of(u); pts = ui.weight_points(uid, 28)
    rate = N.weekly_rate(pts)
    delta, key = N.adjust_decision(rate, u["surplus"], wk, u["sex"])
    last_adj = u["last_adjust"] and util.parse_day(u["last_adjust"])
    today = util.today(u["tz"])
    lines = [f"📋 <b>نتیجهٔ بررسی هفتهٔ {wk}</b>", f"⚖️ وزن: {fnum(d['kg'])} کیلو (از شروع: {sgn(d['kg'] - u['start_w'])})"]
    if rate is not None: lines.append(f"📈 روند: {sgn(rate, 2)} کیلو در هفته (هدف سالم: {'۰٫۲۵ تا ۰٫۵' if u['sex'] == 'f' else '۰٫۵ تا ۱'})")
    adherence_low = d["a"] < 75
    applied = 0
    if adherence_low and key in ("low", "low_max"):
        lines.append(f"🍽 چون فقط ~{d['a']}٪ طبق برنامه خوردی، کالری را بالا نمی‌برم؛ اول سعی کن به همین هدف برسی (گینر + وعده‌های اضافه).")
    elif last_adj is not None and (today - last_adj).days < 6 and delta:
        lines.append("⏳ تنظیم کالری در ۶ روز گذشته انجام شده؛ صبر می‌کنیم اثرش دیده شود.")
    elif key == "need_data":
        lines.append("برای تنظیم کالری حداقل دو وزن‌کشی با فاصلهٔ ۴+ روز لازمه؛ هفتهٔ بعد دقیق‌تر می‌شه.")
    elif key == "ok":
        lines.append("✅ سرعت افزایش وزن ایده‌آله؛ کالری را تغییر نمی‌دهم.")
    elif key == "fast_early":
        lines.append("⚠️ سرعت بالاست، اما ۲ هفتهٔ اول کراتین و گلیکوژن آب نگه می‌دارند (۰٫۵ تا ۱٫۵ کیلو). فعلاً کالری را کم نمی‌کنم؛ هفته‌های بعد دوباره می‌سنجیم.")
    elif key in ("low", "high"):
        applied = delta
        db.update_user(uid, surplus=u["surplus"] + delta, last_adjust=today.isoformat())
        if delta > 0: lines.append(f"🔼 وزنت کند بالا رفت (زیر ۰٫۲۵ کیلو در هفته) ← کالری روزانه <b>+{delta}</b> kcal (مازاد جدید: {u['surplus'] + delta}).")
        else: lines.append(f"🔽 سرعت از ۱ کیلو در هفته بیشتر بود (چربی زیاد می‌گیری) ← کالری روزانه <b>{delta}</b> kcal.")
    elif key == "low_max":
        lines.append("مازاد به سقف رسیده؛ اگر باز هم وزنت بالا نرفت، با پزشک/متخصص تغذیه مشورت کن (خواب، استرس، بیماری، جذب).")
    elif key == "high_min":
        lines.append("مازاد از قبل کمه؛ ادامه بده و روند را زیر نظر بگیر.")
    t = N.targets(ui.U(uid))
    lines.append(f"🔥 کالری هدف فعلی: <b>{t['kcal']}</b> kcal | پروتئین {t['protein']} g")
    offer_dl = d["f"] >= 4 or d["p"] == 2 or P.phase_of(wk)["key"] == "intensify" and wk % 2 == 0
    if d["p"] == 2: lines.append("🩹 درد مفصل/تاندون را جدی بگیر: وزنه را سبک کن، حرکت دردناک را عوض کن؛ اگر ادامه داشت پیش پزشک/فیزیوتراپ برو.")
    if d["f"] >= 4: lines.append("😮‍💨 خستگی بالاست؛ خواب و غذا را چک کن.")
    pr = N.projection(d["kg"], u["target_w"], u["target_days"], u["sex"])
    left_days = max(0, u["target_days"] - (today - P.start_date(u)).days)
    if d["kg"] < u["target_w"]:
        r = rate if rate and rate > 0.1 else 0.75
        lines.append(f"🎯 تا {fnum(u['target_w'])} کیلو: {fnum(u['target_w'] - d['kg'])} کیلو مانده. با همین روند حدود {(u['target_w'] - d['kg']) / r:.0f} هفتهٔ دیگر؛ {left_days // 7} هفته تا مهلت ۲ ماهه مانده.")
    db.update_user(uid, last_checkin_week=wk)
    db.ex("INSERT INTO checkins(user_id,week,day,kg,fatigue,pain,adherence,rate,action,kcal_change,ts) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (uid, wk, today.isoformat(), d["kg"], d["f"], d["p"], d["a"], rate, key, applied, util.now()))
    db.set_await(uid, None)
    rows = []
    if offer_dl and u["deload_week"] != wk + 1: lines.append("\n🌿 پیشنهاد: هفتهٔ بعد را سبک (دیلود) کنیم؟"); rows.append([btn("🌿 بله، هفتهٔ بعد سبک", "ci:dl:1"), btn("نه، ادامه", "ci:dl:0")])
    rows.append([btn("📈 نمودار وزن", "p:chart:w"), btn("🏠 منو", "m:menu")])
    return show(uid, mid, "\n".join(lines), kb(rows))

# ---------------------------------------------------------------- progress summary + charts
def progress(uid, mid=None):
    u = ui.U(uid); wk = P.week_of(u); today = util.today(u["tz"]); w = ui.current_weight(uid)
    pts = ui.weight_points(uid); rate = N.weekly_rate(pts); rl, rh = config.rates(u["sex"])
    done = db.val("SELECT COUNT(*) FROM workouts WHERE user_id=? AND finished=1", (uid,), 0)
    planned = P.n_sessions(u) * (wk - 1) + sum(1 for i in range(P.n_sessions(u)))
    days_in = (today - P.start_date(u)).days
    sets_n = db.val("SELECT COUNT(*) FROM sets WHERE user_id=?", (uid,), 0); vol = db.val("SELECT SUM(w*reps) FROM sets WHERE user_id=?", (uid,), 0) or 0
    lines = [f"📊 <b>خلاصهٔ پیشرفت</b> — روز {days_in + 1}، هفتهٔ {wk}", "",
             f"⚖️ وزن: {fnum(u['start_w'])} ← <b>{fnum(w)}</b> کیلو ({sgn(w - u['start_w'])})" + (f" | روند: {sgn(rate, 2)} کیلو/هفته" if rate is not None else ""),
             f"🎯 ۲ ماهه ({fnum(u['target_w'])}): {util.bar((w - u['start_w']) / max(0.1, u['target_w'] - u['start_w']))} {max(0, min(100, round((w - u['start_w']) / max(0.1, u['target_w'] - u['start_w']) * 100)))}٪",
             f"🏁 بلندمدت ({fnum(u['goal_w'])}): {util.bar((w - u['start_w']) / max(0.1, u['goal_w'] - u['start_w']))}"]
    if w < u["target_w"]:
        r = rate if rate and rate > 0.1 else None
        if r: lines.append(f"⏳ با روند فعلی رسیدن به {fnum(u['target_w'])}: حدود {(u['target_w'] - w) / r:.0f} هفتهٔ دیگر (بازهٔ واقع‌بینانه {(u['target_w'] - w) / rh:.0f}–{(u['target_w'] - w) / rl:.0f} هفته)")
        else: lines.append(f"⏳ رسیدن به {fnum(u['target_w'])} با {fnum(rl, 2)}–{fnum(rh, 2)} کیلو در هفته: {(u['target_w'] - w) / rh:.0f} تا {(u['target_w'] - w) / rl:.0f} هفته")
    lines.append(f"\n🏋️ جلسه‌های انجام‌شده: {done} | ست‌ها: {sets_n} | حجم کل: {fnum(vol / 1000, 1)} تن")
    ms = []
    for k, lab in MEAS:
        rows = db.q("SELECT cm FROM measures WHERE user_id=? AND kind=? ORDER BY day, id", (uid, k))
        if len(rows) >= 2: ms.append(f"{lab[2:]}: {fnum(rows[0]['cm'])}←{fnum(rows[-1]['cm'])}")
        elif rows: ms.append(f"{lab[2:]}: {fnum(rows[0]['cm'])}")
    if ms: lines.append("📏 " + " | ".join(ms))
    prs = db.q("SELECT ex, val FROM prs WHERE user_id=? AND kind='e1rm' ORDER BY val DESC LIMIT 3", (uid,))
    if prs: lines.append("🏆 رکوردها: " + "، ".join(f"{X.ex_name(p['ex'])} {fnum(p['val'])}" for p in prs))
    ts = db.val("SELECT COUNT(DISTINCT day) FROM supp WHERE user_id=? AND kind='creatine' AND day>=?", (uid, (today - dt.timedelta(days=6)).isoformat()), 0)
    if u["creatine_on"]: lines.append(f"🧪 کراتین در ۷ روز اخیر: {ts}/7 روز")
    lines.append("\n" + ("✨ راه خوبی می‌روی!" if done else "هنوز تمرینی ثبت نشده؛ از «تمرین امروز» شروع کن."))
    return show(uid, mid, "\n".join(lines), kb([[btn("📈 وزن", "p:chart:w"), btn("📏 اندازه‌ها", "p:chart:m")], [btn("💪 قدرت", "p:str"), btn("📦 حجم هفتگی", "p:chart:v")], [btn("🏆 رکوردها", "p:prs"), btn("📦 خروجی داده", "p:export")], ui.menu_row()]))

def send_chart(uid, kind):
    u = ui.U(uid); today = util.today(u["tz"])
    if kind == "w":
        pts = ui.weight_points(uid)
        rl, rh = config.rates(u["sex"])
        png = charts.weight_chart(pts, P.start_date(u), u["start_w"] or (pts[0][1] if pts else u["weight"]), u["target_w"], u["goal_w"], u["target_days"], rl, rh)
        cap = f"📈 مسیر وزن — منطقهٔ سبز: {fnum(rl, 2)} تا {fnum(rh, 2)} کیلو در هفته"
    elif kind == "m":
        series = {k: [(util.parse_day(r["day"]), r["cm"]) for r in db.q("SELECT day, cm FROM measures WHERE user_id=? AND kind=? ORDER BY day, id", (uid, k))] for k, _ in MEAS}
        if not any(series.values()): return send(uid, "هنوز اندازه‌ای ثبت نشده. از «ثبت اندازه‌ها» شروع کن.", kb([[btn("📏 ثبت اندازه‌ها", "t:m")]]))
        png = charts.measures_chart(series); cap = "📏 اندازه‌ها (سانتی‌متر)"
    elif kind == "v":
        rows = db.q("SELECT w.week wk, SUM(s.w*s.reps) v FROM sets s JOIN workouts w ON w.id=s.workout_id WHERE s.user_id=? GROUP BY w.week ORDER BY w.week", (uid,))
        if not rows: return send(uid, "هنوز تمرینی ثبت نشده.")
        png = charts.volume_chart([(r["wk"], r["v"]) for r in rows]); cap = "📦 حجم تمرین هفتگی"
    else:
        eid = kind[1:]
        rows = db.q("SELECT day, MAX(w) mw, MAX(w*(1+MIN(reps,12)/30.0)) e FROM sets WHERE user_id=? AND ex=? GROUP BY day ORDER BY day", (uid, eid))
        if not rows: return send(uid, "برای این حرکت هنوز ستی ثبت نشده.")
        png = charts.strength_chart(eid, [(util.parse_day(r["day"]), r["mw"], r["e"]) for r in rows]); cap = f"💪 {X.ex_name(eid)}"
    r = C.send_photo(uid, png, cap)
    if r is None: send(uid, "ارسال تصویر نمودار انجام نشد؛ بعداً دوباره امتحان کن.")
    return send(uid, "نمودار دیگری می‌خواهی؟", kb([[btn("📊 پیشرفت", "p:menu"), btn("🏠 منو", "m:menu")]]))

def strength_menu(uid, mid=None):
    exs = db.q("SELECT ex, COUNT(*) n FROM sets WHERE user_id=? GROUP BY ex ORDER BY n DESC", (uid,))
    if not exs: return show(uid, mid, "هنوز ستی ثبت نشده.", kb([ui.menu_row()]))
    return show(uid, mid, "نمودار قدرت کدام حرکت؟", kb([[btn(X.ex_name(r["ex"]), f"p:chart:s{r['ex']}")] for r in exs[:12]] + [[btn("◀️ پیشرفت", "p:menu")]]))

# ---------------------------------------------------------------- export
def export_zip(uid):
    u = ui.U(uid); buf = io.BytesIO()
    def csv_text(header, rows):
        s = io.StringIO(); w = csv.writer(s); w.writerow(header); w.writerows(rows); return "\ufeff" + s.getvalue()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("weights.csv", csv_text(["date", "kg"], [(r["day"], r["kg"]) for r in db.q("SELECT day,kg FROM weights WHERE user_id=? ORDER BY day,id", (uid,))]))
        z.writestr("measurements.csv", csv_text(["date", "kind", "cm"], [(r["day"], r["kind"], r["cm"]) for r in db.q("SELECT day,kind,cm FROM measures WHERE user_id=? ORDER BY day,id", (uid,))]))
        z.writestr("workouts.csv", csv_text(["id", "date", "week", "session", "title", "finished"], [(r["id"], r["day"], r["week"], r["sidx"] + 1, r["title"], r["finished"]) for r in db.q("SELECT * FROM workouts WHERE user_id=? ORDER BY id", (uid,))]))
        z.writestr("sets.csv", csv_text(["date", "workout_id", "exercise", "exercise_fa", "set", "kg", "reps", "est_1rm"],
                   [(r["day"], r["workout_id"], r["ex"], X.ex_name(r["ex"]), r["setno"], r["w"], r["reps"], round(P.e1rm(r["w"], r["reps"]), 1)) for r in db.q("SELECT * FROM sets WHERE user_id=? ORDER BY id", (uid,))]))
        z.writestr("supplements.csv", csv_text(["date", "kind", "amount"], [(r["day"], r["kind"], r["amount"]) for r in db.q("SELECT day,kind,amount FROM supp WHERE user_id=? ORDER BY id", (uid,))]))
        z.writestr("water.csv", csv_text(["date", "ml"], [(r["day"], r["ml"]) for r in db.q("SELECT day,ml FROM water WHERE user_id=? ORDER BY id", (uid,))]))
        z.writestr("checkins.csv", csv_text(["date", "week", "kg", "fatigue", "pain", "adherence", "rate", "action", "kcal_change"],
                   [(r["day"], r["week"], r["kg"], r["fatigue"], r["pain"], r["adherence"], r["rate"], r["action"], r["kcal_change"]) for r in db.q("SELECT * FROM checkins WHERE user_id=? ORDER BY id", (uid,))]))
        prof = {k: u[k] for k in ("sex", "age", "height", "weight", "start_w", "best_w", "goal_w", "target_w", "days_pw", "plan_type", "train_days", "sess_min", "injuries", "activity", "surplus", "protein_gk", "gainer_name", "gainer_g", "gainer_kcal", "gainer_prot", "gainer_n", "creatine_g", "start_date")}
        z.writestr("profile.json", json.dumps(prof, ensure_ascii=False, indent=1))
    return buf.getvalue()

def export(uid):
    data = export_zip(uid)
    r = C.send_document(uid, f"fitness-export-{util.today(ui.U(uid)['tz']).isoformat()}.zip", data, "📦 همهٔ داده‌هایت (CSV + پروفایل)")
    if r is None: send(uid, "ارسال فایل انجام نشد؛ بعداً دوباره امتحان کن.")

def cb(uid, mid, p):
    k = p[0]
    if k == "t":
        if p[1] == "menu": db.set_await(uid, None); return menu(uid, mid)
        if p[1] == "w": return weight_prompt(uid, mid)
        if p[1] == "wl": return log_weight(uid, float(p[2]), mid, (db.get_await(uid)[1] or {}).get("ctx") if db.get_await(uid)[0] == "weigh" else None)
        if p[1] == "m": return meas_start(uid, mid)
        if p[1] == "ms": return meas_ask(uid, mid, int(p[2]))
    if k == "p":
        if p[1] == "menu": return progress(uid, mid)
        if p[1] == "chart": return send_chart(uid, p[2])
        if p[1] == "str": return strength_menu(uid, mid)
        if p[1] == "prs":
            import workout; return workout.prs_view(uid, mid)
        if p[1] == "export": return export(uid)
