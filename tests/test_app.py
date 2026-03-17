import pytest
import os
from app import app

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

def test_compare_page(client):
    """Test if the comparison home page loads."""
    rv = client.get('/compare')
    assert rv.status_code == 200
    assert b'Aktien Vergleich' in rv.data
