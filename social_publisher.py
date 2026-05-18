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



def post_to_x(caption, image_path):
    """Postet ein Bild mit Text auf X (Twitter)."""
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        print("[SKIP] X-Credentials fehlen.")
        return False
        
    try:
        # v1.1 Auth for Media Upload
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api_v1 = tweepy.API(auth)
        
        # v2 Client for Tweeting
        client_v2 = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET
        )
        
        # Upload media
        media = api_v1.media_upload(filename=image_path)
        media_id = media.media_id
        
        # Create tweet
        client_v2.create_tweet(text=caption, media_ids=[media_id])
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
            public_url = f"http://3.71.191.12/static/temp_social/{filename}"
        
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
            
    except Exception as e:
        print(f"[ERR] Instagram-Posting fehlgeschlagen: {e}")
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

def run_social_sync(symbol, caption, image_path, blog_url=None, wp_img_url=None, title=None, comment_text=None):
    """Hier erfolgt der koordinierte Social-Media-Push."""
    print(f"Bündele Social-Media-Push für {symbol}...")
    
    # 1. X (Twitter)
    post_to_x(caption, image_path)
    
    # 2. Facebook (Offizielle API)
    post_to_facebook_page(caption, image_path, link_url=blog_url, comment_text=comment_text)
    
    # 3. Instagram (Offizielle API)
    post_to_instagram_feed(caption, image_path, wp_img_url=wp_img_url, link_url=blog_url, comment_text=comment_text)
    
    # 4. Pinterest (Offizielle API)
    # Pinterest requires a strict title. Fallback to symbol if not provided.
    pin_title = title if title else f"Aktienanalyse: {symbol}"
    post_to_pinterest(pin_title, caption, image_path, link_url=blog_url)

if __name__ == "__main__":
    # Test-Run
    # run_social_sync("TSLA", "Test-Post!", "path/to/test.png", "https://schatzsuche40.de/test-post")
    pass
