# Gym Fitness Coach — Workout Plan & Muscle-Gain Tracker Bot (Telegram & Bale)

> Telegram & Bale gym coach bot: weekly progressive-overload workout plan, set logging, next-weight suggestions, PRs, bodyweight charts, nutrition, creatine/gainer planning. Men/women programs. Persian UI.

## 🌐 فارسی

ربات تلگرام و بله **مربی بدنسازی**: برنامه هفتگی با اضافه‌بار تدریجی (برای آقایان و خانم‌ها)، ثبت وزنه×تکرار، پیشنهاد خودکار وزنه بعدی، رکوردها، ثبت وزن و اندازه‌ها با نمودار، تغذیه با کالری و پروتئین و منوی ایرانی، گینر و کراتین، یادآور و بازبینی هفتگی، آموزش تصویری حرکات.

**کلیدواژه‌ها:** برنامه بدنسازی، ربات بدنسازی، افزایش وزن، حجم‌گیری، برنامه تمرینی باشگاه، ربات مربی ورزشی تلگرام، کراتین، گینر، رژیم غذایی

## 🇬🇧 English

**Gym fitness coach bot for Telegram and Bale**: weekly workout plans with progressive overload (separate male/female programs), set logging with next-weight suggestions and personal records, bodyweight/measurement charts, nutrition targets (calories/protein), gainer & creatine scheduling, reminders, weekly review and exercise images/tutorial links. SQLite, Python.

**Keywords:** workout planner bot, gym tracker Telegram bot, progressive overload, muscle gain plan, bodybuilding program, fitness coach bot, weight gain, creatine schedule

## 🇷🇺 Русский

**Бот-тренер для зала в Telegram и Bale**: недельный план тренировок с прогрессией нагрузки (программы для мужчин и женщин), журнал подходов, подсказка следующего веса, рекорды, графики веса, питание (калории и белок), гейнер и креатин, напоминания. Интерфейс на персидском.

**Ключевые слова:** план тренировок в зале, бот фитнес тренер Telegram, набор мышечной массы, прогрессия нагрузки, бодибилдинг, креатин

## 🇩🇪 Deutsch

**Fitness-Coach-Bot für Telegram und Bale**: Wochentrainingsplan mit progressiver Überlastung (Programme für Männer und Frauen), Satz-Protokoll mit Gewichtsvorschlag und Rekorden, Gewichtsdiagramme, Ernährung (Kalorien/Protein), Gainer und Kreatin, Erinnerungen. Persische Oberfläche.

**Stichwörter:** Trainingsplan Bot, Fitnessstudio Tracker Telegram, Muskelaufbau Plan, progressive Überlastung, Krafttraining, Kreatin

---

## Features

- 8-week program with deload weeks; men/women split programs
- Set logging (weight x reps), 1RM estimates, next-weight suggestion, PRs
- Bodyweight and measurement charts
- Nutrition targets, Iranian meal menu, gainer/creatine placement
- Reminders and weekly review
- Exercise images/animations from Free Exercise DB (Unlicense) fetched via `fetch_exercise_media.py`
- One process per platform (Telegram / Bale) with shared core

## Setup

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
export FITNESS_TELEGRAM_BOT_TOKEN=...   # optional, @BotFather
export FITNESS_BALE_BOT_TOKEN=...       # optional, Bale @botfather
export OWNER_ID=123456789               # Telegram owner id; on Bale use the one-time /claim code printed in the log
./run.sh            # ./run.sh telegram | ./run.sh bale
./venv/bin/python test_offline.py
```

> **Configuration note:** the owner/admin identity is read from environment variables (`OWNER_ID`, `OWNER_USERNAME`, `SUPPORT_USERNAME`) with the placeholder `example_owner`. Set them to your own values before running. Never commit bot tokens — they are read only from the environment.

## Usage

Open your bot in the messenger and send `/start`. See the detailed documentation below for commands, admin panel and platform-specific notes.

## License

Code released under the [MIT License](LICENSE).

---

## Detailed documentation

# مربی بدنسازی | Fitness Coach — ربات تلگرام و بله

ربات برنامهٔ بدنسازی شخصی (باشگاه با تجهیزات کامل): برنامهٔ هفتگی با اضافه‌بار تدریجی، ثبت وزنه×تکرار، پیشنهاد خودکار وزنهٔ بعدی، رکوردها، وزن و اندازه‌ها با نمودار، کالری و ماکرو، منوی غذایی ایرانی، گینر و کراتین، یادآورها و تنظیم هفتگی خودکار.
پایتون، `getUpdates` (long polling)، SQLite (WAL)، **یک پردازش برای هر پلتفرم** (تلگرام و بله با هستهٔ مشترک؛ داده‌ها جداست چون شناسهٔ کاربران در دو پیام‌رسان متفاوت است). رابط فقط فارسی.

> ⚠️ **هشدار پزشکی:** این ربات جایگزین پزشک/متخصص تغذیه نیست. عددهای کالری، افزایش وزن و ۱RM تخمینی‌اند. دربارهٔ استروئید و داروهای نیروزا هیچ توصیه‌ای نمی‌کند (و پیام‌های مرتبط را رد می‌کند). مشکل کلیوی ← کراتین فعال نمی‌شود و پیام «با پزشک مشورت کن» نشان داده می‌شود.

## اجرا
```bash
cd fitness-bot
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
export FITNESS_TELEGRAM_BOT_TOKEN='<توکن BotFather تلگرام>'   # اختیاری؛ بدون آن تلگرام راه نمی‌افتد
export FITNESS_BALE_BOT_TOKEN='<توکن @botfather بله>'          # اختیاری؛ بدون آن بله بی‌سروصدا رد می‌شود
./run.sh            # هر پلتفرمی که توکنش تنظیم است را جدا و با راه‌اندازی مجدد خودکار اجرا می‌کند (./run.sh telegram | ./run.sh bale)
./stop.sh [telegram|bale]
./venv/bin/python test_offline.py                         # آزمون‌ها با API جعلی (تلگرام)
FITNESS_PLATFORM=bale ./venv/bin/python test_offline.py   # همان آزمون‌ها برای بله
./venv/bin/python test_bale.py                            # آزمون‌های آداپتور بله
```
توکن‌ها فقط از متغیر محیطی خوانده می‌شوند؛ هرگز چاپ، ذخیره یا لاگ نمی‌شوند (فیلتر حذف توکن روی لاگ فعال است). لاگ‌ها: `bot.log` (تلگرام)، `bale.log` (بله). دیتابیس: `fitness.db` / `fitness_bale.db`.

| | تلگرام | بله |
|---|---|---|
| متغیر توکن | `FITNESS_TELEGRAM_BOT_TOKEN` | `FITNESS_BALE_BOT_TOKEN` |
| API | api.telegram.org (HTML) | tapi.bale.ai (HTML ← Markdown خودکار) |
| پروفایل | نام، توضیح، دستورهای فارسی خودکار | فقط `setMyCommands` خودکار؛ نام/توضیح را در `@botfather` بله بگذارید |
| مالک `/admin` | شناسهٔ عددی `100000001` | کد یک‌بارمصرف: در `bale.log` عبارت `OWNER CLAIM CODE` را بخوانید و در بله `/claim <کد>` بفرستید (پیام حذف می‌شود) |

نمودارها PNG ساده‌اند (matplotlib + فونت Vazirmatn داخل `assets/`)، پس روی هر دو پلتفرم یکسان کار می‌کنند. از قابلیت‌های مخصوص تلگرام (رنگ دکمه، inline mode، WebApp) استفاده نشده است. ربات فقط در چت خصوصی کار می‌کند.

## امکانات
- **شروع (onboarding):** هشدار پزشکی، سن/قد/وزن/بهترین وزن/هدف‌ها، مدت استراحت، ۳ یا ۴ روز (پیشنهاد: ۴ روز بالاتنه/پایین‌تنه؛ جایگزین: ۳ روز تمام‌بدن)، روزهای هفته، مدت جلسه (۴۵–۹۰ دقیقه)، آسیب‌ها، سطح فعالیت، نگرانی کلیوی، گینر (گرم/کیلوکالری/پروتئین هر سروینگ)، کراتین (۳–۵ گرم)، **وزنهٔ شروع هر حرکت** با دکمه‌های ۵/۱۰/۱۵/۲۰/۲۵ یا عدد دلخواه، یادآورها.
- **انتظار صادقانه:** رشد سالم ۰٫۵–۱ کیلو در هفته (≈ ۶–۸ کیلو در ۲ ماه، با کمی چربی). اگر هدف ۲ ماهه واقع‌بینانه نباشد (مثلاً ۶۰←۷۳) ربات می‌گوید چه چیزی در ۲ ماه دست‌یافتنی است و رسیدن به هدف چند هفته طول می‌کشد. حافظهٔ عضلانی برگشت را سریع‌تر می‌کند، اما هفتهٔ ۱–۲ سازگاری (RIR ۳–۴) است.
- **برنامه:** هفتهٔ ۱–۲ سازگاری (۸۰٪ و ۹۰٪ وزنهٔ مرجع، ست کم)، ۳–۶ ساخت حجم (RIR ۲–۳ ← ۱–۲، ۸–۱۲ تکرار)، ۷–۸ تشدید (۶–۱۰ تکرار)، هفتهٔ ۹ سبک (دیلود) و چرخهٔ بعد. دیلود با بررسی هفتگی (خستگی/درد) یا از تنظیمات پیشنهاد/فعال می‌شود. تعداد حرکت‌ها با مدت جلسه، و حرکت‌های ناجور با آسیب‌ها (شانه، کمر، زانو، آرنج، مچ، گردن) تنظیم/جایگزین می‌شود.
- **تمرین روزانه (`/today`):** لیست حرکت‌ها، توضیح کوتاه اجرا، گرم‌کردن (ست‌های گرم‌کن محاسبه‌شده)، هدف ست×تکرار، RIR و استراحت؛ ثبت ست با دکمه (وزنه ۵–۲۵، ➕/➖، ✏️ + تعداد تکرار) یا متن (`20x10`)؛ حذف آخرین ست؛ جایگزین/رد حرکت؛ حجم کل و پیام بعد از تمرین (گینر/کراتین).
- **اضافه‌بار (double progression):** وقتی همهٔ ست‌ها به سقف تکرار برسند وزنه +گام و تکرار از پایین شروع می‌شود؛ در بازه وزنه ثابت و تکرار بیشتر؛ زیر بازه سبک‌تر. هفتهٔ سبک ۱۰٪ کمتر.
- **رکوردها:** ۱RM تخمینی (Epley) و سنگین‌ترین وزنه (≥۳ تکرار)؛ اولین ست مبناست (رکورد حساب نمی‌شود).
- **وزن و اندازه‌ها:** ثبت وزن (دکمه یا عدد)، اندازهٔ بازو/سینه/کمر/ران، نمودار وزن با خط ۷۳ و ۸۰ و ناحیهٔ واقع‌بینانه (۰٫۵–۱ کیلو/هفته)، نمودار اندازه‌ها، قدرت هر حرکت، حجم هفتگی.
- **تغذیه:** Mifflin-St Jeor × فعالیت + مازاد ۴۵۰ kcal (۴۰۰–۵۰۰ شروع)، پروتئین ۲ g/kg (۱٫۸–۲٫۲)، چربی ۲۵٪، بقیه کربوهیدرات، آب؛ منوی روزانهٔ ایرانی (صبحانه، ناهار، شام، ۲ میان‌وعده) با تنظیم به کالری هدف و پیشنهاد افزودنی؛ گینر از کالری غذا کم می‌شود.
- **گینر و کراتین:** ثبت اندازهٔ سروینگ و کیلوکالری، ۱ سروینگ بعد از تمرین/بین وعده؛ کراتین ۳–۵ گرم روزانه، هر ساعت، با آب، **بدون لودینگ**، هشدار پزشک برای کلیه؛ ثبت مصرف روزانه و آب.
- **یادآورها:** تمرین (روز تمرین)، کراتین، گینر، آب (۴ بار)، خواب، وزن‌کشی/بررسی هفتگی. هر یادآور روزی یک بار، فقط اگر کار انجام نشده، و بیش از ۳ ساعت دیرتر فرستاده نمی‌شود. زمان‌ها قابل تغییرند (پیش‌فرض Asia/Tehran).
- **تنظیم هفتگی خودکار:** در بررسی هفتگی (وزن + خستگی + درد + پایبندی): افزایش < ۰٫۲۵ kg/هفته ← +۱۵۰ تا ۲۰۰ kcal؛ > ۱ kg/هفته ← −۱۵۰ تا ۲۰۰ (در ۲ هفتهٔ اول چون کراتین/گلیکوژن آب نگه می‌دارند کم نمی‌شود)؛ پایبندی کم ← کالری بالا نمی‌رود؛ حداکثر یک تنظیم در ۶ روز.
- **پیشرفت و خروجی:** `/progress` (وزن، روند، درصد هدف، تخمین زمان رسیدن، جلسه‌ها، رکوردها، اندازه‌ها)، `/export` (zip شامل CSVهای وزن، اندازه، تمرین، ست‌ها، مکمل، آب، بررسی‌ها + پروفایل).
- **مالک (`/admin`):** آمار، پیام همگانی، بن/آنبن.

## جنسیت (مرد/زن)
جنسیت در شروع و در «تنظیمات ← جنسیت» انتخاب می‌شود (کاربران قبلی، به‌صورت پیش‌فرض **مرد** مهاجرت می‌شوند). چیزهایی که بر اساس آن عوض می‌شود:
| | مرد | زن |
|---|---|---|
| ثابت Mifflin-St Jeor | +۵ | −۱۶۱ |
| مازاد کالری شروع / حدود | +۴۵۰ (۱۵۰–۹۰۰) | +۳۰۰ (۱۰۰–۵۰۰) |
| پروتئین (بازه، پیش‌فرض) | ۱٫۸–۲٫۲ (۲٫۰) g/kg | ۱٫۶–۲٫۰ (۱٫۸) g/kg |
| افزایش وزن واقع‌بینانه | ۰٫۵–۱ کیلو/هفته (≈ ۶–۸ کیلو در ۲ ماه) | ۰٫۲۵–۰٫۵ کیلو/هفته (≈ ۲–۴ کیلو در ۲ ماه) |
| تنظیم هفتگی خودکار | < ۰٫۲۵ ← +۱۵۰–۲۰۰؛ > ۱ ← −۱۵۰–۲۰۰ | < ۰٫۱۲ ← +۱۰۰–۱۵۰؛ > ۰٫۶ ← −۱۰۰–۱۵۰ |
| برنامه | بالاتنه/پایین‌تنه (۴ روز) یا تمام‌بدن (۳ روز) | پایین‌تنه/بالاتنه با تأکید باسن و پا (حرکت‌های هیپ‌ترست، اسکوات، RDL، ابداکتور، کیک‌بک، گابلت اسکوات)؛ بالاتنه برای حفظ و فرم‌دهی با یک ست کمتر (پس از دو هفتهٔ سازگاری) |
| بازهٔ تکرار | مثل برنامه | +۲ تا +۳ تکرار بالاتر |
گینر و کراتین فقط وقتی در برنامهٔ غذا، یادآور و پیام بعد از تمرین می‌آیند که خودت در تنظیم آن‌ها را فعال کرده باشی.

## ویدیو / آموزش هر حرکت
در کارت هر حرکت دکمهٔ «🎬 ویدیو / آموزش» هست: لینک جستجوی یوتیوب با نام انگلیسی حرکت (`https://www.youtube.com/results?search_query=<name>+form`) به‌صورت دکمه و متن، و تصویر/انیمیشن حرکت: روی تلگرام GIF دو‌فریمی (شروع/پایان حرکت)، روی بله آلبوم دو عکس (و در صورت خطا، عکس‌های تکی). «💡 نکات بیشتر» نکته‌ها، اشتباهات رایج و لینک جستجوی دوم (تکنیک و اشتباهات) را می‌دهد.
تصاویر از **Free Exercise DB** (`yuhonas/free-exercise-db`، مجوز **The Unlicense** = دامنهٔ عمومی) هستند و با `fetch_exercise_media.py` یک‌بار در `assets/ex/` ذخیره شده‌اند؛ ربات هنگام اجرا چیزی دانلود نمی‌کند. اگر فایلی نباشد فقط لینک فرستاده می‌شود. (مبدأ اصلی عکس‌ها را مستقل راستی‌آزمایی نکرده‌ایم؛ مجوز اعلام‌شدهٔ مخزن Unlicense است.) ویدیوی یوتیوب فقط لینک جستجوست؛ چیزی از یوتیوب دانلود یا جاسازی نمی‌شود.

## فرض‌ها
- وزنه‌های ۵/۱۰/۱۵/۲۰/۲۵ به‌عنوان وزنهٔ شروع هر حرکت (مرجع) استفاده می‌شوند؛ گام افزایش: دمبل ۱–۲ کیلو، هالتر/سیم‌کش/دستگاه ۲٫۵ (پرس پا و هیپ‌ترست ۵). دمبل = وزن هر دست.
- هفته‌ها از روز شروع (روز ثبت‌نام) شمرده می‌شوند.
- کالری و ماکرو غذاها تقریبی (±۱۵٪) و متن‌های آموزشی/منو بازبینی‌نشده توسط متخصص‌اند.

