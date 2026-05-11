#!/bin/bash
#
# auto_pipeline.sh — Vollautomatische Daten-Pipeline
#
# Pipeline:
#   1. Git Pull (neuester Code)
#   2. Python: update_csv_local.py (ALLE Metriken inkl. Dividenden)
#   3. Git Commit & Push (stock_data.csv)
#   4. SSH: deploy.sh auf AWS Server auslösen
#
# Cronjob (alle 2 Tage um 06:00):
#   0 6 */2 * * /home/frank/Aktien-tool2/auto_pipeline.sh >> /home/frank/Aktien-tool2/logs/cron.log 2>&1
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

AWS_HOST="ubuntu@3.71.191.12"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/pipeline_$(date +%Y-%m-%d_%H%M).log"

exec > >(tee -a "$LOGFILE") 2>&1

echo "=============================================="
echo "  PIPELINE START: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ── SSH Key finden ──
SSH_KEY=""
for key in "$HOME/.ssh/id_rsa_antigravity_2048" \
           "$HOME/.ssh/id_rsa_antigravity" \
           "$HOME/.ssh/aktien_deploy" \
           "$HOME/.ssh/id_ed25519" \
           "$HOME/.ssh/id_rsa"; do
    if [ -f "$key" ]; then
        SSH_KEY="$key"
        break
    fi
done

if [ -z "$SSH_KEY" ]; then
    echo "❌ Kein SSH-Key gefunden in ~/.ssh/"
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
    echo "❌ Python nicht gefunden!"
    exit 1
fi
echo "📌 Python: $($PYTHON --version 2>&1)"

# ── Step 1: Git Pull ──
echo ""
echo "── Step 1: Git Pull ──"
git pull origin main || echo "⚠ Git pull fehlgeschlagen"

# ── Step 2: Daten aktualisieren ──
echo ""
echo "── Step 2: update_csv_local.py (alle Metriken + Dividenden) ──"
$PYTHON update_csv_local.py || echo "⚠ update_csv_local.py hatte Fehler, fahre fort..."

# ── Step 3: Git Commit & Push ──
echo ""
echo "── Step 3: Git Commit & Push ──"
git add stock_data.csv
if git diff --cached --quiet; then
    echo "ℹ Keine Änderungen"
else
    git commit -m "Automated Data Update $(date +%Y-%m-%d)"
    git push origin main
    echo "✅ Push erfolgreich"
fi

# ── Step 4: AWS Deployment ──
echo ""
echo "── Step 4: AWS Deploy ──"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$AWS_HOST" \
    "cd /home/ubuntu/aktien-tool2 && bash deploy.sh && sudo systemctl restart compare-app.service" || {
    echo "⚠ Deploy fehlgeschlagen"
}

# ── Fertig ──
echo ""
echo "=============================================="
echo "  FERTIG: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Log: $LOGFILE"
echo "=============================================="
