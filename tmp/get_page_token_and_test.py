import requests

USER_TOKEN = "EAA8x4HLPSKMBRLIdHroILuQNdFNZATupwypkc6PykgJJO18aJAZCKraPrW1aZCCiXazmH1kYRZANfT1mcpA722PaifrKibWG0TywWG9hZB3vggMdzvqSiXVkkaKPpvUPKLbmWkxartlvY1YTgGIzhEEbBotEMU5euKJQdQArORS9NWMiZBt0pdOTT5Pf9OwgxhNcZBAWceHBAZDZD"
PAGE_ID = "112395201353218"

def get_page_token():
    # 1. Get Page Details incl. Access Token
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=access_token,name&access_token={USER_TOKEN}"
    r = requests.get(url)
    print("PAGE INFO:", r.json())
    return r.json().get('access_token')

if __name__ == "__main__":
    PAGE_TOKEN = get_page_token()
    if PAGE_TOKEN:
        print("Erfolg! Page Token erhalten:", PAGE_TOKEN[:10] + "...")
        # 2. Try to post with Page Token
        url_post = f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
        params = {
            "caption": "Test Post via Automatisch generiertem Page Token",
            "url": "https://schatzsuche40.de/wp-content/uploads/2026/03/AAPL_analysis.png", # Test with existing image
            "access_token": PAGE_TOKEN
        }
        r_post = requests.post(url_post, data=params)
        print("POST RESULT:", r_post.json())
