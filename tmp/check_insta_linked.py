import requests

TOKEN = "EAA8x4HLPSKMBRFeQmAc6eLAKZCLzyA9lHGrw23ZBBM2CXJWNqEfdxvgpUV0RaJdt5lAGUw4ISt7Q3rzfPTd2uOxGWV2N2Ahotl3nPYOOspS8ygZAOAUmPwASo8WUS7BZCKMg1ZA2BGNavuwBY3ZAmfZBCVWrVgvrisiN4Czuf4bLMmdpegMTHacLiqgrsUjTxM6qYxZCVExZC35U9ZCWZCC8FRI6THtf0taB1yWHQjcYRRK9qPHfBB7dGGLRdN4NYqo7zFq4MBL0Ey4qoqjTNvLyuH1wiikv5qW1dhrpMbZCuQZDZD"
PAGE_ID = "112395201353218"

def check_instagram():
    # 1. Get Page Details to see linked Instagram
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN}"
    r = requests.get(url)
    print("PAGE INSTA:", r.json())

if __name__ == "__main__":
    check_instagram()
