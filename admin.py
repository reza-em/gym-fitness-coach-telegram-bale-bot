"""Owner panel (/admin): stats, broadcast, ban/unban. Telegram owner = numeric id 100000001; Bale owner = one-time /claim code."""
import secrets, time, logging
import config, db, util
import core as C, ui
from core import btn, kb, send, show
from plat import PLAT

log = logging.getLogger("bot")

def ensure_claim_code():
    """Bale: print a one-time claim code to the log while no owner is bound."""
    if not PLAT.claim: return None
    if db.val("SELECT COUNT(*) FROM users WHERE is_admin=1", (), 0): return None
    code = db.meta_get("claim_code")
    if not code:
        code = "-".join(secrets.token_hex(2).upper() for _ in range(3)); db.meta_set("claim_code", code)
    log.info("OWNER CLAIM CODE (send '/claim %s' to the Bale bot once): %s", code, code)
    return code

def try_claim(uid, code):
    key = ("claim", uid)
    if not C.rate_ok(key, 5, 3600): return "throttled"
    real = db.meta_get("claim_code")
    if not real or (code or "").strip().upper() != real: return "bad"
    db.update_user(uid, is_admin=1); db.meta_set("claim_code", None)
    return "ok"

def sync_owner(uid):
    """Telegram: the numeric owner id is admin automatically."""
    if not PLAT.claim and uid == config.OWNER_ID:
        db.update_user(uid, is_admin=1)

def panel(uid, mid=None):
    n = db.val("SELECT COUNT(*) FROM users", (), 0); ob = db.val("SELECT COUNT(*) FROM users WHERE onboarded=1", (), 0)
    day7 = (util.today("Asia/Tehran") - __import__("datetime").timedelta(days=7)).isoformat()
    act = db.val("SELECT COUNT(DISTINCT user_id) FROM activity WHERE day>=?", (day7,), 0)
    wo = db.val("SELECT COUNT(*) FROM workouts WHERE finished=1", (), 0); st = db.val("SELECT COUNT(*) FROM sets", (), 0)
    txt = f"🛠 <b>پنل مالک</b> ({PLAT.label})\n👥 کاربران: {n} (پروفایل کامل: {ob})\n🔥 فعال در ۷ روز: {act}\n🏋️ جلسه‌های ثبت‌شده: {wo} | ست‌ها: {st}"
    return show(uid, mid, txt, kb([[btn("📣 پیام همگانی", "ad:bc")], [btn("🚫 بن/آنبن با شناسه", "ad:ban")], ui.menu_row()]))

def on_text(uid, aw, d, text):
    if aw == "a_bc":
        t = text.strip()
        if not t: return send(uid, "متن خالی است.")
        db.set_await(uid, "a_bc2", {"text": t})
        return send(uid, f"پیش‌نمایش پیام همگانی:\n\n{t}\n\nبه {db.val('SELECT COUNT(*) FROM users WHERE onboarded=1 AND banned=0 AND can_dm=1', (), 0)} نفر ارسال شود؟",
                    kb([[btn("✅ ارسال", "ad:bcgo"), btn("لغو", "ad:menu")]]), html=False)
    if aw == "a_ban":
        i = util.parse_int(text, 1, 10**15)
        if not i or not db.get_user(i): return send(uid, "کاربری با این شناسه نیست.")
        cur = db.get_user(i)["banned"]; db.update_user(i, banned=0 if cur else 1); db.set_await(uid, None)
        return send(uid, f"کاربر {i} " + ("آنبن شد." if cur else "بن شد."))
    return False

def callback(uid, mid, p):
    if not db.is_admin(uid): return
    k = p[1]
    if k == "menu": db.set_await(uid, None); return panel(uid, mid)
    if k == "bc": db.set_await(uid, "a_bc"); return show(uid, mid, "متن پیام همگانی را بفرست (لغو: /cancel):")
    if k == "ban": db.set_await(uid, "a_ban"); return show(uid, mid, "شناسهٔ عددی کاربر را بفرست:")
    if k == "bcgo":
        aw, d = db.get_await(uid)
        if aw != "a_bc2": return
        db.set_await(uid, None); sent = fail = 0
        for u in db.q("SELECT id FROM users WHERE onboarded=1 AND banned=0 AND can_dm=1"):
            r = send(u["id"], d["text"], html=False)
            if r: sent += 1
            else: fail += 1; db.update_user(u["id"], can_dm=0)
            time.sleep(1.0 / config.BROADCAST_PER_SEC)
        return send(uid, f"ارسال شد: {sent} | ناموفق: {fail}")
