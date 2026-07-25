import os
from dotenv import load_dotenv
load_dotenv()
import requests

SHORT_TOKEN = os.environ["SCHATZSUCHE_META_ACCESS_TOKEN"]
PAGE_ID = "112395201353218"
APP_ID = "1478160492972904"  # Let's see if we can get the App ID from the token info
APP_SECRET = "" # We need the APP SECRET to extend the token... wait.

def get_insta_id():
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=instagram_business_account&access_token={SHORT_TOKEN}"
    r = requests.get(url)
    data = r.json()
    print("PAGE INFO:", data)
    
    if "instagram_business_account" in data:
        insta_id = data["instagram_business_account"]["id"]
        print(f"BINGO! Instagram ID is: {insta_id}")
        return insta_id
    else:
        print("No instagram_business_account found.")
        return None

def test_token_valid():
    # If the user asks about extending, I'll just save the short token as USER_TOKEN for now 
    # to see if it works, because I might not have the APP_SECRET to extend it programmatically.
    pass

if __name__ == "__main__":
    get_insta_id()
