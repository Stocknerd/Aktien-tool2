import os
from dotenv import load_dotenv
load_dotenv()
import requests

TOKEN = os.environ["SCHATZSUCHE_META_ACCESS_TOKEN"]
PAGE_ID = "112395201353218"

def find_insta_id():
    # 1. Try to get instagram_business_account from Page
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=instagram_business_account,name&access_token={TOKEN}"
    r = requests.get(url)
    print("PAGE INFO:", r.json())
    
    # 2. Try to list all instagram accounts for the businesses the user manages
    url_biz = f"https://graph.facebook.com/v20.0/me/adaccounts?fields=instagram_accounts{{id,username}}&access_token={TOKEN}"
    r_biz = requests.get(url_biz)
    print("BIZ INSTA INFO:", r_biz.json())

if __name__ == "__main__":
    find_insta_id()
