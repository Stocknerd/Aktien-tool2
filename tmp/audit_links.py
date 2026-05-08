import requests
from bs4 import BeautifulSoup
import re

URLS = [
    "https://schatzsuche40.de/",
    "https://schatzsuche40.de/meine-depots/",
    "https://schatzsuche40.de/geld-anlegen/",
    "https://schatzsuche40.de/wo-aktien-kaufen/"
]

def extract_links():
    results = []
    for url in URLS:
        print(f"Scraping {url}...")
        try:
            r = requests.get(url, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            for l in links:
                href = l['href']
                # Common affiliate patterns
                if any(p in href for p in ["amzn.to", "financeads", "awin", "tradedoubler", "ref=", "affiliate"]):
                    status = "Unknown"
                    try:
                        # Check status (follow redirects)
                        r2 = requests.head(href, allow_redirects=True, timeout=5)
                        status = r2.status_code
                        final_url = r2.url
                    except:
                        status = "Error"
                        final_url = "N/A"
                    
                    results.append({
                        "source": url,
                        "text": l.get_text().strip(),
                        "href": href,
                        "status": status,
                        "final_url": final_url
                    })
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            
    return results

if __name__ == "__main__":
    links = extract_links()
    with open("affiliate_links_audit.md", "w") as f:
        f.write("# Affiliate Link Audit\n\n")
        f.write("| Source | Text | Link | Status | Final URL |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for l in links:
            f.write(f"| {l['source']} | {l['text']} | {l['href']} | {l['status']} | {l['final_url']} |\n")
    print(f"Extracted {len(links)} links. See affiliate_links_audit.md")
