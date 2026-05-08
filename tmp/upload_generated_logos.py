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

# Paths to generated images (I'll need to use the exact filenames from the output)
# Note: I'll use the filenames provided in the previous turns
IMG_FILES = {
    "mintos": r"C:\Users\fhofmann\.gemini\antigravity\brain\1b0a5e00-fda2-4600-a917-8361004f0c35\mintos_logo_clean_1778213861559.png",
    "bondora": r"C:\Users\fhofmann\.gemini\antigravity\brain\1b0a5e00-fda2-4600-a917-8361004f0c35\bondora_logo_clean_1778213877614.png",
    "twino": r"C:\Users\fhofmann\.gemini\antigravity\brain\1b0a5e00-fda2-4600-a917-8361004f0c35\twino_logo_clean_1778213893605.png",
    "robocash": r"C:\Users\fhofmann\.gemini\antigravity\brain\1b0a5e00-fda2-4600-a917-8361004f0c35\robocash_logo_clean_1778213910202.png"
}

def upload_local_file(name, filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
    
    print(f"Uploading {name} logo to WordPress...")
    with open(filepath, 'rb') as f:
        media_headers = HEADERS.copy()
        media_headers["Content-Disposition"] = f"attachment; filename=p2p_{name}_premium.png"
        media_headers["Content-Type"] = "image/png"
        
        res = requests.post(f"{BASE}/media", headers=media_headers, data=f)
        if res.status_code in (200, 201):
            new_url = res.json().get('source_url')
            print(f"SUCCESS! {name} logo uploaded: {new_url}")
            return new_url
        else:
            print(f"Upload failed for {name}: {res.status_code} {res.text}")
            return None

if __name__ == "__main__":
    results = {}
    for name, path in IMG_FILES.items():
        new_url = upload_local_file(name, path)
        if new_url:
            results[name] = new_url
    
    print("\n--- NEW LOGO URLS ---")
    for name, url in results.items():
        print(f"'{name}': '{url}',")
