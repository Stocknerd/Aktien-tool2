#!/bin/bash
#
# auto_pipeline.sh — Vollautomatische Daten-Pipeline
# Läuft auf Linux (Cronjob) oder manuell auf jedem System mit bash.
#
# Pipeline:
#   1. Git Pull (neuester Code)
#   2. Python: refresh_dividends.py (alle 4.000+ Aktien)
#   3. Git Commit & Push (stock_data.csv)
#   4. SSH: deploy.sh auf AWS Server auslösen
#
# Usage:
#   bash auto_pipeline.sh              # Nur Dividenden-Refresh (~30 Min)
#   bash auto_pipeline.sh --full       # Voller Refresh inkl. alle Metriken (~3h)
#
# Cronjob (alle 2 Tage um 06:00):
#   0 6 */2 * * /home/frank/Aktien-tool2/auto_pipeline.sh >> /home/frank/Aktien-tool2/logs/cron.log 2>&1
#
# Cronjob (Sonntags voller Refresh):
#   0 4 * * 0 /home/frank/Aktien-tool2/auto_pipeline.sh --full >> /home/frank/Aktien-tool2/logs/cron_full.log 2>&1
#
set -e

# ── Konfiguration ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

AWS_HOST="ubuntu@3.71.191.12"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/pipeline_$(date +%Y-%m-%d_%H%M).log"

FULL_MODE=false
if [ "$1" = "--full" ]; then
    FULL_MODE=true
fi

# ── Logging ──
exec > >(tee -a "$LOGFILE") 2>&1

echo "=============================================="
echo "  PIPELINE START: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Mode: $([ "$FULL_MODE" = true ] && echo 'FULL (all metrics)' || echo 'DIVIDENDS ONLY')"
echo "=============================================="

# ── SSH Key finden ──
SSH_KEY=""
for key in "$HOME/.ssh/id_rsa_antigravity_2048" \
           "$HOME/.ssh/id_rsa_antigravity" \
           "$HOME/.ssh/id_ed25519" \
           "$HOME/.ssh/id_rsa"; do
    if [ -f "$key" ]; then
        SSH_KEY="$key"
        break
    fi
done

if [ -z "$SSH_KEY" ]; then
    echo "❌ ERROR: Kein SSH-Key gefunden in ~/.ssh/"
    echo "   Bitte einen Key erstellen: ssh-keygen -t ed25519"
    echo "   Und auf dem AWS-Server autorisieren."
    exit 1
fi
echo "📌 SSH Key: $SSH_KEY"

# ── Python finden ──
PYTHON=""
for py in python3 python; do
    if command -v "$py" &>/dev/null; then
        PYTHON="$py"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ ERROR: Python nicht gefunden!"
    exit 1
fi
echo "📌 Python: $PYTHON ($($PYTHON --version 2>&1))"

# ── Step 1: Git Pull ──
echo ""
echo "── Step 1: Git Pull ──"
git pull origin main || echo "⚠ Git pull failed (maybe no remote changes)"

# ── Step 2: Daten aktualisieren ──
echo ""
echo "── Step 2: Daten aktualisieren ──"

if [ "$FULL_MODE" = true ]; then
    echo "🔄 Voller Refresh (update_csv_local.py)..."
    $PYTHON update_csv_local.py || {
        echo "⚠ update_csv_local.py hatte Fehler, fahre trotzdem fort..."
    }
fi

echo "🔄 Dividenden-Refresh (refresh_dividends.py)..."
$PYTHON tmp/refresh_dividends.py || {
    echo "⚠ refresh_dividends.py hatte Fehler, fahre trotzdem fort..."
}

# ── Step 3: Git Commit & Push ──
echo ""
echo "── Step 3: Git Commit & Push ──"
git add stock_data.csv
if git diff --cached --quiet; then
    echo "ℹ Keine Änderungen in stock_data.csv"
else
    COMMIT_MSG="Automated Data Update $(date +%Y-%m-%d)"
    [ "$FULL_MODE" = true ] && COMMIT_MSG="Full Data Refresh $(date +%Y-%m-%d)"
    git commit -m "$COMMIT_MSG"
    git push origin main
    echo "✅ Git Push erfolgreich"
fi

# ── Step 4: AWS Deployment ──
echo ""
echo "── Step 4: AWS Deployment ──"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$AWS_HOST" \
    "cd /home/ubuntu/aktien-tool2 && bash deploy.sh && sudo systemctl restart compare-app.service" || {
    echo "⚠ AWS Deployment fehlgeschlagen!"
    echo "  Server möglicherweise nicht erreichbar."
}

# ── Zusammenfassung ──
echo ""
echo "=============================================="
echo "  PIPELINE FERTIG: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Log: $LOGFILE"

# Zähle Aktien mit Dividenden-Daten
if command -v $PYTHON &>/dev/null; then
    DIV_COUNT=$($PYTHON -c "
import pandas as pd
df = pd.read_csv('stock_data.csv')
dy = pd.to_numeric(df.get('Dividendenrendite', []), errors='coerce')
ex = df['Ex-Dividenden-Datum'].notna().sum() if 'Ex-Dividenden-Datum' in df.columns else 0
print(f'{(dy > 0).sum()} Dividendenzahler, {ex} mit Ex-Datum')
" 2>/dev/null || echo "Stats nicht verfügbar")
    echo "  📊 $DIV_COUNT"
fi

echo "=============================================="
