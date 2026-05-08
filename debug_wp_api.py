import requests
from requests.auth import HTTPBasicAuth
import json

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def debug_post():
    data = {
        "title": "API Debug Test - Please ignore",
        "content": "Testing Excerpt, Tags, and Featured Image assignment.",
        "excerpt": "This is a test excerpt that should appear in SEO.",
        "status": "draft",
        "tags": [13, 23], # ETF and European Stocks
        "categories": [5],
        "meta": {
            "prosodia_vgw_os_pzm_method": "automatic"
        }
    }
    
    print("Creating debug post...")
    response = requests.post(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json=data, headers={'Content-Type': 'application/json'})
    
    if response.status_code == 201:
        res_json = response.json()
        print(f"Success! Created Post ID: {res_json.get('id')}")
        print(f"Tags in response: {res_json.get('tags')}")
        print(f"Excerpt in response: {res_json.get('excerpt')}")
        print(f"Categories in response: {res_json.get('categories')}")
        # Check if fields are actually set
        if not res_json.get('tags'):
            print("WARNING: Tags were NOT set.")
        if not res_json.get('excerpt', {}).get('raw') and not res_json.get('excerpt', {}).get('rendered'):
             print("WARNING: Excerpt might be empty.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    debug_post()
