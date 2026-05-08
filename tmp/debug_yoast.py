import requests
from requests.auth import HTTPBasicAuth
import json

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL" # The basic pass

def test_meta_injection():
    # We will create a simple draft post and see if the custom_seo_data does anything
    post_data = {
        "title": "Debug Meta Test",
        "content": "This is a test of Yoast meta injection.",
        "status": "draft",
        "custom_seo_data": {
            "yoast_desc": "This is the Yoast test description.",
            "yoast_kw": "debug, test",
            "prosodia_active": True
        }
    }
    
    print("SENDING payload:")
    print(json.dumps(post_data, indent=2))
    
    r = requests.post(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json=post_data)
    
    print(f"\nSTATUS CODE: {r.status_code}")
    if r.status_code in [200, 201]:
        data = r.json()
        print(f"Post ID: {data.get('id')}")
        # Now fetch it back to see if meta was applied somehow
        # Note: REST API will not return protected meta by default unless registered, but let's see.
        r2 = requests.get(f"{WP_URL}/{data.get('id')}", auth=HTTPBasicAuth(WP_USER, WP_PASS))
        print("Meta returned:", r2.json().get('meta'))
    else:
        print("ERROR:", r.text)

if __name__ == "__main__":
    test_meta_injection()
