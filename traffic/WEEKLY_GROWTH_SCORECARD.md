# Schatzsuche 4.0 – Weekly Growth Scorecard

## Änderung 2026-07-21

### Hypothese

Eine klare, indexierbare Startseiten-Hauptüberschrift sowie ein suchintentgerechter SEO-Titel und eine Meta-Description verbessern die Verständlichkeit der Startseite für Nutzer und Suchmaschinen. Wirkung darf erst anhand späterer GSC-Daten bewertet werden.

### Ausgangszustand

- HTTP 200 und korrektes Canonical.
- HTML-Titel: `Willkommen! - Schatzsuche 4.0`.
- keine Meta-Description.
- kein H1.
- sichtbare Hauptaussage `Professionelle Aktienanalyse — einfach & schnell.` war als H2 ausgezeichnet.

### Live geändert

WordPress-Seite 1045 (`/`, interner Slug `willkommen`):

1. vorhandene Hero-Hauptüberschrift semantisch von H2 auf H1 geändert;
2. die zwei bestehenden Hero-CSS-Selektoren entsprechend von H2 auf H1 umgebunden;
3. Yoast-SEO-Titel gesetzt: `Aktienanalyse, Screener & Vergleich | Schatzsuche 4.0`;
4. Yoast-Meta-Description gesetzt: `Aktien analysieren, vergleichen und filtern: kostenlose Tools für Kennzahlen, Dividenden und Aktienbewertung – plus echte Depotupdates.`

Nicht verändert: URL, Canonical, Robots, Seitentitel `Willkommen!`, Navigation, CTA-Texte, Links, Layoutstruktur und WordPress-Template.

### Verifikation

- WordPress REST-Updates: HTTP 200.
- XML-RPC-Yoast-Felder: jeweils genau einmal gespeichert und read-only zurückgelesen.
- Öffentliche Startseite: HTTP 200.
- Canonical: `https://schatzsuche40.de/`.
- Robots: index/follow; kein noindex.
- öffentlicher Titel: exakt 53 Zeichen.
- öffentliche Meta-Description: exakt 135 Zeichen.
- öffentliches HTML: genau ein H1.
- H1-Text: `Professionelle Aktienanalyse — einfach & schnell.`
- Desktop berechnet: Farbe `rgb(247, 247, 247)`, 35,2 px, Gewicht 800.
- Mobile 390 × 844: 25,6 px, Gewicht 800, kein horizontaler Überlauf.
- Browser: keine JavaScript-Fehler; visuelle Prüfung ohne Layoutbruch.
- Drei gültige JSON-Rollback-Artefakte unter `traffic/backups/`.

### Messzugang

Site Kit ist mit GSC und GA4 konfiguriert, aber reale GSC-Query-/Page- und GA4-Landingpage-Probes antworten HTTP 403 / `missing_required_scopes`. Deshalb liegen noch keine belastbaren Vorher-Metriken vor und es wird keine Rankingwirkung behauptet.

### Globaler H1-Punkt – live gelöst und am 2026-07-26 vollständig verifiziert

Der frühere Crawlzustand mit 182 von 184 URLs ohne H1 ist nicht mehr aktuell. Ein vollständiger Live-Crawl aller 185 eindeutigen WordPress-Sitemap-URLs ergab 0 Fehler und auf jeder URL genau ein H1. Repräsentative Beiträge, Seiten, Kategorien, Tags, Autor, Blogübersicht und Startseite wurden zusätzlich normal sowie mit Cache-Busting geprüft: HTTP 200, Canonical unverändert, jeweils genau ein H1. Ein aktueller Beitrag blieb auf Desktop 1280 × 720 und Mobil 390 × 844 sichtbar und lesbar, ohne horizontalen Überlauf oder Browserfehler. In diesem Verifikationslauf war keine WordPress-Mutation nötig, weil der globale Zustand bereits korrigiert war. Vollständige Evidenz: `traffic/H1_VERIFICATION_2026-07-26.md`.

### Reviewtermine

- 14 Tage: 2026-08-04
- 28 Tage: 2026-08-18

Sobald Site Kit neu autorisiert ist, vergleichen:

- Startseiten-Impressionen
- Startseiten-Klicks
- CTR
- durchschnittliche Position
- organische Startseiten-Sessions
- Klicks von der Startseite zu Screener und Vergleich

Entscheidung danach: `scale`, `refine`, `wait` oder `deprioritize`.
