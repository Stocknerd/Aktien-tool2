import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Die Berechtigungen (Scopes) für den YouTube-Upload
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'  # Required for thumbnails.set()
]

def get_authenticated_service(token_file='token_finance.pickle'):
    """
    Handhabt den OAuth2-Flow und gibt den YouTube-Service zurück.
    Erstellt lokal eine token_finance.pickle für spätere Logins.
    """
    credentials = None
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            credentials = pickle.load(token)
            
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                print("ERROR: 'client_secrets.json' fehlt! Bitte im Ordner ablegen.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            credentials = flow.run_local_server(port=0)
        
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)

    return build('youtube', 'v3', credentials=credentials)

def sanitize_tags(tags):
    """
    Säubere Tags für YouTube:
    - Splittet Tags, falls sie Kommas enthalten (GPT-Fehler-Kompensation).
    - Entfernt ungültige Zeichen (" < > etc).
    - Limit 500 Chars insgesamt.
    - Tags zwischen 3 und 30 Zeichen.
    """
    if not tags: return []
    
    flat_tags = []
    for tag in tags:
        parts = str(tag).split(",")
        for p in parts:
            clean_p = p.replace("<", "").replace(">", "").replace('"', "").replace("'", "").strip()
            if clean_p:
                flat_tags.append(clean_p)
                
    seen = set()
    unique_tags = []
    for t in flat_tags:
        if t.lower() not in seen:
            unique_tags.append(t)
            seen.add(t.lower())

    final_tags = []
    total_len = 0
    for t in unique_tags:
        if len(t) < 2 or len(t) > 50: continue
            
        if total_len + len(t) + 2 < 480: 
            final_tags.append(t)
            total_len += len(t) + 2
        else:
            break
            
    return final_tags

def upload_video(video_file, metadata_dict, privacy_status='public', publish_at=None, token_file='token_finance.pickle', thumbnail_file=None):
    """
    Lädt ein Video auf YouTube hoch unter Verwendung der Metadaten-Dict.
    publish_at erwartet ein ISO 8601 Datum (z.B. '2025-12-01T15:00:00Z').
    """
    if not os.path.exists(video_file):
        print(f"ERROR: Video-Datei nicht gefunden: {video_file}")
        return False

    title = metadata_dict.get('title', 'AI Video Automation')
    description = metadata_dict.get('description', 'Automatisch generiertes Video.')
    tags = sanitize_tags(metadata_dict.get('tags', []))

    # Fallback to local token path or base dir path
    if not os.path.exists(token_file):
        base_dir_token = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token_finance.pickle')
        if os.path.exists(base_dir_token):
            token_file = base_dir_token

    youtube = get_authenticated_service(token_file)
    if not youtube:
        print("ERROR: YouTube Service konnte nicht authentifiziert werden.")
        return False

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22', # 22 = People & Blogs
            'defaultAudioLanguage': 'de',
            'defaultLanguage': 'de'
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False,
        }
    }

    if publish_at:
        body['status']['publishAt'] = publish_at
        body['status']['privacyStatus'] = 'private'
        print(f"INFO: Video wird geplant fuer: {publish_at}")

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    try:
        print(f"UPLOAD: Starte YouTube Upload: {title}...")
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"🔼 YouTube Upload-Status: {int(status.progress() * 100)}%")

        video_id = response['id']
        print(f"DONE: YouTube Upload erfolgreich! Video ID: {video_id}")
        print(f"LINK: https://youtu.be/{video_id}")
        
        # THUMBNAIL UPLOAD
        if thumbnail_file and os.path.exists(thumbnail_file):
            print(f"THUMBNAIL: Lade Thumbnail hoch: {thumbnail_file}")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_file)
                ).execute()
                print("DONE: Thumbnail erfolgreich gesetzt!")
            except Exception as e:
                print(f"WARNING: Thumbnail-Upload fehlgeschlagen: {e}")
                
        return True

    except Exception as e:
        if "invalid_grant" in str(e).lower() or "expired" in str(e).lower():
            print("\n📢 ERROR: Dein YouTube-Token ist abgelaufen oder ungueltig.")
            print("👉 Bitte loesche die Datei 'token_finance.pickle' im Hauptverzeichnis und starte das Skript neu!")
        else:
            print(f"ERROR: YouTube Upload fehlgeschlagen: {e}")
        return False
