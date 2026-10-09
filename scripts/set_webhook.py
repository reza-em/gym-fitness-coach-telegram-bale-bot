#!/usr/bin/env python3
"""Manage the Telegram / Bale webhook for the serverless deployment (run from your own machine, AFTER deploying).

    # info (read-only):
    python scripts/set_webhook.py info   --platform telegram
    # point the bot at Vercel (the polling bot for that token must be STOPPED first, see DEPLOY_VERCEL.md):
    python scripts/set_webhook.py set    --platform telegram --url https://<project>.vercel.app
    python scripts/set_webhook.py set    --platform bale     --url https://<project>.vercel.app
    # back to long polling (rollback; starting bot.py also deletes the webhook automatically):
    python scripts/set_webhook.py delete --platform telegram

Token: read from the env var named by --token-env (default FITNESS_TELEGRAM_BOT_TOKEN / FITNESS_BALE_BOT_TOKEN), so a
TEST bot can be used first, e.g. --token-env FITNESS_TELEGRAM_TEST_BOT_TOKEN.
Webhook URL: Telegram -> <url>/api/tg + secret_token header (TELEGRAM_WEBHOOK_SECRET);
             Bale     -> <url>/api/bale/<BALE_WEBHOOK_SECRET> (Bale's setWebhook only accepts `url`, no secret_token).
Nothing secret is printed: tokens are never shown and the Bale path secret is masked."""
import os, sys, json, argparse
import requests

API = {"telegram": "https://api.telegram.org", "bale": "https://tapi.bale.ai"}
TOKEN_ENV = {"telegram": "FITNESS_TELEGRAM_BOT_TOKEN", "bale": "FITNESS_BALE_BOT_TOKEN"}

def mask(s, secrets):
    s = str(s)
    for x in secrets:
        if x: s = s.replace(x, "<secret>")
    return s

def call(platform, token, method, data=None):
    r = requests.post("%s/bot%s/%s" % (API[platform], token, method), json=data or {}, timeout=30)
    try: return r.json()
    except Exception: return {"ok": False, "description": "HTTP %d (non-JSON response)" % r.status_code}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("info", "set", "delete"))
    ap.add_argument("--platform", choices=("telegram", "bale"), required=True)
    ap.add_argument("--url", help="deployment base URL, e.g. https://fitness-bot.vercel.app (for 'set')")
    ap.add_argument("--token-env", help="env var holding the bot token (default: %s)" % TOKEN_ENV)
    ap.add_argument("--drop-pending", action="store_true", help="drop queued updates on set/delete (default: keep them)")
    ap.add_argument("--max-connections", type=int, default=10, help="Telegram only: parallel webhook connections (default 10)")
    a = ap.parse_args()

    tok_env = a.token_env or TOKEN_ENV[a.platform]
    token = os.environ.get(tok_env, "").strip()
    if not token: sys.exit("%s is not set" % tok_env)
    tg_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    bale_secret = os.environ.get("BALE_WEBHOOK_SECRET", "").strip()
    secrets = [token, tg_secret, bale_secret]

    if a.action == "info":
        res = call(a.platform, token, "getWebhookInfo")
    elif a.action == "delete":
        data = {"drop_pending_updates": True} if a.drop_pending and a.platform == "telegram" else {}
        res = call(a.platform, token, "deleteWebhook", data)
    else:
        if not a.url or not a.url.startswith("https://"): sys.exit("--url https://... is required for 'set'")
        base = a.url.rstrip("/")
        if a.platform == "telegram":
            if not tg_secret: sys.exit("TELEGRAM_WEBHOOK_SECRET is not set (must equal the value configured in Vercel)")
            data = {"url": base + "/api/tg", "secret_token": tg_secret, "allowed_updates": ["message", "callback_query"],
                    "max_connections": a.max_connections, "drop_pending_updates": bool(a.drop_pending)}
        else:
            if not bale_secret: sys.exit("BALE_WEBHOOK_SECRET is not set (must equal the value configured in Vercel)")
            data = {"url": base + "/api/bale/" + bale_secret}
        res = call(a.platform, token, "setWebhook", data)
        if res.get("ok"):
            print("setWebhook ok ->", mask(data["url"], secrets))
            res = call(a.platform, token, "getWebhookInfo")
    print(mask(json.dumps(res, ensure_ascii=False, indent=1), secrets))
    sys.exit(0 if res.get("ok") else 1)

if __name__ == "__main__":
    main()
