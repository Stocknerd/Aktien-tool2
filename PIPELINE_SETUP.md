# 🔄 Automatische Daten-Pipeline

## Was passiert?

`auto_pipeline.sh` führt die komplette Aktualisierung in einem Schritt aus:

1. **Git Pull** — holt den neuesten Code
2. **update_csv_local.py** — aktualisiert alle 4.000+ Aktien via Yahoo Finance (KGV, Dividenden, Margen, alles)
3. **Git Push** — pushed die aktualisierte `stock_data.csv`
4. **AWS Deploy** — startet die Webseite neu

## Setup auf deinem Linux-Rechner

```bash
# 1. Repo klonen
cd ~ && git clone https://github.com/Stocknerd/Aktien-tool2.git
cd Aktien-tool2

# 2. Python-Deps
pip3 install yfinance pandas numpy

# 3. SSH-Key für AWS einrichten
#    Option A: Vom Windows-PC kopieren
#    Option B: Neuen Key erstellen + auf AWS autorisieren:
ssh-keygen -t ed25519 -f ~/.ssh/aktien_deploy -N ""
ssh-copy-id -i ~/.ssh/aktien_deploy.pub ubuntu@3.71.191.12

# 4. Testen
bash auto_pipeline.sh

# 5. Cronjob (alle 2 Tage um 06:00)
crontab -e
# Einfügen:
0 6 */2 * * /home/DEIN_USER/Aktien-tool2/auto_pipeline.sh >> /home/DEIN_USER/Aktien-tool2/logs/cron.log 2>&1
```

## Logs

```
logs/pipeline_2026-05-11_0600.log
logs/cron.log
```
