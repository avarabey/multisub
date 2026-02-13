#!/usr/bin/env bash
set -euo pipefail

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-3}"
MAX_TIME="${MAX_TIME:-8}"

if curl -fsS --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME" "$HEALTH_URL" >/dev/null; then
  exit 0
fi

logger -t multisub-healthcheck "Healthcheck failed for $HEALTH_URL, restarting multisub"
systemctl restart multisub.service
sleep 2

if curl -fsS --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME" "$HEALTH_URL" >/dev/null; then
  logger -t multisub-healthcheck "multisub recovered after restart"
  exit 0
fi

logger -t multisub-healthcheck "multisub is still unhealthy after restart"
exit 1
