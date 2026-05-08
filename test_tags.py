import requests
from requests.auth import HTTPBasicAuth
import json

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/tags"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

def get_or_create_tag(tag_name):
    # First search for it
    search_res = requests.get(f"{WP_URL}?search={tag_name}", auth=HTTPBasicAuth(WP_USER, WP_PASS))
    if search_res.status_code == 200:
        results = search_res.json()
        for tag in results:
            if tag['name'].lower() == tag_name.lower():
                print(f"Found existing tag '{tag_name}' with ID {tag['id']}")
                return tag['id']
                
    # Create if not found
    create_data = {"name": tag_name}
    create_res = requests.post(WP_URL, auth=HTTPBasicAuth(WP_USER, WP_PASS), json=create_data)
    if create_res.status_code == 201:
        tag_id = create_res.json().get('id')
        print(f"Created new tag '{tag_name}' with ID {tag_id}")
        return tag_id
    elif create_res.status_code == 400:
        # Term already exists
        err = create_res.json()
        if err.get('code') == 'term_exists':
             tag_id = err.get('data', {}).get('term_id')
             print(f"Tag '{tag_name}' existed (term_exists) with ID {tag_id}")
             return tag_id
             
    print(f"Failed to process tag {tag_name}: {create_res.text}")
    return None

if __name__ == "__main__":
    for tag in ["Aktienanalyse", "Dividende", "Börse"]:
        get_or_create_tag(tag)
