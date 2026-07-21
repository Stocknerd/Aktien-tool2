# Schatzsuche 4.0 – technische Traffic-Baseline

Stand: 2026-07-21 07:25 CEST
Domain: https://schatzsuche40.de/
Quelle: öffentlicher HTTP-/Sitemap-Crawl; keine GSC-/GA4-Werte wurden angenommen oder erfunden.

## Öffentliche Erreichbarkeit und Indexierbarkeit

- Startseite: HTTP 200, Canonical `https://schatzsuche40.de/`, Robots `index, follow`.
- `robots.txt`: HTTP 200; Yoast-Sitemap korrekt eingetragen.
- `sitemap_index.xml`: HTTP 200; 5 Teil-Sitemaps.
- Insgesamt 184 Sitemap-URLs geprüft; alle lieferten HTTP 200 und ein zur URL passendes Canonical.
- Keine Sitemap-URL war per Meta-Robots auf `noindex` gesetzt.

## Bestätigte technische Chancen

### P0: H1-/Template-Fehler

- 182 von 184 Sitemap-URLs liefern im serverseitigen HTML nicht genau einen H1, sondern keinen H1.
- Nur diese beiden URLs lieferten genau einen H1:
  - `https://schatzsuche40.de/die-5-wichtigsten-kennzahlen-fuer-die-aktienanalyse/`
  - `https://schatzsuche40.de/leitfaden-aktienbewertung/`
- Betroffen sind auch Startseite, Blog, Artikel, Seiten und Archive.
- Wahrscheinliche Ursache: globales Theme-/Elementor-Template statt 182 einzelner Inhaltsfehler.
- Vor einer Änderung das aktive Header-/Single-/Archive-Template prüfen; anschließend repräsentative URLs live auf genau einen sichtbaren H1 testen.

### P0: Startseite ohne Suchversprechen

- Live-Titel: `Willkommen! - Schatzsuche 4.0`.
- Keine Meta-Description im HTML.
- Kein H1 im HTML.
- Dadurch ist weder für Nutzer noch Suchmaschine klar, ob die Seite Aktienanalyse, Dividenden, Depotberichte oder Finanzbildung als Hauptnutzen anbietet.

### P1: Fehlende Meta-Descriptions

- 101 von 184 Sitemap-URLs haben keine Meta-Description im HTML.
- Nicht alle benötigen eine manuelle Description; zuerst Startseite, wichtige Hubs und GSC-Near-Wins priorisieren.

### P1: Index-Bloat durch Archive

- 29 Tag-Archive, 2 Kategoriearchive und 1 Autorenarchiv sind in den Sitemaps und indexierbar.
- Vor `noindex`/Entfernung aus der Sitemap zuerst GSC-Landingpage-Daten prüfen. Dünne oder überschneidende Archive danach gezielt aus dem Index nehmen beziehungsweise zu echten Hubs ausbauen.

### P1: Wiederholte Dividendenserie

- 21 indexierbare URLs gehören zur Titelfamilie `Top 3 Dividendenaktien im Check: Analyse & Ausblick (Datum)`.
- Mehrere fast gleich benannte Datumsseiten können Suchintentionen aufsplitten und sind kein Ersatz für einen dauerhaften Dividenden-Hub.
- Nicht blind löschen oder umleiten: erst GSC-Abdeckung, Klicks, Impressionen, Backlinks und individuelle Inhalte prüfen.

## Publikationsfrische

- WordPress REST bestätigt laufende Veröffentlichung.
- Jüngster öffentlich geprüfter Beitrag: 2026-07-20.
- Die zehn neuesten Beiträge bestehen überwiegend aus der wiederkehrenden `Top 3 Dividendenaktien`-Serie; dazwischen stehen ein Dividendenwachstums-Guide und ein Depotupdate.

## Sicherheitsblocker vor breiteren Automationen

- In zwei von Git verfolgten Python-Dateien liegen WordPress-Zugangsdaten im Klartext.
- Keine Zugangsdaten werden in diesem Artefakt wiederholt.
- Vor neuer Publisher-/SEO-Automation: Zugang rotieren, aus Git entfernen, Secrets serverseitig injizieren und bisherige Git-Historie als potenziell kompromittiert behandeln.

## Noch fehlende Primärdaten

Für belastbare URL-Priorisierung fehlen aktuell in diesem Audit:

- GSC: Klicks, Impressionen, CTR und Position für 28/90 Tage
- GSC: Queries und Landingpages
- GA4: organische Landingpage-Sessions und Engagement
- Indexierungsbericht / Crawled-currently-not-indexed / Duplicate-canonical-Signale

Ohne diese Daten werden keine Near-Wins, Gewinnerseiten oder Rankingeffekte behauptet.
