import requests
import pandas as pd
from io import StringIO
import os

def download_msci_world():
    url = "https://www.ishares.com/uk/individual/en/products/251882/ishares-msci-world-ucits-etf-acc-fund/1506575576011.ajax?fileType=csv&fileName=SWDA_holdings&dataType=fund"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"Downloading MSCI World holdings from: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Save raw for inspection
    with open("msci_world_raw.csv", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved raw holdings to msci_world_raw.csv")

if __name__ == "__main__":
    download_msci_world()
