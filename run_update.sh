#!/bin/bash
# =========================================================================
# Schatzsuche 4.0: Automatisches Datenupdate & AWS-Deployment (LINUX)
# =========================================================================

# Zum Verzeichnis des Skripts wechseln
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# Log-Ordner anlegen falls nicht vorhanden
mkdir -p logs
LOGFILE="${PROJECT_DIR}/logs/linux_update.log"

echo "=========================================================================" >> "$LOGFILE"
echo "📊 [$(date '+%Y-%m-%d %H:%M:%S')] Starte automatisiertes Datenupdate..." >> "$LOGFILE"
echo "=========================================================================" >> "$LOGFILE"

# 1. Neueste Skript-Updates von GitHub ziehen
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔄 [1/3] Git Pull..." >> "$LOGFILE"
git pull origin main >> "$LOGFILE" 2>&1

# 2. Virtuelle Umgebung aktivieren & Update ausführen
if [ -d ".venv" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🐍 [2/3] Aktiviere venv..." >> "$LOGFILE"
    source .venv/bin/activate >> "$LOGFILE" 2>&1
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📈 Starte local_data_sync.py (QUICK=1)..." >> "$LOGFILE"
    # QUICK=1 für schnellen Durchlauf (nur geänderte/fehlende Ticker)
    export QUICK="1"
    python3 local_data_sync.py >> "$LOGFILE" 2>&1
    
    deactivate
else
    echo "❌ [$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Keine virtuelle Umgebung (.venv) gefunden!" >> "$LOGFILE"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ [3/3] Datenupdate und Deployment erfolgreich abgeschlossen." >> "$LOGFILE"
else
    echo "❌ [$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Datenupdate fehlgeschlagen!" >> "$LOGFILE"
    exit 1
fi

echo "=========================================================================" >> "$LOGFILE"
echo "🎉 [$(date '+%Y-%m-%d %H:%M:%S')] Datenupdate und Server-Deployment ERFOLGREICH!" >> "$LOGFILE"
echo "=========================================================================" >> "$LOGFILE"
