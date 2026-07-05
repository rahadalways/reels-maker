#!/usr/bin/env bash
# Reels Maker — Ubuntu/Debian VPS setup (ekbar cholabe)।
set -e
cd "$(dirname "$0")/.."
echo "==> Reels Maker VPS setup shuru..."

# 1. system deps
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-pip

# 2. python venv + deps
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-server.txt

# 3. secrets file (na thakle template banai)
if [ ! -f engine/.env ]; then
  cat > engine/.env <<'EOF'
REELS_LLM_API_KEY=your_opencode_zen_key_here
REELS_UI_PASSWORD=change_this_password
EOF
  echo "==> engine/.env banano holo — EDIT KORO (API key + UI password)!"
else
  echo "==> engine/.env already ache, rekhe dilam."
fi

echo ""
echo "✅ Setup shesh!"
echo "   1. nano engine/.env   (API key + password boshao)"
echo "   2. bash deploy/run.sh   (server chalu)"
