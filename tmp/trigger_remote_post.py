import os
import requests
import json

# Modify wp_auto_publisher.py to use "publish" instead of "draft"
path = "wp_auto_publisher.py"
with open(path, "r") as f:
    content = f.read()

# Replace draft with publish
modified = content.replace('"status": "draft"', '"status": "publish"')

print("🚀 Status auf 'publish' gesetzt...")
with open(path, "w") as f:
    f.write(modified)

try:
    print("🤖 Starte KI-Analyse und Publikation...")
    import wp_auto_publisher
    wp_auto_publisher.generate_blog_post()
    print("✅ Prozess abgeschlossen!")
finally:
    # Always revert to draft
    print("🧹 Setze Status zurück auf 'draft'...")
    with open(path, "w") as f:
        f.write(content)
