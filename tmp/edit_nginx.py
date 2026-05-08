import os

config_path = "/etc/nginx/sites-enabled/compare"
with open(config_path, 'r') as f:
    content = f.read()

# Add CDNs to CSP
if "https://cdn.jsdelivr.net" not in content:
    content = content.replace("style-src 'self' 'unsafe-inline'", "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net")

if "https://fonts.googleapis.com" not in content:
    content = content.replace("font-src 'self' data:", "font-src 'self' data: https://fonts.googleapis.com https://fonts.gstatic.com")

# Also add scripts if needed
if "https://cdn.jsdelivr.net" not in content:
     content = content.replace("script-src 'self'", "script-src 'self' https://cdn.jsdelivr.net")

with open("/tmp/compare_nginx", 'w') as f:
    f.write(content)

print("Modified config written to /tmp/compare_nginx")
