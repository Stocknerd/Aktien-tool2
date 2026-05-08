import requests

USER_TOKEN = "EAA8x4HLPSKMBRLIdHroILuQNdFNZATupwypkc6PykgJJO18aJAZCKraPrW1aZCCiXazmH1kYRZANfT1mcpA722PaifrKibWG0TywWG9hZB3vggMdzvqSiXVkkaKPpvUPKLbmWkxartlvY1YTgGIzhEEbBotEMU5euKJQdQArORS9NWMiZBt0pdOTT5Pf9OwgxhNcZBAWceHBAZDZD"

def check_token_perms():
    url = f"https://graph.facebook.com/v20.0/me/permissions?access_token={USER_TOKEN}"
    r = requests.get(url)
    data = r.json()
    print("TOKEN PERMISSIONS:", data)

if __name__ == "__main__":
    check_token_perms()
