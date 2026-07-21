# Site-Kit-Messzugang – Schatzsuche 4.0

Stand: 2026-07-21
Prüfart: authentifizierte WordPress-/Site-Kit-GET-Abfragen; keine Einstellungen oder Tokens verändert.

## Konfiguration

- Site Kit: verbunden; mindestens ein verbundener Administrator vorhanden.
- Search Console: Modul aktiv und verbunden.
- GSC-Property: `https://schatzsuche40.de/`.
- Analytics 4: Modul aktiv und verbunden; Property, Webstream und Measurement-ID sind konfiguriert.
- PageSpeed Insights: aktiv und verbunden.

## Benutzer-/OAuth-Status

- Der authentifizierte WordPress-Administrator besitzt die erforderlichen WordPress-/Site-Kit-Leserechte.
- Site-Kit-OAuth-Status für diesen Benutzer: `authenticated=false`.
- Erteilte Google-Scopes: keine.

## Reale Report-Probes

Zeitraum: 2026-06-22 bis 2026-07-20.

- GSC Queries: HTTP 403, `missing_required_scopes`.
- GSC Pages: HTTP 403, `missing_required_scopes`.
- GA4 Landingpages: HTTP 403, `missing_required_scopes`.

Es wurden daher keine Klicks, Impressionen, CTR-, Positions-, Session- oder Engagementwerte erzeugt oder angenommen.

## Erforderlicher manueller Schritt

Einmalige Google-Neuauthentifizierung in WordPress Site Kit für Administrator/User 1 mit den read-only Berechtigungen für Search Console und Analytics. Danach dieselben drei GET-Abfragen erneut ausführen und die Ergebnisse in `WEEKLY_GROWTH_SCORECARD.md` und `QUERY_URL_MAP.md` übernehmen.
