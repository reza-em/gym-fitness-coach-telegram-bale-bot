#!/bin/bash
# Fitness-coach bot launcher: one detached auto-restart supervisor PER PLATFORM, single instance each.
# Tokens come from the environment only (never written anywhere):  FITNESS_TELEGRAM_BOT_TOKEN, FITNESS_BALE_BOT_TOKEN
#   ./run.sh                 start every platform whose token env var is set (idempotent)
#   ./run.sh telegram|bale   start just one platform
#   ./stop.sh [telegram|bale] stop
cd "$(dirname "$0")"
DIR="$(pwd)"
PY="$DIR/venv/bin/python"; [ -x "$PY" ] || PY=python3

if [ "$1" = "--loop" ]; then          # internal: supervisor loop for platform $2
  P="$2"
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

start_one() {
  local P="$1" VAR LOG
  if [ "$P" = "bale" ]; then VAR=FITNESS_BALE_BOT_TOKEN; LOG=bale.log; else VAR=FITNESS_TELEGRAM_BOT_TOKEN; LOG=bot.log; fi
  if [ -z "$(printenv "$VAR")" ]; then echo "$VAR not set - $P bot not started"; return 1; fi
  if [ -f "run_$P.pid" ] && kill -0 "$(cat "run_$P.pid")" 2>/dev/null; then
    echo "fitness-bot ($P) already running (supervisor pid $(cat "run_$P.pid"))"; return 0
  fi
  setsid nohup "$DIR/run.sh" --loop "$P" >/dev/null 2>&1 < /dev/null &
  sleep 1; echo "fitness-bot ($P) started (supervisor pid $(cat "run_$P.pid" 2>/dev/null)); log: $DIR/$LOG"
}

RC=1
case "$1" in
  telegram|bale) start_one "$1"; RC=$? ;;
  "") for P in telegram bale; do start_one "$P" && RC=0; done ;;
  *) echo "usage: $0 [telegram|bale]" >&2; exit 2 ;;
esac
exit $RC
