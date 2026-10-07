"""Calorie / macro targets (Mifflin-St Jeor x activity + surplus), Iranian-food-friendly meal templates, mass gainer & creatine logic,
realistic gain projection and weekly auto-adjust rules. All numbers are estimates."""
import math
import config, util

ACTIVITY = {1.45: "عمدتاً نشسته (پشت میز، دانشجو) + تمرین", 1.6: "نیمه‌فعال (کار ایستاده/رفت‌وآمد زیاد) + تمرین", 1.75: "پرتحرک (کار فیزیکی) + تمرین"}

def bmr(sex, w, h, age):
    return 10 * w + 6.25 * h - 5 * age + (5 if sex != "f" else -161)

def targets(u, weight=None):
    """-> dict(bmr, tdee, kcal, protein, fat, carbs, water_ml, gainer_kcal, gainer_prot, food_kcal, food_prot)"""
    w = float(weight or u["weight"]); b = bmr(u.get("sex") or "m", w, float(u["height"]), int(u["age"]))
    tdee = b * float(u["activity"]); kcal = tdee + int(u["surplus"])
    prot = float(u["protein_gk"]) * w
    fat = 0.25 * kcal / 9
    carbs = max(0.0, (kcal - prot * 4 - fat * 9) / 4)
    gk = gp = 0.0
    if u.get("gainer_on") and u.get("gainer_kcal"):
        n = int(u.get("gainer_n") or 1); gk = n * float(u["gainer_kcal"]); gp = n * float(u.get("gainer_prot") or 0)
    return dict(bmr=round(b), tdee=round(tdee), kcal=round(kcal), protein=round(prot), fat=round(fat), carbs=round(carbs),
                water_ml=int(round((35 * w) / 100.0) * 100), gainer_kcal=round(gk), gainer_prot=round(gp),
                food_kcal=round(kcal - gk), food_prot=round(max(0.0, prot - gp)))

# ---------------------------------------------------------------- projection (honest expectations)
def weeks_to(cur, target, rate): return (target - cur) / rate if rate > 0 and target > cur else 0.0

def projection(cur, goal_target, deadline_days=config.DEFAULT_TARGET_DAYS, sex="m"):
    """What is realistic: gain of 0.5-1 kg/week (men) or 0.25-0.5 kg/week (women)."""
    rl, rh = config.rates(sex)
    wk = deadline_days / 7.0
    lo, hi = cur + rl * wk, cur + rh * wk
    need = (goal_target - cur) / wk if wk else 0
    return dict(weeks=wk, lo=lo, hi=hi, need_rate=need, realistic=need <= rh + 1e-9, rate_lo=rl, rate_hi=rh,
                eta_lo=weeks_to(cur, goal_target, rh), eta_hi=weeks_to(cur, goal_target, rl))

def weekly_rate(points):
    """points: [(date, kg)] oldest first -> kg/week estimated from the last 14-21 days (average of the latest 7-day window vs the previous one)
    or a plain slope when the data is sparse. None if < 2 points or < 4 days of span."""
    if len(points) < 2: return None
    last_day = points[-1][0]
    span = (last_day - points[0][0]).days
    if span < 4: return None
    win = [p for p in points if (last_day - p[0]).days <= 6]
    prev = [p for p in points if 7 <= (last_day - p[0]).days <= 13]
    if win and prev:
        a = sum(k for _, k in win) / len(win); b = sum(k for _, k in prev) / len(prev)
        ca = sum((d - last_day).days for d, _ in win) / len(win); cb = sum((d - last_day).days for d, _ in prev) / len(prev)
        dd = ca - cb
        return (a - b) / dd * 7 if dd else None
    # slope from the first to the last point
    return (points[-1][1] - points[0][1]) / span * 7

def adjust_decision(rate, surplus, week, sex="m"):
    """Weekly auto-adjust. Men: <0.25 kg/wk -> +150..200 kcal; >1 kg/wk -> reduce 150..200. Women (half the rates): <0.12 -> +100..150; >0.6 -> -100..-150.
    Creatine/glycogen water is ignored for 'too fast' during the first 2 weeks. -> (delta_kcal, text_key)"""
    c = config.sx(sex); lo_b, hi_b = c["bounds"]
    if rate is None: return 0, "need_data"
    if rate < c["low"]:
        d = c["low_d"][1] if rate < c["vlow"] else c["low_d"][0]
        if surplus + d > hi_b: d = max(0, hi_b - surplus)
        return d, "low" if d else "low_max"
    if rate > c["high"]:
        if week <= 2: return 0, "fast_early"
        d = -(c["high_d"][1] if rate > c["vhigh"] else c["high_d"][0])
        if surplus + d < lo_b: d = min(0, lo_b - surplus)
        return d, "high" if d else "high_min"
    return 0, "ok"

# ---------------------------------------------------------------- meal templates (approximate kcal / protein g)
def M(name, kcal, prot): return dict(name=name, kcal=kcal, prot=prot)
MEALS = {
 "breakfast": [
  M("املت/نیمرو ۳ تخم‌مرغ + ۲ برگ نان سنگک + پنیر و گردو + چای", 650, 30),
  M("حلیم (یک کاسهٔ بزرگ) با شکر و دارچین + یک لیوان شیر", 650, 30),
  M("نان + پنیر + گردو + ۲ تخم‌مرغ آب‌پز + خیار و گوجه + یک لیوان شیر پرچرب", 700, 38),
  M("املت گوجه‌فرنگی با ۳ تخم‌مرغ + نان بربری + چای", 640, 28),
  M("جو دوسر پخته با شیر + موز + عسل + گردو", 650, 24),
  M("عدسی با نان + ۱ تخم‌مرغ آب‌پز + سبزی خوردن", 600, 30),
  M("نان + کره بادام‌زمینی + عسل + موز + شیر کاکائو", 750, 28),
  M("کوکو سبزی (۲ تکه) + نان + پنیر + یک لیوان شیر", 600, 32),
 ],
 "lunch": [
  M("چلوکبابِ کوبیده (۲ سیخ) + برنج (۱٫۵ کفگیر) + گوجه + ماست", 1000, 50),
  M("چلو جوجه‌کباب (حدود ۳۰۰ گرم مرغ) + برنج + سالاد + ماست", 950, 62),
  M("عدس‌پلو با مرغ + سالاد شیرازی + ماست", 850, 45),
  M("خورش قیمه + برنج + ماست", 900, 38),
  M("قرمه‌سبزی + برنج + سالاد", 900, 40),
  M("ماکارونی با گوشت چرخ‌کرده + سالاد + ماست", 900, 40),
  M("زرشک‌پلو با مرغ + ماست", 900, 50),
  M("ماهی (سرخ‌شده/کبابی) + برنج + سبزی", 800, 48),
  M("خوراک لوبیا چیتی با گوشت + برنج + ماست", 850, 38),
  M("خورش کرفس یا بادمجان + برنج + ماست‌ و سبزی", 850, 34),
 ],
 "dinner": [
  M("املت اسفناج/قارچ ۳ تخم‌مرغ + نان + ماست", 600, 32),
  M("ساندویچ مرغ یا تن‌ماهی در نان + سیب‌زمینی", 700, 40),
  M("کوکو سیب‌زمینی/سبزی + نان + ماست + خیار", 600, 24),
  M("سوپ جو با مرغ + نان", 550, 30),
  M("پلو با مرغ (پرس کوچک‌تر) + سالاد", 750, 45),
  M("آش رشته یا عدسی + نان + ماست", 650, 25),
  M("کتلت (۳ عدد) + نان + سالاد + ماست", 700, 35),
  M("کتهٔ تن‌ماهی با سبزیجات", 700, 40),
 ],
 "snack": [
  M("یک لیوان شیر پرچرب + موز + ۳ خرما", 380, 12),
  M("ماست چکیده + عسل + گردو", 350, 20),
  M("یک مشت مخلوط مغزها (بادام، گردو، پسته) + کشمش", 300, 8),
  M("ساندویچ کره بادام‌زمینی با نان", 400, 14),
  M("نان + پنیر + گردو + خیار", 350, 14),
  M("اسموتی: شیر + موز + جو دوسر + کره بادام‌زمینی", 550, 25),
 ],
}
EXTRAS = [
  ("یک مشت گردو/بادام (حدود ۳۰ گرم)", 180), ("یک قاشق غذاخوری روغن زیتون روی غذا/سالاد", 120), ("یک لیوان شیر پرچرب", 150),
  ("یک کفگیر برنج اضافه", 200), ("یک عدد موز", 105), ("سه عدد خرما", 70), ("یک قاشق غذاخوری کره بادام‌زمینی", 95),
]
SLOTS = [("breakfast", "🌅 صبحانه", 0.25), ("snack", "🥜 میان‌وعدهٔ صبح", 0.10), ("lunch", "🍛 ناهار", 0.30), ("snack", "🥛 میان‌وعدهٔ عصر", 0.11), ("dinner", "🌙 شام", 0.24)]

def day_plan(food_kcal, seed=0):
    """-> dict(meals=[(label, template, budget)], total_kcal, total_prot, gap, extras=[(text,kcal)]). Deterministic given the seed."""
    meals, used = [], set(); tot_k = tot_p = 0
    for si, (kind, label, frac) in enumerate(SLOTS):
        budget = food_kcal * frac
        order = sorted(range(len(MEALS[kind])), key=lambda i: abs(MEALS[kind][i]["kcal"] - budget))
        top = [i for i in order[:4] if (kind, i) not in used] or order[:4]
        idx = top[(seed + si) % len(top)]; used.add((kind, idx))
        t = MEALS[kind][idx]; meals.append((label, t, round(budget)))
        tot_k += t["kcal"]; tot_p += t["prot"]
    gap = food_kcal - tot_k
    extras = []; g = gap
    if gap > 90:
        for _ in range(4):
            if g < 90: break
            cand = min(EXTRAS, key=lambda e: abs(e[1] - g) if e[1] <= g + 40 else 10**6)
            if cand[1] > g + 40: break
            extras.append(cand); g -= cand[1]
    return dict(meals=meals, total_kcal=tot_k, total_prot=tot_p, gap=round(gap), extras=extras)

def gainer_text(u):
    n = int(u.get("gainer_n") or 1)
    return (f"{u.get('gainer_name') or 'گینر'}: هر اسکوپ {util.fnum(u.get('gainer_g'))} گرم ≈ {util.fnum(u.get('gainer_kcal'))} کیلوکالری"
            + (f" و {util.fnum(u.get('gainer_prot'))} گرم پروتئین" if u.get("gainer_prot") else "") + f"، روزی {n} بار")

def creatine_ok(u): return not u.get("kidney")

DISCLAIMER_SUPP = (
 "⚠️ این‌ها پیشنهاد آموزشی‌اند، نه نسخهٔ پزشکی. اگر بیماری، بارداری، یا دارو داری قبل از هر مکمل با پزشک صحبت کن."
)

def recommend_supplements(u):
    """Plain-Persian, optional supplement ideas based on profile/goal. Not medical advice."""
    w = float(u.get("weight") or 0) or 70
    tw = float(u.get("target_w") or u.get("goal_w") or w)
    goal = "gain" if tw > w + 0.5 else ("lose" if tw < w - 0.5 else "recomp")
    brk = int(u.get("break_months") or 0)
    beginner = brk >= 3 or not u.get("onboarded")
    kidney = bool(u.get("kidney"))
    sex = u.get("sex") or "m"
    lines = ["💊 <b>پیشنهاد مکمل (اختیاری)</b>", DISCLAIMER_SUPP, ""]

    if goal == "gain":
        lines.append("🎯 هدفت بیشتر <b>افزایش وزن/عضله</b> به نظر می‌رسه.")
        lines.append("• <b>پروتئین غذایی</b> اولویته (مرغ، تخم‌مرغ، ماست، حبوبات). مکمل پروتئین فقط اگر غذا کم آوردی.")
        if not kidney:
            lines.append("• <b>کراتین مونوهیدرات</b> ۳–۵ گرم روزانه — ساده و مؤثر برای قدرت (اجباری نیست).")
        else:
            lines.append("• کراتین را به‌خاطر نگرانی کلیه پیشنهاد نمی‌کنم تا با پزشک چک کنی.")
        lines.append("• <b>گینر</b> فقط اگر با غذا به کالری نمی‌رسی؛ یک اسکوپ بعد از تمرین کافی است، اجباری نیست.")
        lines.append("• مولتی‌ویتامین ارزان‌قیمت فقط اگر رژیم یکنواخته — جادو نیست.")
    elif goal == "lose":
        lines.append("🎯 هدفت بیشتر <b>کاهش چربی</b> به نظر می‌رسه.")
        lines.append("• اول کالری و پروتئین غذا را درست کن؛ مکمل چربی‌سوز لازم نیست و معمولاً تبلیغاتیه.")
        if not kidney:
            lines.append("• <b>کراتین</b> می‌تونی نگه داری (قدرت در کسری کالری بهتر می‌ماند)؛ آب کافی بنوش.")
        lines.append("• گینر برای این هدف معمولاً مناسب نیست.")
        lines.append("• کافئین قهوه/چای قبل تمرین اگر تحمل می‌کنی — اختیاری.")
    else:
        lines.append("🎯 وزنت نزدیک هدفه — تمرکز روی <b>فرم و قدرت</b>.")
        if not kidney:
            lines.append("• کراتین ۳–۵ گرم اختیاری.")
        lines.append("• گینر لازم نیست مگر اشتها خیلی کم باشد.")

    if beginner:
        lines.append("")
        lines.append("🌱 <b>مبتدی / برگشت بعد از استراحت:</b> عجله نکن. خواب، غذای کافی، و فرم حرکت مهم‌تر از هر مکملی است.")
    lines.append("")
    lines.append("🏠 <b>تمرین خانه / وزنه سبک:</b> همان کراتین و پروتئین غذایی کافی است؛ تجهیزات خاص مکمل نمی‌خواهد.")
    if sex == "f":
        lines.append("برای خانم‌ها دوز کراتین همان ۳–۵ گرم است؛ گینر را سبک‌تر بگیر اگر می‌خواهی.")
    lines.append("")
    lines.append("اگر خواستی از دکمه‌های همین منو گینر/کراتین را روشن یا خاموش کن — هیچ‌کدام اجباری نیست.")
    return "\n".join(lines)
