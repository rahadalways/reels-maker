#!/usr/bin/env bash
# Reels Maker — server chalu (gunicorn, public IP:port)।
cd "$(dirname "$0")/.."

# engine/.env theke env load
set -a
# shellcheck disable=SC1091
source engine/.env
set +a

HOST="${REELS_HOST:-0.0.0.0}"
PORT="${REELS_PORT:-5000}"

if [ "${REELS_UI_PASSWORD:-}" = "change_this_password" ] || [ -z "${REELS_UI_PASSWORD:-}" ]; then
  echo "⚠️  WARNING: REELS_UI_PASSWORD set kora nai / default ache — engine/.env e change koro!"
fi

echo "🚀 http://${HOST}:${PORT}  (Ctrl+C bondho korte)"
exec .venv/bin/gunicorn \
  --workers 1 --threads 8 --timeout 3600 \
  --bind "${HOST}:${PORT}" \
  --chdir engine/web app:app
