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

Site Kit ist autorisiert; Frank sieht reale GSC-/GA4-Zahlen im WordPress-Dashboard. Nur die separaten serverseitigen Query-/Page-/Landingpage-Probes dieses Repositories antworten weiterhin HTTP 403 / `missing_required_scopes`. Das ist kein Site-Kit-Verbindungsfehler. Da noch kein datierter Export im Repository liegt, wird weiterhin keine Rankingwirkung behauptet.

### Globaler H1-Punkt – live gelöst und am 2026-07-26 vollständig verifiziert

Der frühere Crawlzustand mit 182 von 184 URLs ohne H1 ist nicht mehr aktuell. Ein vollständiger Live-Crawl aller 185 eindeutigen WordPress-Sitemap-URLs ergab 0 Fehler und auf jeder URL genau ein H1. Repräsentative Beiträge, Seiten, Kategorien, Tags, Autor, Blogübersicht und Startseite wurden zusätzlich normal sowie mit Cache-Busting geprüft: HTTP 200, Canonical unverändert, jeweils genau ein H1. Ein aktueller Beitrag blieb auf Desktop 1280 × 720 und Mobil 390 × 844 sichtbar und lesbar, ohne horizontalen Überlauf oder Browserfehler. In diesem Verifikationslauf war keine WordPress-Mutation nötig, weil der globale Zustand bereits korrigiert war. Vollständige Evidenz: `traffic/H1_VERIFICATION_2026-07-26.md`.

### Startseiten-Hub-Ergänzung – live verifiziert 2026-07-27

- neuer Inline-CTA von der Depotsektion zu `/meine-depots/`;
- neuer CTA vom Leitfadenbereich zu `/leitfaden-aktienbewertung/`;
- beide exakten Selektoren, Linktexte und Ziel-URLs anonym auf normaler und cacheumgehender Startseite geprüft;
- unabhängiges Review entdeckte eine mobile Überbreite durch `white-space` und Flex-Kind-Mindestbreiten;
- mobile Depotsektion begrenzt und CTAs unter 640 px als eigene Blöcke dargestellt;
- Browsernachweis bei 320, 360 und 390 px: beide CTAs vollständig sichtbar, Dokumentbreite exakt gleich Viewportbreite;
- weiterhin HTTP 200, korrektes Canonical, genau ein H1, `index, follow` und keine Browserwarnungen;
- hashgenaue Backups und REST-Readbacks für jede begrenzte Mutation vorhanden.

### API-Baseline 2026-07-29

Der bisher fehlende automatisierte Leseweg ist durch ein dediziertes Read-only-Servicekonto ersetzt. Echte GA4- und GSC-Berichte wurden erfolgreich abgerufen und unter `traffic/exports/TRAFFIC_EXPORT_2026-07-29.json` gesichert. Vollständige Bewertung: `traffic/TRAFFIC_ASSESSMENT_2026-07-29.md`.

Aktuelle 28-Tage-Kernaussagen:

- GA4: 84 Sitzungen (−7,7 %), 102 Seitenaufrufe (−25,5 %), 21 engagierte Sitzungen (−22,2 %)
- GSC: 524 Impressionen (+69,6 %), 7 Klicks (−12,5 %), CTR 1,34 %, Position 60,3
- Organic Search ist mit 13 Sitzungen klein, aber qualitativ der stärkste Kanal: 46,2 % Engagement-Rate, 2,15 Seiten je Sitzung und 152 Sekunden durchschnittliche Sitzungsdauer
- 27 von 185 Sitemap-URLs erhielten in 28 Tagen mindestens eine Impression
- Startseite bleibt bis zu den geplanten Reviews auf `wait`
- priorisierte nächste Chancen: Value-Investing-Snippet, interne Stärkung des Dividendenwachstum-Hubs, anschließend P2P-Reassessment nach Wirkung der Aktualisierung vom 24. Juli

### Reviewtermine

- 14 Tage: 2026-08-04
- 28 Tage: 2026-08-18

Zum 14-/28-Tage-Termin anhand der sichtbaren Site-Kit-Daten oder eines kontrollierten Exports vergleichen:

- Startseiten-Impressionen
- Startseiten-Klicks
- CTR
- durchschnittliche Position
- organische Startseiten-Sessions
- Klicks von der Startseite zu Screener und Vergleich

Entscheidung danach: `scale`, `refine`, `wait` oder `deprioritize`.

## 14-Tage-Review 2026-08-04

### Datenstand und Vergleichsbasis

- Der dedizierte Read-only-Export lief am 2026-08-04 erfolgreich für GA4 und GSC; Rohdaten: `traffic/exports/TRAFFIC_EXPORT_2026-08-04.json`.
- Neuer rollierender Export: GA4 2026-07-07 bis 2026-08-03, GSC final 2026-07-05 bis 2026-08-01. Baseline-Export vom 2026-07-29: GA4 2026-07-01 bis 2026-07-28, GSC final 2026-06-29 bis 2026-07-26. Die Fenster überlappen stark und dienen nur als Snapshot-Vergleich.
- Für die Startseitenwirkung wurde zusätzlich ab dem Änderungstag gemessen: GA4 2026-07-21 bis 2026-08-03 (14 Tage) gegen 2026-07-07 bis 2026-07-20. Wegen der GSC-Finalisierung sind erst 12 Tage verfügbar: 2026-07-21 bis 2026-08-01 gegen 2026-07-09 bis 2026-07-20. Der Änderungstag 2026-07-21 kann noch anteilig den Vorzustand enthalten.

### Startseite – Snapshot des neuen Exports gegen Baseline

- GSC, neue 28 Tage 2026-07-05 bis 2026-08-01: 6 Klicks, 13 Impressionen, 46,15 % CTR, Position 22,46. Baseline-Fenster 2026-06-29 bis 2026-07-26: 7 Klicks, 15 Impressionen, 46,67 % CTR, Position 26,60.
- GA4 Organic Search als Landingpage, neue 28 Tage 2026-07-07 bis 2026-08-03: 9 Sitzungen, 4 engagierte Sitzungen, 44,44 % Engagement-Rate, 21 Seitenaufrufe und 206,8 Sekunden durchschnittliche Sitzungsdauer. Baseline-Fenster 2026-07-01 bis 2026-07-28: 10 Sitzungen, 4 engagierte Sitzungen, 40,00 %, 23 Seitenaufrufe und 165,0 Sekunden.
- Websiteweit zeigt GA4 im neuen 28-Tage-Fenster 236 Sitzungen statt 84 im Baseline-Snapshot. Davon entfallen 193 auf Direct; die letzten sieben Tage enthalten 173 Sitzungen, aber nur 2 engagierte Sitzungen. Dieser unplausibel schwache Direct-Schub wird nicht als SEO-Wachstum gewertet. Organic Search blieb im neuen Fenster mit 11 Sitzungen, 5 engagierten Sitzungen und 24 Seitenaufrufen klein.
- Websiteweite GSC-Werte im neuen 28-Tage-Fenster: 6 Klicks, 492 Impressionen, 1,22 % CTR und Position 58,83; im Baseline-Snapshot waren es 7 Klicks, 524 Impressionen, 1,34 % und Position 60,32.

### Startseite – Zeitraum seit der SEO-Änderung

GSC, verfügbare finalisierte 12 Tage 2026-07-21 bis 2026-08-01 gegen die gleich lange Vorperiode 2026-07-09 bis 2026-07-20:

- Klicks: 2 statt 2
- Impressionen: 3 statt 6
- CTR: 66,67 % statt 33,33 %
- durchschnittliche Position: 1,67 statt 47,17

GA4 Organic Search als Landingpage, 14 Tage 2026-07-21 bis 2026-08-03 gegen 2026-07-07 bis 2026-07-20:

- Sitzungen: 6 statt 3
- engagierte Sitzungen: 1 statt 3
- Engagement-Rate: 16,67 % statt 100,00 %
- Seitenaufrufe: 8 statt 13
- Seitenaufrufe je Sitzung: 1,33 statt 4,33
- durchschnittliche Sitzungsdauer: 176,7 statt 267,1 Sekunden

Die GSC-Position und CTR sehen positiv aus, beruhen nach der Änderung aber auf nur drei Impressionen und unverändert zwei Klicks. GA4 zeigt zwar doppelt so viele organische Startseiten-Sitzungen, gleichzeitig aber deutlich weniger Engagement und Seitenaufrufe. Daraus lässt sich noch keine belastbare positive oder negative SEO-Wirkung ableiten.

### Öffentlicher technischer Recheck

- Startseite HTTP 200; genau ein Canonical auf `https://schatzsuche40.de/`.
- Robots: `index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1`; kein `noindex`.
- Genau ein H1: `Professionelle Aktienanalyse — einfach & schnell.`
- SEO-Titel unverändert: `Aktienanalyse, Screener & Vergleich | Schatzsuche 4.0` (53 Zeichen).
- Meta-Description unverändert: `Aktien analysieren, vergleichen und filtern: kostenlose Tools für Kennzahlen, Dividenden und Aktienbewertung – plus echte Depotupdates.` (135 Zeichen).
- Browsercheck bei 390 × 844 px: Dokument- und Viewportbreite jeweils exakt 390 px, kein horizontaler Überlauf und keine JavaScript-Seitenfehler.

### Entscheidung

**`wait` bis zum 28-Tage-Review am 2026-08-18.** Die technische Umsetzung ist weiterhin sauber, aber drei finalisierte GSC-Impressionen nach der Änderung sind für `scale`, `refine` oder `deprioritize` zu wenig. Insbesondere rechtfertigt die scheinbare Positionsverbesserung noch keine weitere Startseitenmutation; die gemischten GA4-Qualitätssignale sprechen ebenfalls für unverändertes Weitermessen.

## Änderung 2026-08-10

### Hypothese

Eine Kürzung des SEO-Titels der Value-Investing-Seite auf ein kürzeres, intentnaheres Format sowie das Hinzufügen einer passenden Meta-Description steigern die Klickrate (CTR) und die Klicks bei Impressionen auf Position 6.

### Live geändert

WordPress-Post 2066 (`/wie-finde-ich-unterbewertete-aktien-ein-value-investing-leitfaden/`):

1. Yoast-SEO-Titel gekürzt: `Unterbewertete Aktien finden: Value-Investing-Leitfaden` (von 84 Zeichen mit Brand-Suffix auf 56 Zeichen).
2. Yoast-Meta-Description gesetzt: `Wie findet man unterbewertete Aktien? Unser Value-Investing-Leitfaden zeigt dir die besten Kennzahlen, Strategien und Tools für deine Aktienanalyse.` (zuvor leer).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress REST-Update: HTTP 200.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/post-2066-pre-seo-20260810.json` (SHA-256: `b43ae01a8044363d852fa85db33f82a081ce031a512174022b47dfbcb9ead759`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: Exakt `<title>Unterbewertete Aktien finden: Value-Investing-Leitfaden</title>`.
  - HTML-Meta-Description: Exakt `<meta name="description" content="Wie findet man unterbewertete Aktien? Unser Value-Investing-Leitfaden zeigt dir die besten Kennzahlen, Strategien und Tools für deine Aktienanalyse." />`.
  - H1-Check: Genau 1 H1 vorhanden (`Wie finde ich unterbewertete Aktien? Ein Value-Investing-Leitfaden`).

## Änderung 2026-08-11

### Hypothese

Gezielte, kontextbezogene interne Verlinkungen aus thematisch passenden, rankenden Dividendenartikeln zum Dividendenwachstum-Hub stärken dessen organische Autorität und verbessern mittelfristig die Positionierung für die Keywords "dividendenwachstum" und "dividendenwachstum strategie" (derzeit Pos 18-19).

### Live geändert

WordPress-Posts 2063 (`/dividendenrendite-verstehen-berechnen-der-ultimative-guide/`) und 2069 (`/dividendenrendite-verstehen-berechnen-der-ultimative-guide-2/`):

1. **Post 2063**: Am Ende des Abschnitts "Achtung vor Dividendenfallen" einen internen Link zum Dividendenwachstum-Guide (`/dividendenwachstum-strategie-guide/`) hinzugefügt.
2. **Post 2069**: Nach der Liste im Abschnitt "Wie man Dividendenfallen vermeidet" ebenfalls einen thematischen Link zum Dividendenwachstum-Guide hinzugefügt.

Nicht verändert: URL, Page-Templates, restlicher HTML-Inhalt, sonstige externe Links oder Metadaten.

### Verifikation

- WordPress REST-Update: Jeweils HTTP 200.
- Authentifiziertes Readback: Jeweils erfolgreich ausgelesen und das Vorhandensein der Ziel-URL im Content verifiziert.
- Backups erstellt unter `traffic/backups/`:
  - `post-2063-pre-link-20260811.json` (SHA-256: `83cf155e7f6cc4da07edd8d3f9398e25e0b9ec22130a6f1f202cf6cd8817da2b`)
  - `post-2069-pre-link-20260811.json` (SHA-256: `5995c929becd7744438461e590f04f779df5f11e1e7bb28ef7f716940565521b`)
- Anonyme Live-Smokes mit Cache-Busting (`?nocache=1`):
  - Post 2063: HTTP 200, Link auf `/dividendenwachstum-strategie-guide/` im HTML nachweisbar.
  - Post 2069: HTTP 200, Link auf `/dividendenwachstum-strategie-guide/` im HTML nachweisbar.

## Änderung 2026-08-12

### Hypothese

Eine Optimierung des SEO-Titels der Einsteigerseite "Aktien, Anleihen oder ETFs?" hin zu einem klaren, vergleichs- und suchintentfokussierten Titel sowie das Setzen einer ansprechenden Meta-Description steigern die Klickrate (CTR) und die Klicks bei Impressionen für relevante Einsteiger-Suchanfragen (wie "aktien oder anleihen").

### Live geändert

WordPress-Page 71 (`/aktien-anleihen-oder-etfs/`):

1. Yoast-SEO-Titel gekürzt/optimiert: `Aktien oder Anleihen? Vergleich & Unterschied einfach erklärt` (zuvor Fallback auf Page-Titel `Aktien, Anleihen oder ETFs? - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Aktien oder Anleihen kaufen? Erfahre verständlich den Unterschied beider Wertpapiere sowie Chancen & Risiken für Einsteiger – inkl. ETFs im Vergleich.` (zuvor Fallback).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status 1 (SUCCESS).
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-71-pre-seo-20260812.json` (SHA-256: `2d862f1b6faccdb36db23d5c032d4b6ca4bac8f81d11bbe6fae0e7d36685904a`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: `<title>Aktien oder Anleihen? Vergleich &amp; Unterschied einfach erklärt</title>`.
  - HTML-Meta-Description: `<meta name="description" content="Aktien oder Anleihen kaufen? Erfahre verständlich den Unterschied beider Wertpapiere sowie Chancen &amp; Risiken für Einsteiger – inkl. ETFs im Vergleich." />`.
  - H1-Check: Genau 1 H1 vorhanden (`Aktien, Anleihen oder ETFs?`).

## Änderung 2026-08-13

### Hypothese

Gezielte, kontextbezogene interne Verlinkungen aus thematisch passenden, unterstützenden Kennzahlen-Artikeln zum "Leitfaden Aktienbewertung" Hub stärken dessen organische Autorität und verbessern die Relevanzsignale für Suchen rund um "Aktien bewerten".

### Live geändert

WordPress-Posts 2062 (`/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger/`), 2064 (`/die-5-wichtigsten-kennzahlen-fuer-die-aktienanalyse/`) und 2067 (`/was-bedeuten-kuv-kbv-peg-das-grosse-kennzahlen-glossar/`):

1. **Post 2062**: Am Ende der Zusammenfassung einen internen Link zum Hub `/leitfaden-aktienbewertung/` hinzugefügt.
2. **Post 2064**: Am Ende des Artikels nach der Erwähnung des Tools einen internen Link zum Hub `/leitfaden-aktienbewertung/` hinzugefügt.
3. **Post 2067**: In die Liste der "Praktischen Tipps" einen internen Link zum Hub `/leitfaden-aktienbewertung/` aufgenommen.

Nicht verändert: URLs, Page-Templates, restlicher HTML-Inhalt, sonstige externe Links oder Metadaten.

### Verifikation

- WordPress REST-Update: Jeweils HTTP 200.
- Authentifiziertes Readback: Jeweils erfolgreich ausgelesen und das Vorhandensein der Ziel-URL im Content verifiziert.
- Backups erstellt unter `traffic/backups/`:
  - `post-2062-pre-link-20260813T101452Z.json` (SHA-256: `c0a50063f71f52775224d1ff25887012259a46604b71df9273123bd81dd78433`)
  - `post-2064-pre-link-20260813T101502Z.json` (SHA-256: `347a33d511280484070fc4c3f85597f54f3cac0dad9663ec5a004e366869b915`)
  - `post-2067-pre-link-20260813T101510Z.json` (SHA-256: `7701e381cfb1f268b2698553756fe4cc48fd1cbd55da91807a3c41d5fe3ac269`)
- Anonyme Live-Smokes mit Cache-Busting (`?nocache=1`):
  - Post 2062: HTTP 200, Link auf `/leitfaden-aktienbewertung/` im HTML nachweisbar.
  - Post 2064: HTTP 200, Link auf `/leitfaden-aktienbewertung/` im HTML nachweisbar.
  - Post 2067: HTTP 200, Link auf `/leitfaden-aktienbewertung/` im HTML nachweisbar.

## Änderung 2026-08-14

### Hypothese

Die Ergänzung einer optimierten Meta-Description (zuvor leer/fehlend) sowie die Kürzung des SEO-Titels auf ein intentnahes Format für die Buchrezension „Der Weg zur finanziellen Freiheit“ von Bodo Schäfer steigern die Klickrate (CTR) und die Klicks bei Impressionen auf Position 49.

### Live geändert

WordPress-Page 379 (`/der-weg-zur-finanziellen-freiheit/`):

1. Yoast-SEO-Titel gesetzt: `Der Weg zur finanziellen Freiheit: Bodo Schäfer Buchkritik` (zuvor Fallback auf Page-Titel `Der Weg zur finanziellen Freiheit - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Lohnt sich Bodo Schäfers Bestseller „Der Weg zur finanziellen Freiheit“? Unsere ehrliche Buchkritik zeigt dir die wichtigsten Lektionen und Tipps für Einsteiger.` (zuvor leer).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status 1 (SUCCESS).
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-379-pre-seo-20260814.json` (SHA-256: `7722e453a2df153fe7676ccb6662cf573b8613de671d6f39d8171cb83108876d`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Der Weg zur finanziellen Freiheit: Bodo Schäfer Buchkritik`.
  - HTML-Meta-Description: enthält `Lohnt sich Bodo Schäfers Bestseller „Der Weg zur finanziellen Freiheit“? Unsere ehrliche Buchkritik zeigt dir die wichtigsten Lektionen und Tipps für Einsteiger.`.
  - H1-Check: Genau 1 H1 vorhanden (`Der Weg zur finanziellen Freiheit`).

## Änderung 2026-08-15

### Hypothese

Die Ergänzung eines suchintentorientierten SEO-Titels und einer optimierten Meta-Description für die Buchrezension „Die Kunst über Geld nachzudenken“ von André Kostolany steigern die Klickrate (CTR) und die Klicks bei Impressionen auf Position 29.

### Live geändert

WordPress-Page 513 (`/die-kunst-ueber-geld-nachzudenken/`):

1. Yoast-SEO-Titel gesetzt: `Die Kunst über Geld nachzudenken: Kostolany Buchkritik` (zuvor Fallback auf Page-Titel `Die Kunst über Geld nachzudenken - Schatzsuche 4.0`).
2. Yoast-Meta-Description optimiert: `Lohnt sich Andre Kostolanys Klassiker „Die Kunst über Geld nachzudenken“? Unsere ausführliche Buchkritik zeigt dir die wichtigsten Lektionen des Börsen-Gurus.` (zuvor generisch).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status 1 (SUCCESS).
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-513-pre-seo-20260815.json` (SHA-256: `bc5f97725da48196edaa6a2b2e1e84bd794064386b0bf11c3e615368c8140e5d`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: `<title>Die Kunst über Geld nachzudenken: Kostolany Buchkritik</title>`.
  - HTML-Meta-Description: enthält `Lohnt sich Andre Kostolanys Klassiker „Die Kunst über Geld nachzudenken“? Unsere ausführliche Buchkritik zeigt dir die wichtigsten Lektionen des Börsen-Gurus.`.
  - H1-Check: Genau 1 H1 vorhanden (`Die Kunst über Geld nachzudenken`).

## Änderung 2026-08-16

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und einer optimierten Meta-Description für das „Aktien-Vergleichstool“ steigern die Klickrate (CTR) und die Klicks bei bestehenden Impressionen auf einer durchschnittlichen Position von 5.50.

### Live geändert

WordPress-Page 1661 (`/aktien-vergleichstool/`):

1. Yoast-SEO-Titel gesetzt: `Aktien-Vergleichstool: Zwei Aktien kostenlos vergleichen` (zuvor kein expliziter Titel vorhanden, Fallback auf Page-Titel `Aktien-Vergleichstool - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Zwei Aktien im direkten Vergleich: Vergleiche kostenlos Fundamentaldaten, KGV, Margen, Dividenden und Analysten-Kursziele zweier Aktientitel.` (zuvor leer).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status 1 (SUCCESS).
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1661-pre-seo-20260816.json` (SHA-256: `c7a67c7297ce5dce6dffaba90dfd3b19b1b3d63b13ad7c5f3092c00ad0b97a0d`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Aktien-Vergleichstool: Zwei Aktien kostenlos vergleichen`.
  - HTML-Meta-Description: enthält `Zwei Aktien im direkten Vergleich: Vergleiche kostenlos Fundamentaldaten, KGV, Margen, Dividenden und Analysten-Kursziele zweier Aktientitel.`.
  - H1-Check: Genau 1 H1 vorhanden.

## Änderung 2026-08-17

### Hypothese

Die Ergänzung eines suchintentfokussierten, optimierten SEO-Titels sowie einer ansprechenden Meta-Description (zuvor leer/fehlend) für den hochaktuellen Blogbeitrag „Das neue Altersvorsorgedepot“ steigern die Klickrate (CTR) und die Klicks bei künftigen Impressionen für relevante Suchen rund um das Thema „Altersvorsorgedepot“ (derzeit Pos 1.00 bei einer ersten Impression).

### Live geändert

WordPress-Post 2281 (`/altersvorsorgedepot-regeln-foerderung-tipps/`):

1. Yoast-SEO-Titel gesetzt: `Altersvorsorgedepot: Regeln, Förderung & Tipps` (zuvor Fallback).
2. Yoast-Meta-Description gesetzt: `Das neue private Altersvorsorgedepot im Check: Alles über staatliche Förderung, das neue Zulagenmodell, Steuervorteile und ETFs für deine Altersvorsorge.` (zuvor leer).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status 1 (SUCCESS).
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/post-2281-pre-seo-20260817.json` (SHA-256: `3a8f12f6dc49465ac0c9985151d373d71fec54a44d734d5a6072810c0bd9d29c`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Altersvorsorgedepot: Regeln, Förderung &amp; Tipps`.
  - HTML-Meta-Description: enthält `Das neue private Altersvorsorgedepot im Check: Alles über staatliche Förderung, das neue Zulagenmodell, Steuervorteile und ETFs für deine Altersvorsorge.`.
  - H1-Check: Genau 1 H1 vorhanden (`Das neue Altersvorsorgedepot: Regeln, Förderung & Worauf du achten musst`).


## 28-Tage-Review 2026-08-18 (Startseite)

### Datenstand und Vergleichsbasis

- Der dedizierte Read-only-Export lief am 2026-08-18 erfolgreich für GA4 und GSC; Rohdaten: `traffic/exports/TRAFFIC_EXPORT_2026-08-18.json`.
- Messung für die 28 Tage seit der Änderung (2026-07-21 bis 2026-08-17) gegen die vorherige 28-Tage-Periode.

### Startseite – Vergleich 28 Tage nach Änderung vs. Vorperiode

- **GSC (Homepage):**
  - Klicks: 6 statt 6 (unverändert)
  - Impressionen: 13 statt 14 (-7,1 %)
  - CTR: 46,15 % statt 42,86 % (+3,29 Prozentpunkte)
  - Durchschnittliche Position: 1,85 statt 28,43 (+26,58 Positionen)
- **GA4 Organic Search Landing Page (Homepage `/`):**
  - Sitzungen: 9 statt 7 (+28,6 %)
  - Engagierte Sitzungen: 3 statt 5 (-40,0 %)
  - Engagement-Rate: 33,33 % statt 71,43 % (-38,1 Prozentpunkte)
  - Seitenaufrufe (Views): 13 statt 20 (-35,0 %)
  - Durchschnittliche Sitzungsdauer: 119,8 Sekunden statt 239,9 Sekunden (-50,1 %)

### Bewertung und Entscheidung

- **Bewertung:** Die durchschnittliche Suchposition der Startseite hat sich durch die H1- und Snippet-Korrektur drastisch verbessert und auf Position ~1.8 stabilisiert (Brand-Keywords). Die absolute Anzahl an Klicks und Impressionen bleibt jedoch minimal (6 Klicks in 28 Tagen) und der Zuwachs ist vernachlässigbar. GA4 zeigt zwar minimal mehr Sessions auf der Startseite als organischem Einstieg, jedoch sind die Engagement-Signale (Engagement-Rate, Verweildauer) rückläufig.
- **Entscheidung: `deprioritize` / `wait`.** Weitere Änderungen an der Startseite sind aktuell nicht sinnvoll. Die Startseite rankt stabil für die Brand, liefert aber keinen signifikanten organischen Hebel für informationelle Suchanfragen. Der Fokus wird vollumfänglich von der Startseite abgezogen und auf die thematischen Hubs (insb. Dividendenwachstum, Kennzahlen) und spezifische informationelle Unterseiten verlagert.

## Änderung 2026-08-19

### Hypothese

Die Optimierung des SEO-Titels der zentralen Tool-Seite `/aktien-tool/` hin zu einer suchintent-orientierten Variante steigert die Klickrate (CTR) und erhöht die Klicks auf die Seite bei bzw. nach Erreichen von Spitzenpositionen für informationelle Suchanfragen (wie "aktien analyse tool" oder "aktienanalyse tool"), wo die Seite bereits erste Impressionen hat (Schnitt-Position 3,9 in 28 Tagen).

### Live geändert

WordPress-Page 1210 (`/aktien-tool/`):

1. Yoast-SEO-Titel optimiert: `Aktien-Analyse-Tool: Aktien kostenlos online analysieren` (zuvor Fallback auf Page-Titel `Aktien-Analyse Tool - Schatzsuche 4.0`).
2. Yoast-Meta-Description explizit gesetzt/gesichert: `Analysiere Aktien kostenlos mit über 30 Kennzahlen, Analysten-Ratings und Kurszielen. Erhalte eine übersichtliche Infografik für deine Aktienbewertung.` (zuvor bereits vorhanden, nun in der Konfiguration verankert).

Nicht verändert: URL, Content (inkl. embedded Tool-Iframe), Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1210-pre-seo-20260819.json` (SHA-256: `d051c81875f329a5a92c6189da339b3a1248a582ef6a1558573743bbdc69789d`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Aktien-Analyse-Tool: Aktien kostenlos online analysieren`.
  - HTML-Meta-Description: enthält `Analysiere Aktien kostenlos mit über 30 Kennzahlen, Analysten-Ratings und Kurszielen. Erhalte eine übersichtliche Infografik für deine Aktienbewertung.`.
  - H1-Check: Genau 1 H1 vorhanden (`Aktien-Analyse Tool`).


## Änderung 2026-08-20

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und einer optimierten Meta-Description für die zentrale Seite `/dividend-rechner/` (zuvor leer/fehlend) steigert die Klickrate (CTR) und die Klicks bei Impressionen auf einer durchschnittlichen Position von 11,0.

### Live geändert

WordPress-Page 1965 (`/dividend-rechner/`):

1. Yoast-SEO-Titel gesetzt: `Dividenden-Rechner: Passives Einkommen & Zinseszins berechnen` (zuvor Fallback auf Page-Titel `Dividenden-Rechner - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Berechne dein zukünftiges passives Einkommen mit unserem kostenlosen Dividendenrechner: Simuliere Sparraten, Dividendenwachstum & Zinseszins-Effekt.` (zuvor leer).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1965-pre-seo-20260820.json` (SHA-256: `a45b88c1337f3f59c3aab185e7ecaeaa84f2725e3b72c92640d8331e2c81cc24`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Dividenden-Rechner: Passives Einkommen &amp; Zinseszins berechnen`.
  - HTML-Meta-Description: enthält `Berechne dein zukünftiges passives Einkommen mit unserem kostenlosen Dividendenrechner: Simuliere Sparraten, Dividendenwachstum &amp; Zinseszins-Effekt.`.
  - H1-Check: Genau 1 H1 vorhanden.


## Änderung 2026-08-21

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und einer optimierten Meta-Description für die zentrale Seite `/dividenden-kalender/` (zuvor leer/fehlend) steigert die Klickrate (CTR) und die Klicks bei künftigen Impressionen (bislang 0 in 90 Tagen).

### Live geändert

WordPress-Page 1901 (`/dividenden-kalender/`):

1. Yoast-SEO-Titel gesetzt: `Dividenden-Kalender 2026: HV-Termine & Dividenden kostenlos` (zuvor Fallback auf Page-Titel `Dividenden-Kalender 2026 - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Finde alle HV-Termine und Dividenden für 2026 im kostenlosen Dividenden-Kalender: Simpel filtern und Dividendenhöhe deutscher & US-Aktien checken.` (zuvor leer).

Nicht verändert: URL, Content (inkl. embedded iframe), Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1901-pre-seo-20260821.json` (SHA-256: `ae9d375f95f37e65fa150362458f63f25867f0a6481ad8dc8f87e12190e7f9e5`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Dividenden-Kalender 2026: HV-Termine & Dividenden kostenlos`.
  - HTML-Meta-Description: enthält `Finde alle HV-Termine und Dividenden für 2026 im kostenlosen Dividenden-Kalender: Simpel filtern und Dividendenhöhe deutscher & US-Aktien checken.`.
  - H1-Check: Genau 1 H1 vorhanden.


## Änderung 2026-08-22

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und die Verfeinerung der Meta-Description für die Broker-Empfehlungsseite `/wo-aktien-kaufen/` (ID 69) steigern die Klickrate (CTR) und die Klicks bei bestehenden Suchimpressionen für Beginner-Anfragen (wie "wo aktien kaufen").

### Live geändert

WordPress-Page 69 (`/wo-aktien-kaufen/`):

1. Yoast-SEO-Titel gesetzt: `Wo Aktien kaufen? Depot & Broker Vergleich für Einsteiger` (zuvor Fallback auf Page-Titel `Wo Aktien kaufen? - Schatzsuche 4.0`).
2. Yoast-Meta-Description aktualisiert: `Wo Aktien kaufen? Unser Depot- und Broker-Vergleich zeigt dir die besten Anbieter, Gebühren und Tipps für einen einfachen Einstieg.` (zuvor `Wo kann man Aktien kaufen? Erfahre, worauf es bei Depot, Broker, Gebühren und Sparplänen ankommt, und vergleiche mögliche Anbieter.`).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-69-pre-seo-20260822.json` (SHA-256: `dc81faa29db2355e932fb5fddc64096847a453766104671f764062730419fcb7`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Wo Aktien kaufen? Depot & Broker Vergleich für Einsteiger`.
  - HTML-Meta-Description: enthält `Wo Aktien kaufen? Unser Depot- und Broker-Vergleich zeigt dir die besten Anbieter, Gebühren und Tipps für einen einfachen Einstieg.`.
  - H1-Check: Genau 1 H1 vorhanden.


## Änderung 2026-08-23

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und die Optimierung der Meta-Description für die P2P-Vergleichsseite `/die-besten-plattformen/` (ID 423) steigern die Klickrate (CTR) und die Klicks bei bestehenden Suchimpressionen für P2P-bezogene Anfragen (wie "p2p plattformen", "beste p2p plattformen").

### Live geändert

WordPress-Page 423 (`/die-besten-plattformen/`):

1. Yoast-SEO-Titel gesetzt: `P2P-Plattformen Vergleich 2026: Die besten Anbieter` (zuvor kein expliziter Titel vorhanden, Fallback auf Page-Titel `Beste P2P-Plattformen 2026 im Vergleich`).
2. Yoast-Meta-Description aktualisiert: `P2P-Plattformen im Vergleich 2026: Welche P2P-Plattform liefert die besten Zinsen? Mintos, Bondora, Robocash & Twino im Härtetest – inkl. Risiken.` (zuvor `Vergleiche P2P-Plattformen wie Mintos, Bondora, Robocash und Twino nach Rendite, Mindestanlage, Sicherheit und Liquidität.`).

Nicht verändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-423-pre-seo-20260823.json` (SHA-256: `645c7ee39ec53cacada4c0b02d38441d3641fc217666b5fb852f15fb9bd0251a`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `P2P-Plattformen Vergleich 2026: Die besten Anbieter`.
  - HTML-Meta-Description: enthält `P2P-Plattformen im Vergleich 2026: Welche P2P-Plattform liefert die besten Zinsen? Mintos, Bondora, Robocash & Twino im Härtetest – inkl. Risiken.`.
  - H1-Check: Genau 1 H1 vorhanden.


## Änderung 2026-08-24

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels und die Optimierung der Meta-Description (zuvor Fallback-Titel und standardmäßige Description) für die Hub-Seite `/leitfaden-aktienbewertung/` (ID 1309) steigern die Klickrate (CTR) und die Klicks bei Impressionen (bislang 11 Impressionen, 0 Klicks) für Suchen wie „Aktien bewerten lernen“ und „Aktienbewertung Leitfaden“.

### Live geändert

WordPress-Page 1309 (`/leitfaden-aktienbewertung/`):

1. Yoast-SEO-Titel gesetzt: `Aktien bewerten lernen: Leitfaden & Checkliste (PDF)` (zuvor Fallback `Leitfaden Aktienbewertung für Einsteiger - Schatzsuche 4.0`).
2. Yoast-Meta-Description aktualisiert: `Aktien bewerten lernen: Kostenloser Leitfaden (PDF) zur Aktienbewertung für Einsteiger – mit praktischer Checkliste, Spickzettel und Kennzahlen.` (zuvor `Jetzt kostenlos downloaden: 8-seitiger Leitfaden zur Aktienbewertung für Einsteiger. Mit Spickzettel & Blanko-Checkliste zum Ausdrucken.`).

Nicht geändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1309-pre-seo-20260824.json` (SHA-256: `7f4ab8bd3f69ee6bc001d50f17cb98609aa9f2c71d9f57937652a2d60a93cf48`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Aktien bewerten lernen: Leitfaden &amp; Checkliste (PDF)`.
  - HTML-Meta-Description: enthält `Aktien bewerten lernen: Kostenloser Leitfaden (PDF) zur Aktienbewertung für Einsteiger – mit praktischer Checkliste, Spickzettel und Kennzahlen.`.
  - H1-Check: Genau 1 H1 vorhanden (`Leitfaden Aktienbewertung für Einsteiger`).


## Änderung 2026-08-25

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels (zuvor Fallback-Titel) und die Optimierung der Meta-Description für die Ratgeberseite `/warum-in-immobilien-investieren/` (ID 979) steigern die Klickrate (CTR) und die Klicks bei bestehenden Impressionen (bislang 22 Impressionen für "warum in immobilien investieren" bei einer durchschnittlichen Position von ~68 in 90 Tagen).

### Live geändert

WordPress-Page 979 (`/warum-in-immobilien-investieren/`):

1. Yoast-SEO-Titel gesetzt: `Warum in Immobilien investieren? Vorteile & Chancen` (zuvor Fallback `Warum in Immobilien investieren? - Schatzsuche 4.0`).
2. Yoast-Meta-Description aktualisiert: `Warum in Immobilien investieren? Erfahre alle Vorteile wie Inflationsschutz, Wertsteigerung und Mieteinnahmen für deinen langfristigen Vermögensaufbau.` (zuvor `Entdecke, warum der Kauf von Wohnimmobilien auf Kredit eine ausgezeichnete Investition ist. Lerne die Vorteile und den gesamten Prozess kennen.`).

Nicht geändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-979-pre-seo-20260825.json` (SHA-256: `606d216bd68cc53c120a5d6b501d320e44ecdb295dd41b58a8c3df1e405c605a`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Warum in Immobilien investieren? Vorteile &amp; Chancen`.
  - HTML-Meta-Description: enthält `Warum in Immobilien investieren? Erfahre alle Vorteile wie Inflationsschutz, Wertsteigerung und Mieteinnahmen für deinen langfristigen Vermögensaufbau.`.
  - H1-Check: Genau 1 H1 vorhanden (`Warum in Immobilien investieren?`).

## Änderung 2026-08-26

### Hypothese

Die Ergänzung einer suchintentorientierten Meta-Description (zuvor leer/fehlend) sowie die Optimierung des SEO-Titels für die Depotübersichts-Seite `/meine-depots/` (ID 114) steigern die CTR und etablieren den Depot-Hub mit realen Erfahrungssignalen im Index.

### Live geändert

WordPress-Page 114 (`/meine-depots/`):

1. Yoast-SEO-Titel gesetzt: `Aktiendepot & Broker: Meine Empfehlungen & Erfahrungen` (zuvor Fallback `Meine Depots - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Welches Aktiendepot ist das beste? Meine persönlichen Empfehlungen und Erfahrungen mit Scalable Capital, Traders Place und C24 Bank im Vergleich.` (zuvor leer).

Nicht geändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-114-pre-seo-20260826.json` (SHA-256: `99ef966079e6b923435e4817ddbbfe872e64aa77450bbbac666d1e62199a725a`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Aktiendepot &amp; Broker: Meine Empfehlungen &amp; Erfahrungen`.
  - HTML-Meta-Description: enthält `Welches Aktiendepot ist das beste? Meine persönlichen Empfehlungen und Erfahrungen mit Scalable Capital, Traders Place und C24 Bank im Vergleich.`.
  - H1-Check: Genau 1 H1 vorhanden (`Meine Depots`).

## Änderung 2026-08-27

### Hypothese

Die Ergänzung einer suchintentorientierten Meta-Description (zuvor leer/fehlend) sowie die Optimierung des SEO-Titels für die KGV-Einsteigerseite `/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger/` (ID 2062) steigern die Klickrate (CTR) und etablieren die Seite in den Suchergebnissen für grundlegende KGV-Suchanfragen.

### Live geändert

WordPress-Post 2062 (`/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger/`):

1. Yoast-SEO-Titel gesetzt: `Was ist das KGV? Kurs-Gewinn-Verhältnis einfach erklärt` (zuvor Fallback `Was ist das KGV? – Einfach erklärt für Anfänger - Schatzsuche 4.0`).
2. Yoast-Meta-Description gesetzt: `Was bedeutet das Kurs-Gewinn-Verhältnis (KGV)? Wie berechnet man es und was ist ein gutes KGV? Unser Leitfaden für Einsteiger mit Beispielen.` (zuvor leer).

Nicht geändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/post-2062-pre-seo-20260827.json` (SHA-256: `b9f100f85031e702db4a13bdb54dbe5658bdea050db950d345784046204e2d08`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `Was ist das KGV? Kurs-Gewinn-Verhältnis einfach erklärt`.
  - HTML-Meta-Description: enthält `Was bedeutet das Kurs-Gewinn-Verhältnis (KGV)? Wie berechnet man es und was ist ein gutes KGV? Unser Leitfaden für Einsteiger mit Beispielen.`.
  - H1-Check: Genau 1 H1 vorhanden (`Was ist das KGV? – Einfach erklärt für Anfänger`).

## Änderung 2026-08-28

### Hypothese

Die Ergänzung eines suchintentorientierten, ansprechenden SEO-Titels (zuvor Fallback-Titel) und die Optimierung der Meta-Description für die Tool- und Dashboard-Seite `/p2p-dashboard/` (ID 1921) steigern die Klickrate (CTR) und die Klicks bei bestehenden Impressionen (bislang 10 Impressionen für "p2p dashboard" bei einer durchschnittlichen Position von ~17.1 in 90 Tagen).

### Live geändert

WordPress-Page 1921 (`/p2p-dashboard/`):

1. Yoast-SEO-Titel gesetzt: `P2P Dashboard: Plattformen vergleichen & Zinsen berechnen` (zuvor Fallback `P2P Dashboard - Schatzsuche 4.0`).
2. Yoast-Meta-Description aktualisiert: `P2P-Plattformen im Zinsen- & Risiko-Vergleich: Berechne dein passives Einkommen und den Zinseszins-Effekt kostenlos im P2P-Dashboard.` (zuvor `Vergleiche führende P2P-Plattformen nach Rendite und Konditionen. Berechne mit dem Zinseszins-Rechner dein mögliches passives Einkommen.`).

Nicht geändert: URL, Content, Layout, H1.

### Verifikation

- WordPress XML-RPC-Update: Status SUCCESS.
- Authentifiziertes Readback: Werte erfolgreich ausgelesen und verifiziert.
- Backup erstellt: `traffic/backups/page-1921-pre-seo-20260828.json` (SHA-256: `215832d5a05a5854272c3c5f89fbd743ef0e1d024b99982d1d8689e2ae0806aa`).
- Anonymer Live-Smoke mit Cache-Busting (`?nocache=1`):
  - HTTP Status: 200.
  - HTML-Titel: enthält `P2P Dashboard: Plattformen vergleichen &amp; Zinsen berechnen`.
  - HTML-Meta-Description: enthält `P2P-Plattformen im Zinsen- &amp; Risiko-Vergleich: Berechne dein passives Einkommen und den Zinseszins-Effekt kostenlos im P2P-Dashboard.`.
  - H1-Check: Genau 1 H1 vorhanden (`P2P Dashboard`).
 
 
## Änderung 2026-08-29
 
### Hypothese
 
Die Deaktivierung (Drafting) der verwaisten Duplikat-URL `/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger-2/` (ID 2068) verhindert Duplicate Content und Kannibalisierung mit der optimierten Haupt-URL `/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger/` (ID 2062). Dies bündelt alle Suchsignale auf der kanonischen Zielseite.
 
### Live geändert
 
WordPress-Post 2068 (`/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger-2/`):
 
1. Status von `publish` auf `draft` gesetzt.
 
Nicht geändert: Original-Post 2062, dessen Inhalt oder URLs.
 
### Verifikation
 
- WordPress REST-Update: HTTP 200.
- Authentifiziertes Readback: Status erfolgreich als `draft` verifiziert.
- Backup erstellt: `traffic/backups/post-2068-pre-draft-20260829.json` (SHA-256: `1113b11a00f9d82f8b6dba48e1d58895e6ae3c039d998441d6e708219959dfbb`).
- Anonymer Live-Smoke mit Cache-Busting:
  - Duplikat-URL `/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger-2/` liefert HTTP 404.
  - Original-URL `/was-ist-das-kgv-einfach-erklaert-fuer-anfaenger/` liefert HTTP 200.



