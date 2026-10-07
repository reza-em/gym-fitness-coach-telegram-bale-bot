"""📂 Body-type program bank: چاقی (fat loss) / لاغری (lean gain) / تناسب (fit: maintenance / recomposition).

Pure data + classification (no Telegram/Bale code; the screens are in bodytype.py). Same style as exdata.py:
every exercise id below MUST exist in exdata.EX so the tutorial buttons (🎬 Aparat/YouTube, images) keep working.
Session format = exdata templates: (title, [(exercise_id, priority)]); priority 1 = essential, higher numbers are dropped first
when the session would not fit the user's time. Sets / reps / RIR / loads still come from program.py (phases + double progression).

Only general, well-established guidance is used (BMI cut-offs, ~150-300 min/week of moderate activity, protein 1.6-2.2 g/kg,
modest calorie deficit/surplus). No invented statistics or citations."""
import exdata as X

CATS = ("fat", "lean", "fit")
CAT_FA = {"fat": "چاقی", "lean": "لاغری", "fit": "تناسب"}
CAT_EMOJI = {"fat": "🔥", "lean": "🌱", "fit": "⚖️"}
CAT_GOAL = {"fat": "کاهش چربی با حفظ عضله", "lean": "افزایش وزن سالم و عضله‌سازی", "fit": "حفظ تناسب / ریکامپ (چربی کمتر، عضلهٔ بیشتر)"}
DAYS = (2, 3, 4, 5, 6)
MENU_LABEL = "📂 برنامه بر اساس وضعیت بدنی"

BMI_UNDER, BMI_OVER = 18.5, 25.0     # WHO adult cut-offs: <18.5 underweight, 18.5-24.9 normal, >=25 overweight
GOAL_DELTA = 3.0                     # kg: inside the normal BMI range a goal this far below/above the current weight picks fat-loss / lean-gain

# ---------------------------------------------------------------- classification
def bmi(weight, height_cm):
    if not weight or not height_cm: return None
    h = float(height_cm) / 100.0
    return float(weight) / (h * h)

def auto_category(height_cm, weight, goal_w=None):
    """-> (cat or None, bmi or None, reason_fa). BMI <18.5 lean, >=25 fat, otherwise fit unless the goal weight says lose/gain."""
    b = bmi(weight, height_cm)
    if b is None: return None, None, "قد یا وزن ثبت نشده است"
    if b < BMI_UNDER: return "lean", b, "BMI کمتر از ۱۸٫۵ است"
    if b >= BMI_OVER: return "fat", b, "BMI ۲۵ یا بیشتر است"
    if goal_w:
        diff = float(goal_w) - float(weight)
        if diff <= -GOAL_DELTA: return "fat", b, f"BMI در محدودهٔ سالم است ولی هدفت کم‌کردن حدود {abs(diff):.0f} کیلو است"
        if diff >= GOAL_DELTA: return "lean", b, f"BMI در محدودهٔ سالم است ولی هدفت اضافه‌کردن حدود {diff:.0f} کیلو است"
    return "fit", b, "BMI در محدودهٔ سالم (۱۸٫۵ تا ۲۴٫۹) است"

def _goal(u):
    return u.get("goal_w") or u.get("target_w")

def info(u, weight=None):
    """-> dict(cat, auto, bmi, reason, manual). `cat` honours the user's manual override (users.body_cat); None when height/weight unknown."""
    w = weight or u.get("weight")
    auto, b, reason = auto_category(u.get("height"), w, _goal(u))
    manual = u.get("body_cat") if u.get("body_cat") in CATS else None
    return dict(cat=manual or auto, auto=auto, bmi=b, reason=reason, manual=bool(manual))

def category(u, weight=None): return info(u, weight)["cat"]

# ---------------------------------------------------------------- session library
def S(title, items): return (title, list(items))
_UL, _FB = X.TEMPLATES["ul"], X.TEMPLATES["fb"]          # the original 4-day / 3-day programmes were built for lean gain
_ULF, _FBF = X.TEMPLATES_F["ul"], X.TEMPLATES_F["fb"]

# shared male push/pull/legs (lean + fit, 5-6 days)
M_PUSH = S("پوش A (سینه، سرشانه، پشت‌بازو)", [("bench_bb", 1), ("ohp_db", 1), ("incline_db", 2), ("lateral", 3), ("tri_pd", 3), ("tri_overhead", 4)])
M_PULL = S("پول A (پشت، پشت‌شانه، جلوبازو)", [("lat_pd", 1), ("row_cable", 1), ("row_db", 2), ("face_pull", 3), ("curl_db", 3), ("hammer", 4)])
M_LEGS = S("پا A و شکم", [("squat_bb", 1), ("rdl", 1), ("leg_press", 2), ("leg_curl", 2), ("calf", 3), ("cable_crunch", 4)])
M_PUSH2 = S("پوش B (حجمی)", [("incline_db", 1), ("chest_press_m", 1), ("ohp_machine", 2), ("cable_fly", 3), ("lateral", 3), ("tri_overhead", 4)])
M_PULL2 = S("پول B (حجمی)", [("row_machine", 1), ("lat_pd", 1), ("row_cable", 2), ("rear_delt", 3), ("curl_cable", 3), ("hammer", 4)])
M_LEGS2 = S("پا B (حجمی)", [("leg_press", 1), ("hip_thrust", 1), ("lunge_db", 2), ("leg_ext", 3), ("leg_curl", 3), ("calf", 4)])

# male fat loss: machine / dumbbell friendly, less spinal loading, whole body often
FM_FB_A = S("تمام‌بدن A", [("goblet_squat", 1), ("chest_press_m", 1), ("lat_pd", 1), ("hip_thrust", 2), ("ohp_machine", 2), ("cable_crunch", 3)])
FM_FB_B = S("تمام‌بدن B", [("leg_press", 1), ("bench_db", 1), ("row_cable", 1), ("rdl", 2), ("lateral", 3), ("leg_curl", 3), ("cable_crunch", 4)])
FM_FB_C = S("تمام‌بدن C", [("leg_press", 1), ("incline_db", 1), ("row_machine", 1), ("lunge_db", 2), ("face_pull", 3), ("tri_pd", 4), ("curl_cable", 4)])
FM_UP_A = S("بالاتنه A", [("chest_press_m", 1), ("lat_pd", 1), ("ohp_db", 2), ("row_cable", 2), ("lateral", 3), ("tri_pd", 4), ("curl_db", 4)])
FM_LO_A = S("پایین‌تنه A", [("leg_press", 1), ("rdl", 1), ("leg_curl", 2), ("leg_ext", 3), ("calf", 3), ("cable_crunch", 4)])
FM_UP_B = S("بالاتنه B", [("incline_db", 1), ("row_machine", 1), ("ohp_machine", 2), ("pec_fly", 3), ("face_pull", 3), ("hammer", 4), ("tri_overhead", 4)])
FM_LO_B = S("پایین‌تنه B", [("goblet_squat", 1), ("hip_thrust", 1), ("lunge_db", 2), ("leg_curl", 2), ("calf", 3), ("cable_crunch", 4)])
FM_PUSH = S("پوش (سینه، سرشانه، پشت‌بازو)", [("chest_press_m", 1), ("ohp_machine", 1), ("incline_db", 2), ("lateral", 3), ("tri_pd", 3), ("pec_fly", 4)])
FM_PULL = S("پول (پشت و جلوبازو)", [("lat_pd", 1), ("row_machine", 1), ("row_cable", 2), ("face_pull", 3), ("curl_cable", 3), ("hammer", 4)])
FM_LEGS = S("پا و شکم", [("leg_press", 1), ("goblet_squat", 1), ("leg_curl", 2), ("hip_thrust", 2), ("calf", 3), ("cable_crunch", 3)])

# male lean gain (2 days: heavy compounds)
LM_FB_A = S("تمام‌بدن A (قدرتی)", [("squat_bb", 1), ("bench_bb", 1), ("row_cable", 1), ("ohp_db", 2), ("curl_db", 3), ("tri_pd", 3), ("calf", 4)])
LM_FB_B = S("تمام‌بدن B (قدرتی)", [("rdl", 1), ("incline_db", 1), ("lat_pd", 1), ("leg_press", 2), ("lateral", 3), ("hammer", 4), ("tri_overhead", 4)])

# male fit / recomposition
TM_FB_A = S("تمام‌بدن A", [("squat_bb", 1), ("bench_db", 1), ("lat_pd", 1), ("ohp_machine", 2), ("leg_curl", 3), ("curl_cable", 4), ("cable_crunch", 4)])
TM_FB_B = S("تمام‌بدن B", [("rdl", 1), ("incline_db", 1), ("row_cable", 1), ("lunge_db", 2), ("lateral", 3), ("tri_pd", 4)])
TM_FB_C = S("تمام‌بدن C", [("leg_press", 1), ("chest_press_m", 1), ("row_db", 1), ("hip_thrust", 2), ("face_pull", 3), ("hammer", 4), ("calf", 4)])
TM_UP_A = S("بالاتنه A", [("bench_db", 1), ("lat_pd", 1), ("ohp_db", 2), ("row_cable", 2), ("cable_fly", 3), ("curl_db", 4), ("tri_pd", 4)])
TM_LO_A = S("پایین‌تنه A", [("squat_bb", 1), ("leg_curl", 1), ("lunge_db", 2), ("leg_ext", 3), ("calf", 3), ("cable_crunch", 4)])
TM_UP_B = S("بالاتنه B", [("incline_db", 1), ("row_machine", 1), ("ohp_machine", 2), ("lateral", 3), ("rear_delt", 3), ("hammer", 4), ("tri_overhead", 4)])
TM_LO_B = S("پایین‌تنه B", [("rdl", 1), ("leg_press", 1), ("hip_thrust", 2), ("leg_curl", 3), ("calf", 3), ("cable_crunch", 4)])

# shared female sessions (glute / lower-body emphasis, like exdata.TEMPLATES_F)
F_GLUTE = S("باسن و پشت‌ران", [("hip_thrust", 1), ("rdl", 1), ("cable_kick", 2), ("leg_curl", 2), ("abduct_m", 3), ("calf", 4)])
F_GLUTE2 = S("باسن + شکم", [("hip_thrust", 1), ("goblet_squat", 1), ("abduct_m", 2), ("cable_kick", 2), ("leg_curl", 3), ("cable_crunch", 3)])
F_QUAD = S("پا (جلوران و باسن)", [("leg_press", 1), ("goblet_squat", 1), ("lunge_db", 2), ("leg_ext", 3), ("calf", 3), ("cable_crunch", 4)])

# female fat loss
FF_FB_A = S("تمام‌بدن A (تأکید باسن)", [("goblet_squat", 1), ("hip_thrust", 1), ("lat_pd", 1), ("chest_press_m", 2), ("abduct_m", 3), ("cable_crunch", 4)])
FF_FB_B = S("تمام‌بدن B (تأکید پا)", [("leg_press", 1), ("rdl", 1), ("row_cable", 1), ("ohp_machine", 2), ("cable_kick", 3), ("tri_pd", 4)])
FF_FB_C = S("تمام‌بدن C", [("leg_press", 1), ("hip_thrust", 1), ("row_machine", 1), ("incline_db", 2), ("leg_curl", 2), ("lateral", 3), ("curl_cable", 4)])
FF_LO_A = S("پایین‌تنه A (باسن و ران)", [("hip_thrust", 1), ("leg_press", 1), ("rdl", 1), ("abduct_m", 3), ("calf", 4)])
FF_UP_A = S("بالاتنه A", [("lat_pd", 1), ("chest_press_m", 1), ("row_cable", 2), ("ohp_machine", 2), ("lateral", 3), ("tri_pd", 4)])
FF_LO_B = S("پایین‌تنه B (پا و پشت‌ران)", [("goblet_squat", 1), ("lunge_db", 1), ("cable_kick", 2), ("leg_curl", 2), ("leg_ext", 3), ("calf", 4)])
FF_UP_B = S("بالاتنه B + شکم", [("incline_db", 1), ("row_db", 1), ("face_pull", 2), ("lateral", 3), ("curl_db", 4), ("cable_crunch", 4)])

# female lean gain (2 days)
LF_FB_A = S("تمام‌بدن A (تأکید باسن)", [("squat_bb", 1), ("hip_thrust", 1), ("lat_pd", 1), ("chest_press_m", 2), ("row_cable", 2), ("cable_crunch", 4)])
LF_FB_B = S("تمام‌بدن B (تأکید پا)", [("rdl", 1), ("leg_press", 1), ("incline_db", 1), ("row_db", 1), ("ohp_machine", 2), ("abduct_m", 3)])

# female fit / recomposition
TF_FB_A = S("تمام‌بدن A", [("squat_bb", 1), ("hip_thrust", 1), ("lat_pd", 1), ("bench_db", 2), ("abduct_m", 3), ("cable_crunch", 4)])
TF_FB_B = S("تمام‌بدن B", [("rdl", 1), ("lunge_db", 1), ("row_cable", 1), ("ohp_db", 2), ("cable_kick", 3), ("tri_overhead", 4)])
TF_FB_C = S("تمام‌بدن C", [("leg_press", 1), ("hip_thrust", 1), ("row_machine", 1), ("incline_db", 2), ("leg_curl", 3), ("lateral", 3), ("curl_db", 4)])
TF_LO_A = S("پایین‌تنه A (باسن)", [("hip_thrust", 1), ("squat_bb", 1), ("leg_curl", 2), ("leg_press", 3), ("abduct_m", 3), ("calf", 4)])
TF_UP_A = S("بالاتنه A + شکم", [("lat_pd", 1), ("incline_db", 1), ("row_cable", 2), ("ohp_machine", 2), ("lateral", 3), ("face_pull", 3), ("cable_crunch", 4)])
TF_LO_B = S("پایین‌تنه B (پا)", [("rdl", 1), ("lunge_db", 1), ("goblet_squat", 2), ("cable_kick", 3), ("leg_ext", 3), ("calf", 4)])
TF_UP_B = S("بالاتنه B", [("chest_press_m", 1), ("row_db", 1), ("ohp_machine", 2), ("face_pull", 3), ("curl_cable", 4), ("tri_pd", 4)])

# ---------------------------------------------------------------- the bank: PLANS[cat][sex][days] = (name, sessions)
PLANS = {
 "fat": {
  "m": {2: ("تمام‌بدن (۲ روز)", [FM_FB_A, FM_FB_B]),
        3: ("تمام‌بدن (۳ روز)", [FM_FB_A, FM_FB_B, FM_FB_C]),
        4: ("بالاتنه/پایین‌تنه (۴ روز)", [FM_UP_A, FM_LO_A, FM_UP_B, FM_LO_B]),
        5: ("بالاتنه/پایین‌تنه + تمام‌بدن (۵ روز)", [FM_UP_A, FM_LO_A, FM_FB_C, FM_UP_B, FM_LO_B]),
        6: ("پوش/پول/پا ×۲ (۶ روز)", [FM_PUSH, FM_PULL, FM_LEGS, M_PUSH2, M_PULL2, FM_LO_B])},
  "f": {2: ("تمام‌بدن با تأکید باسن (۲ روز)", [FF_FB_A, FF_FB_B]),
        3: ("تمام‌بدن با تأکید باسن (۳ روز)", [FF_FB_A, FF_FB_B, FF_FB_C]),
        4: ("پایین‌تنه/بالاتنه (۴ روز)", [FF_LO_A, FF_UP_A, FF_LO_B, FF_UP_B]),
        5: ("پایین‌تنه/بالاتنه + روز باسن (۵ روز)", [FF_LO_A, FF_UP_A, F_GLUTE, FF_LO_B, FF_UP_B]),
        6: ("پایین‌تنه/بالاتنه/باسن ×۲ (۶ روز)", [FF_LO_A, FF_UP_A, F_GLUTE, FF_LO_B, FF_UP_B, F_GLUTE2])},
 },
 "lean": {
  "m": {2: ("تمام‌بدن قدرتی (۲ روز)", [LM_FB_A, LM_FB_B]),
        3: (X.PLAN_NAMES["fb"], _FB),
        4: (X.PLAN_NAMES["ul"], _UL),
        5: ("بالاتنه/پایین‌تنه + پوش/پول/پا (۵ روز)", [_UL[0], _UL[1], M_PUSH, M_PULL, M_LEGS]),
        6: ("پوش/پول/پا ×۲ (۶ روز)", [M_PUSH, M_PULL, M_LEGS, M_PUSH2, M_PULL2, M_LEGS2])},
  "f": {2: ("تمام‌بدن با تأکید باسن (۲ روز)", [LF_FB_A, LF_FB_B]),
        3: (X.PLAN_NAMES_F["fb"], _FBF),
        4: (X.PLAN_NAMES_F["ul"], _ULF),
        5: ("پایین‌تنه/بالاتنه + روز باسن (۵ روز)", [_ULF[0], _ULF[1], F_GLUTE, _ULF[2], _ULF[3]]),
        6: ("پایین‌تنه/بالاتنه/باسن ×۲ (۶ روز)", [_ULF[0], _ULF[1], F_GLUTE, _ULF[2], _ULF[3], F_QUAD])},
 },
 "fit": {
  "m": {2: ("تمام‌بدن (۲ روز)", [TM_FB_A, TM_FB_B]),
        3: ("تمام‌بدن (۳ روز)", [TM_FB_A, TM_FB_B, TM_FB_C]),
        4: ("بالاتنه/پایین‌تنه (۴ روز)", [TM_UP_A, TM_LO_A, TM_UP_B, TM_LO_B]),
        5: ("بالاتنه/پایین‌تنه + پوش/پول/پا (۵ روز)", [TM_UP_A, TM_LO_A, M_PUSH, M_PULL, M_LEGS]),
        6: ("پوش/پول/پا ×۲ (۶ روز)", [M_PUSH, M_PULL, M_LEGS, M_PUSH2, M_PULL2, M_LEGS2])},
  "f": {2: ("تمام‌بدن با تأکید باسن (۲ روز)", [TF_FB_A, TF_FB_B]),
        3: ("تمام‌بدن با تأکید باسن (۳ روز)", [TF_FB_A, TF_FB_B, TF_FB_C]),
        4: ("پایین‌تنه/بالاتنه (۴ روز)", [TF_LO_A, TF_UP_A, TF_LO_B, TF_UP_B]),
        5: ("پایین‌تنه/بالاتنه + روز باسن (۵ روز)", [TF_LO_A, TF_UP_A, F_GLUTE, TF_LO_B, TF_UP_B]),
        6: ("پایین‌تنه/بالاتنه/باسن ×۲ (۶ روز)", [TF_LO_A, TF_UP_A, F_GLUTE, TF_LO_B, TF_UP_B, F_QUAD])},
 },
}

def _sex(sex): return "f" if sex == "f" else "m"
def clamp_days(n):
    try: n = int(n)
    except (TypeError, ValueError): n = 4
    return max(DAYS[0], min(DAYS[-1], n))

def template(cat, days, sex="m"):
    """Session list (exdata template format) for a category / days per week / sex."""
    return PLANS[cat if cat in PLANS else "fit"][_sex(sex)][clamp_days(days)][1]

def plan_name(cat, days, sex="m"):
    return PLANS[cat if cat in PLANS else "fit"][_sex(sex)][clamp_days(days)][0]

def exercises(cat, days, sex="m"):
    """Distinct exercise ids of a bank template, in order of appearance."""
    seen = []
    for _t, items in template(cat, days, sex):
        for e, _p in items:
            if e not in seen: seen.append(e)
    return seen

def all_exercise_ids():
    return {e for c in PLANS.values() for s in c.values() for _n, sess in s.values() for _t, items in sess for e, _p in items}

def days_of(u):
    """Days per week of the user's programme: plan_type ul=4 / fb=3 / dN=N, else users.days_pw."""
    pt = u.get("plan_type") or ""
    if pt == "ul": return 4
    if pt == "fb": return 3
    if pt[:1] == "d" and pt[1:].isdigit(): return clamp_days(pt[1:])
    return clamp_days(u.get("days_pw") or 4)

def user_template(u):
    """The weekly programme used by program.py (today / week / reminders). Category from the profile (or the user's override);
    without height/weight (e.g. bare test dicts) the classic 3/4-day templates are used, exactly as before."""
    sex = u.get("sex") or "m"; cat = category(u)
    if cat is None:
        if u.get("plan_type") in ("ul", "fb"): return X.template(u["plan_type"], sex)
        cat = "fit"
    return template(cat, days_of(u), sex)

def user_plan_name(u):
    sex = u.get("sex") or "m"; cat = category(u)
    if cat is None and u.get("plan_type") in ("ul", "fb"): return X.plan_name(u["plan_type"], sex)
    cat = cat or "fit"
    return f"{CAT_EMOJI[cat]} {CAT_FA[cat]} — {plan_name(cat, days_of(u), sex)}"

# ---------------------------------------------------------------- guidance texts (general, well-established)
CARDIO = {
 "fat": ["🚶 پیاده‌روی روزانه را بالا ببر: از تعداد قدم فعلی‌ات شروع کن و هر هفته حدود ۱۰۰۰ قدم اضافه کن تا به ۷ تا ۱۰ هزار قدم برسی.",
         "🚴 کاردیوی کم‌فشار (پیاده‌روی تند، دوچرخهٔ ثابت، الپتیکال، شنا): ۳ تا ۵ جلسه در هفته، هر بار ۲۰ تا ۴۰ دقیقه؛ روی‌هم حدود ۱۵۰ تا ۳۰۰ دقیقه فعالیت متوسط در هفته.",
         "🗣 شدت مناسب: نفس‌نفس بزنی ولی هنوز بتوانی جمله‌های کوتاه بگویی (تست صحبت).",
         "⚡ اینتروال (HIIT) اختیاری است: فقط بعد از ۴ تا ۶ هفته عادت‌کردن، حداکثر ۱ تا ۲ بار در هفته و با وسیلهٔ کم‌ضربه مثل دوچرخه یا الپتیکال.",
         "🦵 اگر وزنت خیلی بالاست یا زانو/مچ پا حساس است، دویدن و پرش را فعلاً کنار بگذار.",
         "🏋️ کاردیو را بعد از وزنه یا در روز جدا انجام بده تا قدرتت در تمرین وزنه کم نشود."],
 "lean": ["❤️ کاردیو کم ولی منظم برای سلامت قلب: ۲ تا ۳ جلسه در هفته، هر بار ۱۵ تا ۲۰ دقیقه پیاده‌روی تند یا دوچرخهٔ سبک.",
          "🔥 کاردیوی زیاد کالری می‌سوزاند و افزایش وزن را کند می‌کند؛ اگر کاردیوی بیشتری دوست داری، همان‌قدر هم غذا اضافه کن.",
          "🤸 قبل از وزنه ۵ تا ۱۰ دقیقه گرم‌کردن سبک (دوچرخه یا پیاده‌روی) کافی است.",
          "⚡ اینتروال سنگین لازم نیست؛ انرژی‌ات را برای وزنه نگه دار."],
 "fit": ["📅 هدف کلی: حدود ۱۵۰ دقیقه فعالیت متوسط یا ۷۵ دقیقه فعالیت شدید در هفته (یا ترکیبی از هر دو).",
         "🚴 مثال: ۲ جلسه × ۳۰ دقیقه کاردیوی پیوسته + ۱ جلسه اینتروال کوتاه (مثلاً ۸ تا ۱۰ بار ۳۰ ثانیه تند و ۹۰ ثانیه آرام).",
         "🚶 پیاده‌روی روزانه حدود ۷ تا ۱۰ هزار قدم برای حفظ تناسب عالی است.",
         "🏋️ کاردیو را بعد از وزنه یا در روز جدا بگذار؛ روز پا اینتروال سنگین نزن."],
}

NUTRITION = {
 "fat": ["📉 کسری ملایم: حدود ۳۰۰ تا ۶۰۰ کالری کمتر از کالری نگهداری. کاهش وزن واقع‌بینانه حدود ۰٫۵ تا ۱ درصد وزن بدن در هفته است.",
         "🥩 پروتئین بالا در هر وعده (مرغ، ماهی، تخم‌مرغ، ماست، پنیر، عدس و لوبیا) تا عضله حفظ شود و دیرتر گرسنه شوی.",
         "🥑 چربی متوسط (حدود ۲۵ تا ۳۰ درصد کالری): روغن را با قاشق اندازه بگیر و سرخ‌کردنی را کم کن.",
         "🍚 کربوهیدرات = بقیهٔ کالری، بیشتر از منابع پرفیبر: نان سنگک یا جو، برنج کمتر و همراه سالاد، حبوبات، میوه.",
         "🍽 الگوی بشقاب: نصف بشقاب سبزی و سالاد، یک‌چهارم پروتئین، یک‌چهارم برنج یا نان.",
         "🥤 نوشابه، آبمیوهٔ صنعتی، شیرینی و تنقلات را حذف یا خیلی کم کن؛ چای و قهوه بدون قند یا با قند کم."],
 "lean": ["📈 مازاد ملایم: حدود ۳۰۰ تا ۵۰۰ کالری بیشتر از نگهداری (ربات هر هفته بر اساس روند وزنت خودکار تنظیمش می‌کند).",
          "🥩 پروتئین حدود ۱٫۶ تا ۲٫۲ گرم به ازای هر کیلو وزن، پخش در ۴ تا ۵ وعده.",
          "🥑 چربی حدود ۲۵ درصد کالری؛ کربوهیدرات بقیه، به‌خصوص قبل و بعد از تمرین (برنج، نان، سیب‌زمینی، موز، خرما).",
          "🍽 اگر اشتها کم است: وعده‌ها را ۵ تا ۶ تا کن و از خوراکی‌های پرکالری کم‌حجم کمک بگیر (مغزها، کره بادام‌زمینی، خرما، شیر پرچرب، روغن زیتون روی غذا).",
          "🥛 نوشیدنی‌های کالری‌دار مثل شیر و اسموتی (شیر + موز + جو دوسر) راه ساده‌ای برای رسیدن به کالری‌اند."],
 "fit": ["⚖️ کالری حدود نگهداری؛ برای ریکامپ (چربی کمتر و عضلهٔ بیشتر) ۱۰۰ تا ۳۰۰ کالری کمتر، به‌خصوص در روزهای استراحت.",
         "🥩 پروتئین حدود ۱٫۶ تا ۲٫۲ گرم به ازای هر کیلو وزن.",
         "🥑 چربی حدود ۲۵ تا ۳۰ درصد کالری؛ کربوهیدرات بقیه و روزهای تمرین کمی بیشتر.",
         "📏 هر هفته وزن و دور کمر را چک کن: اگر ۲ هفته پشت سر هم وزن بالا رفت، ۱۰۰ تا ۲۰۰ کالری کم کن؛ اگر قدرتت افت کرد، کمی اضافه کن."],
}

SAMPLE_DAY = {
 "fat": [("🌅 صبحانه", "۲ تخم‌مرغ آب‌پز + یک تکهٔ کوچک نان سنگک + پنیر کم‌چرب + خیار و گوجه + چای بدون قند"),
         ("🍎 میان‌وعده", "یک سیب یا پرتقال + یک کاسه ماست کم‌چرب"),
         ("🍛 ناهار", "جوجه‌کباب یا مرغ گریل (۱۵۰ تا ۲۰۰ گرم) + ۴ تا ۵ قاشق برنج + سالاد شیرازی + ماست"),
         ("🥜 عصر", "۱۰ تا ۱۵ عدد بادام یا یک لیوان شیر کم‌چرب"),
         ("🌙 شام", "عدسی یا خوراک لوبیا با نان کم، یا املت سبزیجات با ۲ تخم‌مرغ + سبزی خوردن")],
 "lean": [("🌅 صبحانه", "۳ تخم‌مرغ (نیمرو یا املت) + نان بربری یا سنگک + پنیر و گردو + یک لیوان شیر پرچرب"),
          ("🥛 میان‌وعده", "اسموتی شیر + موز + جو دوسر + یک قاشق کره بادام‌زمینی"),
          ("🍛 ناهار", "چلو جوجه‌کباب یا چلوکباب کوبیده با برنج کافی + ماست + سالاد"),
          ("🍌 قبل یا بعد از تمرین", "موز + ۳ تا ۴ خرما + ماست، یا ساندویچ نان و پنیر و گردو"),
          ("🌙 شام", "عدس‌پلو با مرغ یا ماکارونی با گوشت چرخ‌کرده + ماست")],
 "fit": [("🌅 صبحانه", "۲ تا ۳ تخم‌مرغ + نان سنگک + پنیر + خیار و گوجه + چای"),
         ("🍎 میان‌وعده", "یک میوه + یک مشت کوچک گردو یا بادام"),
         ("🍛 ناهار", "خورش قرمه‌سبزی یا قیمه با برنج اندازه (۶ تا ۸ قاشق) + سالاد + ماست"),
         ("🥛 عصر", "ماست یونانی یا یک لیوان شیر + یک میوه"),
         ("🌙 شام", "ماهی یا مرغ با سبزیجات و سیب‌زمینی یا کمی برنج")],
}

def supplements(cat, kidney=False):
    """Supplement notes, consistent with nutrition.recommend_supplements (creatine optional, gainer only for lean gain, no fat burners)."""
    cr = ("• کراتین را به‌خاطر نگرانی کلیوی پیشنهاد نمی‌کنم؛ اول با پزشک صحبت کن." if kidney else None)
    if cat == "fat":
        return ["• اول کالری و پروتئین غذا را درست کن؛ قرص و پودر «چربی‌سوز» لازم نیست و معمولاً تبلیغاتی است.",
                cr or "• کراتین مونوهیدرات ۳ تا ۵ گرم در روز اختیاری است و کمک می‌کند در کسری کالری قدرتت بماند؛ آب کافی بنوش.",
                "• گینر برای کاهش چربی مناسب نیست.",
                "• پروتئین پودری (وی) فقط اگر با غذا به پروتئین روزانه نمی‌رسی.",
                "• کافئینِ چای یا قهوه قبل از تمرین اگر به آن حساس نیستی، اختیاری است."]
    if cat == "lean":
        return [cr or "• کراتین مونوهیدرات ۳ تا ۵ گرم هر روز (بدون دورهٔ بارگیری)؛ ساده و مؤثر برای قدرت، ولی اجباری نیست.",
                "• گینر فقط اگر با غذا به کالری هدف نمی‌رسی؛ معمولاً یک اسکوپ بعد از تمرین کافی است.",
                "• پروتئین غذایی اولویت دارد؛ پودر پروتئین فقط برای پرکردن کمبود.",
                "• مولتی‌ویتامین فقط اگر غذایت خیلی یکنواخت است؛ جادو نمی‌کند."]
    return [cr or "• کراتین ۳ تا ۵ گرم در روز اختیاری است.",
            "• گینر لازم نیست، مگر اشتهایت خیلی کم باشد.",
            "• پروتئین پودری فقط اگر با غذا به پروتئین روزانه نمی‌رسی."]

SAFETY_ALL = ["⚠️ این برنامه آموزشی است و جای پزشک یا متخصص تغذیه را نمی‌گیرد.",
              "🩺 اگر بیماری قلبی، فشار خون، دیابت، مشکل کلیه یا آسیب مفصلی داری، باردار هستی یا دارو مصرف می‌کنی، قبل از شروع با پزشک مشورت کن.",
              "🛑 هنگام تمرین اگر درد قفسهٔ سینه، سرگیجه، تنگی نفس غیرعادی یا درد تیز مفصل داشتی، همان لحظه متوقف شو."]
SAFETY = {
 "fat": ["📉 رژیم‌های خیلی کم‌کالری (تقریباً زیر ۱۵۰۰ کالری برای آقایان و زیر ۱۲۰۰ برای خانم‌ها) فقط زیر نظر پزشک.",
         "🐢 کاهش وزن خیلی سریع عضله را هم از بین می‌برد؛ عجله نکن.",
         "👟 کفش مناسب بپوش و حجم تمرین و کاردیو را آرام‌آرام بالا ببر تا زانو و کمر آسیب نبینند.",
         "🧠 اگر رابطه‌ات با غذا آزاردهنده شده (پرخوری عصبی یا وسواس رژیم)، با متخصص صحبت کن."],
 "lean": ["🩺 اگر بی‌اشتهایی شدید، کاهش وزن ناخواسته یا مشکل گوارشی داری، اول با پزشک بررسی کن؛ کم‌وزنی گاهی علت پزشکی دارد.",
          "🍔 افزایش وزن با فست‌فود و شیرینی زیاد یعنی چربی بیشتر، نه عضله؛ غذای واقعی بخور.",
          "🧠 اگر رابطه‌ات با غذا آزاردهنده است، با متخصص صحبت کن."],
 "fit": ["😴 خواب ۷ تا ۹ ساعت و هر ۶ تا ۸ هفته یک هفتهٔ سبک (دیلود) برای ریکاوری.",
         "📈 وزنه‌ها را آرام و با فرم درست بالا ببر؛ عجله برای رکورد زدن آسیب می‌زند."],
}

# ---------------------------------------------------------------- personal numbers (estimates)
FLOOR_KCAL = {"m": 1500, "f": 1200}     # don't suggest less than this without medical supervision

def numbers(u, cat, weight=None):
    """Daily calories & macros for a category from the bot's own maintenance estimate (Mifflin-St Jeor x activity, nutrition.targets).
    fat: deficit ~20% of maintenance (300-600 kcal), protein from a reference weight (weight at BMI 25 when above it);
    lean: the bot's own surplus; fit: maintenance. -> dict or None when the profile is incomplete."""
    import nutrition as N
    if not (u.get("height") and u.get("age") and (weight or u.get("weight"))): return None
    w = float(weight or u["weight"]); sex = _sex(u.get("sex"))
    t = N.targets(u, w); maint = t["tdee"]; gk = float(u.get("protein_gk") or (1.8 if sex == "f" else 2.0))
    h = float(u["height"]) / 100.0; ref = w
    if cat == "fat":
        ref = min(w, BMI_OVER * h * h)
        delta = -int(round(min(600, max(300, 0.20 * maint)) / 50.0) * 50)
        kcal = max(FLOOR_KCAL[sex], maint + delta); fat_pct = 0.30
    elif cat == "lean":
        delta = int(u.get("surplus") or 0); kcal = maint + delta; fat_pct = 0.25
    else:
        delta = 0; kcal = maint; fat_pct = 0.30
    prot = gk * ref
    fat = max(fat_pct * kcal / 9.0, 0.6 * ref)
    carbs = max(0.0, (kcal - prot * 4 - fat * 9) / 4.0)
    return dict(maint=int(round(maint)), kcal=int(round(kcal)), delta=int(round(kcal - maint)), protein=int(round(prot)), fat=int(round(fat)),
                carbs=int(round(carbs)), fiber=int(round(14 * kcal / 1000.0)), water_l=round(35 * w / 1000.0, 1), ref_w=round(ref, 1), gk=gk)
