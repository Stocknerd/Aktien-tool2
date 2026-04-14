import requests
from requests.auth import HTTPBasicAuth
import json

wp_url = "https://schatzsuche40.de/wp-json/wp/v2/posts"
wp_user = "schatzsuche40"
wp_pass = "VIhSXAT1tAJagL4dR8LJnHWL" # Application Password

post_data = {
    "title": "Automated Test Post by KI-Bot",
    "content": "This is a test post submitted via the <strong>WordPress REST API</strong> using Python and Application Passwords. If you can read this, the integration works perfectly!",
    "status": "draft",  # Important: Draft so it's not live immediately
    "categories": [1] # IDs of categories
}

print("Attempting to post draft to WordPress via REST API...")

response = requests.post(
    wp_url,
    auth=HTTPBasicAuth(wp_user, wp_pass),
    json=post_data,
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 201:
    print("Success! Post created successfully.")
    post_info = response.json()
    print(f"Post ID: {post_info.get('id')}")
    print(f"Post URL: {post_info.get('link')}")
else:
    print(f"Failed with status code: {response.status_code}")
    print(response.text)
