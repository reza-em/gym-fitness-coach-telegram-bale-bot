"""Vercel serverless entrypoint (Flask WSGI app `app`). One function serves both bots:

  POST /api/tg                    Telegram webhook   (header X-Telegram-Bot-Api-Secret-Token == TELEGRAM_WEBHOOK_SECRET)
  POST /api/bale/<secret>         Bale webhook       (Bale's setWebhook has no secret_token -> secret path segment == BALE_WEBHOOK_SECRET)
  GET|POST /api/cron/tick?platform=telegram|bale|all   reminders (Authorization: Bearer CRON_SECRET, or X-Cron-Secret header)
  GET /api/health                 liveness (no secrets, no DB access)

Each webhook request: pick the platform (plat.use), dedupe by update_id, run the existing handler synchronously,
answer 200. No background threads (the polling-mode reminder thread is replaced by the cron endpoint).
Local run:  FITNESS_DB_PATH=... python api/index.py  (or: flask --app api.index run)"""
import os, sys, time, hmac, logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
os.environ.setdefault("FITNESS_SERVERLESS", "1")                 # plat.py: /tmp for local files, per-request platform
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")        # matplotlib needs a writable cache dir (bundle is read-only)

from flask import Flask, request, jsonify                       # noqa: E402
import plat, db                                                 # noqa: E402
import core as C                                                # noqa: E402
import bot, remind, admin                                       # noqa: E402

C.setup_logging()
log = logging.getLogger("bot")
app = Flask(__name__)

def _eq(a, b):
    return bool(a) and bool(b) and hmac.compare_digest(str(a).encode(), str(b).encode())

def _webhook(platform):
    P = plat.get(platform)
    if not P.token:
        log.error("%s is not set - cannot answer %s updates", P.token_env, platform)
        return jsonify(ok=False, error="bot token not configured"), 503
    up = request.get_json(silent=True, force=True)
    if not isinstance(up, dict):
        return jsonify(ok=False, error="bad update"), 400
    t0 = time.time()
    try:
        with plat.use(platform):
            handled = bot.process_update(up)
    except Exception as e:                                       # DB down etc.: 500 -> the platform re-delivers later
        log.exception("%s update %s failed: %s", platform, up.get("update_id"), C.safe(e)[:200])
        return jsonify(ok=False), 500
    log.info("%s update %s %s in %.2fs", platform, up.get("update_id"), "handled" if handled else "duplicate", time.time() - t0)
    return jsonify(ok=True)

@app.post("/api/tg")
def telegram_webhook():
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret: return jsonify(ok=False, error="TELEGRAM_WEBHOOK_SECRET not configured"), 503
    if not _eq(request.headers.get("X-Telegram-Bot-Api-Secret-Token"), secret):
        return jsonify(ok=False), 401
    return _webhook("telegram")

@app.post("/api/bale/<path:given>")
def bale_webhook(given):
    secret = os.environ.get("BALE_WEBHOOK_SECRET", "")
    if not secret: return jsonify(ok=False, error="BALE_WEBHOOK_SECRET not configured"), 503
    if not _eq(given, secret): return jsonify(ok=False), 401
    return _webhook("bale")

@app.post("/api/bale")
def bale_webhook_no_secret():
    return jsonify(ok=False), 401

def _cron_authorized():
    secret = os.environ.get("CRON_SECRET", "")
    if not secret: return False
    auth = request.headers.get("Authorization", "")
    given = auth[7:] if auth.startswith("Bearer ") else request.headers.get("X-Cron-Secret", "")
    return _eq(given, secret)

@app.route("/api/cron/tick", methods=["GET", "POST"])
def cron_tick():
    if not os.environ.get("CRON_SECRET"): return jsonify(ok=False, error="CRON_SECRET not configured"), 503
    if not _cron_authorized(): return jsonify(ok=False), 401
    want = (request.args.get("platform") or "all").strip().lower()
    names = plat.NAMES if want == "all" else (want,)
    if any(n not in plat.NAMES for n in names): return jsonify(ok=False, error="platform must be telegram|bale|all"), 400
    budget = float(os.environ.get("CRON_TICK_BUDGET_S", "50"))
    deadline = time.time() + budget
    out = {}
    for n in names:
        P = plat.get(n)
        if not P.token: out[n] = "skipped (no token)"; continue
        try:
            with plat.use(n):
                bot.ensure_ready()
                sent = remind.tick(deadline=deadline)
                bc = 0
                try: bc = admin.broadcast_step(deadline=deadline)    # resumable admin broadcast: next chunk
                except Exception as e: log.warning("broadcast_step: %s", C.safe(e)[:120])
                try: db.prune_updates()
                except Exception as e: log.warning("prune_updates: %s", C.safe(e)[:80])
                try: bot.setup_profile()                         # no-op unless commands/texts changed (sha in meta)
                except Exception as e: log.warning("setup_profile: %s", C.safe(e)[:80])
            out[n] = {"sent": sent, **({"broadcast": bc} if bc else {})}
        except Exception as e:
            log.exception("tick %s failed: %s", n, C.safe(e)[:200])
            out[n] = "error"
    status = 500 if any(v == "error" for v in out.values()) else 200
    return jsonify(ok=status == 200, result=out), status

@app.get("/api/health")
@app.get("/api")
def health():
    return jsonify(ok=True, platforms={n: bool(plat.get(n).token) for n in plat.NAMES},
                   storage={n: ("turso" if plat.get(n).turso_url else "sqlite") for n in plat.NAMES})

@app.errorhandler(404)
def not_found(_e): return jsonify(ok=False, error="not found"), 404

if __name__ == "__main__":                                       # local dev server
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8787")), debug=False)
