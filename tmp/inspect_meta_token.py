import os
from dotenv import load_dotenv
load_dotenv()
import urllib.request
import json

USER_TOKEN = os.environ["SCHATZSUCHE_META_ACCESS_TOKEN"]
META_PAGE_ID = "112395201353218"

url = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}?fields=access_token&access_token={USER_TOKEN}"
req = urllib.request.Request(url)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("PAGE TOKEN:")
        print(data.get("access_token"))
except Exception as e:
    print("Error:", e)
