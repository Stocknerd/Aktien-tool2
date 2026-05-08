import requests
from requests.auth import HTTPBasicAuth
import json

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts/1764"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def inspect_post():
    response = requests.get(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS))
    if response.status_code == 200:
        data = response.json()
        print("Excerpt:")
        print(data.get("excerpt"))
        print("\nMeta:")
        print(data.get("meta"))
        print("\nYoast Head JSON:")
        y_head = data.get("yoast_head_json", {})
        print("Description:", y_head.get("description", "Not found"))
    else:
        print(f"Failed to fetch post: {response.status_code}")

if __name__ == "__main__":
    inspect_post()
