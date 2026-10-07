"""Optional hybrid AI coaching: Jev classifies topic, Gemini (Cheaper Inference) answers.
Keys from env only — never hardcoded. Graceful fallback if no key / API error."""
import os, base64, logging, json
import requests
import exdata as X, texts, config

log = logging.getLogger("bot")

# --- Chat / vision (Cheaper Inference / OpenAI-compatible) ---
API_KEY = (os.environ.get("OPENAI_API_KEY")
           or os.environ.get("FITNESS_OPENAI_API_KEY")
           or os.environ.get("LLM_API_KEY")
           or "").strip()
BASE_URL = (os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("FITNESS_OPENAI_BASE_URL")
            or "https://api.cheaperinference.com/v1").rstrip("/")
CHAT_MODEL = os.environ.get("FITNESS_AI_MODEL") or os.environ.get("OPENAI_MODEL") or "gemini-3.8-flash"
VISION_MODEL = os.environ.get("FITNESS_VISION_MODEL") or os.environ.get("OPENAI_VISION_MODEL") or "gemini-3.8-flash"

# --- Jev (topic classification only) ---
JEV_API_KEY = (os.environ.get("JEV_AI_API_KEY")
               or os.environ.get("FITNESS_OPENROUTER_API_KEY")
               or os.environ.get("FITNESS_JEV_API_KEY")
               or "").strip()
JEV_BASE_URL = (os.environ.get("JEV_AI_BASE_URL")
                or os.environ.get("FITNESS_JEV_BASE_URL")
                or "https://jev-ai.pro/api").rstrip("/")
JEV_MODEL = os.environ.get("FITNESS_JEV_MODEL") or "jev-latest"

TOPIC_LABELS = {
    "exercise": "تمرین / فرم حرکت / برنامه ورزشی",
    "diet": "تغذیه / کالری / وعده غذایی",
    "supplement": "مکمل (کراتین / گینر / پروتئین غذایی)",
    "photo_related": "تحلیل عکس بدن / فرم (کاربر باید عکس بفرستد)",
    "other": "موضوع عمومی بدنسازی یا خارج از محدوده",
}
VALID_TOPICS = set(TOPIC_LABELS)

SYSTEM = (
 "تو «مربی بدنسازی» ربات فارسی @planerem_bot هستی. کاربر مبتدی است؛ تمرین خانه یا سالن با وزنهٔ سبک. "
 "جواب‌ها کوتاه، واضح، فارسی عامیانه (نه اصطلاحات انگلیسی گنگ). "
 "فقط دربارهٔ تمرین، فرم حرکت، برنامه، تغذیهٔ ساده، گینر/کراتین، ریکاوری حرف بزن. "
 "هرگز استروئید/SARM/داروی نیروزا توصیه نکن. تشخیص پزشکی نده؛ اگر درد تیز/بیماری بود بگو با پزشک مشورت کند. "
 "از داده‌های حرکت‌های ربات استفاده کن اگر مرتبط است. برای مکمل‌ها فقط پیشنهاد اختیاری و ایمن بده (کراتین/گینر/پروتئین غذایی)؛ اجباری نکن و تشخیص پزشکی نده. اگر سؤال خارج از تخصص است مودبانه بگو از منوی ربات استفاده کند."
)

PHOTO_SYSTEM = (
 SYSTEM + " کاربر اختیاری عکس بدن/فرم/پیشرفت فرستاده. بازخورد کلی و ایمن بده: "
 "نشانه‌های ظاهری وضعیت بدن در سطح مربیگری (مثلاً شانه جلو آمده، قوس کمر)، نه تشخیص پزشکی. "
 "واضح بگو این نظر مربیگری است نه معاینه. اگر عکس نامربوط/نامناسب است مودبانه رد کن. حداکثر ۸–۱۰ خط."
)

FALLBACK_NO_KEY = (
 "الان لایهٔ هوش مصنوعی فعاله نیست (کلید API تنظیم نشده). "
 "از منو برای برنامه و آموزش حرکات استفاده کن، یا برای هر حرکت دکمهٔ «🎬 ویدیو / آموزش» را بزن.\n"
 "برای فعال‌سازی AI: متغیر محیطی <code>OPENAI_API_KEY</code> (یا <code>FITNESS_OPENAI_API_KEY</code>) را ست کن."
)
FALLBACK_ERR = "الان نتونستم از هوش مصنوعی جواب بگیرم 😕 از منو یا دکمهٔ آموزش حرکات استفاده کن، یا کمی بعد دوباره بپرس."

def available():
    return bool(API_KEY)

def jev_available():
    return bool(JEV_API_KEY)

def _exercise_context(limit=24):
    rows = []
    for eid, ex in list(X.EX.items())[:limit]:
        rows.append(f"- {ex['fa']} / {ex['en']} ({ex['grp']}): {ex['how'][:120]}")
    return "حرکت‌های موجود در ربات:\n" + "\n".join(rows)

def _chat(messages, model=None, max_tokens=700):
    if not API_KEY:
        return None, "no_key"
    url = BASE_URL + "/chat/completions"
    headers = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
    body = {"model": model or CHAT_MODEL, "messages": messages, "temperature": 0.4, "max_tokens": max_tokens}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code >= 400:
            log.warning("ai http %s: %s", r.status_code, r.text[:200])
            return None, "http_%s" % r.status_code
        data = r.json()
        txt = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        return (txt or None), None
    except Exception as e:
        log.warning("ai error: %s", type(e).__name__)
        return None, "err"

def classify_topic(text):
    """Use Jev to classify free-text into exercise/diet/supplement/photo_related/other.
    Returns (topic, err). On failure topic is 'other' and err is set — caller may still answer."""
    if not JEV_API_KEY:
        return "other", "no_jev_key"
    url = JEV_BASE_URL + "/v1/systemone"
    headers = {"Authorization": "Bearer " + JEV_API_KEY, "Content-Type": "application/json"}
    body = {
        "model": JEV_MODEL,
        "state": (text or "")[:4000],
        "questions": {
            "topic": {
                "type": "choice",
                "instructions": (
                    "Classify this Persian fitness-bot user message into exactly one topic. "
                    "exercise = workout form, exercises, training program, sets/reps. "
                    "diet = food, calories, meals, macros. "
                    "supplement = creatine, gainer, protein powder, safe OTC supplements. "
                    "photo_related = user wants body/form photo analysis or mentions sending a photo. "
                    "other = greetings, off-topic, medical diagnosis, steroids, or unclear."
                ),
                "criteria": {
                    "exercise": "Workout, form, exercises, training plan, sets/reps",
                    "diet": "Nutrition, calories, meals, macros",
                    "supplement": "Creatine, gainer, protein powder, safe supplements",
                    "photo_related": "Photo/body form analysis request",
                    "other": "Other, unclear, or out of scope",
                },
            }
        },
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        if r.status_code >= 400:
            log.warning("jev http %s: %s", r.status_code, r.text[:200])
            return "other", "http_%s" % r.status_code
        data = r.json()
        ans = ((data.get("answers") or {}).get("topic") or {})
        choice = (ans.get("choice") or "").strip().lower()
        if choice not in VALID_TOPICS:
            log.warning("jev unexpected choice: %r", choice)
            return "other", "bad_choice"
        return choice, None
    except Exception as e:
        log.warning("jev error: %s", type(e).__name__)
        return "other", "err"

def _topic_hint(topic):
    label = TOPIC_LABELS.get(topic, TOPIC_LABELS["other"])
    extra = {
        "exercise": "روی فرم حرکت، برنامه تمرین و نکات ایمنی تمرکز کن.",
        "diet": "روی تغذیه ساده، کالری و وعده‌ها تمرکز کن؛ رژیم پزشکی نده.",
        "supplement": "فقط مکمل ایمن (کراتین/گینر/پروتئین) با احتیاط؛ اجباری نکن.",
        "photo_related": "اگر عکس نفرستاده، بگو عکس بفرستد؛ تحلیل پزشکی نکن.",
        "other": "اگر خارج از بدنسازی است مودبانه به منو ارجاع بده.",
    }.get(topic, "")
    return f"موضوع تشخیص‌داده‌شده: {topic} ({label}). {extra}"

def answer(uid, text, user_ctx=None):
    """Free-text coaching: Jev classify → Gemini answer with topic context."""
    if not available():
        return FALLBACK_NO_KEY
    if hasattr(texts, "is_steroid_like") and texts.is_steroid_like(text):
        return texts.NO_STEROIDS

    topic, jerr = classify_topic(text)
    if jerr:
        log.info("jev classify fallback topic=%s err=%s", topic, jerr)

    ctx = user_ctx or ""
    sys = SYSTEM + "\n\n" + _topic_hint(topic) + "\n\n" + _exercise_context()
    user_msg = (f"زمینهٔ کاربر: {ctx}\n\n" if ctx else "") + f"موضوع: {topic}\nسؤال: {text}"
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_msg},
    ]
    out, err = _chat(messages)
    if not out:
        return FALLBACK_ERR
    return out[:3500]

def analyze_photo(uid, image_bytes, caption="", user_ctx=None):
    """Optional vision coaching via Gemini. Caller must only invoke when user sent a photo.
    Never call from onboarding. (Jev clef skipped for now.)"""
    if not available():
        return FALLBACK_NO_KEY
    b64 = base64.b64encode(image_bytes).decode("ascii")
    mime = "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n": mime = "image/png"
    elif image_bytes[:4] == b"RIFF": mime = "image/webp"
    prompt = (caption or "لطفاً این عکس را از نظر فرم بدنسازی / وضعیت ظاهری بررسی کن.").strip()
    ctx = user_ctx or ""
    messages = [
        {"role": "system", "content": PHOTO_SYSTEM},
        {"role": "user", "content": [
            {"type": "text", "text": (f"زمینه: {ctx}\n" if ctx else "") + prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]},
    ]
    out, err = _chat(messages, model=VISION_MODEL, max_tokens=800)
    if not out:
        return FALLBACK_ERR
    return out[:3500]

def user_context(u):
    if not u: return ""
    parts = []
    if u.get("sex"): parts.append("جنسیت=" + ("زن" if u["sex"] == "f" else "مرد"))
    if u.get("age"): parts.append(f"سن={u['age']}")
    if u.get("weight"): parts.append(f"وزن={u['weight']}")
    if u.get("plan_type"): parts.append(f"برنامه={u['plan_type']}")
    try:
        import programs_db as PDB
        c = PDB.category(u)
        if c: parts.append(f"وضعیت بدنی={PDB.CAT_FA[c]}")
    except Exception:
        pass
    if u.get("injuries"): parts.append(f"آسیب={u['injuries']}")
    return "، ".join(parts)
