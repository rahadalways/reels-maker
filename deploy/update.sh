#!/usr/bin/env bash
# VM e manually update korte (auto-deploy chara): latest tene rebuild + restart.
set -e
cd "$(dirname "$0")/.."
git pull origin main
docker compose up -d --build
docker image prune -f
echo "✅ updated & running — docker compose ps diye dekho"
