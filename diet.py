"""Nutrition (targets, Iranian meal plan), supplements (mass gainer + creatine) and water."""
import json
import config, db, util, nutrition as N, texts
import core as C, ui
from core import btn, kb, send, show
from util import esc, fnum

# ---------------------------------------------------------------- nutrition
def targets_text(u):
    t = N.targets(u, ui.current_weight(u["id"]))
    lines = [f"🍽 <b>هدف تغذیهٔ روزانه</b> (وزن {fnum(ui.current_weight(u['id']))} کیلو)",
             f"🔥 کالری هدف: <b>{t['kcal']}</b> kcal  (نگهداری ≈ {t['tdee']} + مازاد {u['surplus']})",
             f"🥩 پروتئین: <b>{t['protein']}</b> g ({u['protein_gk']:g} گرم به ازای هر کیلو؛ بازهٔ مناسب "+('۱٫۶–۲٫۰' if u['sex'] == 'f' else '۱٫۸–۲٫۲')+")",
             f"🍚 کربوهیدرات: {t['carbs']} g | 🥑 چربی: {t['fat']} g", f"💧 آب: حدود {t['water_ml']/1000:.1f} لیتر (روز تمرین نیم‌لیتر بیشتر)"]
    if u["gainer_on"] and u["gainer_kcal"]:
        lines.append(f"🥤 گینر ({int(u['gainer_n'])} بار در روز) ≈ {t['gainer_kcal']} kcal و {t['gainer_prot']} g پروتئین ← سهم غذای اصلی: {t['food_kcal']} kcal و {t['food_prot']} g پروتئین")
    import macros
    if macros.saved_line(u): lines.append(macros.saved_line(u))
    lines.append("\n<i>فرمول Mifflin-St Jeor × سطح فعالیت؛ عددها تخمینی‌اند و هر هفته بر اساس روند وزنت خودکار تنظیم می‌شوند.</i>")
    return "\n".join(lines)

def menu(uid, mid=None):
    u = ui.U(uid)
    return show(uid, mid, targets_text(u), kb([[btn("🍛 منوی پیشنهادی امروز", "n:day:0")], [btn("💊 گینر و کراتین", "s:menu"), btn("💧 آب", "wt:menu")],
                                                 [btn("🔧 تغییر مازاد/پروتئین", "n:tune")], [btn("🧮 ماشین‌حساب کالری و ماکرو", "mc:start:n")], ui.menu_row()]))

def day_text(u, k):
    t = N.targets(u, ui.current_weight(u["id"]))
    seed = util.today(u["tz"]).toordinal() + k
    pl = N.day_plan(t["food_kcal"], seed)
    train = util.today(u["tz"]).weekday() in [int(x) for x in u["train_days"].split(",") if x != ""]
    lines = [f"🍽 <b>منوی پیشنهادی</b> (هدف غذا: {t['food_kcal']} kcal، پروتئین {t['food_prot']} g)", ""]
    for label, m, budget in pl["meals"]:
        lines.append(f"{label} (~{budget} kcal)\n   {m['name']} — {m['kcal']} kcal، {m['prot']} g پروتئین")
    if u["gainer_on"] and u["gainer_kcal"]:
        lines.append(("\n🥤 گینر: بعد از تمرین (تا یک ساعت بعد)" if train else "\n🥤 گینر: بین وعده‌ها (مثلاً عصر)") + f" — {t['gainer_kcal']} kcal")
    lines.append(f"\nجمع غذا ≈ {pl['total_kcal']} kcal و {pl['total_prot']} g پروتئین" + (f" (+ گینر = {pl['total_kcal'] + t['gainer_kcal']} kcal)" if t["gainer_kcal"] else ""))
    if pl["extras"]:
        lines.append("برای رسیدن به هدف اضافه کن: " + "؛ ".join(f"{e} (+{kk})" for e, kk in pl["extras"]))
    elif pl["gap"] < -150:
        lines.append(f"این منو حدود {-pl['gap']} kcal بیشتر از هدفه؛ پرس‌ها را کمی کوچک‌تر بگیر یا یک میان‌وعده را حذف کن.")
    if t["food_prot"] and pl["total_prot"] < t["food_prot"] - 15:
        lines.append(f"پروتئین منو کمتر از هدفه؛ یک تخم‌مرغ/ماست/پنیر یا مرغ بیشتر اضافه کن (~{t['food_prot'] - pl['total_prot']} g کم است).")
    lines.append("\n<i>کالری‌ها تقریبی‌اند (±۱۵٪). می‌توانی هر غذا را با غذای هم‌ارزش ایرانی دیگر عوض کنی.</i>")
    return "\n".join(lines)

def day(uid, mid=None, k=0):
    u = ui.U(uid)
    return show(uid, mid, day_text(u, k), kb([[btn("🔄 گزینه‌های دیگر", f"n:day:{k + 1}")], [btn("🍽 هدف‌ها", "n:menu"), btn("🏠 منو", "m:menu")]]))

def tune(uid, mid=None):
    u = ui.U(uid); c = config.sx(u["sex"]); opts = c["protein_opts"]
    rng = "۲۵۰–۳۵۰" if u["sex"] == "f" else "۴۰۰–۵۰۰"
    return show(uid, mid, f"🔧 مازاد کالری فعلی: <b>+{u['surplus']}</b> kcal (بازهٔ پیشنهادی برای شروع {rng}؛ ربات هر هفته خودش تنظیم می‌کند).\nپروتئین: {u['protein_gk']:g} g/kg (بازهٔ مناسب {opts[0]:g}–{opts[-1]:g}).",
                kb([[btn("−50 مازاد", "n:s:-50"), btn("+50 مازاد", "n:s:50")], [btn(f"پروتئین {o:g}", f"n:p:{o:g}") for o in opts], [btn("◀️ تغذیه", "n:menu")]]))

def nutri_cb(uid, mid, p):
    k = p[1]
    if k == "menu": return menu(uid, mid)
    if k == "day": return day(uid, mid, int(p[2]) if len(p) > 2 else 0)
    if k == "tune": return tune(uid, mid)
    if k == "s":
        u = ui.U(uid); lo, hi = config.sx(u["sex"])["bounds"]; db.update_user(uid, surplus=max(lo, min(hi, u["surplus"] + int(p[2])))); return tune(uid, mid)
    if k == "p": db.update_user(uid, protein_gk=float(p[2])); return tune(uid, mid)

# ---------------------------------------------------------------- supplements
def today_supp(u):
    d = util.today(u["tz"]).isoformat()
    rows = db.q("SELECT kind, COUNT(*) n, SUM(amount) a FROM supp WHERE user_id=? AND day=? GROUP BY kind", (u["id"], d))
    return {r["kind"]: (r["n"], r["a"]) for r in rows}

def water_today(u):
    return db.val("SELECT SUM(ml) FROM water WHERE user_id=? AND day=?", (u["id"], util.today(u["tz"]).isoformat()), 0) or 0

def supp_menu(uid, mid=None):
    u = ui.U(uid); ts = today_supp(u); lines = ["💊 <b>مکمل‌ها</b>", ""]
    rows = []
    if u["gainer_on"] and u["gainer_kcal"]:
        n = int(ts.get("gainer", (0, 0))[0]); lines.append(f"🥤 {N.gainer_text(u)}\n   امروز: {n}/{int(u['gainer_n'])} بار " + ("✅" if n >= u['gainer_n'] else ""))
        rows.append([btn("✅ گینر خوردم", "s:log:gainer"), btn("⚙️ تنظیم گینر", "s:gset")])
    else:
        lines.append("🥤 گینر: تنظیم نشده."); rows.append([btn("➕ تنظیم گینر", "s:gset")])
    if not N.creatine_ok(u):
        lines.append("\n🧪 کراتین: به‌خاطر نگرانی کلیوی غیرفعال شد؛ قبل از مصرف با پزشک مشورت کن.")
    elif u["creatine_on"]:
        n = int(ts.get("creatine", (0, 0))[0]); lines.append(f"\n🧪 کراتین: روزی {fnum(u['creatine_g'])} گرم (بدون لودینگ، هر ساعت از روز با آب)؛ امروز: {'✅' if n else 'هنوز نه'}")
        rows.append([btn("✅ کراتین خوردم", "s:log:creatine"), btn("⚙️ دوز", "s:cset")])
    else:
        lines.append("\n🧪 کراتین: غیرفعال."); rows.append([btn("➕ فعال‌کردن کراتین", "s:cset")])
    w = water_today(u); tgt = N.targets(u)["water_ml"]
    lines.append(f"\n💧 آب امروز: {w} از {tgt} ml")
    rows.append([btn("💧 +250", "wt:250"), btn("💧 +500", "wt:500")])
    rows.append([btn("💡 پیشنهاد مکمل برای من", "s:rec")])
    rows.append([btn("ℹ️ گینر", "s:info:g"), btn("ℹ️ کراتین", "s:info:c")]); rows.append(ui.menu_row())
    return show(uid, mid, "\n".join(lines), kb(rows))

def log_supp(uid, kind, mid=None):
    u = ui.U(uid)
    if kind == "creatine" and not (u["creatine_on"] and N.creatine_ok(u)): return supp_menu(uid, mid)
    amt = u["creatine_g"] if kind == "creatine" else u["gainer_kcal"]
    db.ex("INSERT INTO supp(user_id,day,kind,amount,ts) VALUES(?,?,?,?,?)", (uid, util.today(u["tz"]).isoformat(), kind, amt, util.now()))
    return supp_menu(uid, mid)

def water_add(uid, ml, mid=None):
    u = ui.U(uid)
    db.ex("INSERT INTO water(user_id,day,ml,ts) VALUES(?,?,?,?)", (uid, util.today(u["tz"]).isoformat(), ml, util.now()))
    return supp_menu(uid, mid)

def supp_cb(uid, mid, p):
    k = p[1]
    if k == "menu": db.set_await(uid, None); return supp_menu(uid, mid)
    if k == "log": return log_supp(uid, p[2], mid)
    if k == "info": return show(uid, mid, texts.GAINER_INFO if p[2] == "g" else texts.CREATINE_INFO, kb([[btn("◀️ مکمل‌ها", "s:menu")]]))
    if k == "rec": return show(uid, mid, N.recommend_supplements(ui.U(uid)), kb([[btn("◀️ مکمل‌ها", "s:menu")]]))
    if k == "gset": return gainer_step(uid, "gainer_g", mid, ctx="st")
    if k == "gmilk": return supp_menu(uid, mid)
    if k == "cset":
        u = ui.U(uid)
        if u["kidney"]: return show(uid, mid, "به‌خاطر نگرانی کلیوی کراتین فعال نمی‌شود. اول با پزشک صحبت کن.", kb([[btn("◀️ مکمل‌ها", "s:menu")]]))
        return show(uid, mid, "دوز روزانهٔ کراتین مونوهیدرات (۳–۵ گرم، بدون لودینگ):", kb([[btn("۳ گرم", "s:c:3"), btn("۴ گرم", "s:c:4"), btn("۵ گرم", "s:c:5")], [btn("خاموش", "s:c:0")]]))
    if k == "c":
        g = int(p[2]); db.update_user(uid, creatine_on=1 if g else 0, creatine_g=g or 5, creatine_start=util.today(ui.U(uid)["tz"]).isoformat() if g and not ui.U(uid)["creatine_start"] else ui.U(uid)["creatine_start"])
        return supp_menu(uid, mid)

# ---- gainer setup (shared by onboarding ctx="ob" and supplements ctx="st")
def gainer_step(uid, step, mid=None, ctx="st"):
    if step == "gainer_g":
        db.update_user(uid, gainer_on=1)
        db.set_await(uid, "ob:gainer_g", {"ctx": ctx})
        return show(uid, mid, "🥤 روی برچسب قوطی، <b>هر بار مصرف</b> (یک اسکوپ) چند <b>گرم</b> است؟ مثلاً 150\nاگر خواستی اسم برند را هم بنویس: <code>150 ماسل‌تک</code>")
    if step == "gainer_kcal":
        db.set_await(uid, "ob:gainer_kcal", {"ctx": ctx}); return show(uid, mid, "همان یک اسکوپ چند <b>کیلوکالری</b> دارد؟ (روی برچسب Calories؛ مثلاً 570)")
    if step == "gainer_prot":
        db.set_await(uid, "ob:gainer_prot", {"ctx": ctx}); return show(uid, mid, "همان یک اسکوپ چند گرم <b>پروتئین</b> دارد؟ (مثلاً 25؛ اگر نمی‌دانی 0 بنویس)")
    if step == "gainer_n":
        return show(uid, mid, "روزی چند بار گینر می‌خوری؟ پیشنهاد: ۱ بار بعد از تمرین.",
                    kb([[btn("۱ بار در روز ⭐", f"ob:gnn:1"), btn("۲ بار در روز", f"ob:gnn:2")]]))

def gainer_text(uid, step, text, d):
    ctx = (d or {}).get("ctx", "st")
    if step == "gainer_g":
        parts = util.norm(text).split(None, 1)
        g = util.parse_num(parts[0], 10, 1000) if parts else None
        if g is None: return send(uid, "یک عدد گرم بنویس (مثلاً 150).")
        db.update_user(uid, gainer_g=g, gainer_name=(parts[1][:30] if len(parts) > 1 else None)); return gainer_step(uid, "gainer_kcal", ctx=ctx)
    if step == "gainer_kcal":
        v = util.parse_num(text, 50, 2000)
        if v is None: return send(uid, "یک عدد کیلوکالری بنویس (مثلاً 570).")
        db.update_user(uid, gainer_kcal=v); return gainer_step(uid, "gainer_prot", ctx=ctx)
    if step == "gainer_prot":
        v = util.parse_num(text, 0, 200)
        if v is None: return send(uid, "یک عدد گرم پروتئین بنویس (یا 0).")
        db.update_user(uid, gainer_prot=v); db.set_await(uid, None); return gainer_step(uid, "gainer_n", ctx=ctx)

def gainer_set_n(uid, mid, n, ctx):
    db.update_user(uid, gainer_n=n, gainer_on=1); db.set_await(uid, None)
    if ctx == "ob":
        import onboarding; return onboarding.nxt(uid, "gainer_amt", mid)
    return supp_menu(uid, mid)
