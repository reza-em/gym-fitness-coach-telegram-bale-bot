#!/usr/bin/env python3
"""Fitness coach bot (مربی بدنسازی) — long polling, single instance per platform. Platform: FITNESS_PLATFORM=telegram|bale (see plat.py)."""
import os, sys, json, time, logging, fcntl, hashlib, re
import plat
from plat import PLAT, IS_BALE
import config, db, util, texts
import core as C
from core import call, send, ApiError, btn, kb, show

log = logging.getLogger("bot")
if __name__ == "__main__" and not PLAT.token:
    print("%s is not set%s" % (PLAT.token_env, " - skipping the %s bot" % PLAT.label if IS_BALE else ""), file=sys.stderr)
    sys.exit(0 if IS_BALE else 1)

import media as M, ui, onboarding as OB, workout as W, track as T, diet as D, remind as R, settings as S, admin as A

COMMANDS = [("start", "شروع و ساخت برنامه 💪"), ("today", "تمرین امروز 🏋️"), ("week", "برنامهٔ هفته 📅"), ("weight", "ثبت وزن ⚖️"), ("measure", "ثبت اندازه‌ها 📏"),
            ("checkin", "بررسی هفتگی ✅"), ("food", "تغذیه و کالری 🍽"), ("supplements", "گینر و کراتین 💊"), ("progress", "پیشرفت و نمودار 📊"), ("prs", "رکوردها 🏆"),
            ("reminders", "یادآورها ⏰"), ("settings", "تنظیمات ⚙️"), ("export", "خروجی داده‌ها 📦"), ("help", "راهنما ❓"), ("cancel", "لغو")]
ABOUT_FA = "مربی بدنسازی شخصی: برنامهٔ هفتگی، ثبت وزنه، تغذیه ایرانی، گینر و کراتین، یادآور و نمودار پیشرفت"
DESC_FA = ("من مربی بدنسازی‌ات هستم 💪 برنامهٔ تمرین شخصی (۳ یا ۴ روز)، ثبت وزنه‌ها و رکوردها، وزن و اندازه‌ها، کالری و منوی ایرانی، گینر و کراتین، یادآورها و نمودار پیشرفت. "
           "توصیهٔ پزشکی نیست و دربارهٔ استروئید و مواد نیروزا کمکی نمی‌کنم.")

def setup_profile():
    """Persian bot profile. Telegram: name/about/description + commands (default + fa). Bale: only setMyCommands exists (name/description in @botfather)."""
    cmds = json.dumps([{"command": c, "description": d} for c, d in COMMANDS], ensure_ascii=False)
    sig = hashlib.sha256(json.dumps([config.BOT_NAME, ABOUT_FA, DESC_FA, COMMANDS, PLAT.name], ensure_ascii=False).encode()).hexdigest()
    if db.meta_get("profile_sha") == sig: return True
    ok = True
    steps = [("setMyCommands", {"commands": cmds})]
    if not IS_BALE:
        steps += [("setMyCommands", {"commands": cmds, "language_code": "fa"}), ("setMyName", {"name": config.BOT_NAME}),
                  ("setMyName", {"name": config.BOT_NAME, "language_code": "fa"}),
                  ("setMyShortDescription", {"short_description": ABOUT_FA}), ("setMyShortDescription", {"short_description": ABOUT_FA, "language_code": "fa"}),
                  ("setMyDescription", {"description": DESC_FA}), ("setMyDescription", {"description": DESC_FA, "language_code": "fa"})]
    for m, d in steps:
        try: call(m, d)
        except ApiError as e:
            ok = False; log.warning("%s failed: %s", m, C.safe(e)[:100])
    if ok:
        db.meta_set("profile_sha", sig)
    log.info("profile set (ok=%s)%s", ok, " - Bale: name/about must be set in Bale's @botfather" if IS_BALE else "")
    return ok

# ---------------------------------------------------------------- messages
def is_steroid(text):
    t = text.lower()
    return any(re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t) if w.isascii() else w in t for w in texts.STEROID_WORDS)

def private_message(msg):
    frm = msg["from"]; uid = frm["id"]; text = (msg.get("text") or "").strip()
    u, new = db.touch_user(frm)
    A.sync_owner(uid)
    if db.is_banned(uid): return send(uid, "دسترسی شما به این ربات بسته شده است.")
    if not C.rate_ok(("p", uid), config.PRIVATE_MSGS_PER_MIN):
        if C.rate_ok(("pn", uid), 1, 30): send(uid, "کمی آهسته‌تر 🙂 چند ثانیه بعد دوباره بفرست.")
        return
    if not text: return
    if text.startswith("/"):
        parts = text.split(None, 1); cmd = parts[0][1:].split("@")[0].lower(); arg = parts[1].strip() if len(parts) > 1 else ""
        return command(uid, cmd, arg, msg)
    u = db.get_user(uid)
    if is_steroid(text): return send(uid, texts.NO_STEROIDS, kb([ui.menu_row()]))
    aw, d = db.get_await(uid)
    if aw:
        if aw.startswith("ob:"):
            if OB.on_text(uid, aw, d, text) is not False: return
        elif aw in ("set", "wcustom"):
            if W.on_text(uid, aw, d, text) is not False: return
        elif aw in ("weigh", "meas"):
            if T.on_text(uid, aw, d, text) is not False: return
        elif aw == "rtime": return R.on_text(uid, aw, d, text)
        elif aw.startswith("a_") and db.is_admin(uid):
            if A.on_text(uid, aw, d, text) is not False: return
    if not u["onboarded"]: return OB.start(uid)
    send(uid, "برای ادامه از منو استفاده کن 👇", ui.menu_markup())

def command(uid, cmd, arg, msg=None):
    u = db.get_user(uid)
    if cmd == "start": db.set_await(uid, None); return OB.start(uid) if not u["onboarded"] else ui.show_menu(uid)
    if cmd == "claim":
        if not PLAT.claim: return send(uid, "نیازی به این دستور نیست.")
        r = A.try_claim(uid, arg)
        if msg: C.delete_msg(uid, msg.get("message_id"))
        return send(uid, {"ok": "✅ شما مالک این ربات شدید. /admin", "bad": "کد اشتباه است.", "throttled": "تلاش زیاد؛ بعداً دوباره."}[r])
    if cmd == "help": return send(uid, texts.HELP, kb([ui.menu_row()]))
    if cmd == "admin":
        if not db.is_admin(uid): return send(uid, "این دستور فقط برای مالک است.")
        return A.panel(uid)
    if not u["onboarded"]: return OB.start(uid)
    if cmd in ("cancel", "menu"): db.set_await(uid, None); return ui.show_menu(uid)
    if cmd in ("today", "workout", "log"): db.set_await(uid, None); return W.today(uid)
    if cmd == "week": return W.week_view(uid)
    if cmd in ("weight", "weigh"):
        if arg and util.parse_num(arg, 30, 250): return T.log_weight(uid, util.parse_num(arg))
        return T.weight_prompt(uid)
    if cmd in ("measure", "measures"): return T.meas_start(uid)
    if cmd == "checkin": return T.ci_start(uid)
    if cmd in ("food", "nutrition"): return D.menu(uid)
    if cmd in ("supplements", "supp"): return D.supp_menu(uid)
    if cmd in ("progress", "chart"): return T.progress(uid)
    if cmd == "prs": return W.prs_view(uid)
    if cmd in ("reminders", "remind"): return R.menu(uid)
    if cmd == "settings": return S.menu(uid)
    if cmd == "export": return T.export(uid)
    send(uid, "دستور ناشناخته. از منو استفاده کن 👇", ui.menu_markup())

def private_callback(cb):
    msg = cb["message"]; uid = cb["from"]["id"]; mid = msg["message_id"]; d = cb.get("data") or ""; p = d.split(":")
    db.touch_user(cb["from"]); A.sync_owner(uid)
    if db.is_banned(uid): return C.answer_cb(cb["id"])
    C.answer_cb(cb["id"])
    if not C.rate_ok(("pc", uid), config.PRIVATE_MSGS_PER_MIN * 2): return
    k = p[0]; u = db.get_user(uid)
    if k == "ob": return OB.callback(uid, mid, p)
    if not u["onboarded"]: return OB.start(uid)
    if k == "m":
        if p[1] == "menu": return ui.show_menu(uid, mid)
        if p[1] == "help": return show(uid, mid, texts.HELP, kb([ui.menu_row()]))
    if k in ("w", "x", "xj", "xw", "xr", "xc", "xu", "xh", "xa", "xa2", "xl", "wf", "wff"): return W.cb(uid, mid, p)
    if k == "xv": return M.video(uid, p[1])
    if k == "xm": return M.more(uid, mid, p[1])
    if k in ("t", "p"): return T.cb(uid, mid, p)
    if k == "ci": return T.ci_cb(uid, mid, p)
    if k == "n": return D.nutri_cb(uid, mid, p)
    if k == "s": return D.supp_cb(uid, mid, p)
    if k == "wt":
        if p[1] == "menu": return D.supp_menu(uid, mid)
        return D.water_add(uid, int(p[1]), mid)
    if k == "r": return R.cb(uid, mid, p)
    if k == "st": return S.cb(uid, mid, p)
    if k == "ad": return A.callback(uid, mid, p)

def handle_update(up):
    try:
        msg = up.get("message")
        if "callback_query" in up:
            cb = up["callback_query"]
            if not cb.get("message"): return C.answer_cb(cb["id"])
            if cb["message"]["chat"].get("type", "private") == "private": return private_callback(cb)
            return C.answer_cb(cb["id"])
        if not msg or not msg.get("chat"): return
        if msg["chat"].get("type", "private") != "private":
            return                      # groups are not supported: workouts and body data are private
        if msg.get("from") and not msg["from"].get("is_bot"): private_message(msg)
    except Exception as e:
        log.exception("handler error: %s", C.safe(e))
        try:
            chat = (up.get("message") or (up.get("callback_query") or {}).get("message") or {}).get("chat", {})
            if chat.get("type", "private") == "private" and chat.get("id"):
                send(chat["id"], "یک خطای غیرمنتظره پیش آمد 😕 دوباره امتحان کن یا /start بزن.", html=False)
        except Exception: pass

def single_instance():
    fd = open(os.path.join(plat.BASE, PLAT.lock_name), "a+")
    try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another instance is already running", file=sys.stderr); sys.exit(0)
    fd.seek(0); fd.truncate(); fd.write(str(os.getpid())); fd.flush()
    return fd

def main():
    _lock = single_instance()
    C.setup_logging(); db.init()
    try:
        me = call("getMe"); C.BOT_USERNAME = me["username"]; C.BOT_ID = me["id"]
    except ApiError as e:
        log.error("getMe failed: %s", C.safe(e)[:100]); sys.exit(1)
    log.info("%s (%s) started: @%s", config.BOT_NAME, PLAT.label, C.BOT_USERNAME)
    db.meta_set("bot_username", C.BOT_USERNAME)
    setup_profile()
    A.ensure_claim_code()
    try:
        wh = call("getWebhookInfo")
        if wh.get("url"): log.info("Webhook was set; deleting to use long polling"); call("deleteWebhook")
    except ApiError as e: log.warning("webhook check: %s", C.safe(e)[:80])
    R.start()
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if not IS_BALE: params["allowed_updates"] = json.dumps(["message", "callback_query"])
            if offset: params["offset"] = offset
            updates = call("getUpdates", params, timeout=45)
        except ApiError as e:
            log.warning("getUpdates: %s", C.safe(e)[:100]); time.sleep(5); continue
        for up in updates:
            offset = up["update_id"] + 1
            handle_update(up)

if __name__ == "__main__":
    main()
