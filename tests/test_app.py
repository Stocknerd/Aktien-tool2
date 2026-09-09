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


def test_home_exposes_consent_safe_social_attribution_and_analysis_event(client):
    rv = client.get('/?utm_source=instagram&utm_medium=organic_social&utm_campaign=aktien_duell')
    html = rv.get_data(as_text=True)

    assert rv.status_code == 200
    assert 'id="qc-consent-banner"' in html
    assert 'window.s40TrackEvent' in html
    assert "utm_source" in html
    assert 'data-s40-event="analysis_started"' in html
    assert 'data-s40-page="analysis_start"' in html
    assert 'id="stock-search"' in html
    assert 'autocomplete="off" required' in html


def test_compare_and_analysis_result_expose_completion_measurement(client):
    compare = client.get('/', base_url='https://compare.schatzsuche40.de')
    analysis_result = client.get(
        '/result/test.png?ticker=AAPL',
        base_url='https://tool.schatzsuche40.de',
    )
    compare_result = client.get(
        '/compare/result/test.png?t1=AAPL&t2=MSFT',
        base_url='https://compare.schatzsuche40.de',
    )

    assert 'data-s40-event="comparison_started"' in compare.get_data(as_text=True)
    assert 'data-s40-page="comparison_start"' in compare.get_data(as_text=True)
    assert 'data-s40-page="analysis_completed"' in analysis_result.get_data(as_text=True)
    assert 'data-s40-completion-id=""' in analysis_result.get_data(as_text=True)
    assert 'window.s40TrackEvent' in analysis_result.get_data(as_text=True)
    assert 'data-s40-page="comparison_completed"' in compare_result.get_data(as_text=True)
    assert 'data-s40-completion-id=""' in compare_result.get_data(as_text=True)


def test_analysis_completion_marker_is_bound_and_consumed_once(client):
    base_url = 'https://tool.schatzsuche40.de'
    with client.session_transaction(base_url=base_url) as flask_session:
        flask_session['s40_pending_analysis_completed'] = 'AAPL_result.png'

    first = client.get('/result/AAPL_result.png?ticker=AAPL', base_url=base_url)
    refresh = client.get('/result/AAPL_result.png?ticker=AAPL', base_url=base_url)

    assert 'data-s40-completion-id="AAPL_result.png"' in first.get_data(as_text=True)
    assert 'data-s40-completion-id=""' in refresh.get_data(as_text=True)


def test_comparison_completion_marker_is_bound_and_consumed_once(client):
    base_url = 'https://compare.schatzsuche40.de'
    with client.session_transaction(base_url=base_url) as flask_session:
        flask_session['s40_pending_comparison_completed'] = 'COMPARE_AAPL_MSFT.png'

    first = client.get(
        '/compare/result/COMPARE_AAPL_MSFT.png?t1=AAPL&t2=MSFT',
        base_url=base_url,
    )
    refresh = client.get(
        '/compare/result/COMPARE_AAPL_MSFT.png?t1=AAPL&t2=MSFT',
        base_url=base_url,
    )

    assert 'data-s40-completion-id="COMPARE_AAPL_MSFT.png"' in first.get_data(as_text=True)
    assert 'data-s40-completion-id=""' in refresh.get_data(as_text=True)


def test_parallel_analysis_completion_markers_can_be_consumed_in_reverse_order(client):
    base_url = 'https://tool.schatzsuche40.de'
    first_result = 'AAPL_first.png'
    second_result = 'MSFT_second.png'
    with client.session_transaction(base_url=base_url) as flask_session:
        flask_session['s40_pending_analysis_completed'] = [first_result, second_result]

    second = client.get(f'/result/{second_result}?ticker=MSFT', base_url=base_url)
    first = client.get(f'/result/{first_result}?ticker=AAPL', base_url=base_url)
    repeated = client.get(f'/result/{first_result}?ticker=AAPL', base_url=base_url)

    assert f'data-s40-completion-id="{second_result}"' in second.get_data(as_text=True)
    assert f'data-s40-completion-id="{first_result}"' in first.get_data(as_text=True)
    assert 'data-s40-completion-id=""' in repeated.get_data(as_text=True)


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
