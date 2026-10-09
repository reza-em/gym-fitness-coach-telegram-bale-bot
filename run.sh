#!/bin/bash
# Fitness-coach bot launcher: one detached auto-restart supervisor PER PLATFORM, single instance each.
# Tokens come from the environment only (never written anywhere):  FITNESS_TELEGRAM_BOT_TOKEN, FITNESS_BALE_BOT_TOKEN
#   ./run.sh                 start every platform whose token env var is set (idempotent)
#   ./run.sh telegram|bale   start just one platform
#   ./run.sh ticker          start only the reminder ticker (see below)
#   ./stop.sh [telegram|bale|ticker] stop
# Reminder ticker (fallback for the GitHub Actions cron, which is best effort): when FITNESS_TICK_URL is set (.env), e.g.
#   FITNESS_TICK_URL=https://planerem-fitness-bot.vercel.app/api/cron/tick?platform=telegram
#   CRON_SECRET_FILE=/home/box/.secrets/CRON_SECRET     (or CRON_SECRET in the environment)
# every ./run.sh call also makes sure ONE detached loop POSTs that URL every FITNESS_TICK_EVERY seconds (default 300).
# Reminder claims are idempotent per user/day, so ticks from GitHub and from here may overlap safely.
cd "$(dirname "$0")"
DIR="$(pwd)"
# Optional local, git-ignored settings (e.g. OWNER_ID / OWNER_USERNAME). Never commit .env.
if [ -f "$DIR/.env" ]; then set -a; . "$DIR/.env"; set +a; fi
# AI defaults (override with env)
# Chat+vision: Cheaper Inference (Gemini). Classify: Jev AI.
export FITNESS_OPENAI_BASE_URL="${FITNESS_OPENAI_BASE_URL:-https://api.cheaperinference.com/v1}"
export FITNESS_AI_MODEL="${FITNESS_AI_MODEL:-gemini-3.8-flash}"
export FITNESS_VISION_MODEL="${FITNESS_VISION_MODEL:-gemini-3.8-flash}"
# Jev key: prefer JEV_AI_API_KEY; also accept FITNESS_OPENROUTER_API_KEY (legacy name for this key)
if [ -z "${JEV_AI_API_KEY:-}" ] && [ -n "${FITNESS_OPENROUTER_API_KEY:-}" ]; then
  export JEV_AI_API_KEY="$FITNESS_OPENROUTER_API_KEY"
fi
export JEV_AI_BASE_URL="${JEV_AI_BASE_URL:-https://jev-ai.pro/api}"
export FITNESS_JEV_MODEL="${FITNESS_JEV_MODEL:-jev-latest}"

PY="$DIR/venv/bin/python"; [ -x "$PY" ] || PY=python3

# Platforms that run as webhooks on Vercel must NOT be polled here (bot.py would delete the webhook on start).
# Set in .env, e.g. FITNESS_DISABLE_POLLING=telegram   (rollback: remove it, then ./run.sh telegram)
disabled() { case " ${FITNESS_DISABLE_POLLING//,/ } " in *" $1 "*) return 0 ;; esac; return 1; }

if [ "$1" = "--loop" ]; then          # internal: supervisor loop for platform $2
  P="$2"
  disabled "$P" && exit 0
  if [ "$P" = "bale" ]; then LOG=bale.log; else LOG=bot.log; fi
  exec 9>"run_$P.lock"
  flock -n 9 || exit 0                # only one supervisor per platform, ever
  echo $$ > "run_$P.pid"
  umask 077
  export FITNESS_PLATFORM="$P"
  trap 'rm -f "run_$P.pid"; exit 0' TERM INT
  while true; do
    "$PY" bot.py >> "$LOG" 2>&1
    RC=$?
    echo "$(date '+%F %T') $P bot exited ($RC), restarting in 5s" >> "$LOG"
    [ "$RC" = "0" ] && [ -z "$(printenv "FITNESS_$(echo "$P" | tr a-z A-Z)_BOT_TOKEN")" ] && break
    sleep 5
  done
  exit 0
fi

if [ "$1" = "--ticker" ]; then        # internal: reminder ticker loop
  exec 8>"run_ticker.lock"
  flock -n 8 || exit 0                # only one ticker, ever
  echo $$ > "run_ticker.pid"
  umask 077
  trap 'rm -f "run_ticker.pid"; exit 0' TERM INT
  while true; do
    S="${CRON_SECRET:-}"; [ -z "$S" ] && [ -n "${CRON_SECRET_FILE:-}" ] && S="$(cat "$CRON_SECRET_FILE" 2>/dev/null)"
    if [ -z "$S" ]; then echo "$(date '+%F %T') ticker: no CRON_SECRET / CRON_SECRET_FILE" >> ticker.log
    else
      # the secret goes through stdin (curl -K -), never on the command line (visible in ps)
      OUT=$(printf 'header = "Authorization: Bearer %s"\n' "$S" | curl -sS -K - -X POST --max-time 150 -w ' HTTP %{http_code}' "$FITNESS_TICK_URL" 2>&1 | tr -d '\n' | head -c 300)
      echo "$(date '+%F %T') tick: $OUT" >> ticker.log
    fi
    sleep "${FITNESS_TICK_EVERY:-300}" & wait $!    # wait: TERM is handled immediately
  done
fi

start_ticker() {
  [ -n "${FITNESS_TICK_URL:-}" ] || { [ "$1" = "explicit" ] && echo "FITNESS_TICK_URL not set - ticker not started"; return 1; }
  if [ -f run_ticker.pid ] && kill -0 "$(cat run_ticker.pid)" 2>/dev/null; then
    [ "$1" = "explicit" ] && echo "reminder ticker already running (pid $(cat run_ticker.pid))"; return 0
  fi
  setsid nohup "$DIR/run.sh" --ticker >/dev/null 2>&1 < /dev/null &
  sleep 1; echo "reminder ticker started (pid $(cat run_ticker.pid 2>/dev/null)); log: $DIR/ticker.log"
}

start_one() {
  local P="$1" VAR LOG
  if [ "$P" = "bale" ]; then VAR=FITNESS_BALE_BOT_TOKEN; LOG=bale.log; else VAR=FITNESS_TELEGRAM_BOT_TOKEN; LOG=bot.log; fi
  if disabled "$P"; then echo "$P polling disabled (FITNESS_DISABLE_POLLING) - it runs on Vercel; not started"; return 1; fi
  if [ -z "$(printenv "$VAR")" ]; then echo "$VAR not set - $P bot not started"; return 1; fi
  if [ -f "run_$P.pid" ] && kill -0 "$(cat "run_$P.pid")" 2>/dev/null; then
    echo "fitness-bot ($P) already running (supervisor pid $(cat "run_$P.pid"))"; return 0
  fi
  setsid nohup "$DIR/run.sh" --loop "$P" >/dev/null 2>&1 < /dev/null &
  sleep 1; echo "fitness-bot ($P) started (supervisor pid $(cat "run_$P.pid" 2>/dev/null)); log: $DIR/$LOG"
}

RC=1
case "$1" in
  telegram|bale) start_one "$1"; RC=$?; start_ticker ;;
  "") for P in telegram bale; do start_one "$P" && RC=0; done; start_ticker && RC=0 ;;
  ticker) start_ticker explicit; RC=$? ;;
  *) echo "usage: $0 [telegram|bale|ticker]" >&2; exit 2 ;;
esac
exit $RC
