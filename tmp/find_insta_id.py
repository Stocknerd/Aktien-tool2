import requests

TOKEN = "EAA8x4HLPSKMBRFeQmAc6eLAKZCLzyA9lHGrw23ZBBM2CXJWNqEfdxvgpUV0RaJdt5lAGUw4ISt7Q3rzfPTd2uOxGWV2N2Ahotl3nPYOOspS8ygZAOAUmPwASo8WUS7BZCKMg1ZA2BGNavuwBY3ZAmfZBCVWrVgvrisiN4Czuf4bLMmdpegMTHacLiqgrsUjTxM6qYxZCVExZC35U9ZCWZCC8FRI6THtf0taB1yWHQjcYRRK9qPHfBB7dGGLRdN4NYqo7zFq4MBL0Ey4qoqjTNvLyuH1wiikv5qW1dhrpMbZCuQZDZD"
PAGE_ID = "112395201353218"

def find_insta_id():
    # 1. Try to get instagram_business_account from Page
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=instagram_business_account,name&access_token={TOKEN}"
    r = requests.get(url)
    print("PAGE INFO:", r.json())
    
    # 2. Try to list all instagram accounts for the businesses the user manages
    url_biz = f"https://graph.facebook.com/v20.0/me/adaccounts?fields=instagram_accounts{{id,username}}&access_token={TOKEN}"
    r_biz = requests.get(url_biz)
    print("BIZ INSTA INFO:", r_biz.json())

if __name__ == "__main__":
    find_insta_id()
