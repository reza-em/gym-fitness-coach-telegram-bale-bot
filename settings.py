"""Settings: profile numbers, schedule, injuries, activity, time zone, restart program, delete data."""
import config, db, util, program as P, exdata as X, nutrition as N
import core as C, ui, onboarding as OB
from core import btn, kb, send, show
from util import fnum

def menu(uid, mid=None):
    u = ui.U(uid); db.set_await(uid, None)
    inj = "، ".join(X.INJURIES[k] for k in u["injuries"].split(",") if k) or "ندارد"
    txt = (f"⚙️ <b>تنظیمات</b>\n👤 {config.sx(u['sex'])['label']} | سن {u['age']} | قد {fnum(u['height'])} | وزن {fnum(u['weight'])}\n🎯 هدف ۲ ماهه {fnum(u['target_w'])} | بلندمدت {fnum(u['goal_w'])} | بهترین وزن {fnum(u['best_w'])}\n"
           f"📋 {X.plan_name(u['plan_type'], u['sex'])} | {u['sess_min']} دقیقه | روزها: {'، '.join(util.WEEKDAYS[d] for d in sorted(P.train_days(u), key=util.WEEK_ORDER.index))}\n🩹 محدودیت‌ها: {inj}\n"
           f"🔥 مازاد کالری +{u['surplus']} | پروتئین {u['protein_gk']:g} g/kg\n🕒 منطقهٔ زمانی: {u['tz']}")
    return show(uid, mid, txt, kb([
        [btn("🎯 هدف‌ها", "st:goals"), btn("🧍 قد/سن/وزن", "st:body")],
        [btn("⚧ جنسیت (فرمول کالری و برنامه)", "st:sex")],
        [btn("📋 روزها و مدت جلسه", "st:sched"), btn("🩹 آسیب‌ها", "st:inj")],
        [btn("🚶 سطح فعالیت", "st:act"), btn("🕒 منطقهٔ زمانی", "st:tz")],
        [btn("🌿 دیلود هفتهٔ بعد", "st:dl"), btn("📦 خروجی داده", "p:export")],
        [btn("🔁 شروع دوبارهٔ برنامه", "st:restart"), btn("🗑 حذف داده‌ها", "st:del")],
        [btn("⚠️ هشدار پزشکی", "st:disc"), btn("🏠 منو", "m:menu")]]))

def apply_sex(uid, sex):
    """Set the sex and the sex-specific defaults (starting surplus + protein) unless the user already customised them."""
    sex = "f" if sex == "f" else "m"; u = ui.U(uid); old = config.sx(u["sex"]); new = config.sx(sex)
    kw = dict(sex=sex)
    if int(u["surplus"]) == old["surplus"] or not u["onboarded"]: kw["surplus"] = new["surplus"]
    if abs(float(u["protein_gk"]) - old["protein"]) < 1e-9 or not u["onboarded"]: kw["protein_gk"] = new["protein"]
    db.update_user(uid, **kw)

def ask(uid, mid, field):
    prompt, lo, hi, isint, opt = OB.NUM[field]
    db.set_await(uid, "ob:" + field, {"back": "st"})
    return show(uid, mid, prompt, kb([[btn("◀️ لغو", "st:menu")]]))

def after_edit(uid, field):
    db.set_await(uid, None)
    if field == "weight":
        u = ui.U(uid); db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (uid, util.today(u["tz"]).isoformat(), u["weight"], util.now()))
    send(uid, "✅ ذخیره شد.")
    return menu(uid)

def cb(uid, mid, p):
    k = p[1]; u = ui.U(uid)
    if k == "menu": return menu(uid, mid)
    if k == "goals":
        return show(uid, mid, "کدام هدف را تغییر بدهم؟", kb([[btn(f"هدف ۲ ماهه ({fnum(u['target_w'])})", "st:f:target_w"), btn(f"بلندمدت ({fnum(u['goal_w'])})", "st:f:goal_w")], [btn(f"بهترین وزن ({fnum(u['best_w'])})", "st:f:best_w")], [btn("◀️", "st:menu")]]))
    if k == "body":
        return show(uid, mid, "کدام را تغییر بدهم؟", kb([[btn(f"سن ({u['age']})", "st:f:age"), btn(f"قد ({fnum(u['height'])})", "st:f:height"), btn(f"وزن ({fnum(u['weight'])})", "st:f:weight")], [btn("◀️", "st:menu")]]))
    if k == "f": return ask(uid, mid, p[2])
    if k == "sex":
        if len(p) > 2:
            apply_sex(uid, p[2])
            return show(uid, mid, "✅ ذخیره شد. کالری، پروتئین، سرعت واقع‌بینانهٔ افزایش وزن و قالب برنامه (تأکید باسن/پا برای خانم‌ها) بر اساس جنسیت به‌روز شد. "
                        "وزنهٔ حرکت‌های جدید را در اولین تمرین انتخاب می‌کنی.", kb([[btn("📅 برنامهٔ هفته", "w:week"), btn("◀️ تنظیمات", "st:menu")]]))
        return show(uid, mid, "جنسیت (برای فرمول کالری Mifflin-St Jeor، پروتئین، سرعت واقع‌بینانهٔ افزایش وزن و قالب برنامه):", kb([[btn("مرد", "st:sex:m"), btn("زن", "st:sex:f")], [btn("◀️", "st:menu")]]))
    if k == "sched":
        return show(uid, mid, "تغییر برنامه از «هفتهٔ جاری» اعمال می‌شود (تمرین‌های ثبت‌شده حفظ می‌شوند).",
                    kb([[btn("۴ روز (بالاتنه/پایین‌تنه)", "st:d:4"), btn("۳ روز (تمام‌بدن)", "st:d:3")], [btn("۴۵ دقیقه", "st:m:45"), btn("۶۰", "st:m:60"), btn("۷۵", "st:m:75"), btn("۹۰", "st:m:90")], [btn("◀️", "st:menu")]]))
    if k == "d":
        n = int(p[2]); db.update_user(uid, days_pw=n, plan_type="ul" if n == 4 else "fb", train_days=",".join(map(str, X.DAY_PRESETS[n][0][1])))
        return show(uid, mid, f"✅ برنامه {n} روزه شد؛ روزهای پیش‌فرض: {X.DAY_PRESETS[n][0][0]}. اگر خواستی روزها را عوض کنی:", kb([[btn(l, f"st:ds:{n}:{i}")] for i, (l, _d) in enumerate(X.DAY_PRESETS[n])] + [[btn("◀️", "st:menu")]]))
    if k == "ds":
        n, i = int(p[2]), int(p[3]); db.update_user(uid, train_days=",".join(map(str, X.DAY_PRESETS[n][i][1]))); return menu(uid, mid)
    if k == "m": db.update_user(uid, sess_min=int(p[2])); return menu(uid, mid)
    if k == "inj":
        cur = {x for x in u["injuries"].split(",") if x}
        if len(p) > 2 and p[2] != "ok":
            cur ^= {p[2]}; db.update_user(uid, injuries=",".join(sorted(cur)))
        if len(p) > 2 and p[2] == "ok": return menu(uid, mid)
        cur = {x for x in ui.U(uid)["injuries"].split(",") if x}
        rows = [[btn(("✅ " if kk in cur else "▫️ ") + v, f"st:inj:{kk}")] for kk, v in X.INJURIES.items()] + [[btn("تأیید ✔️", "st:inj:ok")]]
        return show(uid, mid, "🩹 محدودیت‌ها (حرکت‌های ناجور حذف/جایگزین می‌شوند):", kb(rows))
    if k == "act":
        if len(p) > 2: db.update_user(uid, activity=float(p[2])); return menu(uid, mid)
        return show(uid, mid, "سطح فعالیت روزمره:", kb([[btn(v, f"st:act:{kk}")] for kk, v in N.ACTIVITY.items()]))
    if k == "tz":
        if len(p) > 2: db.update_user(uid, tz=":".join(p[2:])); return menu(uid, mid)
        return show(uid, mid, "منطقهٔ زمانی:", kb([[btn(z, f"st:tz:{z}")] for z in config.TIMEZONES]))
    if k == "dl":
        wk = P.week_of(u); db.update_user(uid, deload_week=wk + 1)
        return show(uid, mid, f"🌿 هفتهٔ {wk + 1} سبک (دیلود) شد.", kb([[btn("◀️ تنظیمات", "st:menu")]]))
    if k == "restart":
        return show(uid, mid, "برنامه از «هفتهٔ ۱» (سازگاری) دوباره شروع شود؟ تاریخچهٔ وزنه‌ها و رکوردها حفظ می‌شود.", kb([[btn("✅ بله", "st:restart2"), btn("خیر", "st:menu")]]))
    if k == "restart2":
        db.update_user(uid, start_date=util.today(u["tz"]).isoformat(), deload_week=0, last_checkin_week=0); return menu(uid, mid)
    if k == "del":
        return show(uid, mid, "⚠️ همهٔ داده‌هایت (وزن، تمرین‌ها، رکوردها، تنظیمات) برای همیشه حذف می‌شود. اول خروجی بگیر!", kb([[btn("📦 خروجی بگیر", "p:export")], [btn("🗑 بله، همه را حذف کن", "st:del2"), btn("خیر", "st:menu")]]))
    if k == "del2":
        delete_user(uid); return show(uid, mid, "همهٔ داده‌هایت حذف شد. هر وقت خواستی /start بزن.")
    if k == "disc":
        import texts; return show(uid, mid, texts.DISCLAIMER, kb([[btn("◀️", "st:menu")]]))

def delete_user(uid):
    with db.tx():
        for t in ("ref_weights", "weights", "measures", "sets", "prs", "supp", "water", "reminders", "rem_sent", "checkins", "workouts"):
            db.ex(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        db.ex("DELETE FROM users WHERE id=?", (uid,))
