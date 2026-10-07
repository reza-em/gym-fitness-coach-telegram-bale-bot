"""Exercise library (gym with full equipment) + session templates. Persian names/how-to; all loads are in kg.
kind: c = compound, i = isolation. inc = smallest sensible jump (kg). avoid = injury keys for which the exercise is replaced/dropped."""

INJURIES = {"shoulder": "شانه", "back": "کمر", "knee": "زانو", "elbow": "آرنج", "wrist": "مچ دست", "neck": "گردن"}

def E(fa, en, grp, kind, eq, inc, rest, how, alts=(), avoid=()):
    return dict(fa=fa, en=en, grp=grp, kind=kind, eq=eq, inc=inc, rest=rest, how=how, alts=list(alts), avoid=set(avoid))

EX = {
 "bench_bb": E("پرس سینه هالتر", "Barbell bench press", "سینه", "c", "هالتر", 2.5, 120,
    "روی نیمکت صاف دراز بکش، کتف‌ها را جمع و پایین نگه دار. هالتر را با کنترل تا میانهٔ سینه پایین بیاور و بدون جداشدن باسن از نیمکت بالا بده. پاها محکم روی زمین؛ مچ‌ها صاف.",
    ["bench_db", "chest_press_m"], ["shoulder", "wrist"]),
 "bench_db": E("پرس سینه دمبل", "Dumbbell bench press", "سینه", "c", "دمبل", 2, 105,
    "دمبل‌ها را کنار سینه نگه دار، آرنج‌ها حدود ۴۵–۶۰ درجه از بدن فاصله. بدون برخورد دمبل‌ها بالا ببر و آرام پایین بیاور تا کشش سینه حس شود.",
    ["chest_press_m", "pec_fly"], ["shoulder"]),
 "incline_db": E("پرس بالاسینه دمبل", "Incline dumbbell press", "سینه", "c", "دمبل", 2, 105,
    "شیب نیمکت ۲۵–۳۰ درجه. دمبل‌ها را از بالای قفسهٔ سینه بالا ببر و با کنترل پایین بیاور. شانه‌ها را بالا نکش.",
    ["chest_press_m", "pec_fly"], ["shoulder"]),
 "chest_press_m": E("پرس سینه دستگاه", "Machine chest press", "سینه", "c", "دستگاه", 2.5, 90,
    "صندلی را طوری تنظیم کن که دسته‌ها هم‌سطح میانهٔ سینه باشد. کمر چسبیده به پشتی، هل بده تا آرنج تقریباً صاف شود (قفل نکن) و آرام برگرد.",
    ["pec_fly"], []),
 "pec_fly": E("فلای سینه (دستگاه پروانه)", "Pec deck fly", "سینه", "i", "دستگاه", 2.5, 75,
    "آرنج کمی خم، دست‌ها را در یک قوس جلو بیاور و سینه را فشار بده؛ برگشت آهسته و بدون رها کردن وزنه.",
    ["cable_fly"], ["shoulder"]),
 "cable_fly": E("کراس‌اور سیم‌کش", "Cable crossover", "سینه", "i", "سیم‌کش", 2.5, 75,
    "یک قدم جلو، تنه کمی خم. دسته‌ها را در قوس از بالا/پهلو جلوی سینه بیاور و یک ثانیه نگه دار.",
    [], ["shoulder"]),
 "row_cable": E("زیربغل سیم‌کش نشسته", "Seated cable row", "پشت", "c", "سیم‌کش", 2.5, 105,
    "کمر صاف، سینه بالا. دسته را به شکم نزدیک کن و کتف‌ها را به هم برسان؛ برگشت آهسته بدون خم‌شدن زیاد تنه.",
    ["row_machine"], []),
 "row_machine": E("زیربغل دستگاه (با تکیه‌گاه سینه)", "Chest-supported machine row", "پشت", "c", "دستگاه", 2.5, 90,
    "سینه را به تکیه‌گاه بچسبان. آرنج‌ها را عقب بکش و کتف‌ها را جمع کن؛ برگشت کنترل‌شده. گزینهٔ مناسب برای کمر حساس.",
    ["row_cable"], []),
 "row_db": E("زیربغل دمبل تک‌دست", "One-arm dumbbell row", "پشت", "c", "دمبل", 2, 90,
    "یک دست و یک زانو روی نیمکت، کمر صاف. دمبل را به سمت کمر بکش (نه به سمت شانه) و آرام پایین بده.",
    ["row_machine", "row_cable"], ["back"]),
 "lat_pd": E("لت‌پول‌داون (سیم‌کش از بالا)", "Lat pulldown", "پشت", "c", "سیم‌کش", 2.5, 90,
    "دست‌ها کمی بازتر از شانه. سینه را بالا بیاور و میله را تا بالای سینه بکش، آرنج‌ها به پایین/پهلو. بدون تاب‌دادن بدن.",
    ["row_cable"], []),
 "face_pull": E("فیس‌پول", "Face pull", "پشت‌شانه", "i", "سیم‌کش", 2.5, 60,
    "طناب را هم‌سطح صورت بکش، آرنج‌ها بالا و بیرون، دست‌ها را از هم باز کن و کتف‌ها را جمع کن. سبک و تمیز؛ برای سلامت شانه عالیه.",
    ["rear_delt"], []),
 "ohp_db": E("پرس سرشانه دمبل", "Dumbbell shoulder press", "شانه", "c", "دمبل", 2, 105,
    "نشسته با پشتی، دمبل‌ها کنار گوش. بالای سر بالا ببر بدون قوس‌دادن کمر و آرام پایین بیاور تا هم‌سطح گوش.",
    ["ohp_machine", "lateral"], ["shoulder", "neck"]),
 "ohp_machine": E("پرس سرشانه دستگاه", "Machine shoulder press", "شانه", "c", "دستگاه", 2.5, 90,
    "صندلی را تنظیم کن که دسته‌ها هم‌سطح شانه باشد. کمر چسبیده به پشتی؛ بالا هل بده و آرام برگرد.",
    ["lateral"], ["shoulder"]),
 "lateral": E("نشر جانب دمبل", "Dumbbell lateral raise", "شانه", "i", "دمبل", 1, 60,
    "دمبل سبک، آرنج کمی خم. تا هم‌سطح شانه از پهلو بالا ببر (انگار می‌خواهی کوزه بریزی)، بدون تاب‌دادن بدن و آرام پایین بیاور.",
    ["face_pull"], ["shoulder"]),
 "rear_delt": E("نشر خم / پروانهٔ معکوس", "Reverse pec deck", "پشت‌شانه", "i", "دستگاه", 2.5, 60,
    "سینه به پشتی، دسته‌ها را به عقب باز کن و کتف‌ها را کمی جمع کن؛ وزنه سبک و حرکت کنترل‌شده.", [], []),
 "curl_db": E("جلوبازو دمبل", "Dumbbell curl", "جلوبازو", "i", "دمبل", 1, 60,
    "ایستاده، آرنج‌ها کنار بدن ثابت. دمبل را بالا بیاور، بالا کمی فشار بده و آرام (۲–۳ ثانیه) پایین ببر. بدون تاب‌دادن کمر.",
    ["curl_cable", "hammer"], ["elbow", "wrist"]),
 "curl_cable": E("جلوبازو سیم‌کش", "Cable curl", "جلوبازو", "i", "سیم‌کش", 2.5, 60,
    "رو به دستگاه، آرنج‌ها ثابت کنار بدن؛ دسته را بالا بیاور و آهسته برگردان. کشش ثابت روی عضله می‌ماند.", ["hammer"], ["elbow"]),
 "hammer": E("جلوبازو چکشی", "Hammer curl", "جلوبازو", "i", "دمبل", 1, 60,
    "کف دست‌ها رو به هم (حالت چکش). مثل جلوبازو معمولی بالا بیاور؛ ساعد و جلوبازو را با هم درگیر می‌کند.", [], ["elbow"]),
 "tri_pd": E("پشت‌بازو سیم‌کش (پوش‌داون)", "Triceps pushdown", "پشت‌بازو", "i", "سیم‌کش", 2.5, 60,
    "آرنج‌ها چسبیده به پهلو، فقط ساعد حرکت کند. پایین هل بده تا کامل صاف شود و آرام برگرد.", ["tri_overhead"], ["elbow"]),
 "tri_overhead": E("پشت‌بازو بالاسر (سیم‌کش/دمبل)", "Overhead triceps extension", "پشت‌بازو", "i", "سیم‌کش", 2.5, 60,
    "آرنج‌ها رو به بالا و نزدیک سر؛ ساعد را از پشت سر صاف کن و آرام برگردان. کشش خوبی روی بخش بلند پشت‌بازو می‌دهد.", [], ["elbow", "shoulder"]),
 "squat_bb": E("اسکوات هالتر", "Barbell back squat", "پا", "c", "هالتر", 2.5, 150,
    "هالتر روی عضلات پشت‌شانه، پاها به عرض شانه. با شکم سفت پایین برو تا ران موازی زمین (یا کمی پایین‌تر)، زانوها در راستای پنجه، و با فشار روی کف پا بالا بیا. اگر ایمنی لازم داری از رک/سیف استفاده کن.",
    ["leg_press", "hip_thrust"], ["back", "knee"]),
 "leg_press": E("پرس پا", "Leg press", "پا", "c", "دستگاه", 5, 120,
    "پشت و باسن چسبیده به صندلی، پاها به عرض شانه وسط صفحه. تا زاویهٔ حدود ۹۰ درجه پایین بیا (باسن بلند نشود) و بدون قفل‌کردن زانو هل بده.",
    ["hip_thrust", "leg_curl"], ["knee"]),
 "rdl": E("ددلیفت رومانیایی", "Romanian deadlift", "پشت‌ران", "c", "هالتر", 2.5, 120,
    "هالتر نزدیک پا، زانوها کمی خم، باسن را به عقب ببر و کمر کاملاً صاف بماند تا کشش پشت‌ران حس شود؛ با فشار باسن به جلو برگرد.",
    ["leg_curl", "hip_thrust"], ["back"]),
 "leg_curl": E("پشت‌ران خوابیده (لگ‌کرل)", "Lying leg curl", "پشت‌ران", "i", "دستگاه", 2.5, 75,
    "لگن چسبیده به نیمکت. پاشنه را به سمت باسن بیاور، یک ثانیه نگه دار و آرام برگردان.", [], []),
 "leg_ext": E("جلوران (لگ‌اکستنشن)", "Leg extension", "جلوران", "i", "دستگاه", 2.5, 75,
    "زانو هم‌راستای محور دستگاه. پا را بالا ببر و جلوران را فشار بده، آرام پایین بیاور؛ تکان‌های ناگهانی ممنوع.", [], ["knee"]),
 "lunge_db": E("لانج دمبل", "Dumbbell lunge", "پا", "c", "دمبل", 2, 90,
    "قدم بلند به جلو (یا اسپلیت اسکوات ثابت). تنه صاف، زانوی جلو هم‌راستای پنجه؛ زانوی عقب را تا نزدیک زمین پایین ببر و با پاشنهٔ جلو بالا بیا.",
    ["leg_press", "hip_thrust"], ["knee"]),
 "hip_thrust": E("هیپ‌ترست", "Hip thrust", "باسن", "c", "هالتر", 5, 105,
    "کتف‌ها روی نیمکت، هالتر (با پد) روی لگن. با فشار پاشنه‌ها باسن را بالا ببر تا بدن از شانه تا زانو صاف شود، یک ثانیه سفت کن و پایین بیاور.",
    ["leg_curl"], []),
 "calf": E("ساق پا (ایستاده/دستگاه)", "Calf raise", "ساق", "i", "دستگاه", 5, 60,
    "کف پنجه روی لبهٔ سکو، تا حد امکان بالا برو، ۱–۲ ثانیه نگه دار و آرام تا کشش کامل پایین بیا. دامنهٔ کامل مهم‌تر از وزنه است.", [], []),
 "cable_crunch": E("کرانچ سیم‌کش", "Cable crunch", "شکم", "i", "سیم‌کش", 2.5, 60,
    "زانو زده، طناب کنار سر؛ ستون فقرات را خم کن و آرنج را به سمت زانو بیاور (نه فقط خم‌شدن از لگن). آرام برگرد.", [], ["back", "neck"]),
}

EX.update({
 "cable_kick": E("کیک‌بک باسن سیم‌کش", "Cable glute kickback", "باسن", "i", "سیم‌کش", 2.5, 60,
    "بند مچ‌بند را به مچ پا ببند، کمی به جلو خم شو و به دستگاه تکیه کن. پا را با زانوی تقریباً صاف به عقب ببر و باسن را سفت کن، بدون قوس‌دادن کمر؛ آرام برگرد.",
    ["hip_thrust"], ["back"]),
 "abduct_m": E("ابداکتور دستگاه (بیرون ران)", "Machine hip abduction", "باسن", "i", "دستگاه", 2.5, 60,
    "کمر چسبیده به پشتی، زانوها را با کنترل به بیرون باز کن و یک ثانیه نگه دار؛ برگشت آهسته، بدون تاب‌دادن تنه.", ["cable_kick"], []),
 "goblet_squat": E("اسکوات گابلت (دمبل)", "Goblet squat", "پا", "c", "دمبل", 2, 90,
    "دمبل را عمودی جلوی سینه نگه دار، پاها کمی بازتر از شانه. با تنهٔ صاف و سینهٔ بالا پایین برو تا ران موازی زمین و با فشار پاشنه بالا بیا. گزینهٔ ملایم‌تر برای کمر و زانو.",
    ["leg_press", "hip_thrust"], ["knee"]),
})
# free-exercise-db (Unlicense / public domain) ids used for the images
FED = {
 "bench_bb": "Barbell_Bench_Press_-_Medium_Grip", "bench_db": "Dumbbell_Bench_Press", "incline_db": "Incline_Dumbbell_Press", "chest_press_m": "Leverage_Chest_Press",
 "pec_fly": "Butterfly", "cable_fly": "Cable_Crossover", "row_cable": "Seated_Cable_Rows", "row_machine": "Leverage_Iso_Row", "row_db": "One-Arm_Dumbbell_Row",
 "lat_pd": "Wide-Grip_Lat_Pulldown", "face_pull": "Face_Pull", "ohp_db": "Dumbbell_Shoulder_Press", "ohp_machine": "Leverage_Shoulder_Press", "lateral": "Side_Lateral_Raise",
 "rear_delt": "Reverse_Machine_Flyes", "curl_db": "Dumbbell_Alternate_Bicep_Curl", "curl_cable": "Standing_Biceps_Cable_Curl", "hammer": "Hammer_Curls",
 "tri_pd": "Triceps_Pushdown", "tri_overhead": "Cable_Rope_Overhead_Triceps_Extension", "squat_bb": "Barbell_Full_Squat", "leg_press": "Leg_Press", "rdl": "Romanian_Deadlift",
 "leg_curl": "Lying_Leg_Curls", "leg_ext": "Leg_Extensions", "lunge_db": "Dumbbell_Lunges", "hip_thrust": "Barbell_Hip_Thrust", "calf": "Standing_Calf_Raises",
 "cable_crunch": "Cable_Crunch", "cable_kick": "One-Legged_Cable_Kickback", "abduct_m": "Thigh_Abductor", "goblet_squat": "Goblet_Squat",
}
for _k, _v in FED.items(): EX[_k]["fed"] = _v

# extra tips + common mistakes: id -> (tips, mistakes)
TIPS = {
 "bench_bb": ("هالتر را روی کف دست (نه انگشتان) بگذار و آرنج‌ها را حدود ۴۵–۶۰ درجه از بدن نگه دار؛ نفس را موقع پایین‌آوردن بگیر و موقع بالا دادن بیرون بده. حتماً با هالتر سنگین از رک/همیار استفاده کن.",
             "برگشت هالتر روی گردن/گلو، جداشدن باسن از نیمکت، بازکردن بیش از حد آرنج‌ها (فشار روی شانه)، پرش هالتر از روی سینه."),
 "bench_db": ("دمبل‌ها را کنار هم و موازی بالا ببر، پایین‌آوردن آهسته (۲–۳ ثانیه) تا کشش سینه.", "دمبل‌ها را خیلی پایین بردن (فشار شانه)، برخورد دمبل‌ها در بالا، قوس شدید کمر."),
 "incline_db": ("شیب ۲۵–۳۰ درجه کافی است؛ بالاتر از آن شانه بیشتر کار می‌کند.", "شیب زیاد نیمکت، بالا کشیدن شانه‌ها تا گوش، پرتاب وزنه از پایین."),
 "chest_press_m": ("ارتفاع صندلی را طوری بگذار که دسته‌ها هم‌سطح میانهٔ سینه باشد. کتف‌ها پشت‌ به پشتی.", "جداشدن کمر از پشتی، قفل‌کردن شدید آرنج، شتاب‌دادن با تکان بدن."),
 "pec_fly": ("به‌جای وزنهٔ سنگین روی کشش و فشار سینه تمرکز کن؛ آرنج‌ها کمی خم و ثابت.", "کشیدن دسته‌ها با شانه، وزنهٔ زیاد با دامنهٔ کوتاه، رهاکردن ناگهانی وزنه."),
 "cable_fly": ("حرکت مثل در آغوش گرفتن یک درخت بزرگ؛ در نقطهٔ بسته یک ثانیه فشار بده.", "خم‌کردن آرنج‌ها (تبدیل به پرس)، تاب‌دادن تنه، وزنهٔ بیش از حد."),
 "row_cable": ("اول کتف‌ها را عقب بیاور، بعد آرنج را بکش؛ سینه بالا و کمر صاف.", "عقب و جلوی زیاد تنه، شانه‌ها بالا (به سمت گوش)، کشیدن فقط با دست."),
 "row_machine": ("سینه را به تکیه‌گاه بچسبان و آرنج‌ها را به سمت پشت و پایین بکش.", "جداکردن سینه از تکیه‌گاه، شانه‌های بالا‌آمده، شتاب دادن."),
 "row_db": ("دمبل را به سمت کمر (نه شانه) بکش و در بالا یک ثانیه نگه دار؛ تنه ثابت.", "چرخش تنه برای بالا بردن وزنه، گرد شدن کمر، دامنهٔ کوتاه."),
 "lat_pd": ("قبل از کشیدن سینه را بالا بیاور و کتف‌ها را پایین بده؛ میله را به بالای سینه بکش.", "کشیدن میله پشت گردن، عقب‌رفتن زیاد تنه (تاب)، کشیدن با بازوها به‌جای پشت."),
 "face_pull": ("وزنهٔ سبک؛ در انتها دست‌ها را بیرون بچرخان (چرخش خارجی) و کتف‌ها را جمع کن.", "وزنهٔ زیاد و استفاده از کمر، بالا‌بردن شانه‌ها، کشیدن طناب به سمت شکم."),
 "ohp_db": ("شکم و باسن را سفت کن؛ دمبل‌ها کمی جلوتر از خط شانه باشند و مسیر قوس‌دار به بالای سر.", "قوس شدید کمر، پایین‌آوردن بیش از حد دمبل‌ها، تکان دادن پا برای بالا بردن (پوش‌پرس ناخواسته)."),
 "ohp_machine": ("دسته‌ها را هم‌سطح شانه بگذار و بدون بالاکشیدن شانه‌ها فشار بده.", "ارتفاع نادرست صندلی، بالارفتن شانه‌ها تا گوش، قوس کمر."),
 "lateral": ("وزنهٔ سبک و آرام؛ آرنج کمی بالاتر از مچ باشد. ۲ ثانیه پایین‌آوردن.", "تاب‌دادن بدن برای بالا بردن، بالابردن بالاتر از شانه، شانه‌های بالا‌کشیده."),
 "rear_delt": ("سینه به پشتی و حرکت از آرنج؛ انقباض کوتاه در انتها.", "استفاده از وزنهٔ زیاد و حرکت با کمر، کوتاه‌کردن حرکت."),
 "curl_db": ("آرنج ثابت کنار بدن؛ در بالا کف دست را کمی به بیرون بچرخان؛ پایین‌آوردن آهسته.", "تاب‌دادن کمر، حرکت آرنج به جلو، وزنهٔ زیاد با دامنهٔ ناقص."),
 "curl_cable": ("آرنج‌ها ثابت و کشش مداوم کابل؛ در بالا یک ثانیه انقباض.", "عقب‌ و جلو رفتن تنه، بالا بردن آرنج‌ها، رها کردن وزنه."),
 "hammer": ("مچ را خنثی نگه دار؛ آرنج‌ها کنار بدن.", "تاب‌دادن کمر، وزنهٔ خیلی زیاد، چرخاندن مچ."),
 "tri_pd": ("آرنج‌ها چسبیده به پهلو، در پایین ۱ ثانیه انقباض؛ تنه کمی خم.", "آرنج‌های باز‌شده، استفاده از وزن بدن (خم شدن زیاد)، دامنهٔ ناقص."),
 "tri_overhead": ("آرنج‌ها به سمت بالا و نزدیک سر؛ کشش کامل در پایین.", "باز شدن آرنج‌ها به بیرون، قوس کمر، وزنهٔ زیاد با تکان."),
 "squat_bb": ("نگاه رو به جلو، شکم سفت (نفس در شکم)، زانوها هم‌راستای پنجه؛ وزن روی میانهٔ پا. از رک و سیف استفاده کن.", "فروریختن زانوها به داخل، گرد شدن کمر در پایین، جداشدن پاشنه از زمین، نیم‌اسکوات با وزنهٔ سنگین."),
 "leg_press": ("پاها را به‌گونه‌ای بگذار که زانو و پنجه هم‌راستا باشد؛ پایین‌ترین نقطه جایی که باسن از صندلی جدا نشود.", "قفل‌کردن کامل زانوها، بلند شدن باسن و گرد شدن کمر در پایین، دامنهٔ خیلی کوتاه."),
 "rdl": ("هالتر نزدیک ساق بماند، باسن به عقب برود (حرکت لولایی)، کمر صاف؛ تا کشش پشت‌ران پایین برو.", "گرد شدن کمر، دور شدن هالتر از بدن، خم‌کردن بیش از حد زانو (تبدیل به اسکوات)."),
 "leg_curl": ("لگن را به نیمکت بچسبان؛ بالا فشار، پایین آهسته (۲–۳ ثانیه).", "بالا آمدن باسن و قوس کمر، وزنهٔ زیاد با تکان، دامنهٔ ناقص."),
 "leg_ext": ("تنظیم محور دستگاه با زانو؛ در بالا ۱ ثانیه فشار، پایین آهسته.", "تکان ناگهانی وزنه، بلند شدن باسن از صندلی، وزنهٔ زیاد با فشار روی زانو."),
 "lunge_db": ("گام به اندازه‌ای بلند که زانوی جلو از پنجه جلوتر نرود؛ تنه صاف.", "گام کوتاه، خم‌شدن تنه به جلو، فرو‌ریختن زانوی جلو به داخل."),
 "hip_thrust": ("چانه کمی جمع، دنده‌ها پایین؛ در بالا باسن را سفت کن و کمر را قوس نده.", "قوس‌دادن کمر به‌جای باسن، پاهای بیش از حد دور یا نزدیک، بالا‌ آمدن با ضربه."),
 "calf": ("پایین‌ترین نقطه کشش کامل، بالا ۱–۲ ثانیه مکث؛ سرعت کم.", "ضربه‌ای حرکت‌کردن (فنری)، دامنهٔ ناقص، خم‌کردن زانو."),
 "cable_crunch": ("حرکت از ستون فقرات است، نه خم‌شدن از لگن؛ شکم را جمع کن و آرام برگرد.", "نشستن روی پاشنه و کشیدن با دست، استفاده از وزنهٔ زیاد با فشار گردن."),
 "cable_kick": ("باسن را سفت کن و حرکت را کوتاه و کنترل‌شده نگه دار؛ کمر ثابت.", "قوس کمر و چرخش لگن، تاب دادن پا، وزنهٔ زیاد."),
 "abduct_m": ("کمی به جلو خم شو تا باسن بیشتر درگیر شود؛ حرکت آهسته.", "ضربه‌ای باز‌کردن پاها، کمر جدا از پشتی، وزنهٔ زیاد با دامنهٔ ناقص."),
 "goblet_squat": ("دمبل را به سینه نزدیک نگه دار؛ آرنج‌ها بین زانوها پایین بروند.", "جلو رفتن زانوها بدون عقب رفتن باسن، گرد شدن کمر، بلند شدن پاشنه‌ها."),
}

# Tutorial links: aparat (search — no fake IDs) + youtube (direct if verified, else search)
TUTORIALS = {
 'bench_bb': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%B3%DB%8C%D9%86%D9%87%20%D9%87%D8%A7%D9%84%D8%AA%D8%B1%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=rT7DgCr-3pg', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Barbell+bench+press+common+mistakes+technique'},
 'bench_db': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%B3%DB%8C%D9%86%D9%87%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=VmB1G1K7v94', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Dumbbell+bench+press+common+mistakes+technique'},
 'incline_db': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%A8%D8%A7%D9%84%D8%A7%D8%B3%DB%8C%D9%86%D9%87%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=8iPEnn-ltC8', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Incline+dumbbell+press+common+mistakes+technique'},
 'chest_press_m': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%B3%DB%8C%D9%86%D9%87%20%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=xUm0BiZCWlQ', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Machine+chest+press+common+mistakes+technique'},
 'pec_fly': {"aparat": 'https://www.aparat.com/result/%D9%81%D9%84%D8%A7%DB%8C%20%D8%B3%DB%8C%D9%86%D9%87%20%28%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%20%D9%BE%D8%B1%D9%88%D8%A7%D9%86%D9%87%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=eozdVDA78K0', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Pec+deck+fly+common+mistakes+technique'},
 'cable_fly': {"aparat": 'https://www.aparat.com/result/%DA%A9%D8%B1%D8%A7%D8%B3%E2%80%8C%D8%A7%D9%88%D8%B1%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=Iwe6AmxVf7o', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Cable+crossover+common+mistakes+technique'},
 'row_cable': {"aparat": 'https://www.aparat.com/result/%D8%B2%DB%8C%D8%B1%D8%A8%D8%BA%D9%84%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D9%86%D8%B4%D8%B3%D8%AA%D9%87%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=GZbfZ033f74', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Seated+cable+row+common+mistakes+technique'},
 'row_machine': {"aparat": 'https://www.aparat.com/result/%D8%B2%DB%8C%D8%B1%D8%A8%D8%BA%D9%84%20%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%20%28%D8%A8%D8%A7%20%D8%AA%DA%A9%DB%8C%D9%87%E2%80%8C%DA%AF%D8%A7%D9%87%20%D8%B3%DB%8C%D9%86%D9%87%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=roCP6wCXPqo', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Chest-supported+machine+row+common+mistakes+technique'},
 'row_db': {"aparat": 'https://www.aparat.com/result/%D8%B2%DB%8C%D8%B1%D8%A8%D8%BA%D9%84%20%D8%AF%D9%85%D8%A8%D9%84%20%D8%AA%DA%A9%E2%80%8C%D8%AF%D8%B3%D8%AA%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=pYcpY20QaE8', "youtube_mistakes": 'https://www.youtube.com/results?search_query=One-arm+dumbbell+row+common+mistakes+technique'},
 'lat_pd': {"aparat": 'https://www.aparat.com/result/%D9%84%D8%AA%E2%80%8C%D9%BE%D9%88%D9%84%E2%80%8C%D8%AF%D8%A7%D9%88%D9%86%20%28%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D8%A7%D8%B2%20%D8%A8%D8%A7%D9%84%D8%A7%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=CAwf7n6Luuc', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Lat+pulldown+common+mistakes+technique'},
 'face_pull': {"aparat": 'https://www.aparat.com/result/%D9%81%DB%8C%D8%B3%E2%80%8C%D9%BE%D9%88%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=0Po47vvj9g4', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Face+pull+common+mistakes+technique'},
 'ohp_db': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%B3%D8%B1%D8%B4%D8%A7%D9%86%D9%87%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=qEwKCR5JCog', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Dumbbell+shoulder+press+common+mistakes+technique'},
 'ohp_machine': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D8%B3%D8%B1%D8%B4%D8%A7%D9%86%D9%87%20%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=Weu9HMHdiDA', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Machine+shoulder+press+common+mistakes+technique'},
 'lateral': {"aparat": 'https://www.aparat.com/result/%D9%86%D8%B4%D8%B1%20%D8%AC%D8%A7%D9%86%D8%A8%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=3VcKaXpzqRo', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Dumbbell+lateral+raise+common+mistakes+technique'},
 'rear_delt': {"aparat": 'https://www.aparat.com/result/%D9%86%D8%B4%D8%B1%20%D8%AE%D9%85%20/%20%D9%BE%D8%B1%D9%88%D8%A7%D9%86%D9%87%D9%94%20%D9%85%D8%B9%DA%A9%D9%88%D8%B3%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=ttvfGg9d76c', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Reverse+pec+deck+common+mistakes+technique'},
 'curl_db': {"aparat": 'https://www.aparat.com/result/%D8%AC%D9%84%D9%88%D8%A8%D8%A7%D8%B2%D9%88%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=ykJmrZ5v0Oo', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Dumbbell+curl+common+mistakes+technique'},
 'curl_cable': {"aparat": 'https://www.aparat.com/result/%D8%AC%D9%84%D9%88%D8%A8%D8%A7%D8%B2%D9%88%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=NFzTWp2qpiE', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Cable+curl+common+mistakes+technique'},
 'hammer': {"aparat": 'https://www.aparat.com/result/%D8%AC%D9%84%D9%88%D8%A8%D8%A7%D8%B2%D9%88%20%DA%86%DA%A9%D8%B4%DB%8C%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=zC3nLlEvin4', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Hammer+curl+common+mistakes+technique'},
 'tri_pd': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B4%D8%AA%E2%80%8C%D8%A8%D8%A7%D8%B2%D9%88%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%28%D9%BE%D9%88%D8%B4%E2%80%8C%D8%AF%D8%A7%D9%88%D9%86%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=2-LAMcpzODU', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Triceps+pushdown+common+mistakes+technique'},
 'tri_overhead': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B4%D8%AA%E2%80%8C%D8%A8%D8%A7%D8%B2%D9%88%20%D8%A8%D8%A7%D9%84%D8%A7%D8%B3%D8%B1%20%28%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4/%D8%AF%D9%85%D8%A8%D9%84%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=_gsUck-7M74', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Overhead+triceps+extension+common+mistakes+technique'},
 'squat_bb': {"aparat": 'https://www.aparat.com/result/%D8%A7%D8%B3%DA%A9%D9%88%D8%A7%D8%AA%20%D9%87%D8%A7%D9%84%D8%AA%D8%B1%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=ultWZbUMPL8', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Barbell+back+squat+common+mistakes+technique'},
 'leg_press': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B1%D8%B3%20%D9%BE%D8%A7%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=IZxyjW7MPJQ', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Leg+press+common+mistakes+technique'},
 'rdl': {"aparat": 'https://www.aparat.com/result/%D8%AF%D8%AF%D9%84%DB%8C%D9%81%D8%AA%20%D8%B1%D9%88%D9%85%D8%A7%D9%86%DB%8C%D8%A7%DB%8C%DB%8C%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=jEy_czb3RKA', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Romanian+deadlift+common+mistakes+technique'},
 'leg_curl': {"aparat": 'https://www.aparat.com/result/%D9%BE%D8%B4%D8%AA%E2%80%8C%D8%B1%D8%A7%D9%86%20%D8%AE%D9%88%D8%A7%D8%A8%DB%8C%D8%AF%D9%87%20%28%D9%84%DA%AF%E2%80%8C%DA%A9%D8%B1%D9%84%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=1Tq3QdYUuHs', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Lying+leg+curl+common+mistakes+technique'},
 'leg_ext': {"aparat": 'https://www.aparat.com/result/%D8%AC%D9%84%D9%88%D8%B1%D8%A7%D9%86%20%28%D9%84%DA%AF%E2%80%8C%D8%A7%DA%A9%D8%B3%D8%AA%D9%86%D8%B4%D9%86%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=ljO4jkwv8wQ', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Leg+extension+common+mistakes+technique'},
 'lunge_db': {"aparat": 'https://www.aparat.com/result/%D9%84%D8%A7%D9%86%D8%AC%20%D8%AF%D9%85%D8%A8%D9%84%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=D7KaRcUTQeE', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Dumbbell+lunge+common+mistakes+technique'},
 'hip_thrust': {"aparat": 'https://www.aparat.com/result/%D9%87%DB%8C%D9%BE%E2%80%8C%D8%AA%D8%B1%D8%B3%D8%AA%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=xDmFkJxPzeM', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Hip+thrust+common+mistakes+technique'},
 'calf': {"aparat": 'https://www.aparat.com/result/%D8%B3%D8%A7%D9%82%20%D9%BE%D8%A7%20%28%D8%A7%DB%8C%D8%B3%D8%AA%D8%A7%D8%AF%D9%87/%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=-M4-G8p8fmc', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Calf+raise+common+mistakes+technique'},
 'cable_crunch': {"aparat": 'https://www.aparat.com/result/%DA%A9%D8%B1%D8%A7%D9%86%DA%86%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/results?search_query=Cable+crunch+form', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Cable+crunch+common+mistakes+technique'},
 'cable_kick': {"aparat": 'https://www.aparat.com/result/%DA%A9%DB%8C%DA%A9%E2%80%8C%D8%A8%DA%A9%20%D8%A8%D8%A7%D8%B3%D9%86%20%D8%B3%DB%8C%D9%85%E2%80%8C%DA%A9%D8%B4%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/results?search_query=Cable+glute+kickback+form', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Cable+glute+kickback+common+mistakes+technique'},
 'abduct_m': {"aparat": 'https://www.aparat.com/result/%D8%A7%D8%A8%D8%AF%D8%A7%DA%A9%D8%AA%D9%88%D8%B1%20%D8%AF%D8%B3%D8%AA%DA%AF%D8%A7%D9%87%20%28%D8%A8%DB%8C%D8%B1%D9%88%D9%86%20%D8%B1%D8%A7%D9%86%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/results?search_query=Machine+hip+abduction+form', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Machine+hip+abduction+common+mistakes+technique'},
 'goblet_squat': {"aparat": 'https://www.aparat.com/result/%D8%A7%D8%B3%DA%A9%D9%88%D8%A7%D8%AA%20%DA%AF%D8%A7%D8%A8%D9%84%D8%AA%20%28%D8%AF%D9%85%D8%A8%D9%84%29%20%D9%81%D8%B1%D9%85%20%D8%B5%D8%AD%DB%8C%D8%AD', "youtube": 'https://www.youtube.com/watch?v=MeIiIdhvXT4', "youtube_mistakes": 'https://www.youtube.com/results?search_query=Goblet+squat+common+mistakes+technique'},
}

def yt_url(eid, kind="form"):
    """YouTube tutorial: verified direct video when available, else honest search. kind=mistakes -> search for mistakes."""
    t = TUTORIALS.get(eid) or {}
    if kind == "mistakes":
        return t.get("youtube_mistakes") or t.get("youtube") or ""
    return t.get("youtube") or ""

def aparat_url(eid):
    """Aparat tutorial search (Persian) — honest result page, no invented video IDs."""
    t = TUTORIALS.get(eid) or {}
    return t.get("aparat") or ""

def tutorial_links(eid):
    """List of (label_fa, url) for UI / PDF."""
    if eid not in EX: return []
    return [("آپارات (فارسی)", aparat_url(eid)), ("یوتیوب", yt_url(eid, "form")), ("یوتیوب — اشتباهات رایج", yt_url(eid, "mistakes"))]

# session templates: (exercise, priority) — priority 1 = essential; when time is short the highest numbers are dropped first.
TEMPLATES = {
 "ul": [   # 4 days: upper / lower / upper / lower
    ("بالاتنه A (قدرتی)", [("bench_bb", 1), ("row_cable", 1), ("ohp_db", 2), ("lat_pd", 2), ("curl_db", 3), ("tri_pd", 3), ("lateral", 4)]),
    ("پایین‌تنه A (قدرتی)", [("squat_bb", 1), ("rdl", 1), ("leg_press", 2), ("leg_curl", 2), ("calf", 3), ("cable_crunch", 4)]),
    ("بالاتنه B (حجمی)", [("incline_db", 1), ("row_db", 1), ("ohp_machine", 2), ("pec_fly", 3), ("face_pull", 3), ("hammer", 4), ("tri_overhead", 4)]),
    ("پایین‌تنه B (حجمی)", [("leg_press", 1), ("hip_thrust", 1), ("leg_curl", 2), ("leg_ext", 3), ("calf", 3), ("cable_crunch", 4)]),
 ],
 "fb": [   # 3 days: full body A / B / C
    ("تمام‌بدن A", [("squat_bb", 1), ("bench_bb", 1), ("row_cable", 1), ("ohp_db", 2), ("curl_db", 3), ("tri_pd", 3), ("cable_crunch", 4)]),
    ("تمام‌بدن B", [("rdl", 1), ("incline_db", 1), ("lat_pd", 1), ("lateral", 2), ("leg_curl", 2), ("hammer", 3), ("tri_overhead", 4)]),
    ("تمام‌بدن C", [("leg_press", 1), ("bench_db", 1), ("row_machine", 1), ("ohp_machine", 2), ("hip_thrust", 2), ("face_pull", 3), ("calf", 3)]),
 ],
}
TEMPLATES_F = {
 "ul": [   # 4 days, lower-body / glute emphasis, upper body toned (fewer sets, higher reps are applied in program.py)
    ("پایین‌تنه A (باسن و ران)", [("hip_thrust", 1), ("squat_bb", 1), ("rdl", 1), ("leg_press", 2), ("abduct_m", 3), ("calf", 4)]),
    ("بالاتنه A (فرم‌دهی)", [("lat_pd", 1), ("chest_press_m", 1), ("ohp_machine", 2), ("row_cable", 2), ("lateral", 3), ("tri_pd", 4), ("curl_cable", 4)]),
    ("پایین‌تنه B (باسن و پشت‌ران)", [("goblet_squat", 1), ("lunge_db", 1), ("cable_kick", 2), ("leg_curl", 2), ("leg_ext", 3), ("calf", 4)]),
    ("بالاتنه B + شکم", [("incline_db", 1), ("row_db", 1), ("face_pull", 2), ("lateral", 3), ("curl_db", 3), ("tri_overhead", 4), ("cable_crunch", 4)]),
 ],
 "fb": [   # 3 days full body, lower emphasis
    ("تمام‌بدن A (تأکید باسن)", [("squat_bb", 1), ("hip_thrust", 1), ("lat_pd", 1), ("chest_press_m", 2), ("cable_kick", 3), ("cable_crunch", 4)]),
    ("تمام‌بدن B (تأکید پا)", [("leg_press", 1), ("rdl", 1), ("incline_db", 1), ("row_cable", 1), ("ohp_machine", 2), ("abduct_m", 3), ("tri_pd", 4)]),
    ("تمام‌بدن C (باسن و پشت‌ران)", [("lunge_db", 1), ("bench_db", 1), ("row_machine", 1), ("cable_kick", 2), ("lateral", 2), ("leg_ext", 3), ("curl_cable", 4)]),
 ],
}
LOWER_GROUPS = {"پا", "پشت‌ران", "جلوران", "باسن", "ساق"}

def template(plan_type, sex="m"):
    """Session template list for a plan type ('ul' 4 days / 'fb' 3 days) and sex ('m' / 'f')."""
    return (TEMPLATES_F if sex == "f" else TEMPLATES)[plan_type]

PLAN_NAMES_F = {"ul": "۴ روز: پایین‌تنه/بالاتنه با تأکید باسن و پا", "fb": "تمام‌بدن (۳ روز) با تأکید باسن و پا"}
def plan_name(plan_type, sex="m"):
    names = PLAN_NAMES_F if sex == "f" else PLAN_NAMES
    if plan_type in names: return names[plan_type]
    n = plan_type[1:] if (plan_type or "")[:1] == "d" else "?"
    return f"برنامهٔ {n} روزه (بانک برنامه‌ها)"

def plan_type_for_days(n):
    """users.plan_type for a days-per-week count: 4 -> 'ul', 3 -> 'fb' (classic templates), 2/5/6 -> 'd2'/'d5'/'d6' (programs_db bank)."""
    n = int(n); return "ul" if n == 4 else "fb" if n == 3 else f"d{n}"

PLAN_NAMES = {"ul": "بالاتنه/پایین‌تنه (۴ روز)", "fb": "تمام‌بدن (۳ روز)"}

DAY_PRESETS = {      # python weekday: 0=Mon ... 5=Sat, 6=Sun
 4: [("شنبه، یکشنبه، سه‌شنبه، چهارشنبه", [5, 6, 1, 2]), ("شنبه، دوشنبه، چهارشنبه، جمعه", [5, 0, 2, 4])],
 3: [("شنبه، دوشنبه، چهارشنبه", [5, 0, 2]), ("یکشنبه، سه‌شنبه، پنجشنبه", [6, 1, 3])],
 2: [("شنبه، سه‌شنبه", [5, 1]), ("یکشنبه، چهارشنبه", [6, 2])],
 5: [("شنبه، یکشنبه، دوشنبه، چهارشنبه، پنجشنبه", [5, 6, 0, 2, 3]), ("شنبه، یکشنبه، سه‌شنبه، چهارشنبه، جمعه", [5, 6, 1, 2, 4])],
 6: [("شنبه تا پنجشنبه (جمعه استراحت)", [5, 6, 0, 1, 2, 3]), ("شنبه تا چهارشنبه + جمعه", [5, 6, 0, 1, 2, 4])],
}

def ex_name(eid): return EX[eid]["fa"] if eid in EX else eid

def program_exercises(plan_type, sex="m"):
    """All distinct exercise ids used by a plan type, in order of appearance."""
    seen = []
    for _t, items in template(plan_type, sex):
        for e, _p in items:
            if e not in seen: seen.append(e)
    return seen
