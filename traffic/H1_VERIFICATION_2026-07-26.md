# Schatzsuche 4.0 – globale H1-Verifikation

Stand: 2026-07-26
Live-Ziel: `https://schatzsuche40.de/`
Änderung in diesem Lauf: keine WordPress-Mutation; der zuvor offene globale Zustand war beim neuen Live-Crawl bereits korrigiert.

## Vollständiger WordPress-Sitemap-Crawl

Quelle: `https://schatzsuche40.de/wp-sitemap.xml`

- 5 Untersitemaps
- 185 eindeutige öffentliche URLs
- 0 Abruffehler
- 185 URLs mit genau einem H1
- 0 URLs ohne H1
- 0 URLs mit mehreren H1

Verteilung:

- Startseite: 1
- Beiträge: 109
- Seiten: 42
- Kategorien: 2
- Tags: 29
- Autor: 1
- Blogübersicht/sonstige: 1

## Repräsentative Cache-Prüfung

Jeweils normale URL und Cache-Busting-URL geprüft:

- Startseite
- aktueller Beitrag
- statische Seite
- Kategorie
- Tag
- Autor
- Blogübersicht

Ergebnis für alle 14 Abrufe:

- HTTP 200
- genau ein H1
- Canonical unverändert auf der normalen URL
- H1-Text entspricht dem sichtbaren Seiten-/Inhaltstitel

## Browser- und Layoutprüfung

Repräsentativer aktueller Beitrag:
`https://schatzsuche40.de/top-3-dividendenaktien-im-check-analyse-ausblick-24-07-2026/`

Desktop 1280 × 720:

- genau ein sichtbares H1
- Farbe `rgb(68, 68, 68)`
- Schriftgröße 50 px
- Gewicht 700
- Zeilenhöhe 60 px
- kein horizontaler Überlauf

Mobil 390 × 844:

- genau ein sichtbares H1
- Farbe `rgb(68, 68, 68)`
- Schriftgröße 30 px
- Gewicht 700
- Zeilenhöhe 36 px
- kein horizontaler Überlauf

Browserkonsole: 0 Fehler, 0 Warnungen.

## Theme- und Messstatus

- Aktives Theme: BeTheme 28.2.1
- Klassisches Theme; WordPress-Template-REST-Liste leer
- Der frühere globale H2-Titelzustand ist öffentlich nicht mehr vorhanden.
- Site Kit meldet Search Console und Analytics 4 als aktiv/verbunden.
- Die Google-Nutzerautorisierung ist weiterhin nicht verfügbar.
- Reale GSC- und GA4-Berichtsanfragen liefern HTTP 403 / `missing_required_scopes`.

## Entscheidung

Der globale H1-Punkt ist anhand des aktuellen öffentlichen Zustands abgeschlossen. Es wird keine weitere Theme-Mutation vorgenommen. Nächster Daten-Gate ist die einmalige Site-Kit-Neuautorisierung; erst danach werden Query-/URL-Prioritäten aus realen GSC-/GA4-Daten abgeleitet.
