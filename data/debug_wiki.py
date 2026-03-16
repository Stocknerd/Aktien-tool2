import pandas as pd
import requests
from io import StringIO

def get_html(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return StringIO(r.text)
    except Exception as e:
        print(f"Error {url}: {e}")
        return None

urls = {
    "TecDAX": "https://en.wikipedia.org/wiki/TecDAX",
    "Nikkei 225": "https://en.wikipedia.org/wiki/Nikkei_225",
    "Euro Stoxx 50": "https://en.wikipedia.org/wiki/EURO_STOXX_50",
    "CAC 40": "https://en.wikipedia.org/wiki/CAC_40",
    "SMI": "https://en.wikipedia.org/wiki/Swiss_Market_Index"
}

for name, url in urls.items():
    print(f"\n--- {name} ---")
    html = get_html(url)
    if html:
        try:
            tables = pd.read_html(html)
            print(f"Found {len(tables)} tables.")
            for i, t in enumerate(tables):
                # Print first few columns to identify the table
                print(f"Table {i} columns: {t.columns.tolist()}")
                if len(t) > 0:
                    print(f"  Row 0: {t.iloc[0].values.tolist()}")
        except Exception as e:
            print(f"Parse error: {e}")
