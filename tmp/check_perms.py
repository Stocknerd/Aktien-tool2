import os
from dotenv import load_dotenv
load_dotenv()
import requests

USER_TOKEN = os.environ["SCHATZSUCHE_META_ACCESS_TOKEN"]
def check_token_perms():
    url = f"https://graph.facebook.com/v20.0/me/permissions?access_token={USER_TOKEN}"
    r = requests.get(url)
    data = r.json()
    print("TOKEN PERMISSIONS:", data)

if __name__ == "__main__":
    check_token_perms()
