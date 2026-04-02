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
# Instagram Business Account ID (to be added)
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

def post_to_facebook_page(caption, image_path, link=None):
    """Postet ein Bild mit Text und optionalem Link auf die Facebook Page."""
    if not (META_PAGE_ID and META_PAGE_ACCESS_TOKEN):
        print("[SKIP] Facebook-Credentials fehlen.")
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
            "access_token": META_PAGE_ACCESS_TOKEN
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

def post_to_instagram_feed(caption, image_path):
    """Postet ein Bild auf den Instagram Business Feed (benötigt Insta-ID)."""
    if not (META_INSTA_ID and META_PAGE_ACCESS_TOKEN):
        print("[SKIP] Instagram Business ID fehlt für offiziellen API-Post.")
        return False
        
    # Instagram Graph API logic to be implemented once permissions are there
    # Requires: UI -> Media Container -> Publish Media
    print("[TODO] Instagram API Integration (Warte auf Berechtigung instagram_content_publish)")
    return False

def run_social_sync(symbol, caption, image_path, blog_url=None):
    """Hier erfolgt der koordinierte Social-Media-Push."""
    print(f"Bündele Social-Media-Push für {symbol}...")
    
    # 1. X (Twitter)
    post_to_x(caption, image_path)
    
    # 2. Facebook (Offizielle API)
    post_to_facebook_page(caption, image_path, link=blog_url)
    
    # 3. Instagram (Placeholder)
    post_to_instagram_feed(caption, image_path)

if __name__ == "__main__":
    # Test-Run
    # run_social_sync("TSLA", "Test-Post!", "path/to/test.png", "https://schatzsuche40.de/test-post")
    pass
