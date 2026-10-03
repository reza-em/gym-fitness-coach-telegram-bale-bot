# Scripted *illustrative* conversation used to render docs/*.png and docs/demo.gif.
# Usage: MOCK_FONT_DIR=file:///path/to/fonts python3 render.py scenario ../   (needs Chrome + ffmpeg + Pillow)
from render import *
SPEC=dict(name='Gym Fitness Coach', icon='🏋️', c1='#22b573', c2='#1b8bd1', scenarios=[
 dict(steps=[
  U('/today'),
  B('🏋️ <b>امروز: بالاتنه A</b> · هفتهٔ ۳ (ساخت حجم)\n\n1️⃣ پرس سینه هالتر — 4×8–10 · RIR 2\n2️⃣ زیربغل سیم‌کش — 3×10–12\n3️⃣ پرس سرشانه دمبل — 3×8–10\n4️⃣ پشت‌بازو سیم‌کش — 3×12\n\n⏱ استراحت: ۹۰ ثانیه', id='t',
    buttons=[['▶️ شروع حرکت ۱'],['🎬 ویدیو / آموزش','🔁 جایگزین']]),
  U('60x8'),
  B('✅ ست ۱ ثبت شد: <code>60 kg × 8</code>\n📈 1RM تخمینی: <b>76 kg</b>\n💡 وزنهٔ بعدی پیشنهادی: <b>60 kg</b> (هدف: ۱۰ تکرار، بعد +۲٫۵)', id='s',
    buttons=[['60','62.5','65','✏️'],['↩️ حذف آخرین ست','➡️ حرکت بعد']]),
 ]),
 dict(steps=[
  U('/progress'),
  B(media=chart_svg([70.2,70.6,71.1,71.5,71.9,72.6,73.0,73.4],'#22b573','Bodyweight (kg) — sample data','',69,75), id='c',
    text='📊 <b>پیشرفت وزن</b>\nروند: <b>+۰٫۴ kg/هفته</b> ✅ (محدودهٔ سالم ۰٫۵–۱ برای آقایان در اوایل)\n🎯 هدف: ۸۰ kg'),
  B('🏆 <b>رکوردها</b>\nپرس سینه: <code>76 kg</code> 1RM ⬆️\nاسکوات: <code>112 kg</code> 1RM ⬆️', id='pr'),
 ]),
 dict(steps=[
  B('🍽 <b>هدف تغذیه</b> (تخمینی)\n\n🔥 کالری: <b>3 050 kcal</b>\n🥩 پروتئین: <b>150 g</b>\n🍚 کربوهیدرات: <b>420 g</b> · 🥑 چربی: <b>85 g</b>\n💧 آب: ۳٫۵ لیتر', id='n',
    buttons=[['🍽 منوی امروز'],['🥤 گینر','⚡ کراتین ۵ g']]),
  B('⏰ <b>یادآوری</b>: ۵ g کراتین با آب — روزانه، بدون لودینگ.', id='r'),
  B('⚠️ جایگزین پزشک/متخصص تغذیه نیست. عددها تخمینی‌اند.', id='w'),
 ]),
])
