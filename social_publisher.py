import os
import requests
import tweepy
from dotenv import load_dotenv

load_dotenv()

# X (Twitter) Credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

# Meta (Facebook/Instagram) Credentials
META_PAGE_ID = os.getenv("META_PAGE_ID")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
META_USER_TOKEN = os.getenv("META_USER_TOKEN") or os.getenv("USER_TOKEN")
# Instagram Business Account ID
META_INSTA_ID = os.getenv("META_INSTA_ID")
# Mode Switch: set to True to prepare assets locally for manual upload instead of hitting the live social APIs
PREPARE_MANUAL_UPLOAD = os.getenv("PREPARE_MANUAL_UPLOAD", "True").lower() == "true"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def save_for_manual_upload(post_type, title, caption, asset_path, comment_text=None, tags=None):
    """
    Saves the media asset (image/video) and metadata in a local folder 
    for easy manual uploading, instead of pushing it via APIs.
    """
    import shutil
    from datetime import datetime
    
    # 1. Create directory structure (supports external cloud sync paths)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sanitized_title = "".join([c if c.isalnum() or c in ['-', '_'] else '_' for c in (title or "post")])
    folder_name = f"{timestamp}_{post_type}_{sanitized_title[:30]}"
    
    uploads_base = os.getenv("MANUAL_UPLOADS_DIR")
    if not uploads_base:
        uploads_base = os.path.join(BASE_DIR, "manual_uploads")
    else:
        uploads_base = os.path.expandvars(uploads_base).replace('"', '').replace("'", "").strip()
        
    target_dir = os.path.join(uploads_base, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # 2. Copy the asset
    target_asset_path = None
    if asset_path and os.path.exists(asset_path):
        ext = os.path.splitext(asset_path)[1]
        target_asset_name = f"media{ext}"
        target_asset_path = os.path.join(target_dir, target_asset_name)
        try:
            shutil.copy2(asset_path, target_asset_path)
        except Exception as e:
            print(f"[MANUAL UPLOAD] Warning: Failed to copy asset: {e}")
    
    # 3. Create details txt file
    details_path = os.path.join(target_dir, "post_details.txt")
    with open(details_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"MANUAL UPLOAD DETAILS - {post_type.upper()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"📁 Asset-Pfad: {target_asset_path}\n")
        f.write(f"📌 Titel: {title or 'N/A'}\n\n")
        
        # Smart-truncated tweet caption
        import re
        x_caption = caption or ""
        if len(x_caption) > 270:
            trimmed = x_caption[:267]
            last_punctuation = max(trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?'))
            if last_punctuation > 180:
                x_caption = trimmed[:last_punctuation + 1]
            else:
                last_space = trimmed.rfind(' ')
                x_caption = trimmed[:last_space] + "..." if last_space > 180 else trimmed + "..."
        x_caption = re.sub(r'https?://\S+', 'Link im Profil', x_caption)
        x_caption = re.sub(r'\b([a-zA-Z0-9-]+\.)?schatzsuche40\.de\b', 'unserem Profil', x_caption)
        x_caption = '\n'.join([re.sub(r'[ \t]+', ' ', line).strip() for line in x_caption.split('\n')]).strip()
        x_caption = re.sub(r'\n{3,}', '\n\n', x_caption)
        
        f.write(f"📝 CAPTION (Instagram / Facebook / Pinterest):\n{'-'*30}\n{caption}\n{'-'*30}\n\n")
        f.write(f"🐦 CAPTION (X / Twitter - link-free & truncated):\n{'-'*30}\n{x_caption}\n{'-'*30}\n\n")
        if comment_text:
            f.write(f"💬 ERSTER KOMMENTAR (Instagram / YouTube):\n{comment_text}\n\n")
        if tags:
            f.write(f"🏷️ EMPFOHLENE TAGS:\n{', '.join(tags) if isinstance(tags, list) else tags}\n\n")
            
        f.write("💡 TIPPS FÜR DEN HOCHLAD-VORGANG:\n")
        f.write("- Instagram Reels: Wähle beim Upload einen passenden Trend-Sound aus der Musikbibliothek.\n")
        f.write("- YouTube Shorts: Verwende den Titel mit #shorts und füge ein passendes YouTube-Audio hinzu.\n")
        f.write("- Pinterest: Nutze das Bild und verlinke direkt auf https://schatzsuche40.de\n")
        
    print(f"\n[MANUAL UPLOAD] Directory created for manual upload: {target_dir}")
    print("                Asset and text details file copied. Check 'post_details.txt'!")
    
    # 4. Trigger Google Drive API Push if configured
    if os.getenv("UPLOAD_TO_GDRIVE", "False").lower() == "true":
        try:
            from google_drive_uploader import push_folder_to_drive
            push_folder_to_drive(target_dir)
        except Exception as gd_err:
            print(f"[MANUAL UPLOAD] Warning: Google Drive API upload failed: {gd_err}")
            
    return True


def post_to_x(caption, image_path):
    """Postet ein Bild mit Text auf X (Twitter). Falls der Bildupload fehlschlägt (z.B. Free-Tier-Einschränkung), wird ein reiner Textpost gesendet."""
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        print("[SKIP] X-Credentials fehlen.")
        return False
    # Smart-truncate caption to 270 characters to comply with X API weighted constraints (emojis count as 2)
    if caption and len(caption) > 270:
        trimmed = caption[:267]
        # Find the last sentence end (. ! ?) in the latter part of the tweet
        last_punctuation = max(trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?'))
        if last_punctuation > 180:
            caption = trimmed[:last_punctuation + 1]
        else:
            # Fallback to word boundary
            last_space = trimmed.rfind(' ')
            if last_space > 180:
                caption = trimmed[:last_space] + "..."
            else:
                caption = trimmed + "..."

    try:
        # v2 Client for Tweeting
        client_v2 = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET
        )
        
        media_id = None
        if image_path and os.path.exists(image_path):
            try:
                # v1.1 Auth for Media Upload
                auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
                api_v1 = tweepy.API(auth)
                media = api_v1.media_upload(filename=image_path)
                media_id = media.media_id
            except Exception as media_err:
                print(f"[WARN] X-Medien-Upload fehlgeschlagen (evtl. Free-Tier aktiv): {media_err}. Versuche reines Text-Posting...")
        
        # Create tweet
        if media_id:
            client_v2.create_tweet(text=caption, media_ids=[media_id])
        else:
            client_v2.create_tweet(text=caption)
            
        print(f"[OK] X: Post erfolgreich gesendet.")
        return True
    except Exception as e:
        print(f"[ERR] X-Posting fehlgeschlagen: {e}")
        return False

def post_comment(post_id, comment_text):
    """Postet einen Kommentar unter einen Facebook- oder Instagram-Post."""
    PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
    if not PAGE_TOKEN or not post_id:
        return False
        
    try:
        url = f"https://graph.facebook.com/v20.0/{post_id}/comments"
        params = {
            "message": comment_text,
            "access_token": PAGE_TOKEN
        }
        r = requests.post(url, params=params)
        data = r.json()
        if "id" in data:
            print(f"[OK] Kommentar erfolgreich unter Post {post_id} gepostet (ID: {data['id']}).")
            return True
        else:
            print(f"[ERR] Kommentar posting fehlgeschlagen unter {post_id}: {data}")
            return False
    except Exception as e:
        print(f"[ERR] Kommentar-Fehler fuer Post {post_id}: {e}")
        return False

def post_to_facebook_page(message, image_path=None, link_url=None, comment_text=None):
    """
    Postet auf die Facebook-Unternehmensseite (Schatzsuche 4.0).
    Nutzt den never-expiring PAGE_TOKEN.
    """
    PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
    META_PAGE_ID = os.environ.get("META_PAGE_ID")
    
    if not PAGE_TOKEN or not META_PAGE_ID:
        print("[SKIP] Facebook-Post: PAGE_TOKEN oder META_PAGE_ID fehlen.")
        return False

    try:
        # Step 1: Upload photo
        url = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}/photos"
        
        # If link is provided, append it to caption
        full_text = message
        if link_url:
            full_text += f"\n\n👉 Mehr lesen: {link_url}"
            
        params = {
            "caption": full_text,
            "access_token": PAGE_TOKEN
        }
        
        with open(image_path, "rb") as img_file:
            files = {"source": img_file}
            r = requests.post(url, params=params, files=files)
            
        data = r.json()
        if "id" in data:
            print(f"[OK] Facebook: Post erfolgreich (Photo ID: {data['id']}).")
            if comment_text:
                post_comment(data['id'], comment_text)
            return True
        else:
            print(f"[ERR] Facebook Fehlermeldung: {data}")
            return False
            
    except Exception as e:
        print(f"[ERR] Facebook-Posting fehlgeschlagen: {e}")
        return False

def post_to_instagram_feed(caption, image_path, wp_img_url=None, link_url=None, comment_text=None):
    """Postet ein Bild auf den Instagram Business Feed (Offizielle API)."""
    PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
    if not (META_INSTA_ID and PAGE_TOKEN):
        print("[SKIP] Instagram Business ID oder Token fehlt.")
        return False
        
    try:
        # Append link to caption if provided (Instagram doesn't have a separate link field)
        full_caption = caption
        if link_url:
            full_caption += f"\n\n🔗 Mehr dazu: {link_url}"
            
        # Step 1: Create Media Container
        # Meta's servers need to FETCH the image, so we need a public HTTPS URL.
        # wp_img_url is the direct URL to the image on the WordPress site.
        if wp_img_url:
            public_url = wp_img_url
        else:
            filename = os.path.basename(image_path)
            public_url = f"https://tool.schatzsuche40.de/static/temp_social/{filename}"
        
        container_url = f"https://graph.facebook.com/v20.0/{META_INSTA_ID}/media"
        params = {
            "image_url": public_url,
            "caption": full_caption,
            "access_token": PAGE_TOKEN
        }
        
        r = requests.post(container_url, params=params)
        data = r.json()
        
        if "id" not in data:
            print(f"[ERR] Instagram Container Fehlermeldung: {data}")
            return False
            
        creation_id = data["id"]
        print(f"[OK] Instagram: Media Container erstellt ({creation_id}).")
        
        # Step 2: Publish Media (with retry for async processing)
        publish_url = f"https://graph.facebook.com/v20.0/{META_INSTA_ID}/media_publish"
        params_pub = {
            "creation_id": creation_id,
            "access_token": PAGE_TOKEN
        }
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            # Wait a few seconds for Meta's CDN to download the image
            time.sleep(5)
            r_pub = requests.post(publish_url, params=params_pub)
            data_pub = r_pub.json()
            
            if "id" in data_pub:
                print(f"[OK] Instagram: Post erfolgreich veröffentlicht (Media ID: {data_pub['id']}).")
                if comment_text:
                    time.sleep(2)  # Kurze Pause, damit die Media ID bei Meta registriert ist
                    post_comment(data_pub['id'], comment_text)
                return True
            elif data_pub.get('error', {}).get('code') == 9007:
                print(f"[WAIT] Instagram Bild verarbeitet noch... (Versuch {attempt+1}/{max_retries})")
                continue
            else:
                print(f"[ERR] Instagram Publish Fehlermeldung: {data_pub}")
                return False
                
        print(f"[ERR] Instagram Timeout: Bild konnte nicht publiziert werden.")
        return False
            
        return False
            
    except Exception as e:
        print(f"[ERR] Instagram-Posting fehlgeschlagen: {e}")
        return False

def post_instagram_reel(caption, video_filename, comment_text=None):
    """
    Postet ein Video als Instagram Reel über die offizielle Graph API.
    Der Video-Pfad muss im Nginx static directory liegen: /static/temp_social/{video_filename}
    sodass er unter https://tool.schatzsuche40.de/static/temp_social/{video_filename} öffentlich erreichbar ist.
    """
    if PREPARE_MANUAL_UPLOAD:
        video_path = os.path.join(BASE_DIR, "static", "temp_social", video_filename)
        return save_for_manual_upload(
            post_type="instagram_reel",
            title="Instagram Reel",
            caption=caption,
            asset_path=video_path,
            comment_text=comment_text
        )
        
    PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
    META_INSTA_ID = os.environ.get("META_INSTA_ID")
    if not (META_INSTA_ID and PAGE_TOKEN):
        print("[SKIP] Instagram Business ID oder Token fehlt für Reel-Posting.")
        return False
        
    try:
        # 100% stable remote URL served via Nginx static
        public_url = f"https://tool.schatzsuche40.de/static/temp_social/{video_filename}"
        print(f"REEL: Sende Video-URL an Meta: {public_url}")
        
        # Step 1: Create Video Container for REELS
        container_url = f"https://graph.facebook.com/v20.0/{META_INSTA_ID}/media"
        params = {
            "media_type": "REELS",
            "video_url": public_url,
            "caption": caption,
            "access_token": PAGE_TOKEN
        }
        
        r = requests.post(container_url, params=params)
        data = r.json()
        
        if "id" not in data:
            print(f"[ERR] Instagram Reel Container Fehler: {data}")
            return False
            
        creation_id = data["id"]
        print(f"[OK] Instagram Reel: Container erstellt ({creation_id}). Warte auf Verarbeitung...")
        
        # Step 2: Publish Media (with retry for async processing)
        publish_url = f"https://graph.facebook.com/v20.0/{META_INSTA_ID}/media_publish"
        params_pub = {
            "creation_id": creation_id,
            "access_token": PAGE_TOKEN
        }
        
        import time
        max_retries = 10
        # Reels processing takes a bit longer, so we wait 20 seconds initially and retry every 15 seconds
        time.sleep(20)
        for attempt in range(max_retries):
            r_pub = requests.post(publish_url, params=params_pub)
            data_pub = r_pub.json()
            
            if "id" in data_pub:
                print(f"[OK] Instagram Reel: Erfolgreich veröffentlicht! (ID: {data_pub['id']}).")
                if comment_text:
                    time.sleep(3)
                    post_comment(data_pub['id'], comment_text)
                return True
            elif data_pub.get('error', {}).get('code') in [9007, 2207027] or "processing" in str(data_pub).lower():
                print(f"[WAIT] Instagram Reel verarbeitet noch... (Versuch {attempt+1}/{max_retries})")
                time.sleep(15)
                continue
            else:
                print(f"[ERR] Instagram Reel Publish Fehler: {data_pub}")
                return False
                
        print(f"[ERR] Instagram Reel Timeout: Video-Verarbeitung hat zu lange gedauert.")
        return False
        
    except Exception as e:
        print(f"[ERR] Instagram Reel Posting fehlgeschlagen: {e}")
        return False

def post_to_pinterest(title, description, image_path, link_url=None):
    """Postet ein Bild auf Pinterest über die offizielle Pinterest v5 API."""
    PIN_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN")
    BOARD_ID = os.environ.get("PINTEREST_BOARD_ID")
    
    if not PIN_TOKEN or not BOARD_ID:
        print("[SKIP] Pinterest: Access Token oder Board ID fehlen in der .env.")
        return False
        
    try:
        import base64
        with open(image_path, "rb") as img_file:
            b64_data = base64.b64encode(img_file.read()).decode('utf-8')
            
        url = "https://api.pinterest.com/v5/pins"
        headers = {
            "Authorization": f"Bearer {PIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Determine content type based on extension
        ext = image_path.lower().split('.')[-1]
        c_type = "image/jpeg" if ext in ['jpg', 'jpeg'] else "image/png"
        
        # Clean title for Pinterest (max 100 chars)
        clean_title = (title[:97] + '...') if len(title) > 100 else title
        
        payload = {
            "board_id": BOARD_ID,
            "title": clean_title,
            "description": description,
            "media_source": {
                "source_type": "image_base64",
                "content_type": c_type,
                "data": b64_data
            }
        }
        
        if link_url:
            payload["link"] = link_url
            
        r = requests.post(url, headers=headers, json=payload)
        
        if r.status_code == 201:
            data = r.json()
            print(f"[OK] Pinterest: Pin erfolgreich erstellt (ID: {data.get('id')}).")
            return True
        else:
            print(f"[ERR] Pinterest API Fehler: {r.text}")
            return False
            
    except Exception as e:
        print(f"[ERR] Pinterest-Posting fehlgeschlagen: {e}")
        return False

def post_facebook_reel(caption, video_path):
    """Postet ein Video als Facebook Reel auf die Facebook-Page (Schatzsuche 4.0)."""
    if PREPARE_MANUAL_UPLOAD:
        print("[SKIP] Facebook Reel: manual upload assets already created via post_instagram_reel.")
        return True
        
    PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
    META_PAGE_ID = os.environ.get("META_PAGE_ID")
    
    if not PAGE_TOKEN or not META_PAGE_ID:
        print("[SKIP] Facebook Reel: PAGE_TOKEN oder META_PAGE_ID fehlen.")
        return False
        
    print(f"UPLOAD: Starte Facebook Reel Upload: {os.path.basename(video_path)}")
    file_size = os.path.getsize(video_path)
    url_base = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}/video_reels"

    try:
        # STEP 1: INIT
        params = {'upload_phase': 'start', 'access_token': PAGE_TOKEN}
        response = requests.post(url_base, params=params).json()
        if 'video_id' not in response:
            print(f"ERROR: FB Reel Init Fehler: {response}")
            return False
        
        video_id = response['video_id']
        upload_url = response.get('upload_url', f"https://rupload.facebook.com/video-reels/{video_id}")
        
        # STEP 2: UPLOAD
        headers = {
            'Authorization': f'OAuth {PAGE_TOKEN}',
            'offset': '0',
            'file_size': str(file_size),
            'Content-Type': 'application/octet-stream'
        }
        with open(video_path, 'rb') as f:
            upload_res = requests.post(upload_url, data=f, headers=headers).json()
            
        if not upload_res.get('success'):
            print(f"ERROR: FB Reel Upload Fehler: {upload_res}")
            return False

        # STEP 3: FINALIZE
        publish_params = {
            'upload_phase': 'finish',
            'access_token': PAGE_TOKEN,
            'video_id': video_id,
            'description': caption,
            'video_state': 'PUBLISHED'
        }
        
        publish_res = requests.post(url_base, params=publish_params).json()
        if publish_res.get('success'):
            print(f"[OK] Facebook Reel erfolgreich veröffentlicht! ID: {video_id}")
            return True
        else:
            print(f"ERROR: FB Reel Publish Fehler: {publish_res}")
            return False
    except Exception as e:
        print(f"[ERR] Facebook Reel-Posting fehlgeschlagen: {e}")
        return False


def run_social_sync(symbol, caption, image_path, blog_url=None, wp_img_url=None, title=None, comment_text=None, skip_instagram=False, strip_links_on_x=None):
    """Hier erfolgt der koordinierte Social-Media-Push."""
    if PREPARE_MANUAL_UPLOAD:
        return save_for_manual_upload(
            post_type="feed_image",
            title=title or f"Aktienanalyse: {symbol}",
            caption=caption,
            asset_path=image_path,
            comment_text=comment_text
        )
        
    print(f"Bündele Social-Media-Push für {symbol}...")
    
    if strip_links_on_x is None:
        strip_links_on_x = os.getenv("STRIP_LINKS_ON_X", "True").lower() == "true"

    # 1. X (Twitter)
    x_caption = caption
    if strip_links_on_x:
        import re
        # Replace HTTP/HTTPS URLs with "Link im Profil"
        x_caption = re.sub(r'https?://\S+', 'Link im Profil', x_caption)
        # Replace raw domain names like schatzsuche40.de
        x_caption = re.sub(r'\b([a-zA-Z0-9-]+\.)?schatzsuche40\.de\b', 'unserem Profil', x_caption)
        # Clean up spacing while preserving newlines
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in x_caption.split('\n')]
        x_caption = '\n'.join(lines).strip()
        # Limit consecutive newlines to at most a double newline
        x_caption = re.sub(r'\n{3,}', '\n\n', x_caption)
        
    post_to_x(x_caption, image_path)
    
    # 2. Facebook (Offizielle API)
    post_to_facebook_page(caption, image_path, link_url=blog_url, comment_text=comment_text)
    
    # 3. Instagram (Offizielle API)
    if not skip_instagram:
        post_to_instagram_feed(caption, image_path, wp_img_url=wp_img_url, link_url=blog_url, comment_text=comment_text)
    else:
        print("[SKIP] Instagram Feed-Posting übersprungen (Reel wird separat gepostet).")
    
    # 4. Pinterest (Offizielle API)
    # Pinterest requires a strict title. Fallback to symbol if not provided.
    pin_title = title if title else f"Aktienanalyse: {symbol}"
    post_to_pinterest(pin_title, caption, image_path, link_url=blog_url)


if __name__ == "__main__":
    # Test-Run
    # run_social_sync("TSLA", "Test-Post!", "path/to/test.png", "https://schatzsuche40.de/test-post")
    pass
