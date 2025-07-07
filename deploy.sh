#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/aktien-tool2"
BACKUP_ROOT="$HOME/backups"
BACKUP_DIR="$BACKUP_ROOT/aktien-tool2-$(date +%F-%H%M%S)"
SERVICE="aktien-tool.service"
PY="$PROJECT_DIR/venv/bin/python"

echo "📦 Backup nach $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
rsync -a --exclude 'venv' --exclude 'backups' "$PROJECT_DIR/" "$BACKUP_DIR/"

echo "🔄 Git Reset + Pull"
cd "$PROJECT_DIR"
git fetch origin main
git reset --hard origin/main

echo "📦 Dependencies aktualisieren"
$PY -m pip install --quiet --upgrade -r requirements.txt

echo "🚀 Service neu starten"
sudo systemctl restart "$SERVICE"
sudo systemctl status  "$SERVICE" --no-pager --lines 3

echo "🧹 Alte Backups (>30 Tage) löschen"
find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'aktien-tool2-*' -mtime +30 -exec rm -rf {} \;

echo "✅ Deployment abgeschlossen"
