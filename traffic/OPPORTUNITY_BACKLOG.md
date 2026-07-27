# Schatzsuche 4.0 – Traffic Opportunity Backlog

Stand: 2026-07-27
Ziel: qualifizierte Websitezugriffe erhöhen; zuerst technische Basis und bestehende Chancen, danach skalieren.

## Rang 1 – WordPress-Zugang absichern — abgeschlossen 2026-07-25

**Ausgangsbefund:** Mehrere Git-verfolgte Hilfsdateien enthielten zwei noch gültige WordPress-Administrator-App-Passwörter; das Repository ist öffentlich. Zusätzlich waren abgelaufene Meta-Tokens und ein wirksamer Guest-/Admin-Token fest im Quellcode hinterlegt.

**Umgesetzt und verifiziert:**
1. neuer WordPress-App-Zugang erstellt, lokal in `.env` mit Modus `600` gespeichert und per `/users/me` mit HTTP 200 geprüft;
2. beide öffentlich kompromittierten WordPress-App-Passwörter widerrufen; beide liefern danach HTTP 401;
3. WordPress-, Meta- und Guest-Token-Konstanten aus 20 Git-Dateien entfernt und fail-closed auf Umgebungsvariablen umgestellt;
4. Guest-/Admin-Token auf dem aktiven AWS-Toolserver in der geschützten `.env` rotiert;
5. Secret-Scan über 150 Git-verfolgte Python-Dateien: 0 verbleibende Klartextkandidaten;
6. 29 Zieltests bestanden;
7. `.gitignore` repariert und `.env.example` ohne Werte ergänzt;
8. Commit `bbac49d` auf den AWS-Toolserver ausgerollt; `aktien-tool.service`, Tool-Health, Compare-Startseite, Compare-Sitemap und WordPress-Startseite liefern HTTP 200;
9. alter Guest-/Admin-Token wird live mit HTTP 403 abgelehnt, der neue geschützte Token mit HTTP 200 akzeptiert;
10. eine bereits vorhandene, fehlerhaft maskierte Pinterest-Env-Zeile wurde nach bytegenauem Parser-Vergleich semantisch unverändert normalisiert; die komplette Server-`.env` lädt danach 27 Keys, Backups liegen außerhalb des Repos mit Modus `600` in einem Verzeichnis mit Modus `700`.

**Resthinweis:** Die widerrufenen/abgelaufenen Werte bleiben in älteren Git-Commits sichtbar, sind aber nicht mehr gültig. Der deaktivierte n8n-Altworkflow `Sustainability AutoPublisher v1` bleibt deaktiviert und besitzt nach der Rotation absichtlich kein getestetes aktuelles Schatzsuche-Credential.

**Wirkung:** Der unmittelbar ausnutzbare öffentliche Zugang ist geschlossen; lokale und serverseitige Laufwege beziehen Secrets nicht mehr aus dem Quellcode.

## Rang 2 – GSC-/GA4-Baseline herstellen

**Status, korrigiert 2026-07-27:** Site Kit ist autorisiert und Frank sieht die realen Search-Console-/Analytics-Zahlen im WordPress-Dashboard. Die separaten serverseitigen Berichtsprobes dieses Repositories liefern weiterhin HTTP 403 / `missing_required_scopes`; das ist eine Grenze des automatisierten Lesewegs und kein Beleg für eine fehlende Site-Kit-Verbindung. Aktuell ist keine menschliche Neuautorisierung erforderlich.

**Aktion:**
1. Wenn ein automatischer Datenlauf eingerichtet wird, GSC-Leistung 28 und 90 Tage kontrolliert übernehmen: Seiten, Suchanfragen, Geräte, Länder.
2. GSC-Indexierungsbericht exportieren.
3. GA4 organische Landingpages und Engagement ergänzen.
4. Danach `QUERY_URL_MAP.md` und `WEEKLY_GROWTH_SCORECARD.md` mit echten Daten füllen.

**Wirkung:** Zeigt Near-Wins, CTR-Probleme, Kannibalisierung und die beste nächste URL.

## Rang 3 – globales H1-/Template-Problem beheben — live abgeschlossen, verifiziert 2026-07-26

**Früherer Befund:** 182 von 184 Sitemap-URLs ohne H1 im gelieferten HTML.

**Aktueller Live-Nachweis:**
1. kompletter Crawl aller 185 eindeutigen WordPress-Sitemap-URLs: 0 Fehler, alle 185 URLs mit genau einem H1;
2. Beiträge, Seiten, Kategorien, Tags, Autor, Blogübersicht und Startseite abgedeckt;
3. sieben repräsentative URL-Typen normal und mit Cache-Busting: jeweils HTTP 200, genau ein H1 und unverändertes Canonical;
4. aktueller Beitrag auf Desktop 1280 × 720 und Mobil 390 × 844 geprüft: H1 sichtbar und lesbar, kein horizontaler Überlauf, keine Browserfehler;
5. in diesem Verifikationslauf keine WordPress-Mutation vorgenommen, da der zuvor offene globale Zustand bereits korrigiert war.

**Evidenz:** `traffic/H1_VERIFICATION_2026-07-26.md`.

## Rang 4 – Startseite zu einem klaren Such- und Nutzerhub machen

**Erledigter technischer Teil:** Die Startseite besitzt inzwischen den SEO-Titel `Aktienanalyse, Screener & Vergleich | Schatzsuche 4.0`, eine passende Meta-Description und genau ein sichtbares H1. Offen bleibt der redaktionelle Hub-Ausbau und dessen spätere Messung.

**Hub-Ergänzung, live verifiziert 2026-07-27:** Zwei konkrete Wege wurden ergänzt: `Alle Depots ansehen` führt zur Depotübersicht und `Online-Leitfaden direkt lesen` zum Aktienbewertungs-Leitfaden. Eine im unabhängigen Review gefundene mobile Überbreite wurde anschließend behoben. Beide CTA-Blöcke liegen bei 320, 360 und 390 px vollständig im Viewport; die Dokumentbreite entspricht jeweils exakt der Viewportbreite. HTTP 200, Canonical, genau ein H1 und `index, follow` blieben erhalten.

**Zielbild:** Ein klarer Einstieg rund um Aktienanalyse, Dividenden und die eigenen Werkzeuge.

**Aktion:**
- präziser SEO-Titel und H1
- verständliches Nutzenversprechen oberhalb des Folds
- direkte Wege zu Aktien-Screener, Vergleich, Dividendenkalender, Aktienbewertungs-Leitfaden und Depotupdates
- 3–5 redaktionell ausgewählte Grundlagen statt chronologischer Beliebigkeit
- passende Meta-Description

**Messung:** GSC-Impressionen/CTR der Startseite nach 14 und 28 Tagen; Klicks auf Kernwerkzeuge in GA4.

## Rang 5 – dauerhafte Themenhubs stärken

Priorität nach vorhandener Site-Struktur, bis GSC eine andere Reihenfolge beweist:

1. **Aktien bewerten / Kennzahlen**
   - Leitfaden Aktienbewertung
   - KGV, KUV, KBV, PEG
   - fünf wichtigste Kennzahlen
   - Aktienvergleich und Screener
2. **Dividenden**
   - Dividendenwachstum
   - Dividendenrendite
   - Dividendenkalender
   - Dividend-Rechner
   - ausgewählte, wirklich unterschiedliche Aktienanalysen
3. **Depot und Strategie**
   - Depotübersicht als Hub
   - monatliche Depotupdates
   - Benchmark-Vergleich

Jeder Hub braucht klare Suchintention, kontextuelle interne Links und einen sinnvollen Weg zum passenden Tool.

## Rang 6 – wiederkehrende `Top 3 Dividendenaktien`-Serie konsolidieren

**Befund:** 21 indexierbare Datums-URLs mit fast identischer Titelfamilie.

**Aktion nach GSC-Prüfung:**
- einen dauerhaften Hub als Eigentümer der breiten Suchintention bestimmen
- Serienartikel nur veröffentlichen, wenn Auswahl, Daten, These und Aktualitätswert eigenständig sind
- alte Seiten mit echten Signalen aktualisieren und intern anbinden
- schwache Überschneidungen je nach Datenlage zusammenführen, umleiten oder aus dem Index nehmen
- keine pauschalen Redirects ohne URL-/Query-Daten

## Rang 7 – Archive bereinigen

- 29 Tag-Archive, 2 Kategorien und 1 Autorenseite auf Nutzen und GSC-Traffic prüfen.
- Dünne Tags ohne eigenen Suchnutzen: `noindex` und aus Sitemap entfernen.
- Strategische Kategorien: zu kuratierten Hubs mit Einleitung, Auswahl und internen Wegen ausbauen.

## Rang 8 – Social als qualifizierten Zubringer nutzen

- Facebook/Instagram-Pipeline weiterhin review-basiert betreiben.
- Nicht nur generische Aktienkarten posten: persönliche Depotentscheidungen, aktuelle Thesen und kurze native Erklärungen testen.
- Pro Paket ein passendes Ziel statt immer Startseite: Kennzahleninhalt → Leitfaden, Dividendeninhalt → Dividenden-Hub, Vergleich → Tool.
- UTM-Parameter und GA4-Kampagnenmessung nutzen.
- Gleiche Website-Landingpage nicht bei jedem Thema erzwingen.

## Arbeitsregel

Pro Runde genau eine messbare Hypothese ändern. Live-URL danach auf Status, Canonical, Indexierbarkeit und sichtbare Darstellung prüfen. Ergebnis nach 14 und 28 Tagen als `scale`, `refine`, `wait` oder `deprioritize` bewerten.
