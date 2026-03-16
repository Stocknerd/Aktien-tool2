#!/usr/bin/env bash
set -euo pipefail

# ===== Config (override via env or CLI VAR=...) =====
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
BRANCH="${BRANCH:-$(git branch --show-current)}"
SERVICES="${SERVICES:-aktien-tool.service compare-app.service}"
REQUIREMENTS="${REQUIREMENTS:-$PROJECT_DIR/requirements.txt}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"
VENV="$PROJECT_DIR/venv"
PY="$VENV/bin/python"

timestamp="$(date +%F-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/monorepo-$timestamp"

echo "📦 Backup → $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
# Exclusion of heavy or unnecessary dirs
rsync -a --delete --exclude 'venv' --exclude 'backups' --exclude 'data/raw' --exclude '.git' "$PROJECT_DIR/" "$BACKUP_DIR/"

echo "🔄 Git Pull ($BRANCH)"
cd "$PROJECT_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "🐍 venv & deps"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install --quiet --upgrade pip
if [[ -f "$REQUIREMENTS" ]]; then
  "$PY" -m pip install --quiet --upgrade -r "$REQUIREMENTS"
fi

echo "📁 Verzeichnisse sicherstellen"
mkdir -p "$PROJECT_DIR/static/generated"
mkdir -p "$PROJECT_DIR/data/raw"
mkdir -p "$PROJECT_DIR/output"
mkdir -p "$PROJECT_DIR/logs"

echo "🚀 Services neu starten:"
for SVC in $SERVICES; do
  echo "   → $SVC"
  sudo systemctl daemon-reload
  sudo systemctl restart "$SVC"
  sudo systemctl status  "$SVC" --no-pager --lines 3 || true
done

echo "🧹 Alte Backups (>30 Tage) entfernen"
find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'monorepo-*' -mtime +30 -exec rm -rf {} \;

echo "✅ Deploy abgeschlossen auf Branch $BRANCH"
