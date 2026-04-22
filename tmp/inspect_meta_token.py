import urllib.request
import json

USER_TOKEN = "EAAVGjnfVF0YBRT1y8JjDzv9rB7UgYyS9mJzu0XGwZAUV2nmxDYdWgfQalFIZAp4yvB3yCH4mYsnPb5CdUtEuTEM1dRsEKa8Run1FI2h3fX6lZB87WtwCeYwiyFHJHtqSxMrt74RKok55hCHL5xsCLEPZCCOZBgZCNpP8yypviZBJ4RGVZBaV4XYyRTplzICZCsYy5WhaNTbMFGAZDZD"
META_PAGE_ID = "112395201353218"

url = f"https://graph.facebook.com/v20.0/{META_PAGE_ID}?fields=access_token&access_token={USER_TOKEN}"
req = urllib.request.Request(url)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("PAGE TOKEN:")
        print(data.get("access_token"))
except Exception as e:
    print("Error:", e)
