import requests
import base64

WP_USER = "schatzsuche40"
WP_APP_PASS = "Pm8T ZqbK 8Muk FgkC kBB0 UIN4"
BASE = "https://schatzsuche40.de/wp-json/wp/v2"

creds = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {creds}",
    "Content-Type": "application/json",
}

BUCHTIPPS_HTML = """<!-- wp:html -->
<style>
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin: 40px 0;
}
.book-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  transition: transform 0.3s ease;
}
.book-card:hover {
  transform: translateY(-5px);
  border-color: #6366f1;
}
.book-card img {
  max-width: 150px;
  height: auto;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}
.book-title {
  color: #fff !important;
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 10px;
}
.book-author {
  color: #94a3b8;
  font-size: 0.9rem;
  margin-bottom: 20px;
}
.book-cta {
  display: inline-block;
  background: #ff9900;
  color: #000 !important;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 700;
  text-decoration: none !important;
}
</style>

<div class="book-grid">
  <!-- Book 1 -->
  <div class="book-card">
    <img src="https://m.media-amazon.com/images/I/81L8q1vW-pL._SL1500_.jpg" alt="The Intelligent Investor">
    <div class="book-title">The Intelligent Investor</div>
    <div class="book-author">Benjamin Graham</div>
    <a href="https://www.amazon.de/dp/0060555661?tag=schatzsuch0c4-21" class="book-cta" target="_blank">Bei Amazon ansehen</a>
  </div>

  <!-- Book 2 -->
  <div class="book-card">
    <img src="https://m.media-amazon.com/images/I/81bsw6fnUiL._SL1500_.jpg" alt="Rich Dad Poor Dad">
    <div class="book-title">Rich Dad Poor Dad</div>
    <div class="book-author">Robert T. Kiyosaki</div>
    <a href="https://www.amazon.de/dp/1612680194?tag=schatzsuch0c4-21" class="book-cta" target="_blank">Bei Amazon ansehen</a>
  </div>

  <!-- Book 3 -->
  <div class="book-card">
    <img src="https://m.media-amazon.com/images/I/41D9K+Cq0oL.jpg" alt="Die Kunst über Geld nachzudenken">
    <div class="book-title">Die Kunst über Geld nachzudenken</div>
    <div class="book-author">André Kostolany</div>
    <a href="https://www.amazon.de/dp/3548359544?tag=schatzsuch0c4-21" class="book-cta" target="_blank">Bei Amazon ansehen</a>
  </div>
</div>
<!-- /wp:html -->"""

def create_page():
    payload = {
        "title": "Buchtipps",
        "content": BUCHTIPPS_HTML,
        "status": "publish",
        "slug": "buchtipps"
    }
    r = requests.post(f"{BASE}/pages", headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print(f"SUCCESS! Page created: {r.json().get('link')}")
    else:
        print(f"FAILED: {r.status_code} {r.text}")

if __name__ == "__main__":
    create_page()
