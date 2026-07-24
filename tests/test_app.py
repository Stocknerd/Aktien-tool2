import pytest
import os
from app import app, build_analysis_title

@pytest.fixture
def client():
    # Ensure a dummy CSV exists for testing if none is present
    if not os.path.exists("stock_data.csv"):
        with open("stock_data.csv", "w", encoding="utf-8") as f:
            f.write("Symbol,Security,KGV,Dividendenrendite,Abfragedatum\n")
            f.write("AAPL,Apple Inc.,30.5,0.005,2026-03-17\n")
            f.write("MSFT,Microsoft Corp.,35.2,0.007,2026-03-17\n")
            
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test if the home page loads correctly."""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Schatzsuche 4.0' in rv.data

def test_search_api(client):
    """Test the search API with a known ticker."""
    rv = client.get('/search?q=AAPL')
    assert rv.status_code == 200
    # Even if AAPL isn't in the CSV, it should return a list
    assert isinstance(rv.get_json(), list)

def test_compare_host_canonical_redirect_and_page(client):
    """Keep comparison content canonical on the dedicated hostname."""
    redirect_response = client.get(
        '/compare', base_url='https://tool.schatzsuche40.de'
    )
    assert redirect_response.status_code == 301
    assert redirect_response.headers['Location'] == 'https://compare.schatzsuche40.de/'

    page_response = client.get('/', base_url='https://compare.schatzsuche40.de')
    assert page_response.status_code == 200
    assert b'Aktien Vergleich' in page_response.data


def test_analysis_title_keeps_brand_for_short_names():
    title = build_analysis_title('Apple Inc.', 'AAPL')
    assert title == 'Apple Inc. (AAPL) - Aktienanalyse | Schatzsuche 4.0'
    assert len(title) <= 60


def test_analysis_title_truncates_long_names_but_keeps_ticker_and_intent():
    title = build_analysis_title('SHENZHEN ENVICOOL TECHNOLOGY LTD A', '002837.SZ')
    assert len(title) <= 60
    assert '(002837.SZ) - Aktienanalyse' in title
    assert title.startswith('SHENZHEN')
    assert '…' in title


def test_stock_landing_renders_bounded_title(client):
    rv = client.get('/analyse/AAPL')
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert '<title>Apple Inc. (AAPL) - Aktienanalyse | Schatzsuche 4.0</title>' in html
