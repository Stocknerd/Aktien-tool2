import requests
import os

logos = {
    "mintos": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Mintos_logo.svg", # SVG is safer for quality
    "bondora": "https://upload.wikimedia.org/wikipedia/commons/d/df/Bondora_logo.svg",
    "robocash": "https://p2pempire.com/media/images/robocash-logo.png", # Fallback source
    "twino": "https://www.p2p-banking.com/wp-content/uploads/2016/11/twino_logo.png"
}

os.makedirs("tmp/logos", exist_ok=True)

for name, url in logos.items():
    try:
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code == 200:
            ext = url.split(".")[-1]
            path = f"tmp/logos/{name}.{ext}"
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded {name}")
        else:
            print(f"Failed {name}: {r.status_code}")
    except Exception as e:
        print(f"Error {name}: {e}")
