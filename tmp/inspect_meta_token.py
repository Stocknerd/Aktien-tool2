import requests

TOKEN = "EAA8x4HLPSKMBRLIdHroILuQNdFNZATupwypkc6PykgJJO18aJAZCKraPrW1aZCCiXazmH1kYRZANfT1mcpA722PaifrKibWG0TywWG9hZB3vggMdzvqSiXVkkaKPpvUPKLbmWkxartlvY1YTgGIzhEEbBotEMU5euKJQdQArORS9NWMiZBt0pdOTT5Pf9OwgxhNcZBAWceHBAZDZD"

def inspect_token():
    url = f"https://graph.facebook.com/debug_token?input_token={TOKEN}&access_token={TOKEN}"
    r = requests.get(url)
    print("DEBUG TOKEN:", r.json())

if __name__ == "__main__":
    inspect_token()
