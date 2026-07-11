#!/usr/bin/env bash
# Bootstrap the deal bot on a fresh Oracle Cloud Always Free VM (Ubuntu ARM).
# Run as a normal user with sudo:  bash deploy/oracle/install.sh
set -euo pipefail

APP_DIR="$HOME/bot-price-nunes"
REPO="https://github.com/Guilhermennf/bot-price-nunes.git"

sudo apt-get update -y
sudo apt-get install -y python3.12 python3.12-venv git

if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
git pull

python3.12 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m playwright install --with-deps chromium

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">>> EDIT $APP_DIR/.env with your real secrets before enabling timers <<<"
fi

# systemd units (user-level would need lingering; system-level is simpler here)
sudo cp deploy/oracle/dealbot-collect.service /etc/systemd/system/
sudo cp deploy/oracle/dealbot-collect.timer   /etc/systemd/system/
sudo cp deploy/oracle/dealbot-post.service    /etc/systemd/system/
sudo cp deploy/oracle/dealbot-post.timer      /etc/systemd/system/
sudo sed -i "s|__APP_DIR__|$APP_DIR|g; s|__USER__|$USER|g" \
  /etc/systemd/system/dealbot-collect.service \
  /etc/systemd/system/dealbot-post.service

sudo systemctl daemon-reload
sudo systemctl enable --now dealbot-collect.timer dealbot-post.timer

echo "Timers active:"
systemctl list-timers 'dealbot-*' --no-pager
