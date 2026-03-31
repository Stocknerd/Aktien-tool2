# 📘 Projekt-Details: Aktien-Tool & Automatisierung

Dieses Dokument enthält alle wichtigen Informationen zur Infrastruktur und Konfiguration (Stand: 31. März 2026).

## 🚀 Infrastruktur
- **Backend (AWS IP):** 3.71.191.12
- **Frontend (WordPress):** schatzsuche40.de (All-Inkl Hosting)
- **KI-Modell:** gpt-5.4-mini
- **Cronjob:** Di & Fr 08:00 Uhr (AWS Server)

## 🛠 Zentrale Dateien
- **App-Logik:** `app.py`
- **Bild-Rendering:** `core.py`
- **KI-Analyse:** `ai_logic.py`
- **Bot-Posting:** `wp_auto_publisher.py`

## 📝 Wichtige Fixes
- **Fuzzy Search:** Die Suche in `app.py` normalisiert Bindestriche/Punkte.
- **Button Injection:** `wp-content/plugins/aktien_injector.php` auf dem WordPress-Server.
- **Kontrast:** AI-Bewertungsbox in `core.py` auf dunklen Hintergrund mit Fettschrift optimiert.
