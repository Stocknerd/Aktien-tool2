#!/usr/bin/env bash
set -euo pipefail

# ===== Config (override via env or CLI VAR=) =====
PROJECT_DIR="${PROJECT_DIR:-/home/ubuntu/aktien-tool2}"
BRANCH="${BRANCH:-main}"
SERVICES="${SERVICES:-aktien-tool.service compare-app.service}"
REQUIREMENTS="${REQUIREMENTS:-$PROJECT_DIR/requirements.txt}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"
VENV="$PROJECT_DIR/venv"
PY="$VENV/bin/python"

timestamp="$(date +%F-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/monorepo-$timestamp"

echo "📦 Backup → $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
rsync -a --delete --exclude 'venv' --exclude 'backups' "$PROJECT_DIR/" "$BACKUP_DIR/"

echo "🔄 Git Pull ($BRANCH)"
cd "$PROJECT_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "🐍 venv & deps"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install --quiet --upgrade pip
if [[ -f "$REQUIREMENTS" ]]; then
  "$PY" -m pip install --quiet --upgrade -r "$REQUIREMENTS"
else
  echo "⚠️  requirements.txt nicht gefunden unter $REQUIREMENTS – überspringe."
fi

# Optional: Build folders for compare app
if [[ -d "$PROJECT_DIR/static" ]]; then
  mkdir -p "$PROJECT_DIR/static/generated"
fi

echo "🚀 Services neu starten:"
for SVC in $SERVICES; do
  echo "   → $SVC"
  sudo systemctl restart "$SVC"
  sudo systemctl status  "$SVC" --no-pager --lines 3 || true
done

echo "🧹 Backups >30 Tage entfernen"
find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'monorepo-*' -mtime +30 -exec rm -rf {} \;

echo "✅ Deploy abgeschlossen"
