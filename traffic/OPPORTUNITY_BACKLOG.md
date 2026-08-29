# Schatzsuche 4.0 – Traffic Opportunity Backlog

Stand: 2026-08-18
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

## Rang 2 – GSC-/GA4-Baseline herstellen — abgeschlossen 2026-07-29

**Umgesetzt und verifiziert:** Dediziertes Read-only-Servicekonto für GA4-Property `299646271` und die Search-Console-Property `https://schatzsuche40.de/` eingerichtet. Echte 7-/28-/90-Tage-Berichte einschließlich Vorperioden, Seiten, Queries, Geräte, Länder, Kanäle und organische Landingpages liefern HTTP 200.

**Artefakte:**

- Rohdaten: `traffic/exports/TRAFFIC_EXPORT_2026-07-29.json`
- Bewertung: `traffic/TRAFFIC_ASSESSMENT_2026-07-29.md`
- aktualisierte Query-/URL-Map: `traffic/QUERY_URL_MAP.md`
- aktualisierte Scorecard: `traffic/WEEKLY_GROWTH_SCORECARD.md`
 
**Datenentscheidung:** Sichtbarkeit wächst, Suchtraffic noch nicht. Nächste Reihenfolge: Value-Investing-Snippet als kleiner Near-Win (abgeschlossen 2026-08-10); Dividendenwachstum-Hub intern stärken (abgeschlossen 2026-08-11); Einsteiger-Guide-Snippet optimieren (abgeschlossen 2026-08-12); Kennzahlen-Hub-Linkstärkung (abgeschlossen 2026-08-13); Bodo Schäfer Buchrezensions-Snippet (abgeschlossen 2026-08-14); Andre Kostolany Buchrezensions-Snippet (abgeschlossen 2026-08-15); Aktien-Vergleichstool-Snippet (abgeschlossen 2026-08-16); Altersvorsorgedepot-Snippet (abgeschlossen 2026-08-17); Aktien-Analyse-Tool-Snippet (abgeschlossen 2026-08-19); Dividenden-Rechner-Snippet (abgeschlossen 2026-08-20); Dividenden-Kalender-Snippet (abgeschlossen 2026-08-21); Depot- und Broker-Vergleich-Snippet (abgeschlossen 2026-08-22); P2P-Plattformen-Snippet (abgeschlossen 2026-08-23); Aktien-bewerten-Leitfaden-Snippet (abgeschlossen 2026-08-24); Immobilien-investieren-Snippet (abgeschlossen 2026-08-25); Meine-Depots-Snippet (abgeschlossen 2026-08-26); KGV-Einsteigerseite-Snippet (abgeschlossen 2026-08-27); P2P-Dashboard-Snippet (abgeschlossen 2026-08-28); Deaktivierung KGV-Duplikat (abgeschlossen 2026-08-29). Keine blinde Massenkonsolidierung.

## Rang 3 – globales H1-/Template-Problem beheben — live abgeschlossen, verifiziert 2026-07-26

**Früherer Befund:** 182 von 184 Sitemap-URLs ohne H1 im gelieferten HTML.

**Aktueller Live-Nachweis:**
1. kompletter Crawl aller 185 eindeutigen WordPress-Sitemap-URLs: 0 Fehler, alle 185 URLs mit genau einem H1;
2. Beiträge, Seiten, Kategorien, Tags, Autor, Blogübersicht und Startseite abgedeckt;
3. sieben repräsentative URL-Typen normal und mit Cache-Busting: jeweils HTTP 200, genau ein H1 und unverändertes Canonical;
4. aktueller Beitrag auf Desktop 1280 × 720 und Mobil 390 × 844 geprüft: H1 sichtbar und lesbar, kein horizontaler Überlauf, keine Browserfehler;
5. in diesem Verifikationslauf keine WordPress-Mutation vorgenommen, da der zuvor offene globale Zustand bereits korrigiert war.

**Evidenz:** `traffic/H1_VERIFICATION_2026-07-26.md`.

## Rang 4 – Startseite zu einem klaren Such- und Nutzerhub machen — abgeschlossen (Review am 2026-08-18)

**Erledigter technischer Teil & Hub-Ergänzung:** Startseite besitzt den SEO-Titel `Aktienanalyse, Screener & Vergleich | Schatzsuche 4.0`, eine Meta-Description, genau ein H1 sowie mobile-optimierte CTAs zu den Hauptbereichen.

**28-Tage-Review (2026-08-18):** Die durchschnittliche Suchposition verbesserte sich deutlich auf 1,85 (Brand-Rankings), aber Klicks (6 in 28 Tagen) und Impressionen (13) blieben nahezu unverändert minimal. Die organischen Einstiege über die Homepage sind sehr gering, und die Verweildauer sank.

**Entscheidung:** `deprioritize / wait`. Keine weiteren Ressourcen auf der Startseite einsetzen, da die Brand-Sichtbarkeit voll stabilisiert ist, aber kein nennenswerter informationeller Such-Traffic über die Homepage generiert werden kann. Der Fokus wechselt vollständig auf informationelle Unterseiten und Themenhubs.


## Rang 5 – dauerhafte Themenhubs stärken

Priorität nach vorhandener Site-Struktur, bis GSC eine andere Reihenfolge beweist:

1. **Aktien bewerten / Kennzahlen** (intern gestärkt am 2026-08-13)
   - Leitfaden Aktienbewertung (Hub-Ziel)
   - KGV (interner Link am 2026-08-13 aus Post 2062 gesetzt; Duplikat ID 2068 am 2026-08-29 auf `draft` gesetzt)
   - KUV, KBV, PEG (interner Link am 2026-08-13 aus Post 2067 gesetzt)
   - fünf wichtigste Kennzahlen (interner Link am 2026-08-13 aus Post 2064 gesetzt)
   - Aktienvergleich und Screener

2. **Dividenden**
   - Dividendenwachstum
   - Dividendenrendite
   - Dividendenkalender (SEO-optimiert am 2026-08-21)
   - Dividend-Rechner (SEO-optimiert am 2026-08-20)
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
