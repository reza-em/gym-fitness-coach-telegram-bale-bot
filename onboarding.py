"""Onboarding: disclaimer -> profile -> schedule -> injuries -> supplements -> per-exercise starting weights -> reminders -> summary."""
import json
import config, db, util, nutrition as N, program as P, exdata as X, texts
import core as C, ui
from core import btn, kb, send, show
from util import esc, fnum, grid

STEPS = ["sex", "age", "height", "weight", "best_w", "goal_w", "target_w", "brk", "days", "dayset", "sess", "inj", "act", "kid", "gainer", "gainer_g", "gainer_kcal", "gainer_prot", "gainer_n", "creatine", "refw", "remind", "done"]
NUM = {   # field: (prompt, lo, hi, is_int, optional)
 "age": ("🎂 سنت چند سال است؟ (فقط عدد، برای محاسبهٔ کالری)", 14, 80, True, False),
 "height": ("📏 قدت چند سانتی‌متر است؟ (مثلاً 185)", 120, 230, False, False),
 "weight": ("⚖️ وزن فعلی‌ات چند کیلو است؟ (مثلاً 60 یا 60.5)", 30, 250, False, False),
 "best_w": ("🏆 وزنِ «بهترین حالت»ت قبل از استراحت چقدر بود؟ (کیلو)", 30, 250, False, True),
 "goal_w": ("🎯 هدف بلندمدت وزنت چند کیلو است؟", 30, 250, False, False),
 "target_w": ("⏳ تا ۲ ماه دیگر می‌خوای به چه وزنی برسی؟ (مثلاً همان وزن بهترین)", 30, 250, False, True),
}

def start(uid, mid=None):
    u = ui.U(uid)
    if u["onboarded"]: return ui.show_menu(uid, mid)
    if not u["ack"]:
        return send(uid, texts.WELCOME, kb([[btn("✅ خواندم و قبول دارم؛ شروع", "ob:ack")]]))
    return goto(uid, resume_step(uid), mid)

def resume_step(uid):
    u = ui.U(uid)
    if not u["age"]: return "sex" if u["awaiting"] is None else "age"
    for f, step in (("height", "height"), ("weight", "weight"), ("goal_w", "best_w")):
        if not u[f]: return step
    return "brk" if u["break_months"] is None else "days"

def skip_step(uid, step):
    u = ui.U(uid)
    if step in ("gainer_g", "gainer_kcal", "gainer_prot", "gainer_n") and not u["gainer_on"]: return True
    if step == "creatine" and u["kidney"]: return True
    return False

def nxt(uid, step, mid=None):
    i = STEPS.index(step) + 1
    while i < len(STEPS) and skip_step(uid, STEPS[i]): i += 1
    return goto(uid, STEPS[i], mid)

def goto(uid, step, mid=None):
    u = ui.U(uid)
    if step in NUM:
        prompt, lo, hi, isint, opt = NUM[step]
        rows = []
        if step == "target_w" and u["best_w"]:
            rows.append([btn(f"همان {fnum(u['best_w'])} کیلو (بهترین وزنم)", f"ob:tw:{u['best_w']}")])
        if opt: rows.append([btn("ردکردن ⏭", f"ob:skip:{step}")])
        db.set_await(uid, "ob:" + step)
        return show(uid, mid, prompt, kb(rows) if rows else None)
    if step == "sex":
        return show(uid, mid, "اول چند سؤال برای ساخت برنامهٔ مخصوص خودت 👇\n\nجنسیت (برای فرمول کالری):", kb([[btn("مرد", "ob:sex:m"), btn("زن", "ob:sex:f")]]))
    if step == "brk":
        return show(uid, mid, "چقدر از تمرین منظم دور بودی؟ (برای شدت شروع)", kb([[btn("کمتر از ۱ ماه", "ob:brk:0"), btn("۱–۳ ماه", "ob:brk:2")], [btn("۳–۶ ماه", "ob:brk:5"), btn("۶ ماه یا بیشتر", "ob:brk:6")]]))
    if step == "days":
        fem = u["sex"] == "f"
        return show(uid, mid, "هفته‌ای چند روز می‌تونی بدنسازی بری؟\n\n"
                    + ("• <b>۴ روز</b> (پیشنهاد من): پایین‌تنه/بالاتنه با تأکید بیشتر روی باسن و پا، هر عضله ۲ بار در هفته.\n" if fem else "• <b>۴ روز</b> (پیشنهاد من): بالاتنه/پایین‌تنه، هر عضله ۲ بار در هفته با جلسه‌های کوتاه‌تر.\n")
                    + ("• <b>۳ روز</b>: تمام‌بدن با تأکید باسن و پا، اگر برنامه‌ات شلوغه یا ریکاوری کندتره.\n" if fem else "• <b>۳ روز</b>: تمام‌بدن، اگر برنامه‌ات شلوغه یا ریکاوری کندتره.\n") +
                    "اگر در ۲ هفتهٔ اول خیلی کوفته بودی، با ۳ روز شروع کن و بعد ۴ روز برو.",
                    kb([[btn("۴ روز ⭐ پیشنهادی", "ob:days:4"), btn("۳ روز", "ob:days:3")]]))
    if step == "dayset":
        n = u["days_pw"]; rows = [[btn(lbl, f"ob:ds:{k}")] for k, (lbl, _d) in enumerate(X.DAY_PRESETS[n])]
        rows.append([btn("✏️ روزها را خودم انتخاب می‌کنم", "ob:dsc")])
        return show(uid, mid, f"روزهای تمرینت؟ (انتخاب کن؛ بین جلسه‌ها استراحت بگذار)", kb(rows))
    if step == "sess":
        return show(uid, mid, "هر جلسه چند دقیقه وقت داری؟ (برنامه بر اساس این زمان کوتاه/بلند می‌شود)",
                    kb([[btn("۴۵", "ob:sm:45"), btn("۶۰", "ob:sm:60"), btn("۷۵", "ob:sm:75"), btn("۹۰", "ob:sm:90")]]))
    if step == "inj":
        return injuries_panel(uid, mid)
    if step == "act":
        return show(uid, mid, "سطح فعالیت روزمره‌ات (جدا از تمرین)؟", kb([[btn(v, f"ob:act:{k}")] for k, v in N.ACTIVITY.items()]))
    if step == "kid":
        return show(uid, mid, "برای کراتین و پروتئین بالا: مشکل کلیوی داری یا دارویی مصرف می‌کنی که کلیه را درگیر می‌کند؟",
                    kb([[btn("نه، ندارم", "ob:kid:0"), btn("بله / مطمئن نیستم", "ob:kid:1")]]))
    if step == "gainer":
        return show(uid, mid, "💊 گینر (مس گینر) داری؟", kb([[btn("بله دارم", "ob:gn:1"), btn("نه", "ob:gn:0")]]))
    if step in ("gainer_g", "gainer_kcal", "gainer_prot", "gainer_n"):
        import diet; return diet.gainer_step(uid, step, mid, ctx="ob")
    if step == "creatine":
        return show(uid, mid, "کراتین هم داری؟ روزانه چند گرم مصرف کنی؟ (دوز استاندارد ۳–۵ گرم، بدون لودینگ)",
                    kb([[btn("۳ گرم", "ob:cr:3"), btn("۴ گرم", "ob:cr:4"), btn("۵ گرم ⭐", "ob:cr:5")], [btn("ندارم / نمی‌خوام", "ob:cr:0")]]))
    if step == "refw":
        return refw_step(uid, mid)
    if step == "remind":
        return show(uid, mid, "⏰ یادآورها (تمرین، کراتین، گینر، آب، خواب، وزن‌کشی هفتگی) را با زمان‌های پیش‌فرض فعال کنم؟ بعداً در منوی یادآورها می‌تونی همه‌چیز را تغییر بدی.",
                    kb([[btn("✅ فعال کن", "ob:rem:1"), btn("بعداً", "ob:rem:0")]]))
    if step == "done":
        return finish(uid, mid)

def injuries_panel(uid, mid=None):
    u = ui.U(uid); cur = {x for x in u["injuries"].split(",") if x}
    rows = [[btn(("✅ " if k in cur else "▫️ ") + v, f"ob:inj:{k}")] for k, v in X.INJURIES.items()]
    rows.append([btn("هیچ‌کدام / تأیید ✔️", "ob:injok")])
    return show(uid, mid, "🩹 درد یا آسیب فعلی/قبلی داری؟ (چندتا را می‌شود انتخاب کرد؛ تمرین‌های ناجور حذف یا جایگزین می‌شوند)", kb(rows))

def train_days_panel(uid, mid=None):
    u = ui.U(uid); cur = set(P.train_days(u)); n = u["days_pw"]
    rows = [[btn(("✅ " if d in cur else "▫️ ") + util.WEEKDAYS[d], f"ob:dt:{d}")] for d in util.WEEK_ORDER]
    rows.append([btn(f"تأیید ({len(cur)}/{n}) ✔️", "ob:dsok")])
    return show(uid, mid, f"{n} روز را انتخاب کن:", kb(rows))

def refw_list(uid):
    u = ui.U(uid); return X.program_exercises(u["plan_type"], u["sex"])

def refw_step(uid, mid=None):
    u = ui.U(uid); exs = refw_list(uid)
    have = {r["ex"] for r in db.q("SELECT ex FROM ref_weights WHERE user_id=?", (uid,))}
    skipped = set((db.get_await(uid)[1] or {}).get("skipped", [])) if (db.get_await(uid)[0] or "").startswith("ob:refw") else set()
    todo = [e for e in exs if e not in have and e not in skipped]
    if not todo:
        return nxt(uid, "refw", mid)
    e = todo[0]; i = exs.index(e) + 1
    last = db.q1("SELECT w FROM ref_weights WHERE user_id=? ORDER BY rowid DESC LIMIT 1", (uid,))
    rows = [[btn(f"{w} کیلو", f"ob:rw:{e}:{w}") for w in config.WEIGHT_QUICK], [btn("✏️ عدد دیگر", f"ob:rwc:{e}"), btn("⏭ بعداً", f"ob:rwskip:{e}")]]
    if last and len(todo) > 1: rows.append([btn(f"بقیه را هم {fnum(last['w'])} کیلو بگذار", f"ob:rwall:{fnum(last['w'])}")])
    rows.append([btn("همه را بعداً (در اولین تمرین می‌پرسم) ⏭⏭", "ob:rwskipall")])
    db.set_await(uid, "ob:refw", {"skipped": sorted(skipped)})
    ex = X.EX[e]
    return show(uid, mid, f"🏋️ وزنهٔ شروع ({i}/{len(exs)}): <b>{ex['fa']}</b>\nآخرین وزنهٔ کاریِ تقریبیت قبل از استراحت چند کیلو بود؟ (برای دمبل: وزن هر دست). "
                f"این فقط نقطهٔ شروعه؛ هفتهٔ اول با ۸۰٪ همین عدد شروع می‌کنیم.", kb(rows))

def finish(uid, mid=None):
    u = ui.U(uid)
    today = util.today(u["tz"]).isoformat()
    with db.tx():
        db.update_user(uid, onboarded=1, start_date=today, start_w=u["weight"], awaiting=None, adata=None,
                       creatine_start=today if u["creatine_on"] else None)
        if not db.val("SELECT COUNT(*) FROM weights WHERE user_id=?", (uid,), 0):
            db.ex("INSERT INTO weights(user_id,day,kg,ts) VALUES(?,?,?,?)", (uid, today, u["weight"], util.now()))
    u = ui.U(uid)
    t = N.targets(u); pr = N.projection(u["weight"], u["target_w"], u["target_days"], u["sex"])
    wk = u["target_days"] // 7
    lines = [f"🎉 <b>برنامه‌ات آماده شد!</b> امروز روز اوله ({util.dlabel(util.today(u['tz']))})", "",
             f"📋 برنامه: {X.plan_name(u['plan_type'], u['sex'])} — روزها: {'، '.join(util.WEEKDAYS[d] for d in sorted(P.train_days(u), key=util.WEEK_ORDER.index))} — {u['sess_min']} دقیقه",
             f"🍽 کالری هدف: <b>{t['kcal']}</b> kcal | پروتئین {t['protein']} g | کربوهیدرات {t['carbs']} g | چربی {t['fat']} g",
             f"💧 آب: حدود {t['water_ml']/1000:.1f} لیتر در روز", ""]
    lines.append(expectation_text(u, pr, wk))
    lines.append("\n" + texts.expect_note(u["sex"]))
    if u["kidney"]: lines.append("\n⚠️ چون مشکل/نگرانی کلیوی گفتی، کراتین را برایت فعال نکردم؛ قبل از مصرف حتماً با پزشک صحبت کن.")
    return show(uid, mid, "\n".join(lines), kb([[btn("🏋️ تمرین امروز", "w:today")], [btn("🍽 برنامهٔ غذایی", "n:day"), btn("🏠 منو", "m:menu")]]))

def expectation_text(u, pr, wk):
    cur, tgt = u["weight"], u["target_w"]
    s = f"🎯 هدفت: {fnum(tgt)} کیلو در {wk} هفته (از {fnum(cur)}). "
    if tgt <= cur:
        return s + "هدفت پایین‌تر یا برابر وزن فعلیه؛ در تنظیمات می‌تونی هدف را عوض کنی."
    if pr["realistic"]:
        return s + f"لازمه ~{pr['need_rate']:.2f} کیلو در هفته، که در محدودهٔ واقع‌بینانه ({fnum(pr['rate_lo'], 2)}–{fnum(pr['rate_hi'], 2)}) است."
    return (s + f"لازمه ~{pr['need_rate']:.1f} کیلو در هفته که بیش از حد واقع‌بینانه است. با {fnum(pr['rate_lo'], 2)}–{fnum(pr['rate_hi'], 2)} کیلو در هفته در این {wk} هفته به حدود "
            f"<b>{fnum(pr['lo'])} تا {fnum(pr['hi'])} کیلو</b> می‌رسی و رسیدن به {fnum(tgt)} حدود <b>{pr['eta_lo']:.0f} تا {pr['eta_hi']:.0f} هفته</b> طول می‌کشد. "
            "این یعنی روی مسیر درستی، فقط سریع‌تر از این نمی‌شه بدون چربی زیاد.")

# ---------------------------------------------------------------- text answers
def on_text(uid, aw, d, text):
    step = aw[3:]
    back = d.get("back") if isinstance(d, dict) else None
    if step in NUM:
        prompt, lo, hi, isint, opt = NUM[step]
        v = util.parse_int(text, lo, hi) if isint else util.parse_num(text, lo, hi)
        if v is None:
            return send(uid, f"عدد معتبر نیست؛ یک عدد بین {lo} و {hi} بنویس.")
        db.update_user(uid, **{step: v})
        if step == "goal_w" and ui.U(uid)["best_w"] is None: pass
        return after_num(uid, step, back)
    if step == "refw_c":
        w = util.parse_num(text, 0.5, 400)
        if w is None: return send(uid, "یک عدد کیلوگرم بنویس (مثلاً 12.5).")
        P.set_ref(uid, d["ex"], w); return refw_step(uid)
    if step.startswith("gainer"):
        import diet; return diet.gainer_text(uid, step, text, d)
    return False

def after_num(uid, step, back=None):
    if back == "st":
        import settings; return settings.after_edit(uid, step)
    if step == "weight":
        db.update_user(uid, start_w=ui.U(uid)["weight"])
    if step == "best_w":
        u = ui.U(uid)
        if not u["target_w"]: db.update_user(uid, target_w=u["best_w"])
    return nxt(uid, step)

def callback(uid, mid, p):
    k = p[1]
    if k == "ack":
        db.update_user(uid, ack=1); return goto(uid, "sex", mid)
    if k == "gnn":
        import diet; return diet.gainer_set_n(uid, mid, int(p[2]), "st" if ui.U(uid)["onboarded"] else "ob")
    if ui.U(uid)["onboarded"] and k not in ("ack",): return
    if k == "sex":
        import settings; settings.apply_sex(uid, p[2]); return nxt(uid, "sex", mid)
    if k == "tw": db.update_user(uid, target_w=float(p[2])); return nxt(uid, "target_w", mid)
    if k == "skip":
        if p[2] == "target_w" and not ui.U(uid)["target_w"]:
            u = ui.U(uid); db.update_user(uid, target_w=min(u["goal_w"], (u["best_w"] or u["goal_w"])))
        return nxt(uid, p[2], mid)
    if k == "brk": db.update_user(uid, break_months=int(p[2])); return nxt(uid, "brk", mid)
    if k == "days":
        n = int(p[2]); db.update_user(uid, days_pw=n, plan_type="ul" if n == 4 else "fb", train_days=",".join(map(str, X.DAY_PRESETS[n][0][1])))
        return nxt(uid, "days", mid)
    if k == "ds":
        u = ui.U(uid); db.update_user(uid, train_days=",".join(map(str, X.DAY_PRESETS[u["days_pw"]][int(p[2])][1]))); return nxt(uid, "dayset", mid)
    if k == "dsc":
        db.update_user(uid, train_days=""); return train_days_panel(uid, mid)
    if k == "dt":
        u = ui.U(uid); cur = set(P.train_days(u)); d = int(p[2])
        cur ^= {d}
        if len(cur) > u["days_pw"]: cur.discard(d)
        db.update_user(uid, train_days=",".join(map(str, sorted(cur)))); return train_days_panel(uid, mid)
    if k == "dsok":
        u = ui.U(uid)
        if len(P.train_days(u)) != u["days_pw"]: return send(uid, f"دقیقاً {u['days_pw']} روز انتخاب کن.")
        return nxt(uid, "dayset", mid)
    if k == "sm": db.update_user(uid, sess_min=int(p[2])); return nxt(uid, "sess", mid)
    if k == "inj":
        u = ui.U(uid); cur = {x for x in u["injuries"].split(",") if x}; cur ^= {p[2]}
        db.update_user(uid, injuries=",".join(sorted(cur))); return injuries_panel(uid, mid)
    if k == "injok": return nxt(uid, "inj", mid)
    if k == "act": db.update_user(uid, activity=float(p[2])); return nxt(uid, "act", mid)
    if k == "kid":
        db.update_user(uid, kidney=int(p[2]), creatine_on=0 if p[2] == "1" else ui.U(uid)["creatine_on"]); return nxt(uid, "kid", mid)
    if k == "gn":
        db.update_user(uid, gainer_on=int(p[2])); return nxt(uid, "gainer", mid)
    if k == "cr":
        g = int(p[2]); db.update_user(uid, creatine_on=1 if g else 0, creatine_g=g or 5); return nxt(uid, "creatine", mid)
    if k == "rw":
        P.set_ref(uid, p[2], float(p[3])); return refw_step(uid, mid)
    if k == "rwc":
        db.set_await(uid, "ob:refw_c", {"ex": p[2]}); return show(uid, mid, f"وزنهٔ شروع «{X.ex_name(p[2])}» را به کیلو بنویس:")
    if k == "rwskip":
        aw, d = db.get_await(uid); d = d or {}; d.setdefault("skipped", []).append(p[2]); db.set_await(uid, "ob:refw", d); return refw_step(uid, mid)
    if k == "rwall":
        w = float(p[2])
        have = {r["ex"] for r in db.q("SELECT ex FROM ref_weights WHERE user_id=?", (uid,))}
        for e in refw_list(uid):
            if e not in have: P.set_ref(uid, e, w)
        return refw_step(uid, mid)
    if k == "rwskipall": return nxt(uid, "refw", mid)
    if k == "rem":
        import remind
        if p[2] == "1": remind.defaults(uid, enable=True)
        else: remind.defaults(uid, enable=False)
        return nxt(uid, "remind", mid)
