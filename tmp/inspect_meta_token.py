import requests

TOKEN = "EAA8x4HLPSKMBRFeQmAc6eLAKZCLzyA9lHGrw23ZBBM2CXJWNqEfdxvgpUV0RaJdt5lAGUw4ISt7Q3rzfPTd2uOxGWV2N2Ahotl3nPYOOspS8ygZAOAUmPwASo8WUS7BZCKMg1ZA2BGNavuwBY3ZAmfZBCVWrVgvrisiN4Czuf4bLMmdpegMTHacLiqgrsUjTxM6qYxZCVExZC35U9ZCWZCC8FRI6THtf0taB1yWHQjcYRRK9qPHfBB7dGGLRdN4NYqo7zFq4MBL0Ey4qoqjTNvLyuH1wiikv5qW1dhrpMbZCuQZDZD"

def inspect_token():
    # 1. Check permissions and Page Info
    url = f"https://graph.facebook.com/v20.0/me?fields=id,name,accounts{{id,name,access_token,link,instagram_business_account}}&access_token={TOKEN}"
    r = requests.get(url)
    print("ME INFO:", r.json())
    
    # 2. Check token permissions directly
    url_debug = f"https://graph.facebook.com/debug_token?input_token={TOKEN}&access_token={TOKEN}"
    r_debug = requests.get(url_debug)
    print("DEBUG TOKEN:", r_debug.json())

if __name__ == "__main__":
    inspect_token()
