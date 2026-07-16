# Social-Pipeline: Performance-, Canva- und Native-Publisher-Workflow

## Qualitätsmix

Die automatisierte Queue priorisiert Formate anhand des Performance-Audits vom 16.07.2026:

1. Persönliche Updates mit echten Zahlen und eigener Erkenntnis
2. Aktuelle Finanzänderungen und relevante Nachrichten
3. Fundierte Evergreen-Erklärungen für Familien und langfristige Anleger
4. Statische Aktien-Feedposts
5. Keine generischen Einzelaktien-Videos

Empfohlener Wochenmix: drei Aktien-Feedposts, zwei aktuelle Themen-Reels, ein Dividendenkalender und persönliche Beiträge nach Bedarf.

Kalenderdaten werden niemals synthetisch ergänzt. Sind weniger als sechs vollständige verifizierte Einträge vorhanden, wird der Kalenderlauf übersprungen.

## Öffentliche API-Veröffentlichung: doppeltes Gate

Öffentliche API-Dispatcher sind standardmäßig gesperrt. Sie laufen nur, wenn beide Variablen ausdrücklich gesetzt sind:

```bash
PREPARE_MANUAL_UPLOAD=False
PUBLIC_PUBLISHING_ALLOWED=True
```

In allen anderen Kombinationen wird ein lokales Manual-Upload-Paket erzeugt. Das zentrale Gate liegt vor Feed-, Reel-, Short-, TikTok-, Pinterest-, X-, Kommentar- und Crosspost-Dispatchern.

Aktuelle Nachrichten (`current_finance_news`) bleiben unabhängig von diesen beiden Variablen immer Review-only. Nur bereits validierte, höchstens 48 Stunden alte HTTPS-RSS-Meldungen werden berücksichtigt; der Entwurf enthält Quellenmetadaten und wird nicht direkt dispatcht.

Google Drive ist kein Social-Post, aber ein externer Datentransfer und besitzt deshalb ein eigenes Doppel-Gate:

```bash
UPLOAD_TO_GDRIVE=True
GDRIVE_TRANSFER_ALLOWED=True
```

Nur wenn beide Werte ausdrücklich `True` sind, wird ein vorbereitetes Paket zu Drive übertragen. Das Public-Publishing-Gate aktiviert Drive nicht.

Dieses öffentliche API-Gate ist vom nativen Browser-Publisher getrennt. Der Browser-Publisher unterstützt absichtlich nur:

- YouTube: `private`
- Facebook in Meta Business Suite: `draft`

Öffentliche Browserveröffentlichung, Scheduling und Instagram-Publishing sind nicht implementiert.

## Performance-basierten Cronplan prüfen

Der Scheduler rendert seinen Wochenmix direkt aus `recommended_weekly_schedule()` und ersetzt nur den markierten Schatzsuche-Social-Block. Fremde Cronjobs bleiben erhalten. Da Debian/Ubuntu-Cron auf diesem Server keine benutzerspezifischen `CRON_TZ`-Zeitpläne unterstützt, werden pro Termin beide möglichen UTC-Stunden eingetragen; ein `TZ=Europe/Berlin`-Stunden-Guard lässt bei CET/CEST jeweils nur den korrekten Lauf durch.

Read-only ausgeben:

```bash
python -m src.social_schedule \
  --project-dir /home/ubuntu/aktien-tool2 \
  --python-path /home/ubuntu/aktien-tool2/venv/bin/python
```

Erwarteter Mix:

- Montag, Mittwoch, Freitag 16:00: Stock-Feed
- Dienstag, Donnerstag 18:00: aktuelles Thema/Review-Paket
- Sonntag 18:00: Dividendenkalender

Erst nach Prüfung installieren:

```bash
python -m src.social_schedule \
  --project-dir /home/ubuntu/aktien-tool2 \
  --python-path /home/ubuntu/aktien-tool2/venv/bin/python \
  --apply
```

Vor dem Installieren wird die bestehende Crontab fail-closed gelesen und im Projekt-Logverzeichnis gesichert. Ein Lesefehler wird nicht als leere Crontab behandelt.

## Persönlichen Canva-Beitrag vorbereiten

1. Beispiel kopieren und ausschließlich echte persönliche Fakten eintragen:

   ```bash
   cp examples/personal_canva_input.example.json /tmp/personal_post.json
   ```

2. Canva-Paket erzeugen:

   ```bash
   python -m src.social_reels_autoposter \
     --track personal \
     --input /tmp/personal_post.json
   ```

3. Im erzeugten Ordner liegen:

   - `canva_bulk_create.csv`: UTF-8-CSV für Canva Bulk Create
   - `canva_brief.md`: Gestaltung und Freigabeschritte
   - `caption_instagram.txt`: faktenbasierte Caption
   - `caption_youtube.txt`: Shorts-Text
   - `post_manifest.json`: Schema-2-Queue mit `publishing.allowed=false`

4. Bestehende Canva-Vorlage duplizieren, über `Apps > Bulk Create` die CSV verbinden und als MP4 exportieren.

5. Export vorprüfen, ohne das Manifest zu verändern:

   ```bash
   python -m src.approve_canva_packet \
     --manifest /pfad/zum/paket/post_manifest.json \
     --export /pfad/zum/canva-export.mp4 \
     --approved-by frank \
     --audio-strategy platform_audio_later
   ```

6. Nach persönlicher visueller Prüfung ausdrücklich freigeben:

   ```bash
   python -m src.approve_canva_packet \
     --manifest /pfad/zum/paket/post_manifest.json \
     --export /pfad/zum/canva-export.mp4 \
     --approved-by frank \
     --audio-strategy platform_audio_later \
     --approve
   ```

Die Freigabe prüft unter anderem MP4, H.264, 1080×1920, Laufzeit, Dateigröße und Audiostrategie. Danach wird der Export als `reviewed_export.mp4` in den Paketordner kopiert und seine SHA-256-Prüfsumme im Manifest fixiert.

Unterstützte Audiostrategien:

- `embedded_licensed`: Export muss eine Audiospur enthalten
- `platform_audio_later`: Export muss ohne Audiospur vorliegen; Audio wird später nativ ergänzt
- `silent_intentional`: bewusst stummer Export ohne Audiospur

Der Personal-Track veröffentlicht niemals selbst.

## Browser-Voraussetzungen

Installiere die optionale Python-Abhängigkeit:

```bash
python -m pip install -r requirements-browser.txt
```

Starte einen sichtbaren, bereits angemeldeten Chrome mit persistentem Profil und CDP-Port `9223`. Playwright verbindet sich nur mit dieser Sitzung. Nach `connect_over_cdp(...)` darf der extern gestartete Browser nicht mit `browser.close()` beendet werden; nur die Playwright-Verbindung wird getrennt.

Die fest eingebauten Schatzsuche-Ziele sind:

- YouTube-Name: `Schatzsuche 4.0`
- YouTube-Kanal-ID: `UCDj-MBezZKZIGMiK8t21oVA`
- Facebook-Seite: `Schatzsuche4.0`
- Meta-Asset-ID: `112395201353218`
- Meta-Business-ID: `625626605438788`

Vor jeder Mutation werden sichtbarer Zielname und stabile ID geprüft. Der letzte aktive Kanal wird nie stillschweigend übernommen.

## Read-only Prüfungen

Angemeldete Browserziele prüfen:

```bash
python -m src.native_browser_publisher verify-session
```

Freigegebenes YouTube-Manifest prüfen:

```bash
python -m src.native_browser_publisher verify-manifest \
  --manifest /pfad/zum/paket/post_manifest.json \
  --target youtube
```

Freigegebenes Meta-Manifest prüfen:

```bash
python -m src.native_browser_publisher verify-manifest \
  --manifest /pfad/zum/paket/post_manifest.json \
  --target meta_facebook
```

Diese Befehle führen keine Veröffentlichung und keinen Upload aus.

## Sichere Browseraktionen

YouTube privat hochladen:

```bash
python -m src.native_browser_publisher youtube-private \
  --manifest /pfad/zum/paket/post_manifest.json \
  --execute
```

Facebook-Reel als Meta-Entwurf speichern:

```bash
python -m src.native_browser_publisher meta-facebook-draft \
  --manifest /pfad/zum/paket/post_manifest.json \
  --execute
```

Mutationen benötigen absichtlich `--execute`. Meta wird für den Entwurfsweg Facebook-only ausgewählt, weil ein kombinierter Facebook-/Instagram-Crosspost den Entwurfsmodus deaktivieren kann.

## Doppelpostschutz und Ergebnisnachweis

Der Publisher berechnet pro Paket und Plattform einen Fingerprint aus:

- Paket-ID und Projekt
- stabilem Zielvertrag
- SHA-256 des geprüften Exports
- Plattformtexten

Nach erfolgreicher Persistenzprüfung wird das Resultat atomar in `publishing.results` geschrieben. Derselbe Fingerprint mit abgeschlossenem Status (`private` oder `draft`) wird bei einem weiteren Lauf als Duplikat abgelehnt. Ein Paket-Lock verhindert parallele Verarbeitung durch zwei Prozesse.

Erfolgsnachweis:

- YouTube: Video-ID extrahiert, Edit-Seite erneut geöffnet, Titel/Beschreibung und `Privat` erneut geprüft
- Meta: Erfolgsmeldung geprüft und Caption anschließend in `Beitragsentwürfe` wiedergefunden

Ein gerenderter Export, eine UI-Meldung oder ein Pipeline-Erfolg allein gilt nicht als veröffentlichter beziehungsweise gespeicherter Plattformzustand.
