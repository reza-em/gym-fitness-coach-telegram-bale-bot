"""📂 Body-type program screens (Telegram + Bale): detected category (چاقی / لاغری / تناسب), the matching workout template,
cardio, nutrition (+ sample Iranian day), supplements, safety, tutorials and a manual category override.
Callback prefix: bt:  (data + classification live in programs_db.py)."""
import config, db, util, exdata as X, programs_db as PDB
import ui
from core import btn, kb, send, show
from util import fnum

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def fa(n): return str(n).translate(_FA)

def _ctx(uid):
    u = ui.U(uid); w = ui.current_weight(uid) or u.get("weight")
    inf = PDB.info(u, w); cat = inf["cat"] or "fit"
    return u, w, inf, cat

def header(u, w, inf, cat):
    L = ["📂 <b>برنامه بر اساس وضعیت بدنی</b>", f"وضعیت تو: {PDB.CAT_EMOJI[cat]} <b>{PDB.CAT_FA[cat]}</b> — {PDB.CAT_GOAL[cat]}"]
    if inf["bmi"] is not None:
        L.append(f"📏 BMI حدود <b>{inf['bmi']:.1f}</b> (قد {fnum(u['height'])} سانتی‌متر، وزن {fnum(w)} کیلو)")
    if inf["manual"]:
        a = inf["auto"]
        L.append("✋ این وضعیت را خودت انتخاب کرده‌ای" + (f" (تشخیص خودکار: {PDB.CAT_FA[a]}، چون {inf['reason']})." if a else "."))
    elif inf["auto"]:
        L.append(f"🤖 تشخیص خودکار: {inf['reason']}.")
    else:
        L.append("🤖 قد یا وزنت ثبت نشده؛ فعلاً برنامهٔ «تناسب» نشان داده می‌شود. از ⚙️ تنظیمات قد و وزن را وارد کن.")
    g = u.get("goal_w")
    if g:
        L.append(f"🎯 هدف بلندمدت: {fnum(g)} کیلو")
        if w and cat == "fat" and float(g) > float(w) + 1:
            L.append("ℹ️ هدفت افزایش وزن است ولی BMI بالای ۲۵ است. BMI عضله و چربی را از هم جدا نمی‌کند؛ اگر عضلانی هستی، با دکمهٔ «🔄 تغییر وضعیت» گزینهٔ «تناسب» یا «لاغری» را انتخاب کن.")
        elif w and cat == "lean" and float(g) < float(w) - 1:
            L.append("ℹ️ BMI تو زیر ۱۸٫۵ است ولی هدفت کم‌کردن وزن است. کم‌کردن وزن در این وضعیت توصیه نمی‌شود؛ بهتر است با پزشک مشورت کنی.")
    return L

def workout_lines(cat, days, sex, current):
    name = PDB.plan_name(cat, days, sex)
    L = [f"🏋️ <b>برنامهٔ تمرین: {name}</b> ({config.sx(sex)['label']})" + (" ✅ برنامهٔ فعلی تو" if current else "")]
    for i, (title, items) in enumerate(PDB.template(cat, days, sex), 1):
        L.append(f"<b>{fa(i)}) {title}</b>\n   " + "، ".join(X.ex_name(e) for e, _p in items))
    if current:
        L.append("ℹ️ «🏋️ تمرین امروز» و «📅 برنامهٔ هفته» از همین قالب ساخته می‌شوند؛ ست، تکرار، RIR و وزنهٔ پیشنهادی بر اساس هفتهٔ برنامه، زمان جلسه و آسیب‌هایت تنظیم می‌شود.")
    else:
        L.append(f"👀 این فقط پیش‌نمایش است؛ برای اینکه تمرین‌هایت {fa(days)} روزه شود، دکمهٔ ✅ پایین را بزن.")
    return L

def numbers_lines(u, w, cat, short=True):
    n = PDB.numbers(u, cat, w)
    if not n: return []
    sign = f"+{n['delta']}" if n["delta"] > 0 else (f"−{-n['delta']}" if n["delta"] < 0 else "بدون تغییر")
    L = [f"🔥 <b>کالری پیشنهادی: {n['kcal']}</b> کیلوکالری (نگهداری ≈ {n['maint']}، {sign})",
         f"🥩 پروتئین {n['protein']} گرم | 🥑 چربی {n['fat']} گرم | 🍚 کربوهیدرات {n['carbs']} گرم"]
    if not short:
        L.append(f"🥦 فیبر حدود {n['fiber']} گرم | 💧 آب حدود {fnum(n['water_l'])} لیتر")
        if cat == "fat" and n["ref_w"] < float(w) - 0.5:
            L.append(f"<i>پروتئین از روی «وزن مرجع» {fnum(n['ref_w'])} کیلو (وزنِ BMI ۲۵ برای قدت) حساب شده، نه کل وزن؛ برای اضافه‌وزن روش رایج همین است.</i>")
        if cat == "fat" and n["kcal"] == PDB.FLOOR_KCAL["f" if u.get("sex") == "f" else "m"]:
            L.append("<i>کالری از حداقل ایمن پایین‌تر نرفت؛ برای کمتر از این حتماً زیر نظر پزشک باش.</i>")
    return L

def screen(uid, mid=None, days=None, note=""):
    u, w, inf, cat = _ctx(uid); sex = u.get("sex") or "m"
    mine = PDB.days_of(u); days = PDB.clamp_days(days or mine)
    L = ([note, ""] if note else []) + header(u, w, inf, cat) + [""] + workout_lines(cat, days, sex, days == mine)
    nl = numbers_lines(u, w, cat)
    if nl: L += [""] + nl
    L += ["", "<i>جزئیات کاردیو، تغذیه و منوی نمونه، مکمل‌ها و نکات ایمنی با دکمه‌های زیر.</i>"]
    rows = [[btn(("✅ " if d == days else "") + f"{fa(d)} روز", f"bt:d:{d}") for d in PDB.DAYS]]
    if days != mine: rows.append([btn(f"✅ تمرین‌هایم را {fa(days)} روزه کن", f"bt:use:{days}")])
    rows += [[btn("🏃 کاردیو", "bt:sec:cardio"), btn("🍽 تغذیه و منوی نمونه", "bt:sec:food")],
             [btn("💊 مکمل‌ها", "bt:sec:supp"), btn("⚠️ نکات ایمنی", "bt:sec:safe")],
             [btn("🎬 آموزش حرکت‌های این برنامه", f"bt:ex:{days}")],
             [btn("🔄 تغییر وضعیت (چاقی / لاغری / تناسب)", "bt:cat")]]
    return show(uid, mid, "\n".join(L), kb(ui.with_back(rows, "m:menu")))

def section(uid, mid, key):
    u, w, inf, cat = _ctx(uid); t = f"{PDB.CAT_EMOJI[cat]} {PDB.CAT_FA[cat]}"
    extra = []
    if key == "cardio":
        L = [f"🏃 <b>کاردیو — {t}</b>", ""] + PDB.CARDIO[cat]
    elif key == "food":
        L = [f"🍽 <b>تغذیه — {t}</b>", ""] + numbers_lines(u, w, cat, short=False) + [""] + PDB.NUTRITION[cat] + ["", "🍛 <b>نمونهٔ یک روز (با غذاهای ایرانی)</b>"]
        L += [f"{a}: {b}" for a, b in PDB.SAMPLE_DAY[cat]]
        L += ["", "<i>اندازه‌ها تقریبی‌اند؛ هر غذا را می‌توانی با غذای هم‌ارزش عوض کنی. منوی روزانهٔ ربات در «🍽 تغذیه» بر اساس هدف کالری خود ربات (مازاد برای افزایش وزن) ساخته می‌شود"
              + ("." if cat == "lean" else "؛ برای این وضعیت، عدد کالری همین صفحه را ملاک بگذار و پرس‌ها را کوچک‌تر بگیر.") + "</i>"]
        extra = [[btn("🍽 تغذیه", "n:menu"), btn("🧮 ماشین‌حساب کالری و ماکرو", "mc:start:m")]]
    elif key == "supp":
        L = [f"💊 <b>مکمل‌ها — {t}</b>", ""] + PDB.supplements(cat, bool(u.get("kidney"))) + ["", "<i>همه اختیاری‌اند، نه نسخهٔ پزشکی.</i>"]
        extra = [[btn("💡 پیشنهاد مکمل برای من", "s:rec"), btn("💊 گینر و کراتین", "s:menu")]]
    else:
        L = [f"⚠️ <b>نکات ایمنی — {t}</b>", ""] + PDB.SAFETY_ALL + PDB.SAFETY[cat]
    return show(uid, mid, "\n".join(L), kb(ui.with_back(extra, "bt:menu")))

def tutorials(uid, mid, days):
    u, w, inf, cat = _ctx(uid); sex = u.get("sex") or "m"; days = PDB.clamp_days(days)
    exs = PDB.exercises(cat, days, sex)
    rows = [[btn("🎬 " + X.ex_name(e), f"xv:{e}") for e in exs[i:i + 2]] for i in range(0, len(exs), 2)]
    return show(uid, mid, f"🎬 <b>آموزش حرکت‌ها</b> — {PDB.plan_name(cat, days, sex)}\nروی هر حرکت بزن تا تصویر، توضیح و لینک آموزش آپارات و یوتیوب بیاید.",
                kb(ui.with_back(rows, f"bt:d:{days}")))

def cat_picker(uid, mid):
    u, w, inf, cat = _ctx(uid)
    rows = [[btn(("✅ " if inf["manual"] and cat == c else "") + f"{PDB.CAT_EMOJI[c]} {PDB.CAT_FA[c]} — {PDB.CAT_GOAL[c]}", f"bt:set:{c}")] for c in PDB.CATS]
    auto = PDB.CAT_FA[inf["auto"]] if inf["auto"] else "نامشخص"
    rows.append([btn(("✅ " if not inf["manual"] else "") + f"🤖 خودکار (الان: {auto})", "bt:set:auto")])
    return show(uid, mid, "🔄 <b>تغییر وضعیت بدنی</b>\nتشخیص خودکار از روی BMI (قد و وزن) و وزن هدفت است. BMI عضله را از چربی جدا نمی‌کند؛ اگر حس می‌کنی "
                "وضعیت دیگری به تو نزدیک‌تر است، خودت انتخاب کن. برنامهٔ تمرین، کالری و نکته‌ها بر همین اساس عوض می‌شوند.", kb(ui.with_back(rows, "bt:menu")))

def use_days(uid, mid, n):
    n = PDB.clamp_days(n)
    db.update_user(uid, days_pw=n, plan_type=X.plan_type_for_days(n), train_days=",".join(map(str, X.DAY_PRESETS[n][0][1])))
    rows = [[btn(lbl, f"bt:ds:{n}:{i}")] for i, (lbl, _d) in enumerate(X.DAY_PRESETS[n])]
    rows.append([btn("🏋️ تمرین امروز", "w:today"), btn("📅 برنامهٔ هفته", "w:week")])
    return show(uid, mid, f"✅ تمرین‌هایت {fa(n)} روزه شد ({PDB.plan_name(PDB.category(ui.U(uid)) or 'fit', n, ui.U(uid).get('sex') or 'm')}).\n"
                f"روزهای پیش‌فرض: {X.DAY_PRESETS[n][0][0]}. اگر روزهای دیگری می‌خواهی انتخاب کن (از ⚙️ تنظیمات هم می‌شود). تمرین‌های ثبت‌شده حفظ می‌شوند.",
                kb(ui.with_back(rows, "bt:menu")))

def cb(uid, mid, p):
    k = p[1] if len(p) > 1 else "menu"
    if k == "menu": return screen(uid, mid)
    if k == "d": return screen(uid, mid, int(p[2]) if len(p) > 2 and p[2].isdigit() else None)
    if k == "sec": return section(uid, mid, p[2] if len(p) > 2 else "cardio")
    if k == "ex": return tutorials(uid, mid, int(p[2]) if len(p) > 2 and p[2].isdigit() else PDB.days_of(ui.U(uid)))
    if k == "cat": return cat_picker(uid, mid)
    if k == "set":
        c = p[2] if len(p) > 2 else "auto"
        db.update_user(uid, body_cat=c if c in PDB.CATS else None)
        cat = PDB.category(ui.U(uid)) or "fit"
        return screen(uid, mid, note=f"✅ وضعیت «{PDB.CAT_FA[cat]}» " + ("(خودکار) " if c not in PDB.CATS else "") +
                      "تنظیم شد. از این به بعد «تمرین امروز» و «برنامهٔ هفته» از برنامهٔ همین وضعیت ساخته می‌شوند.")
    if k == "use" and len(p) > 2 and p[2].isdigit(): return use_days(uid, mid, int(p[2]))
    if k == "ds" and len(p) > 3:
        n, i = PDB.clamp_days(p[2]), int(p[3]) if p[3].isdigit() else 0
        presets = X.DAY_PRESETS[n]
        db.update_user(uid, train_days=",".join(map(str, presets[min(i, len(presets) - 1)][1])))
        return screen(uid, mid, note=f"✅ روزهای تمرین: {presets[min(i, len(presets) - 1)][0]}")
    return screen(uid, mid)

def command(uid):
    return screen(uid)
