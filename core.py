"""Transport shared by all modules: API calls (Telegram + Bale adaptation), token redaction, keyboards, sending, rate limits."""
import os, sys, json, time, logging, threading, collections
import requests
import plat, balefmt, util
from plat import PLAT

TOKEN = PLAT.token      # process-default platform's token (kept for compatibility; redaction uses all tokens)
BOT_USERNAME = ""
BOT_ID = 0
log = logging.getLogger("bot")

def _tokens():
    return [t for t in set(plat.all_tokens() + [TOKEN, PLAT.token]) if t]

class RedactFilter(logging.Filter):
    def filter(self, record):
        try: msg = record.getMessage()
        except Exception: return True
        toks = _tokens()
        if any(t in msg for t in toks):
            for t in toks: msg = msg.replace(t, "<TOKEN>")
            record.msg = msg; record.args = ()
        return True

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for h in logging.getLogger().handlers: h.addFilter(RedactFilter())
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

def safe(e):
    s = str(e)
    for t in _tokens(): s = s.replace(t, "<TOKEN>")
    return s

sess = requests.Session()

class ApiError(Exception):
    def __init__(self, msg="", retry_after=None, code=0):
        super().__init__(msg); self.retry_after = retry_after; self.code = code

# ---------------- Bale adaptation (Telegram-shaped API without parse_mode / styles / some methods) ----------------
BALE_NO_METHODS = ("setMyName", "setMyDescription", "setMyShortDescription")
BALE_DROP_FIELDS = ("disable_web_page_preview", "allowed_updates")
BALE_LIMITS = {"text": 4096, "caption": 1024}

def bale_markup(rm):
    try:
        j = json.loads(rm) if isinstance(rm, str) else rm
        for row in j.get("inline_keyboard", []):
            for b in row:
                b.pop("style", None)
                u = b.get("url")
                if u and u.startswith("https://t.me/") and "share/url" not in u: b["url"] = "https://ble.ir/" + u[len("https://t.me/"):]
        return json.dumps(j, ensure_ascii=False)
    except Exception:
        return rm

def bale_prepare(method, data, files):
    d = dict(data or {}); files = dict(files) if files else files
    html_mode = d.pop("parse_mode", None) == "HTML"
    for f in ("text", "caption"):
        if d.get(f) is not None:
            d[f] = balefmt.to_md(str(d[f]), BALE_LIMITS[f]) if html_mode else balefmt.plain_to_md(str(d[f]), BALE_LIMITS[f])
    for f in BALE_DROP_FIELDS: d.pop(f, None)
    if d.get("reply_markup"): d["reply_markup"] = bale_markup(d["reply_markup"])
    if method == "sendMediaGroup" and d.get("media"):
        try:
            arr = json.loads(d["media"])
            for e in arr:
                hm = e.pop("parse_mode", None) == "HTML"
                if e.get("caption"): e["caption"] = balefmt.to_md(e["caption"], 1024) if hm else balefmt.plain_to_md(e["caption"], 1024)
            d["media"] = json.dumps(arr, ensure_ascii=False)
        except Exception:
            pass
    return d, files

def _call(method, data=None, files=None, timeout=60, _retry=True):
    if PLAT.is_bale:
        if method in BALE_NO_METHODS: raise ApiError("not supported on Bale: " + method)
        if method == "answerCallbackQuery" and str((data or {}).get("callback_query_id", "")).startswith("1"): return True
        data, files = bale_prepare(method, data, files)
    try:
        r = sess.post(PLAT.api + method, data=data, files=files, timeout=timeout)
    except requests.RequestException as e:
        raise ApiError("network: " + type(e).__name__)
    try: j = r.json()
    except Exception: raise ApiError(f"bad response HTTP {r.status_code}", code=r.status_code)
    if not j.get("ok"):
        ra = (j.get("parameters") or {}).get("retry_after")
        if _retry and ra and int(ra) <= 30 and not files:
            time.sleep(int(ra) + 1); return _call(method, data, files, timeout, _retry=False)
        raise ApiError(j.get("description", "unknown error"), ra, j.get("error_code", 0))
    return j["result"]

def call(method, data=None, files=None, timeout=60): return _call(method, data, files, timeout)

# ---------------- keyboards ----------------
def kb(rows): return json.dumps({"inline_keyboard": rows}, ensure_ascii=False)
def btn(text, data=None, url=None):
    b = {"text": text}
    if url: b["url"] = url
    else: b["callback_data"] = data
    return b
grid = util.grid
def link(username): return PLAT.link(username)

def platname(text):
    """Persian texts say «تلگرام/بله» generically; swap the platform word for the active platform where needed."""
    return text.replace("{platform}", PLAT.label)

# ---------------- sending ----------------
def _fix(text, html):
    text = platname(text)
    return util.rtl(text)

def send(chat_id, text, markup=None, html=True, **extra):
    data = {"chat_id": chat_id, "text": _fix(text, html)[:4096], "disable_web_page_preview": True}
    if markup: data["reply_markup"] = markup
    if html: data["parse_mode"] = "HTML"
    data.update(extra)
    try: return call("sendMessage", data)
    except ApiError as e:
        if e.retry_after and int(e.retry_after) <= 30:
            time.sleep(int(e.retry_after) + 1)
            try: return call("sendMessage", data)
            except ApiError: pass
        log.warning("sendMessage failed: %s", safe(e)[:100])
        if "parse" in str(e).lower() and html:           # malformed markup: resend as plain text
            data.pop("parse_mode", None); data["text"] = balefmt.strip_html(data["text"])
            try: return call("sendMessage", data)
            except ApiError: pass

def show(chat_id, msg_id, text, markup=None, html=True):
    """Edit the panel message in place if possible, else send a new one."""
    if msg_id:
        data = {"chat_id": chat_id, "message_id": msg_id, "text": _fix(text, html)[:4096], "disable_web_page_preview": True}
        if markup: data["reply_markup"] = markup
        if html: data["parse_mode"] = "HTML"
        try: return call("editMessageText", data)
        except ApiError as e:
            if "not modified" in str(e).lower(): return None
    return send(chat_id, text, markup, html)

def send_photo(chat_id, photo, caption="", markup=None):
    data = {"chat_id": chat_id}
    if caption: data["caption"] = _fix(caption, True)[:1024]; data["parse_mode"] = "HTML"
    if markup: data["reply_markup"] = markup
    try: return call("sendPhoto", data, files={"photo": ("chart.png", photo, "image/png")}, timeout=90)
    except ApiError as e:
        log.warning("sendPhoto failed: %s", safe(e)[:100])

def send_animation(chat_id, gif_bytes, caption="", markup=None):
    """GIF animation (Telegram). Raises nothing; returns the API result or None."""
    data = {"chat_id": chat_id}
    if caption: data["caption"] = _fix(caption, True)[:1024]; data["parse_mode"] = "HTML"
    if markup: data["reply_markup"] = markup
    try: return call("sendAnimation", data, files={"animation": ("ex.gif", gif_bytes, "image/gif")}, timeout=90)
    except ApiError as e:
        log.warning("sendAnimation failed: %s", safe(e)[:100])

def send_media_group(chat_id, images, caption=""):
    """images: list of JPEG bytes (2-10). Album of photos; the caption sits on the first one."""
    media, files = [], {}
    for i, b in enumerate(images):
        e = {"type": "photo", "media": f"attach://f{i}"}
        if i == 0 and caption: e["caption"] = _fix(caption, True)[:1024]; e["parse_mode"] = "HTML"
        media.append(e); files[f"f{i}"] = (f"f{i}.jpg", b, "image/jpeg")
    try: return call("sendMediaGroup", {"chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False)}, files=files, timeout=90)
    except ApiError as e:
        log.warning("sendMediaGroup failed: %s", safe(e)[:100])

def send_document(chat_id, name, content, caption="", mime="application/zip"):
    data = {"chat_id": chat_id}
    if caption: data["caption"] = _fix(caption, True)[:1000]; data["parse_mode"] = "HTML"
    try: return call("sendDocument", data, files={"document": (name, content, mime)}, timeout=120)
    except ApiError as e:
        log.warning("sendDocument failed: %s", safe(e)[:100])

def delete_msg(chat_id, msg_id):
    if not msg_id: return
    try: call("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})
    except ApiError: pass

def answer_cb(cid, text="", alert=False):
    d = {"callback_query_id": cid}
    if text: d["text"] = text[:200]; d["show_alert"] = alert
    try: call("answerCallbackQuery", d)
    except ApiError as e: log.warning("answerCallbackQuery: %s", safe(e)[:80])

# ---------------- rate limiting ----------------
_rl = collections.defaultdict(collections.deque); _rl_lock = threading.Lock()
def rate_ok(key, limit, window=60.0, now=None):
    now = time.time() if now is None else now
    key = (PLAT.name, key)          # one serverless process serves both platforms
    with _rl_lock:
        d = _rl[key]
        while d and d[0] <= now - window: d.popleft()
        if len(d) >= limit: return False
        d.append(now); return True
def rate_reset():
    with _rl_lock: _rl.clear()
