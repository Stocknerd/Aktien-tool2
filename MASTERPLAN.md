# 🏛️ Masterplan: Die Zukunft des Aktien-Analyse-Tools

Dieses Dokument skizziert die strategische Entwicklung des Projekts "Schatzsuche Aktien-Tool" für die kommenden Monate. Es dient als Wegweiser für alle zukünftigen Tasks.

---

## 🎯 Übergeordnetes Ziel
Das Tool soll von einem reinen "Infografik-Generator" zu einer vollumfänglichen, KI-gestützten Investment-Plattform mit hoher SEO-Reichweite und Nutzerbindung ausgebaut werden.

---

## 📅 Phasen-Plan & Tasks

### Phase 1: Intelligenz-Upgrade (Zufriedenheit & Tiefe)
*Fokus: Die bestehenden Tools smarter machen.*

- [ ] **Task 1.1: KI-Vergleichs-Urteil**
- [ ] **Task 1.2: Technische Indikatoren** (RSI, MACD, 200-Tage)
- [ ] **Task 1.3: "Sektor-Peers" Automatisierung**

### Phase 2: Interaktivität (UX-Boost)
- [ ] **Task 2.1: Interaktive Chart-Einbindung** (Plotly/Chart.js)
- [ ] **Task 2.2: Mobile App Web-View Optimierung**

### Phase 3: Marketing & SEO Automatisierung (Wachstum)
- [ ] **Task 3.1: Social Media Bot (Instagram/X)**
- [ ] **Task 3.2: Automatisierter Newsletter**
- [ ] **Task 3.3: SEO-Link-Struktur**

### Phase 4: Personalisierung (Nutzerbindung)
- [ ] **Task 4.1: KI-Depot-Check** (Portfolio Performance CSV)
- [ ] **Task 4.2: Watchlist & Benachrichtigungen**

### Phase 5: Predictive Intelligence (Frühwarnsysteme)
*Fokus: Nicht nur den Status Quo zeigen, sondern Trends antizipieren.*

- [ ] **Task 5.1: Sektor-Rotations-Analyse**
    - [ ] KI-Analyse: Welcher Sektor (Tech, Staples, Energy) gewinnt im aktuellen Zinsumfeld an Dynamik?
- [ ] **Task 5.2: "Value-Trap" Detektor**
    - [ ] KI-Filter: Unterscheidung zwischen "echtem Value" und fallenden Messern (Value Traps) durch Abgleich von Cashflow-Trends.
- [ ] **Task 5.3: Prognose-Korridor Integration**
    - [ ] Visualisierung von Analysten-Schätzungen (High/Low/Mean) für die nächsten 3 Jahre als Trendgrafik.

### Phase 6: Multimedia & Content-Bot (Vertical Video)
*Fokus: Präsenz auf kurzlebigen Plattformen (TikTok, Instagram Reels, YT Shorts).*

- [ ] **Task 6.1: Automated Video-Teaser Generator**
    - [ ] Skript, das die Infografik in ein dynamisches 9:16 Video verwandelt (Ken Burns Effekt auf Kennzahlen) inkl. KI-Sprachausgabe (Text-to-Speech).
- [ ] **Task 6.2: Podcast-Snippets**
    - [ ] KI-generierte "Daily Stock Briefings" (1-Minute-Audio) basierend auf deinen Daten.

### Phase 7: B2B & API-Ökonomie (Monetarisierung)
*Fokus: Dein Tool als Infrastruktur für andere.*

- [ ] **Task 7.1: Widget-System für andere Finanz-Blogs**
    - [ ] Ein "Embeddable-Widget", das du anderen Bloggern anbieten kannst (z.B. Affiliate-Modell).
- [ ] **Task 7.2: Premium-API Zugang**
    - [ ] Bereitstellung deiner bereinigten und mit KI-analysierten Daten für externe Entwickler.

### Phase 8: Community-Intelligence (Sentiment)
*Fokus: Was denkt der "Schwarm"?*

- [ ] **Task 8.1: Sentiment-Score Integration** (Social Media Monitoring)
- [ ] **Task 8.2: "KI vs. Community" Benchmark** (User-Voting im Tool)

### Phase 9: Quality & User Feedback (Bug Reporting)
*Fokus: Stabilität durch Nutzer-Interaktion.*

- [ ] **Task 9.1: In-App Bug-Reporting Widget**
    - [ ] Ein dezenter "Fehler melden" Button auf den Analyse-Seiten.
    - [ ] Automatisches Mitliefern von Metadaten (Ticker, Zeitstempel, Browser-Info).
- [ ] **Task 9.2: Feedback-Management**
    - [ ] Speicherung der Reports in einer `bugs.csv` oder automatische Benachrichtigung via Bot.

---

## 🛠 Technische Roadmap (Erweitert)

1. **Automatisierter Data-Lifecycle (Server-Side):**
    - [ ] **Task T.1: Robustes Update-Skript** – Konsolidierung von `update_csv.py` und `refresh_data.py` zu einem stabilen Server-Dienst mit Error-Logging.
    - [ ] **Task T.2: Kostenlose Datenbasis** – Optimierung der Scraper für Yahoo Finance (freie Schnittstellen) mit intelligenten Retries und Proxy-Support.
    - [ ] **Task T.3: Premium-API Bridge** – Architektur-Vorbereitung für den schnellen Wechsel auf eine bezahlte Datenquelle (z.B. FinancialModelingPrep, EOD Historical oder Polygon.io), sobald die Skalierung es erfordert.
    - [ ] **Task T.4: Logo-Automatisierung** – Wöchentlicher automatischer Download fehlender Firmen-Logos auf dem AWS-Server.

2. **Caching-Layer:** Implementierung von Redis oder einer SQL-Cache-Tabelle (Dank API-Kostensenkung).
3. **Multi-Sprach-Support:** Vorbereitung für die US-Expansion (Stocknerd.io).
4. **Vector-Database (RAG):** Speicherung alter Analysen für Vergleiche über Zeiträume hinweg.

---

## 📌 Nächste konkrete Schritte
Sobald du das Go gibst, starten wir mit **Phase 1, Task 1.1 (KI-Vergleichs-Urteil)**.

> [!IMPORTANT]
> **Noch nicht gestartet!** Ich warte auf deine Freigabe oder Anpassungswünsche zu diesem Masterplan.
