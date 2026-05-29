import requests, base64

WP_BASE_URL   = "https://schatzsuche40.de/wp-json/wp/v2"
WP_USER       = "schatzsuche40"
WP_PASS       = "R33G PRPb mqee hBGc pvKJ 51iz"

CREDS = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {CREDS}",
    "Content-Type":  "application/json",
}

# 1. Fetch current screener page (ID 1920) with context=edit
response = requests.get(f"{WP_BASE_URL}/pages/1920?context=edit", headers=HEADERS)
page = response.json()
if 'content' not in page or 'raw' not in page['content']:
    print("KEYS:", page.keys())
    if 'message' in page:
        print("API MESSAGE:", page['message'])
    # Try using 'rendered' as a fallback
    current_content = page.get('content', {}).get('rendered', '')
else:
    current_content = page['content']['raw']

print("CURRENT WP CONTENT LENGTH:", len(current_content))

# 2. Define the breakout CSS block
breakout_css = """<!-- wp:html -->
<style>
/* Breakout boxed template for screener page */
.page-id-1920 .container, 
.page-id-1920 .sections_group, 
.page-id-1920 .entry-content,
.page-id-1920 .section_wrapper,
.page-id-1920 .column_attr,
.page-id-1920 .column,
.page-id-1920 .the_content,
.page-id-1920 .the_content_wrapper,
.page-id-1920 .wrap {
    max-width: 100% !important;
    width: 100% !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    margin: 0 !important;
}
#iframe-screener {
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
<!-- /wp:html -->
"""

# Check if breakout_css is already in current_content
if "page-id-1920" in current_content:
    print("Breakout CSS already injected! Updating it...")
    # Clean old styles if any
    import re
    cleaned_content = re.sub(r'<!-- wp:html -->\s*<style>.*?page-id-1920.*?</style>\s*<!-- /wp:html -->', '', current_content, flags=re.DOTALL)
    new_content = breakout_css + cleaned_content
else:
    print("Injecting new breakout CSS...")
    new_content = breakout_css + current_content

# 3. Update the page content back to WordPress!
update_response = requests.post(
    f"{WP_BASE_URL}/pages/1920",
    headers=HEADERS,
    json={"content": new_content}
)

if update_response.status_code == 200:
    print("SUCCESS: Screener full-width breakout CSS successfully injected and updated on WordPress!")
else:
    print("FAILED TO UPDATE PAGE:", update_response.status_code, update_response.text)
