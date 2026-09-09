#!/usr/bin/env bash
set -euo pipefail

# ===== Config (override via env or CLI VAR=...) =====
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
BRANCH="${BRANCH:-$(git branch --show-current)}"
SERVICES="${SERVICES:-aktien-tool.service}"
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

# Keep only the last 3 backups to prevent remote disk bloat
echo "🧹 Aufräumen: Behalte nur die letzten 3 Backups..."
ls -td "$BACKUP_ROOT"/monorepo-* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true

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
mkdir -p "$PROJECT_DIR/static/temp_social"
mkdir -p "$PROJECT_DIR/data/raw"
mkdir -p "$PROJECT_DIR/output"
mkdir -p "$PROJECT_DIR/logs"

echo "🚀 Services neu starten:"
for SVC in $SERVICES; do
  echo "   → $SVC"
  if [[ -f "$PROJECT_DIR/configs/$SVC" ]]; then
    sudo cp "$PROJECT_DIR/configs/$SVC" "/etc/systemd/system/$SVC"
  fi
  sudo systemctl daemon-reload
  sudo systemctl restart "$SVC"
  sudo systemctl status  "$SVC" --no-pager --lines 3 || true
done

echo "🌐 Nginx Konfiguration aktualisieren"
NGINX_CONFIG_CHANGED=0
NGINX_BACKUP_DIR="$(mktemp -d)"
NGINX_CONFIGS=()

backup_and_install_nginx_config() {
  local name="$1"
  local source="$2"
  local available="/etc/nginx/sites-available/$name"
  local enabled="/etc/nginx/sites-enabled/$name"

  NGINX_CONFIGS+=("$name")
  if sudo test -e "$available" || sudo test -L "$available"; then
    sudo cp -a "$available" "$NGINX_BACKUP_DIR/available-$name"
  fi
  if sudo test -e "$enabled" || sudo test -L "$enabled"; then
    sudo cp -a "$enabled" "$NGINX_BACKUP_DIR/enabled-$name"
  fi

  sudo cp "$source" "$available"
  sudo ln -sfn "$available" "$enabled"
  NGINX_CONFIG_CHANGED=1
}

restore_nginx_configs() {
  local name available enabled
  for name in "${NGINX_CONFIGS[@]}"; do
    available="/etc/nginx/sites-available/$name"
    enabled="/etc/nginx/sites-enabled/$name"
    sudo rm -f "$available" "$enabled"
    if sudo test -e "$NGINX_BACKUP_DIR/available-$name" || sudo test -L "$NGINX_BACKUP_DIR/available-$name"; then
      sudo cp -a "$NGINX_BACKUP_DIR/available-$name" "$available"
    fi
    if sudo test -e "$NGINX_BACKUP_DIR/enabled-$name" || sudo test -L "$NGINX_BACKUP_DIR/enabled-$name"; then
      sudo cp -a "$NGINX_BACKUP_DIR/enabled-$name" "$enabled"
    fi
  done
}

if [[ -f "$PROJECT_DIR/configs/aktien-tool.nginx" ]]; then
  backup_and_install_nginx_config "aktien-tool" "$PROJECT_DIR/configs/aktien-tool.nginx"
fi
if [[ -f "$PROJECT_DIR/configs/compare.nginx" ]]; then
  backup_and_install_nginx_config "compare" "$PROJECT_DIR/configs/compare.nginx"
fi
if [[ "$NGINX_CONFIG_CHANGED" == "1" ]]; then
  if ! sudo nginx -t; then
    echo "❌ Nginx-Konfiguration ungültig – stelle vorherigen Stand wieder her" >&2
    restore_nginx_configs
    sudo nginx -t || true
    sudo rm -rf "$NGINX_BACKUP_DIR"
    exit 1
  fi
  sudo systemctl reload nginx
fi
sudo rm -rf "$NGINX_BACKUP_DIR"

echo "🛑 Redundante Services stoppen falls aktiv"
sudo systemctl stop compare-app.service || true
sudo systemctl disable compare-app.service || true

echo "🧹 Alte Backups (>30 Tage) entfernen"
find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'monorepo-*' -mtime +30 -exec rm -rf {} \;

echo "✅ Deploy abgeschlossen auf Branch $BRANCH"
