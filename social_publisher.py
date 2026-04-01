import os
import tweepy
from instagrapi import Client as InstaClient
from dotenv import load_dotenv

load_dotenv()

# X (Twitter) Credentials
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

# Instagram Credentials
INSTA_USER = os.getenv("INSTAGRAM_USER")
INSTA_PASS = os.getenv("INSTAGRAM_PASS")

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

def post_to_instagram(caption, image_path):
    """Postet ein Bild als Feed-Beitrag auf Instagram."""
    if not (INSTA_USER and INSTA_PASS):
        print("[SKIP] Instagram-Credentials fehlen.")
        return False
        
    try:
        cl = InstaClient()
        cl.login(INSTA_USER, INSTA_PASS)
        
        # Post to Feed
        media = cl.photo_upload(image_path, caption)
        print(f"[OK] Instagram: Feed-Post erfolgreich (ID: {media.pk}).")
        return True
    except Exception as e:
        print(f"[ERR] Instagram-Posting fehlgeschlagen: {e}")
        return False

def run_social_sync(symbol, caption, image_path):
    """Hier erfolgt der koordinierte Social-Media-Push."""
    print(f"Bündele Social-Media-Push für {symbol}...")
    
    # 1. X (Twitter)
    post_to_x(caption, image_path)
    
    # 2. Instagram
    post_to_instagram(caption, image_path)

if __name__ == "__main__":
    # Test-Run
    # run_social_sync("TSLA", "Test-Post von Antigravity! 🚀 #Stocknerd", "path/to/test.png")
    pass
