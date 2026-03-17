import pytest
from app import app

@pytest.fixture
def client():
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
