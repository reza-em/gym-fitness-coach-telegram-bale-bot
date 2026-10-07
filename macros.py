"""🧮 Target-weight calories & macros calculator.

Method (all from the TARGET weight in kg) - from coach Saman Kharazmi's (@samankharazmi_6tofit) reel:
  calories = target x 24 | protein g = target x 2.2 | fat g = calories / 30 | fiber g = calories x 0.014
  carbs g = (calories - (protein x 4 + fat x 9)) / 4 | water L = target / 30
The reel gives no way to pick a target weight, so the suggestions here use general standard formulas
(healthy BMI 18.5-24.9, BMI ~22, Devine). The optional "save" only pins these numbers on the nutrition screen;
the bot's own targets (Mifflin-St Jeor + surplus, weekly auto-adjust) are never changed."""
from decimal import Decimal, ROUND_HALF_UP
import db, util, nutrition as N
import ui
from core import btn, kb, send, show
from util import fnum

LO, HI = 35, 200            # accepted target weight (kg)
BMI_LO, BMI_HI, BMI_MID = 18.5, 24.9, 22.0
CREDIT = "روش محاسبه بر اساس آموزش سامان خوارزمی"
LABEL = "🧮 ماشین‌حساب کالری و ماکرو"

def _r(x, nd=0):
    """Half-up rounding (Python's round() is banker's rounding)."""
    q = Decimal(1).scaleb(-nd)
    v = Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(v) if nd == 0 else float(v)

# ---------------------------------------------------------------- math (pure)
def calc(target):
    """target kg -> dict(target, kcal, protein, fat, fiber, carbs, water_l, rest_kcal, pf_kcal).
    Later steps use the rounded earlier numbers, so the step-by-step text always adds up."""
    t = Decimal(str(float(target)))
    kcal = _r(t * 24)
    protein = _r(t * Decimal("2.2"))
    fat = _r(Decimal(kcal) / 30)
    fiber = _r(Decimal(kcal) * Decimal("0.014"))
    pf_kcal = protein * 4 + fat * 9
    rest = kcal - pf_kcal
    carbs = _r(Decimal(max(0, rest)) / 4)
    water = _r(t / 30, 1)
    return dict(target=float(target), kcal=kcal, protein=protein, fat=fat, fiber=fiber, carbs=carbs, water_l=water, pf_kcal=pf_kcal, rest_kcal=rest)

def bmi(weight, height_cm):
    h = float(height_cm) / 100.0
    return float(weight) / (h * h)

def suggestions(height_cm, sex="m"):
    """General standard formulas (NOT from the reel). -> dict(lo, hi, bmi22, devine) in whole kg, or None without a height."""
    if not height_cm: return None
    h = float(height_cm) / 100.0
    lo = int(-(-BMI_LO * h * h // 1))                       # ceil: lowest weight still inside the range
    hi = int(BMI_HI * h * h // 1)                           # floor
    devine = (45.5 if sex == "f" else 50.0) + 0.9 * (float(height_cm) - 152.4)
    return dict(lo=lo, hi=hi, bmi22=_r(BMI_MID * h * h), devine=_r(devine))

# ---------------------------------------------------------------- texts
def card_text(target, u=None):
    m = calc(target); t = fnum(m["target"])
    L = [f"🧮 <b>کالری و ماکروی روزانه</b> برای وزن هدف <b>{t}</b> کیلو", "",
         f"🔥 کالری: <b>{m['kcal']}</b> کیلوکالری",
         f"🥩 پروتئین: <b>{m['protein']}</b> گرم",
         f"🥑 چربی: <b>{m['fat']}</b> گرم",
         f"🍚 کربوهیدرات: <b>{m['carbs']}</b> گرم",
         f"🥦 فیبر: <b>{m['fiber']}</b> گرم",
         f"💧 آب: <b>{fnum(m['water_l'])}</b> لیتر", "",
         "<b>این عددها چطور به دست آمد؟</b>",
         f"۱. کالری = وزن هدف × 24 = {t} × 24 = {m['kcal']}",
         f"۲. پروتئین = وزن هدف × 2.2 = {t} × 2.2 = {m['protein']} گرم",
         f"۳. چربی = کالری ÷ 30 = {m['kcal']} ÷ 30 = {m['fat']} گرم",
         f"۴. فیبر = کالری × 0.014 = {m['kcal']} × 0.014 = {m['fiber']} گرم",
         "۵. کربوهیدرات = بقیهٔ کالری ÷ 4 (هر گرم پروتئین و کربوهیدرات ۴ کالری و هر گرم چربی ۹ کالری دارد)",
         f"   سهم پروتئین و چربی: {m['protein']} × 4 + {m['fat']} × 9 = {m['pf_kcal']} کالری",
         f"   بقیه: {m['kcal']} − {m['pf_kcal']} = {m['rest_kcal']} ← {m['rest_kcal']} ÷ 4 = {m['carbs']} گرم",
         f"۶. آب = وزن هدف ÷ 30 = {t} ÷ 30 = {fnum(m['water_l'])} لیتر"]
    if u and u.get("height"):
        b = bmi(m["target"], u["height"])
        if b < BMI_LO:
            s = suggestions(u["height"], u.get("sex") or "m")
            L += ["", f"⚠️ این وزن هدف برای قد {fnum(u['height'])} سانتی‌متر کمی <b>پایین‌تر از محدودهٔ وزن سالم</b> است (BMI حدود {fnum(b)}). "
                      f"شاید بهتر باشد هدف را حداقل {s['lo']} کیلو بگذاری، یا قبلش با پزشک مشورت کنی."]
    if u and u.get("weight") and u.get("height") and u.get("age"):
        try:
            own = N.targets(u, ui.current_weight(u["id"]))["kcal"]
            L += ["", f"ℹ️ هدف کالری خودِ برنامهٔ ربات (از روی وزن فعلی و برنامهٔ افزایش وزنت) {own} کیلوکالری است و تغییری نمی‌کند؛ این ماشین‌حساب یک روش دیگر برای مقایسه است."]
        except Exception:
            pass
    L += ["", f"📌 {CREDIT}", "<i>این عددها یک راهنمای کلی‌اند، نه توصیهٔ پزشکی. اگر بیماری خاص، بارداری یا رژیم درمانی داری، با پزشک یا متخصص تغذیه هماهنگ کن.</i>"]
    return "\n".join(L)

def saved_line(u):
    """One block for the nutrition screen when the user pinned a calculator result (else '')."""
    tg = u.get("macro_target")
    if not tg: return ""
    m = calc(tg)
    return (f"\n📌 <b>هدف ذخیره‌شده از ماشین‌حساب</b> (وزن هدف {fnum(tg)} کیلو):\n"
            f"🔥 {m['kcal']} کیلوکالری | 🥩 پروتئین {m['protein']} | 🥑 چربی {m['fat']} | 🍚 کربوهیدرات {m['carbs']} | 🥦 فیبر {m['fiber']} گرم | 💧 آب {fnum(m['water_l'])} لیتر")

# ---------------------------------------------------------------- screens
def _back(o): return "mc:back:n" if o == "n" else "mc:back:m"

def start(uid, mid=None, o="m"):
    """Pick a target weight: saved goal, healthy-range suggestions, or type a number."""
    u = ui.U(uid)
    L = [f"{LABEL.split(' ', 1)[0]} <b>{LABEL.split(' ', 1)[1]}</b>",
         "در این روش همه‌چیز از روی <b>وزن هدف</b> حساب می‌شود؛ یعنی وزنی که می‌خواهی به آن برسی، نه وزن فعلی‌ات.", ""]
    rows, seen = [], set()
    def add(label, v):
        k = fnum(v)
        if v and LO <= float(v) <= HI and k not in seen:
            seen.add(k); rows.append([btn(label.format(k), f"mc:c:{k}:{o}")])
    if u.get("goal_w"):
        L.append(f"🎯 وزن هدفی که قبلاً ثبت کردی: <b>{fnum(u['goal_w'])}</b> کیلو")
        add("🎯 هدف خودم: {} کیلو", u["goal_w"])
        if u.get("target_w") and fnum(u["target_w"]) != fnum(u["goal_w"]):
            add("⏳ هدف ۲ ماهه: {} کیلو", u["target_w"])
    s = suggestions(u.get("height"), u.get("sex") or "m")
    if s:
        if u.get("goal_w"): L.append("")
        L += [("اگر هنوز مطمئن نیستی، " if u.get("goal_w") else "هنوز وزن هدف ثبت نکرده‌ای. ") + f"برای قد {fnum(u['height'])} سانتی‌متر:",
              f"• محدودهٔ وزن سالم (BMI بین ۱۸٫۵ تا ۲۴٫۹): حدود {s['lo']} تا {s['hi']} کیلو",
              f"• پیشنهاد برای شروع (BMI حدود ۲۲): <b>{s['bmi22']}</b> کیلو",
              f"• فرمول دیواین (Devine): حدود <b>{s['devine']}</b> کیلو",
              "<i>این پیشنهادها از فرمول‌های عمومی و استاندارد هستند، نه از ویدیوی آموزشی. برای کسی که عضلهٔ زیادی دارد معمولاً کمی پایین‌تر از واقعیت‌اند.</i>"]
        r = []
        for lab, v in (("📏 BMI ۲۲: {} کیلو", s["bmi22"]), ("📐 دیواین: {} کیلو", s["devine"])):
            k = fnum(v)
            if LO <= v <= HI and k not in seen: seen.add(k); r.append(btn(lab.format(k), f"mc:c:{k}:{o}"))
        if r: rows.append(r)
    L += ["", f"👇 یکی از دکمه‌ها را بزن، یا وزن هدفت را به کیلو بنویس (مثلاً 90؛ بین {LO} تا {HI})."]
    db.set_await(uid, "mc", {"o": o})
    return show(uid, mid, "\n".join(L), kb(ui.with_back(rows, _back(o))))

def result(uid, target, mid=None, o="m", note=""):
    db.set_await(uid, None)
    u = ui.U(uid); k = fnum(target)
    saved = u.get("macro_target") is not None and fnum(u["macro_target"]) == k
    rows = [[btn("🗑 برداشتن از صفحهٔ تغذیه", f"mc:rm:{k}:{o}") if saved else btn("📌 ذخیره به‌عنوان هدف روزانه‌ام", f"mc:sv:{k}:{o}")],
            [btn("🔄 یک وزن هدف دیگر", f"mc:start:{o}")]]
    if o == "n": rows.append([btn("🍽 تغذیه", "n:menu")])
    return show(uid, mid, (note + "\n\n" if note else "") + card_text(target, u), kb(ui.with_back(rows, _back(o))))

def _target(s): return util.parse_num(s, LO, HI)

def on_text(uid, aw, d, text):
    t = util.norm(text)
    for w in ("کیلوگرم", "کیلو", "kg", "KG", "Kg"): t = t.replace(w, "")
    v = _target(t.strip())
    o = (d or {}).get("o", "m")
    if v is not None: return result(uid, v, None, o)
    if any(ch.isdigit() for ch in t) and len(t) <= 15:
        return send(uid, f"این عدد را نمی‌توانم وزن هدف حساب کنم 🙂 یک عدد بین {LO} تا {HI} کیلو بنویس (مثلاً 75 یا 82.5).",
                    kb(ui.with_back([], _back(o))))
    db.set_await(uid, None)
    return False             # not a number: let the normal chat handle it

def command(uid, arg=""):
    if arg:
        v = _target(util.norm(arg).replace("کیلو", "").replace("kg", "").strip())
        if v is not None: return result(uid, v)
        send(uid, f"وزن هدف باید عددی بین {LO} تا {HI} کیلو باشد (مثلاً <code>/macros 90</code>).")
    return start(uid)

def cb(uid, mid, p):
    k = p[1] if len(p) > 1 else "start"
    o = "n" if p[-1] == "n" else "m"
    if k == "start": return start(uid, mid, o)
    if k == "back":
        db.set_await(uid, None)
        if o == "n":
            import diet; return diet.menu(uid, mid)
        return ui.show_menu(uid, mid)
    v = util.parse_num(p[2], LO, HI) if len(p) > 2 else None
    if v is None: return start(uid, mid, o)
    if k == "c": return result(uid, v, mid, o)
    if k == "sv":
        db.update_user(uid, macro_target=v)
        return result(uid, v, mid, o, note="✅ <b>ذخیره شد.</b> از این به بعد این عددها در صفحهٔ «🍽 تغذیه» کنار هدف خود ربات هم نشان داده می‌شوند. "
                                            "منوی غذایی پیشنهادی و تنظیم هفتگی ربات تغییری نمی‌کند.")
    if k == "rm":
        db.update_user(uid, macro_target=None)
        return result(uid, v, mid, o, note="🗑 از صفحهٔ تغذیه برداشته شد.")
