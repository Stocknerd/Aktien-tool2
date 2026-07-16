import os
import sys
import json
import pickle
import requests

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import BASE_DIR

# TikTok OAuth2 Endpoints
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_UPLOAD_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"

def get_tiktok_auth_link(client_key, redirect_uri="http://localhost:8080/"):
    """
    Generates the OAuth2 authorization URL for the user to visit in their browser.
    """
    scopes = "user.info.basic,video.upload,comment.publish,video.list"
    state = "tiktok_auth_state_123"
    auth_link = f"{TIKTOK_AUTH_URL}?client_key={client_key}&scope={scopes}&response_type=code&redirect_uri={redirect_uri}&state={state}"
    return auth_link

def generate_tiktok_token(client_key, client_secret, authorization_code, redirect_uri="http://localhost:8080/", token_file="token_tiktok.pickle"):
    """
    Exchanges the authorization code for an access token and refresh token,
    saving them into a pickle file.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": authorization_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    print("TIKTOK OAUTH: Exchanging authorization code for tokens...")
    r = requests.post(TIKTOK_TOKEN_URL, headers=headers, data=data)
    res_data = r.json()
    
    if "access_token" in res_data:
        # Save tokens
        with open(token_file, "wb") as f:
            pickle.dump(res_data, f)
        print("TIKTOK OAUTH: Token successfully generated and saved!")
        return res_data
    else:
        print(f"TIKTOK OAUTH: Error exchanging code: {res_data}")
        return None

def refresh_tiktok_token(client_key, client_secret, token_file="token_tiktok.pickle"):
    """
    Refreshes the access token using the saved refresh token.
    """
    if not os.path.exists(token_file):
        return None
        
    with open(token_file, "rb") as f:
        token_data = pickle.load(f)
        
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print("TIKTOK OAUTH: Refresh token not found in saved data.")
        return None
        
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    print("TIKTOK OAUTH: Refreshing access token...")
    r = requests.post(TIKTOK_TOKEN_URL, headers=headers, data=data)
    res_data = r.json()
    
    if "access_token" in res_data:
        # Update saved token file
        token_data.update(res_data)
        with open(token_file, "wb") as f:
            pickle.dump(token_data, f)
        print("TIKTOK OAUTH: Access token successfully refreshed!")
        return token_data
    else:
        print(f"TIKTOK OAUTH: Refresh failed: {res_data}")
        return None

def get_valid_access_token(client_key, client_secret, token_file="token_tiktok.pickle"):
    """
    Loads saved token data and refreshes it if needed, returning a valid access token.
    """
    if not os.path.exists(token_file):
        return None
        
    with open(token_file, "rb") as f:
        token_data = pickle.load(f)
        
    # Standard refresh to ensure validity (TikTok access tokens last 24h, refreshing is safe)
    refreshed = refresh_tiktok_token(client_key, client_secret, token_file)
    if refreshed:
        return refreshed.get("access_token")
    else:
        return token_data.get("access_token")

def upload_video_to_tiktok(video_path, caption, client_key, client_secret, token_file="token_tiktok.pickle"):
    """
    Uploads a video to TikTok using the Content Posting API v2.
    """
    if not os.path.exists(video_path):
        print(f"TIKTOK: Video file not found: {video_path}")
        return False

    from social_publisher import live_public_dispatch_enabled
    if not live_public_dispatch_enabled():
        print("TIKTOK: Public upload blocked by the central publishing gate.")
        return False
        
    # Fallback path for server
    if not os.path.exists(token_file):
        base_token = os.path.join(BASE_DIR, "token_tiktok.pickle")
        if os.path.exists(base_token):
            token_file = base_token
            
    access_token = get_valid_access_token(client_key, client_secret, token_file)
    if not access_token:
        print("TIKTOK: Authentication failed. token_tiktok.pickle missing or invalid.")
        return False
        
    video_size = os.path.getsize(video_path)
    
    # Clean caption for TikTok (limit 150 characters usually, up to 2200 now but keep it punchy)
    clean_caption = (caption[:240] + "...") if len(caption) > 250 else caption
    
    # Step A: Initiate Share/Upload Request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    body = {
        "post_info": {
            "title": clean_caption,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "comment_disabled": False,
            "duet_disabled": False,
            "stitch_disabled": False
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1
        }
    }
    
    print(f"TIKTOK: Initiating upload request for video size {video_size} bytes...")
    r = requests.post(TIKTOK_UPLOAD_INIT_URL, headers=headers, json=body)
    res_data = r.json()
    
    # TikTok API error handling
    if r.status_code != 200 or "error" in res_data or "data" not in res_data:
        print(f"TIKTOK ERROR: Init upload request failed: {res_data}")
        return False
        
    upload_data = res_data["data"]
    upload_url = upload_data.get("upload_url")
    publish_id = upload_data.get("publish_id")
    
    if not upload_url:
        print(f"TIKTOK ERROR: Upload URL not found in response: {res_data}")
        return False
        
    # Step B: Upload the video file binary (PUT request)
    print("TIKTOK: Uploading raw binary video data to TikTok CDN...")
    put_headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(video_size)
    }
    
    with open(video_path, "rb") as video_file:
        r_put = requests.put(upload_url, headers=put_headers, data=video_file)
        
    if r_put.status_code == 200 or r_put.status_code == 201:
        print(f"TIKTOK SUCCESS: Video successfully uploaded to TikTok! Publish ID: {publish_id}")
        return True
    else:
        print(f"TIKTOK ERROR: Binary upload failed (HTTP {r_put.status_code}): {r_put.text}")
        return False

if __name__ == "__main__":
    # Local CLI helper for tomorrow's authentication
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        print("\n--- TIKTOK HEADLESS OAUTH BOOTSTRAPPER ---")
        c_key = input("Gib deinen TikTok 'Client Key' ein: ").strip()
        if not c_key:
            sys.exit(1)
        link = get_tiktok_auth_link(c_key)
        print(f"\n👉 Öffne diesen Link in deinem Browser und logge dich ein:\n\n{link}\n")
        print("Nach dem Login wirst du auf 'http://localhost:8080/?code=XXXX&state=...' weitergeleitet.")
        auth_code = input("\nGib den 'code' Parameter aus der Adressleiste ein: ").strip()
        c_sec = input("Gib dein TikTok 'Client Secret' ein: ").strip()
        
        generate_tiktok_token(c_key, c_sec, auth_code)
    else:
        print("Usage: python tiktok_uploader.py auth (to trigger OAuth2 flow)")
