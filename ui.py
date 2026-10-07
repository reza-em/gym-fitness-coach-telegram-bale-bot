"""Shared UI helpers: main menu, user lookups, section routing used by several modules."""
import json
import config, db, util
import core as C
from core import btn, kb, send, show
from util import esc

def U(uid): return db.get_user(uid)

def menu_markup():
    return kb([
        [btn("🏋️ تمرین امروز", "w:today"), btn("📅 برنامهٔ هفته", "w:week")],
        [btn("⚖️ وزن و اندازه‌ها", "t:menu"), btn("🍽 تغذیه", "n:menu")],
        [btn("💊 گینر و کراتین", "s:menu"), btn("📊 پیشرفت", "p:menu")],
        [btn("🧮 ماشین‌حساب کالری و ماکرو", "mc:start:m")],
        [btn("⏰ یادآورها", "r:menu"), btn("⚙️ تنظیمات", "st:menu")],
        [btn("❓ راهنما", "m:help")]])

def menu_row(): return [btn("🏠 منو", "m:menu")]

def home_text(u):
    import program as P
    wk = P.week_of(u); ph = P.phase_for_user(u, wk)
    d = util.today(u["tz"])
    return (f"💪 <b>منوی اصلی</b>\n📆 {util.dlabel(d)}\nهفتهٔ {wk} از برنامه: {ph['name']}\n"
            f"🎯 {util.fnum(u['weight'])} ← {util.fnum(u['target_w'])} کیلو (بلندمدت {util.fnum(u['goal_w'])})")

def show_menu(uid, mid=None):
    u = U(uid)
    if not u or not u["onboarded"]:
        import onboarding; return onboarding.start(uid)
    db.set_await(uid, None)
    return show(uid, mid, home_text(u), menu_markup())

def back_kb(extra=None, back="m:menu", label="🏠 منو"):
    rows = list(extra or []); rows.append([btn(label, back)]); return kb(rows)

def with_back(rows, data, label=None):
    """Append a single «بازگشت» row; returns the rows list (not a keyboard)."""
    import texts
    rows = [list(r) for r in (rows or [])]
    rows.append([btn(label or texts.BACK, data)])
    return rows

def current_weight(uid):
    r = db.q1("SELECT kg FROM weights WHERE user_id=? ORDER BY day DESC, id DESC LIMIT 1", (uid,))
    return r["kg"] if r else (U(uid) or {}).get("weight")

def sync_weight(uid):
    """Keep users.weight = latest logged weight."""
    w = current_weight(uid)
    if w: db.update_user(uid, weight=w)
    return w

def weight_points(uid, days=None):
    rows = db.q("SELECT day, AVG(kg) kg FROM weights WHERE user_id=? GROUP BY day ORDER BY day", (uid,))
    pts = [(util.parse_day(r["day"]), r["kg"]) for r in rows]
    if days:
        cut = util.today(U(uid)["tz"]) - __import__("datetime").timedelta(days=days)
        pts = [p for p in pts if p[0] >= cut]
    return pts
