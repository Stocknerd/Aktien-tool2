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

## Korrektur vom 2026-07-27

Frank hat bestätigt, dass Site Kit autorisiert ist und im WordPress-Dashboard reale Zahlen anzeigt. Die damaligen HTTP-403-Antworten belegen daher nur, dass der separate serverseitige Leseweg dieses Repositories nicht über die nötigen Scopes verfügt. Es ist keine Site-Kit-Neuauthentifizierung erforderlich. Für automatisierte Auswertungen muss später ein eigener kontrollierter Datenzugang oder ein datierter Export eingerichtet werden.
