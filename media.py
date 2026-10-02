"""Exercise video / tutorial helper: YouTube search links (always) + free images/animation (free-exercise-db, Unlicense) when bundled locally.
Telegram: looping GIF (sendAnimation); Bale: a 2-photo album (sendMediaGroup), falling back to single photos. Extra tips + common mistakes + 2nd search link."""
import os
import config, exdata as X
import core as C, ui
from core import btn, kb, send
from plat import IS_BALE
from util import esc

DIR = os.path.join(config.ASSETS, "ex")
CREDIT = "تصویر: Free Exercise DB (Unlicense / دامنهٔ عمومی)"

def files(eid):
    g = os.path.join(DIR, f"{eid}.gif"); a = os.path.join(DIR, f"{eid}_0.jpg"); b = os.path.join(DIR, f"{eid}_1.jpg")
    return (g if os.path.exists(g) else None), [p for p in (a, b) if os.path.exists(p)]

def video_markup(eid, more=True):
    rows = [[btn("▶️ جستجوی ویدیو در یوتیوب", url=X.yt_url(eid, "form"))]]
    if more: rows.append([btn("💡 نکات بیشتر و اشتباهات رایج", f"xm:{eid}")])
    rows.append([btn("🏠 منو", "m:menu")])
    return kb(rows)

def video(uid, eid):
    """Send the tutorial: media (if bundled) then the link message."""
    if eid not in X.EX: return
    ex = X.EX[eid]; gif, imgs = files(eid)
    cap = f"🎬 <b>{ex['fa']}</b> ({ex['en']})\n<i>{CREDIT}</i>"
    sent = None
    if gif and not IS_BALE:
        sent = C.send_animation(uid, open(gif, "rb").read(), cap)
    if sent is None and len(imgs) == 2:
        sent = C.send_media_group(uid, [open(p, "rb").read() for p in imgs], cap)
    if sent is None and imgs:
        for i, p in enumerate(imgs):
            r = C.send_photo(uid, open(p, "rb").read(), cap if i == 0 else "")
            sent = sent or r
    steps = f"🎬 <b>ویدیو / آموزش: {ex['fa']}</b>\n{esc(ex['how'])}\n\nبرای دیدن اجرای حرکت (ویدیو)، روی دکمه بزن یا لینک را باز کن:\n{X.yt_url(eid, 'form')}"
    if sent is None: steps += "\n\n(تصویر این حرکت در دسترس نیست؛ فقط لینک.)"
    return send(uid, steps, video_markup(eid))

def more(uid, mid, eid):
    if eid not in X.EX: return
    ex = X.EX[eid]; tips, mistakes = X.TIPS[eid]
    txt = (f"💡 <b>{ex['fa']}</b> — نکات بیشتر\n{tips}\n\n❌ <b>اشتباهات رایج:</b>\n{mistakes}\n\n"
           f"🔗 جستجوی دوم (تکنیک و اشتباهات): {X.yt_url(eid, 'mistakes')}\n<i>اگر درد تیز یا ناراحتی مفصل داشتی، حرکت را قطع کن.</i>")
    rows = [[btn("▶️ ویدیو (یوتیوب)", url=X.yt_url(eid, "form")), btn("🔎 اشتباهات رایج (یوتیوب)", url=X.yt_url(eid, "mistakes"))], [btn("🏠 منو", "m:menu")]]
    return send(uid, txt, kb(rows))
