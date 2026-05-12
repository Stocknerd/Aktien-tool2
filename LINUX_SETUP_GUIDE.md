# 🚀 Schritt-für-Schritt: Daten-Pipeline auf deinem Linux-Rechner einrichten

Dieses Skript erklärt exakt, wie du den Linux-Rechner, der ohnehin immer läuft, so konfigurierst, dass er die Aktien-Daten (alle 4000+ Werte inkl. Dividenden und Margen) **vollautomatisch im Hintergrund** aktualisiert und auf den Live-Server schiebt.

---

### Schritt 1: Auf dem Linux-Rechner einloggen
Öffne das Terminal auf deinem Linux-Rechner. Du solltest dich im Home-Verzeichnis befinden (`/home/dein_benutzername/`).

### Schritt 2: Das Projekt herunterladen
Klone das Repository auf den Linux-Rechner:
```bash
cd ~
git clone https://github.com/Stocknerd/Aktien-tool2.git
cd Aktien-tool2
```

### Schritt 3: Python-Pakete installieren
Die Pipeline benötigt ein paar Python-Bibliotheken (hauptsächlich für Yahoo Finance):
```bash
sudo apt update
sudo apt install -y python3-pip
pip3 install yfinance pandas numpy
```

### Schritt 4: SSH-Key für den AWS Server einrichten
Damit dein Linux-Rechner nach dem Update dem AWS-Server (IP: `3.71.191.12`) den Befehl zum Neustart geben kann, braucht er Zugriff. 

**Erstelle einen neuen Schlüssel auf dem Linux-Rechner:**
```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa_antigravity_2048 -N ""
```
*Tippe einfach Enter, bis der Befehl durchgelaufen ist.*

**Lass dir den öffentlichen Schlüssel anzeigen und kopiere ihn:**
```bash
cat ~/.ssh/id_rsa_antigravity_2048.pub
```
*(Kopiere den Text, der mit `ssh-rsa ...` beginnt).*

**Füge ihn auf dem AWS-Server ein:**
1. Logge dich von deinem *Windows-PC* (wie gewohnt) auf dem AWS-Server ein.
2. Öffne dort die Datei für berechtigte Schlüssel:
   ```bash
   nano ~/.ssh/authorized_keys
   ```
3. Füge den gerade kopierten Text in eine neue Zeile ganz unten ein.
4. Speichere mit `STRG+O`, `Enter`, und schließe mit `STRG+X`.

### Schritt 5: Pipeline testen
Wechsle zurück zu deinem Linux-Rechner und starte die Pipeline einmal manuell, um zu sehen, ob alles klappt:
```bash
cd ~/Aktien-tool2
bash auto_pipeline.sh
```
*Dieser Befehl holt den neuesten Code, aktualisiert fehlende Daten (was dauern kann), lädt sie auf Github hoch und startet die AWS-App neu. Am Ende sollte "FERTIG" stehen.*

### Schritt 6: Cronjob einrichten (Der Autopilot)
Wenn der Test erfolgreich war, automatisieren wir das Ganze!

1. Öffne den Cronjob-Editor:
   ```bash
   crontab -e
   ```
   *(Falls du gefragt wirst, welchen Editor du nutzen willst, wähle `nano`, meistens die 1).*

2. Scrolle ganz nach unten und füge diese Zeile ein:
   ```bash
   0 6 * * * /home/DEIN_LINUX_BENUTZERNAME/Aktien-tool2/auto_pipeline.sh >> /home/DEIN_LINUX_BENUTZERNAME/Aktien-tool2/logs/cron.log 2>&1
   ```
   *(Ersetze `DEIN_LINUX_BENUTZERNAME` durch deinen echten Benutzernamen, z.B. `frank` oder `pi`).*
   **Was macht das?** Die Pipeline läuft ab sofort **jeden Tag um 06:00 Uhr morgens**.

3. Speichere wieder mit `STRG+O`, `Enter`, und schließe mit `STRG+X`.

---

### 🎉 Fertig!
Ab jetzt kümmert sich dein Linux-Rechner im Hintergrund um alles. 

**Fehlersuche:** 
Wenn du wissen willst, was der Roboter treibt, kannst du jederzeit in die Logs schauen:
```bash
cat ~/Aktien-tool2/logs/cron.log
```
