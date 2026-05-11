# 🔄 Automatische Daten-Pipeline — Setup-Anleitung

## Übersicht

Die Pipeline läuft auf deinem **Linux-Rechner** und aktualisiert automatisch:
1. Dividenden-Daten für alle 4.000+ Aktien via Yahoo Finance
2. Pushed die Daten zu GitHub
3. Löst das Deployment auf dem AWS-Server aus

## Schnellstart

### 1. Repository klonen

```bash
cd ~
git clone https://github.com/Stocknerd/Aktien-tool2.git
cd Aktien-tool2
```

### 2. Python-Dependencies installieren

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip git -y
pip3 install yfinance pandas

# Falls pip3 nicht geht:
python3 -m pip install yfinance pandas
```

### 3. SSH-Key für AWS einrichten

**Option A: Bestehenden Key von Windows kopieren**
```bash
# Auf dem Windows-PC:
scp C:\Users\fhofmann\.ssh\id_rsa_antigravity_2048 frank@LINUX-IP:~/.ssh/

# Auf dem Linux-Rechner:
chmod 600 ~/.ssh/id_rsa_antigravity_2048
```

**Option B: Neuen Key erstellen**
```bash
ssh-keygen -t ed25519 -f ~/.ssh/aktien_deploy -N ""

# Dann den Public Key auf den AWS-Server kopieren:
ssh-copy-id -i ~/.ssh/aktien_deploy.pub ubuntu@3.71.191.12
```

### 4. Testen

```bash
# Manueller Test — nur Dividenden (~30 Min)
bash auto_pipeline.sh

# Manueller Test — voller Refresh (~3 Stunden)
bash auto_pipeline.sh --full
```

### 5. Cronjob einrichten

```bash
crontab -e
```

Folgende Zeilen einfügen:

```cron
# Dividenden-Refresh: jeden 2. Tag um 06:00
0 6 */2 * * /home/frank/Aktien-tool2/auto_pipeline.sh >> /home/frank/Aktien-tool2/logs/cron.log 2>&1

# Voller Datenrefresh: Sonntags um 04:00
0 4 * * 0 /home/frank/Aktien-tool2/auto_pipeline.sh --full >> /home/frank/Aktien-tool2/logs/cron_full.log 2>&1
```

> **Wichtig:** Passe `/home/frank/` an deinen tatsächlichen Home-Pfad an!

## Logs

Logs werden automatisch gespeichert in:
```
Aktien-tool2/logs/
├── pipeline_2026-05-11_0600.log
├── dividend_refresh_2026-05-11.log
├── cron.log
└── cron_full.log
```

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| `yfinance` blockiert | VPN nutzen oder User-Agent in `refresh_dividends.py` anpassen |
| SSH Permission denied | Key-Berechtigungen prüfen: `chmod 600 ~/.ssh/id_*` |
| Git Push scheitert | `git config user.email` und `user.name` setzen |
| Python nicht gefunden | `which python3` prüfen, ggf. Pfad in Script anpassen |
