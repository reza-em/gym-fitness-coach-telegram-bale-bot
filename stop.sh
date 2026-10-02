#!/bin/bash
# Stop the fitness-bot supervisor loop(s) and bot process(es):  ./stop.sh [telegram|bale]
cd "$(dirname "$0")"
for P in ${1:-telegram bale}; do
  [ -f "run_$P.pid" ] && kill "$(cat "run_$P.pid")" 2>/dev/null
  L=bot.lock; [ "$P" = "bale" ] && L=bot_bale.lock
  [ -f "$L" ] && { B=$(cat "$L"); [ -n "$B" ] && kill "$B" 2>/dev/null; }
  sleep 1; rm -f "run_$P.pid"
  echo "fitness-bot ($P) stopped"
done
