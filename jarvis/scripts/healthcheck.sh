#!/usr/bin/env bash
# Healthcheck simple : sort 0 si /api/health répond {"status":"ok"}.
URL="${1:-http://localhost:8004/api/health}"
code=$(curl -fsS -o /tmp/jarvis_health.json -w "%{http_code}" "$URL" || echo "000")
if [ "$code" = "200" ] && grep -q '"status"' /tmp/jarvis_health.json; then
  echo "OK ($URL)"; exit 0
fi
echo "KO ($URL) http=$code"; exit 1
