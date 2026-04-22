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

def get_dynamic_page_token():
    """Generates a Page Access Token using the User Token if available."""
    if not META_USER_TOKEN or not META_PAGE_ID:
        return META_PAGE_ACCESS_TOKEN
        
    try:
        url = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}?fields=access_token&access_token={META_USER_TOKEN}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "access_token" in data:
            return data["access_token"]
        return META_PAGE_ACCESS_TOKEN
    except Exception as e:
        print(f"[WARN] Fehler beim Page Token Abruf: {e}")
        return META_PAGE_ACCESS_TOKEN

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

def post_to_facebook_page(caption, image_path, link=None):
    """Postet ein Bild mit Text und optionalem Link auf die Facebook Page."""
    page_token = get_dynamic_page_token()
    if not (META_PAGE_ID and page_token):
        print("[SKIP] Facebook-Credentials (Page ID / Token) fehlen.")
        return False
        
    try:
        # Step 1: Upload photo
        url = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}/photos"
        
        # If link is provided, append it to caption
        full_text = caption
        if link:
            full_text += f"\n\n👉 Mehr lesen: {link}"
            
        params = {
            "caption": full_text,
            "access_token": page_token
        }
        
        with open(image_path, "rb") as img_file:
            files = {"source": img_file}
            r = requests.post(url, params=params, files=files)
            
        data = r.json()
        if "id" in data:
            print(f"[OK] Facebook: Post erfolgreich (Photo ID: {data['id']}).")
            return True
        else:
            print(f"[ERR] Facebook Fehlermeldung: {data}")
            return False
            
    except Exception as e:
        print(f"[ERR] Facebook-Posting fehlgeschlagen: {e}")
        return False

def post_to_instagram_feed(caption, image_path, wp_img_url=None):
    """Postet ein Bild auf den Instagram Business Feed (Offizielle API)."""
    page_token = get_dynamic_page_token()
    if not (META_INSTA_ID and page_token):
        print("[SKIP] Instagram Business ID oder Token fehlt.")
        return False
        
    try:
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
            "caption": caption,
            "access_token": page_token
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
            "access_token": page_token
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

def run_social_sync(symbol, caption, image_path, blog_url=None, wp_img_url=None):
    """Hier erfolgt der koordinierte Social-Media-Push."""
    print(f"Bündele Social-Media-Push für {symbol}...")
    
    # 1. X (Twitter)
    post_to_x(caption, image_path)
    
    # 2. Facebook (Offizielle API)
    post_to_facebook_page(caption, image_path, link=blog_url)
    
    # 3. Instagram (Offizielle API)
    post_to_instagram_feed(caption, image_path, wp_img_url=wp_img_url)

if __name__ == "__main__":
    # Test-Run
    # run_social_sync("TSLA", "Test-Post!", "path/to/test.png", "https://schatzsuche40.de/test-post")
    pass
