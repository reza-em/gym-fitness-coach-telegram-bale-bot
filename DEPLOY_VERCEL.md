# 🚀 Deploy on Vercel (serverless) + Turso — راهنمای استقرار روی Vercel

> Branch: `serverless-vercel`. The polling mode (`run.sh` / `bot.py`) keeps working unchanged; the same code also runs
> as a Vercel function. **Never commit tokens/secrets** — they live only in Vercel / GitHub / your shell env.
>
> این شاخه ربات را روی Vercel (بدون سرور) اجرا می‌کند. حالت قبلی (polling با `run.sh`) هم دست‌نخورده کار می‌کند.
> هیچ توکن یا رمزی را داخل گیت نگذارید.

## How it works / معماری

| Part | Polling (today) | Vercel |
|---|---|---|
| Updates | `getUpdates` loop in `bot.py` | Webhook → `POST /api/tg` (header `X-Telegram-Bot-Api-Secret-Token`), `POST /api/bale/<BALE_WEBHOOK_SECRET>` (Bale's `setWebhook` has **no** `secret_token`, so the secret is a path segment) |
| Platform | `FITNESS_PLATFORM` per process | per request (`plat.use(...)`), one function serves both bots |
| Storage | `fitness.db`, `fitness_bale.db` (SQLite) | Turso/libSQL: **two databases** (`TURSO_DATABASE_URL`, `TURSO_DATABASE_URL_BALE`) |
| Reminders | thread calling `remind.tick()` every 30 s | `GET/POST /api/cron/tick?platform=telegram\|bale\|all` (Bearer `CRON_SECRET`) called every 5 min by GitHub Actions (`.github/workflows/cron-tick.yml`) — Vercel Hobby cron can only run **once per day** |
| Retries | — | duplicate deliveries ignored (`updates_seen` table, keyed by `update_id`) |

Entry point: `api/index.py` (Flask WSGI `app`), config: `vercel.json` (maxDuration 120 s, Hobby allows ≤ 300 s; function region `hnd1` Tokyo = same AWS region as the Turso DB `aws-ap-northeast-1` — change both together), Python `3.13` (`.python-version`).

## Environment variables (names only) / متغیرهای محیطی

Vercel → Project → Settings → Environment Variables (Production):

| Name | Required | Notes |
|---|---|---|
| `FITNESS_TELEGRAM_BOT_TOKEN` | yes (Telegram) | first a **TEST** bot token, the real one only at switchover |
| `FITNESS_BALE_BOT_TOKEN` | yes (Bale) | same: test bot first |
| `TELEGRAM_WEBHOOK_SECRET` | yes | random, `A-Z a-z 0-9 _ -` only, ≤ 256 chars |
| `BALE_WEBHOOK_SECRET` | yes | random, URL-safe |
| `CRON_SECRET` | yes | random; same value as the GitHub secret `CRON_SECRET` |
| `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` | yes | Telegram database |
| `TURSO_DATABASE_URL_BALE` / `TURSO_AUTH_TOKEN_BALE` | yes (Bale) | Bale database (token falls back to `TURSO_AUTH_TOKEN`, e.g. a group token) |
| `OWNER_ID`, `OWNER_USERNAME` | recommended | Telegram owner numeric id (Bale owner uses `/claim`, code is printed in the Vercel logs) |
| `FITNESS_OPENAI_API_KEY` (or `OPENAI_API_KEY`) | optional | AI answers / photo feedback |
| `FITNESS_OPENROUTER_API_KEY` (or `JEV_AI_API_KEY`) | optional | topic classifier |
| `FITNESS_OPENAI_BASE_URL`, `FITNESS_AI_MODEL`, `FITNESS_VISION_MODEL`, `JEV_AI_BASE_URL`, `FITNESS_JEV_MODEL` | optional | defaults are in `ai.py` |
| `CRON_TICK_BUDGET_S` | optional | seconds per tick (default 50) |

GitHub → repo → Settings → Secrets and variables → Actions: `VERCEL_URL` (e.g. `planerem-fitness-bot.vercel.app`), `CRON_SECRET`.
**Set these two only at switchover** (otherwise Vercel and the polling bot would both send reminders). Scheduled
workflows run only from the default branch, so the workflow becomes active after this branch is merged into `main`.

Generate secrets / ساخت رمز تصادفی:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step by step / گام‌به‌گام

### 1. Turso (database) / پایگاه داده
1. Sign up at https://turso.tech (free plan: 100 DBs, 5 GB, 500 M rows read, 10 M rows written / month).
   در turso.tech ثبت‌نام کنید (پلن رایگان کافی است).
2. Install the CLI and log in: `curl -sSfL https://get.tur.so/install.sh | bash` → `turso auth login`.
3. Create two databases in the same group/region (the existing DB `fitness` is in `aws-ap-northeast-1` Tokyo, matching `"regions": ["hnd1"]` in `vercel.json`):
   ```bash
   turso db create fitness-telegram
   turso db create fitness-bale
   turso db show fitness-telegram --url     # -> TURSO_DATABASE_URL
   turso db show fitness-bale --url         # -> TURSO_DATABASE_URL_BALE
   turso db tokens create fitness-telegram  # -> TURSO_AUTH_TOKEN
   turso db tokens create fitness-bale      # -> TURSO_AUTH_TOKEN_BALE
   ```
   (or one group token for both: `turso group tokens create <group>`). If Vercel's region is changed in Project
   Settings → Functions, keep Turso in the same AWS region.

### 2. Vercel (hosting) / میزبانی
1. Sign up at https://vercel.com (Hobby is free) and import the GitHub repo `reza-em/gym-fitness-coach-telegram-bale-bot`,
   **Production Branch = `serverless-vercel`** (Settings → Git) until it is merged. No build command needed.
   یا با CLI: `npx vercel link` و `npx vercel deploy --prod` از پوشهٔ همین شاخه.
2. Add the environment variables above (with the **TEST** bot tokens), then redeploy.
3. Check: `curl https://<project>.vercel.app/api/health` → `{"ok":true,...}` (shows which tokens/storage are configured, never their values).

### 3. Copy the data / انتقال داده‌ها (Telegram and Bale separately)
```bash
cd /workspace/fitness-bot-vercel      # this branch, with .venv (pip install -r requirements.txt)
export TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... TURSO_DATABASE_URL_BALE=... [TURSO_AUTH_TOKEN_BALE=...]
.venv/bin/python scripts/migrate_sqlite_to_turso.py --platform telegram --src ../fitness-bot/fitness.db --dry-run
.venv/bin/python scripts/migrate_sqlite_to_turso.py --platform telegram --src ../fitness-bot/fitness.db --wipe
.venv/bin/python scripts/migrate_sqlite_to_turso.py --platform bale     --src ../fitness-bot/fitness_bale.db --wipe
```
The source is opened read-only (online backup snapshot). A copy made before switchover is only a rehearsal — copy
again with `--wipe` **after** stopping the polling bot (step 5).

### 4. Test with a separate TEST bot first / اول با ربات آزمایشی
1. Create a test bot: Telegram @BotFather `/newbot`; Bale @botfather. Put the test tokens into Vercel
   (`FITNESS_TELEGRAM_BOT_TOKEN` / `FITNESS_BALE_BOT_TOKEN`) and redeploy.
   Tip: for a clean test use separate Turso test DBs, or accept that the test bot sees the copied data.
2. Point the TEST bot at Vercel (from your machine, secrets in env only):
   ```bash
   export FITNESS_TELEGRAM_TEST_BOT_TOKEN=...  TELEGRAM_WEBHOOK_SECRET=...  BALE_WEBHOOK_SECRET=...
   python scripts/set_webhook.py set  --platform telegram --url https://<project>.vercel.app --token-env FITNESS_TELEGRAM_TEST_BOT_TOKEN
   python scripts/set_webhook.py info --platform telegram --token-env FITNESS_TELEGRAM_TEST_BOT_TOKEN
   ```
3. In the test bot: `/start`, full onboarding, `/macros`, `/bodytype`, `/progress` (chart), `/today`, a free-text AI question, a photo.
4. Reminders: `curl -X POST -H "Authorization: Bearer $CRON_SECRET" "https://<project>.vercel.app/api/cron/tick?platform=telegram"`.
5. Vercel → Deployments → Logs: no errors; `getWebhookInfo` shows `pending_update_count` 0 and no `last_error_message`.

### 5. Switchover (real bots) / جابه‌جایی ربات اصلی
Order matters — the polling bot deletes any webhook when it (re)starts, and it would also send reminders twice.
ترتیب مهم است: اول ربات قدیمی را کامل متوقف کنید.
1. `./stop.sh telegram` (or `./stop.sh` for both) in `/workspace/fitness-bot`, and add `FITNESS_DISABLE_POLLING=telegram` (space-separated list, e.g. `telegram bale`) to its `.env` so `run.sh` / `bot.py` never start polling for that platform again (polling would delete the webhook).
2. Fresh data copy with `--wipe` (step 3) for both platforms.
3. Vercel env: replace the test tokens with the real `FITNESS_TELEGRAM_BOT_TOKEN` / `FITNESS_BALE_BOT_TOKEN`, redeploy.
4. `python scripts/set_webhook.py set --platform telegram --url https://<project>.vercel.app` and the same with `--platform bale`
   (queued updates are kept and delivered to the webhook).
5. GitHub secrets `VERCEL_URL` + `CRON_SECRET`; merge `serverless-vercel` into `main` so the 5-minute reminder tick runs. The workflow ticks only `telegram` by default; set the repo variable `TICK_PLATFORMS="telegram bale"` when Bale moves too.
6. Watch logs + `set_webhook.py info` for a day.

### 6. Rollback / بازگشت
1. `python scripts/set_webhook.py delete --platform telegram` (and `bale`) — or simply start the polling bot: `bot.py` deletes the webhook on start.
2. Delete the GitHub secret `VERCEL_URL` (the cron workflow then skips).
3. Data written on Vercel since the switchover lives in Turso. To keep it, export it back before restarting polling, e.g.
   `turso db shell fitness-telegram .dump > tg.sql` → `sqlite3 fitness.db.new < tg.sql` (stop, swap files, keep a backup of the old file).
4. Remove the platform from `FITNESS_DISABLE_POLLING` in `.env`, then `./run.sh telegram` in `/workspace/fitness-bot`.

## Local development / اجرای محلی
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
FITNESS_DATA_DIR=/tmp/fit TELEGRAM_WEBHOOK_SECRET=x BALE_WEBHOOK_SECRET=y CRON_SECRET=z \
FITNESS_TELEGRAM_BOT_TOKEN=... .venv/bin/python api/index.py          # http://127.0.0.1:8787
.venv/bin/python test_serverless.py                                    # webhook app, both platforms, fake Bot API
SERVERLESS_TEST_STORAGE=libsql .venv/bin/python test_serverless.py     # libSQL client on local files
```
`FITNESS_TELEGRAM_API_BASE` / `FITNESS_BALE_API_BASE` can point the bot at a local/fake Bot API server.

## Limits & risks / محدودیت‌ها و ریسک‌ها
- **Cold starts**: first request after idle imports matplotlib/numpy (~1–3 s); the user just sees a slower first reply.
- **Long requests**: AI answers can take up to ~90 s (30 s classifier + 60 s model), photo analysis up to ~2 min; maxDuration is 120 s (raise to 300 in `vercel.json` if needed — Hobby max). If Telegram re-delivers a slow update, it is ignored by the `update_id` dedupe.
- **Admin broadcast** sleeps between messages; with many users it can exceed maxDuration (partially sent).
- **Turso latency**: every query is a network round trip (keep Turso in the same AWS region as the Vercel function). Free-plan quotas block the DB when exceeded.
- **Reminders** depend on GitHub's best-effort schedule (delays of 5–20 min are normal; reminders are still sent up to 180 min late). GitHub disables schedules after 60 days without repo activity.
- **Bale reachability**: Bale's servers must reach `*.vercel.app` and Vercel (US) must reach `tapi.bale.ai`; if either is filtered, use a custom domain or keep Bale on polling (the two platforms can be switched independently).
- In-memory rate limiting is per function instance (looser than before).
