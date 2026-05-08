import os

config_path = "/etc/nginx/sites-enabled/compare"
with open(config_path, 'r') as f:
    content = f.read()

# Comprehensive CSP Update
csp_line = ""
for line in content.splitlines():
    if "add_header Content-Security-Policy" in line:
        csp_line = line
        break

if csp_line:
    new_csp = csp_line
    # Add script-src CDNs
    if "script-src 'self'" in new_csp and "https://cdn.jsdelivr.net" not in new_csp:
        new_csp = new_csp.replace("script-src 'self'", "script-src 'self' https://cdn.jsdelivr.net")
    
    # Add style-src CDNs
    if "style-src 'self'" in new_csp and "https://cdn.jsdelivr.net" not in new_csp:
        new_csp = new_csp.replace("style-src 'self'", "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com")
    
    # Add font-src CDNs
    if "font-src 'self'" in new_csp and "https://fonts.gstatic.com" not in new_csp:
        new_csp = new_csp.replace("font-src 'self' data:", "font-src 'self' data: https://fonts.gstatic.com https://fonts.googleapis.com")

    content = content.replace(csp_line, new_csp)

with open("/tmp/compare_nginx_v2", 'w') as f:
    f.write(content)

print("Modified config written to /tmp/compare_nginx_v2")
