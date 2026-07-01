#!/usr/bin/env bash
# JARVIS v5.6 — Lancement PRODUCTION Linux (Gunicorn) avec arrêt gracieux.
set -euo pipefail

cd "$(dirname "$0")/.."

# ── Environnement ──
[ -f .env ] && set -a && . ./.env && set +a
export PYTHONUNBUFFERED=1
HOST="${JARVIS_HOST:-0.0.0.0}"
PORT="${JARVIS_PORT:-8004}"
WORKERS="${JARVIS_WORKERS:-1}"     # 1 worker : l'état sécurité/gardien est en mémoire
THREADS="${JARVIS_THREADS:-8}"

# ── Venv ──
if [ ! -d .venv ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install -U pip
  pip install -r requirements_v4.txt
  pip install gunicorn
else
  . .venv/bin/activate
fi

# ── HTTPS (optionnel) : reverse-proxy recommandé (nginx/caddy). Sinon certs : ──
SSL_ARGS=()
if [ -n "${JARVIS_SSL_CERT:-}" ] && [ -n "${JARVIS_SSL_KEY:-}" ]; then
  SSL_ARGS=(--certfile "$JARVIS_SSL_CERT" --keyfile "$JARVIS_SSL_KEY")
fi

# ── Logs rotatifs simples ──
mkdir -p logs
LOG="logs/jarvis.access.log"

echo "🚀 JARVIS (Gunicorn) → http://$HOST:$PORT  (healthcheck: /api/health)"
cd server
exec gunicorn \
  --workers "$WORKERS" --threads "$THREADS" --worker-class gthread \
  --bind "$HOST:$PORT" --timeout 120 --graceful-timeout 30 \
  --access-logfile "../$LOG" --error-logfile - --capture-output \
  "${SSL_ARGS[@]}" wsgi:app
