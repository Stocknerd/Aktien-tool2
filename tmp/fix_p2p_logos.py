import requests
import base64
import os

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# URLs for logos (found via search or common paths)
LOGOS = {
    "mintos": "https://www.p2p-investor.de/wp-content/uploads/2021/04/mintos-logo.png",
    "bondora": "https://www.p2p-investor.de/wp-content/uploads/2021/04/bondora-logo.png",
    "robocash": "https://robo.cash/favicon.ico", # I'll use a better one if found
    "twino": "https://www.p2p-investor.de/wp-content/uploads/2021/04/twino-logo.png"
}

def upload_logo(name, url):
    print(f"Downloading {name} logo from {url}...")
    try:
        r = requests.get(url, stream=True, timeout=10, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            print(f"Failed to download {name}: {r.status_code}")
            return None
        
        filename = f"p2p_{name}_logo.png"
        filepath = os.path.join("tmp", filename)
        os.makedirs("tmp", exist_ok=True)
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Uploading {name} logo to WordPress...")
        with open(filepath, 'rb') as f:
            media_headers = HEADERS.copy()
            media_headers["Content-Disposition"] = f"attachment; filename={filename}"
            media_headers["Content-Type"] = "image/png"
            
            res = requests.post(f"{BASE}/media", headers=media_headers, data=f)
            if res.status_code in (200, 201):
                new_url = res.json().get('source_url')
                print(f"SUCCESS! {name} logo uploaded: {new_url}")
                return new_url
            else:
                print(f"Upload failed for {name}: {res.status_code} {res.text}")
                return None
    except Exception as e:
        print(f"Error processing {name}: {e}")
        return None

if __name__ == "__main__":
    results = {}
    for name, url in LOGOS.items():
        new_url = upload_logo(name, url)
        if new_url:
            results[name] = new_url
    
    # Final check: Robocash fallback if favicon is too small
    # I'll just use the icons I generated if any fail
    
    print("\n--- NEW LOGO URLS ---")
    for name, url in results.items():
        print(f"{name}: {url}")
