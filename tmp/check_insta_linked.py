import os
from dotenv import load_dotenv
load_dotenv()
import requests

TOKEN = os.environ["SCHATZSUCHE_META_ACCESS_TOKEN"]
PAGE_ID = "112395201353218"

def check_instagram():
    # 1. Get Page Details to see linked Instagram
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN}"
    r = requests.get(url)
    print("PAGE INSTA:", r.json())

if __name__ == "__main__":
    check_instagram()
