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
            f.write("SIE.DE,Siemens AG,18.4,0.026,2026-03-17\n")
            
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


@pytest.mark.parametrize(
    ("path", "page_name"),
    [
        ("/screener", "screener"),
        ("/dividenden-kalender", "dividend_calendar"),
        ("/dividend-rechner", "dividend_calculator"),
        ("/watchlist", "watchlist"),
        ("/p2p", "p2p_dashboard"),
    ],
)
def test_secondary_tool_pages_have_consent_safe_traffic_measurement(client, path, page_name):
    response = client.get(
        f"{path}?utm_source=social&utm_medium=organic_social&utm_campaign=weekly_growth",
        base_url="https://tool.schatzsuche40.de",
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'data-s40-page="{page_name}"' in html
    assert 'data-embedded="0"' in html
    assert 'id="qc-consent-banner"' in html
    assert 'window.s40TrackEvent' in html
    assert "utm_source" in html


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


def test_compare_host_keeps_search_endpoints_same_origin(client):
    """Autocomplete must not cross the compare/tool origin boundary."""
    search_all = client.get(
        '/api/search-all', base_url='https://compare.schatzsuche40.de'
    )
    legacy_search = client.get(
        '/search?q=AAPL', base_url='https://compare.schatzsuche40.de'
    )
    unrelated_tool = client.get(
        '/screener', base_url='https://compare.schatzsuche40.de'
    )

    assert search_all.status_code == 200
    assert search_all.is_json
    assert legacy_search.status_code == 200
    assert legacy_search.is_json
    assert unrelated_tool.status_code == 301
    assert unrelated_tool.headers['Location'] == 'https://tool.schatzsuche40.de/screener'


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
    assert 'AAPL) Aktie: Analyse, KGV, Dividende & Kursziel | Schatzsuche 4.0</title>' in html


def test_stock_landing_direct_ssr_and_24h_cache(client, monkeypatch):
    import core
    # 1. First request to /analyse/SIE.DE renders 200 OK with cached image, table, h1, and canonical
    rv1 = client.get('/analyse/SIE.DE', base_url='https://tool.schatzsuche40.de')
    assert rv1.status_code == 200
    html1 = rv1.get_data(as_text=True)
    assert '<link rel="canonical" href="https://tool.schatzsuche40.de/analyse/SIE.DE" />' in html1
    assert 'cache_SIE.DE_' in html1
    assert '<h1' in html1
    assert 'Aktienanalyse & Fundamentaldaten</h1>' in html1
    assert '<table' in html1
    assert 'KGV (aktuell)' in html1
    assert '/analyse/SIE.DE?edit=1' in html1
    assert 'X-Robots-Tag' not in rv1.headers

    # 2. Second request to /analyse/SIE.DE uses the 24h image cache without calling render_stock_card
    render_calls = []
    orig_render = core.render_stock_card
    monkeypatch.setattr(core, 'render_stock_card', lambda *a, **kw: render_calls.append(1) or orig_render(*a, **kw))

    rv2 = client.get('/analyse/SIE.DE', base_url='https://tool.schatzsuche40.de')
    assert rv2.status_code == 200
    assert len(render_calls) == 0

    # 3. GET /analyse/SIE.DE?edit=1 opens the configurator (index.html)
    rv_edit = client.get('/analyse/SIE.DE?edit=1', base_url='https://tool.schatzsuche40.de')
    assert rv_edit.status_code == 200
    html_edit = rv_edit.get_data(as_text=True)
    assert 'id="mainForm"' in html_edit
    assert 'value="SIE.DE"' in html_edit

    # 4. GET /result/... sets X-Robots-Tag: noindex, follow
    rv_res = client.get('/result/test.png?ticker=SIE.DE', base_url='https://tool.schatzsuche40.de')
    assert rv_res.status_code == 200
    assert rv_res.headers.get('X-Robots-Tag') == 'noindex, follow'


def test_robots_txt_rules_and_sitemaps(client):
    tool_robots = client.get('/robots.txt', base_url='https://tool.schatzsuche40.de')
    assert tool_robots.status_code == 200
    tool_text = tool_robots.get_data(as_text=True)
    assert 'Disallow: /result/' in tool_text
    assert 'Disallow: /*?embed=1' in tool_text
    assert 'Sitemap: https://tool.schatzsuche40.de/sitemap.xml' in tool_text
    assert 'Sitemap: https://schatzsuche40.de/sitemap_index.xml' in tool_text

    compare_robots = client.get('/robots.txt', base_url='https://compare.schatzsuche40.de')
    assert compare_robots.status_code == 200
    comp_text = compare_robots.get_data(as_text=True)
    assert 'Disallow: /*?embed=1' in comp_text
    assert 'Sitemap: https://compare.schatzsuche40.de/sitemap.xml' in comp_text
    assert 'Sitemap: https://schatzsuche40.de/sitemap_index.xml' in comp_text


def test_google_verification_endpoint(client):
    tool_resp = client.get('/googlef3be5002fc1d35b1.html', base_url='https://tool.schatzsuche40.de')
    assert tool_resp.status_code == 200
    assert tool_resp.content_type.startswith('text/html')
    assert 'google-site-verification: googlef3be5002fc1d35b1.html' in tool_resp.get_data(as_text=True)

    comp_resp = client.get('/googlef3be5002fc1d35b1.html', base_url='https://compare.schatzsuche40.de')
    assert comp_resp.status_code == 200
    assert comp_resp.content_type.startswith('text/html')
    assert 'google-site-verification: googlef3be5002fc1d35b1.html' in comp_resp.get_data(as_text=True)


def test_contextual_broker_recommendations_and_branding(client):
    import inspect
    import core
    from app import get_broker_recommendation

    de_rec = get_broker_recommendation('SIE.DE', 'Siemens', 'EUR')
    assert de_rec['primary']['name'] == 'Scalable Capital'
    assert '0 € Sparplan für Siemens' in de_rec['primary']['headline']
    assert de_rec['primary']['button_text'] == 'Depot eröffnen & Sparplan starten *'
    assert de_rec['secondary']['name'] == 'Consorsbank'
    assert de_rec['secondary']['button_text'] == '50 € Prämie & Sparplan-Angebot *'

    us_rec = get_broker_recommendation('AAPL', 'Apple', 'USD')
    assert us_rec['primary']['name'] == 'CapTrader'
    assert 'Günstig weltweit & US-Optionen für Apple handeln' in us_rec['primary']['headline']
    assert us_rec['primary']['button_text'] == 'Zu CapTrader *'
    assert us_rec['secondary']['name'] == 'Scalable Capital'

    sig = inspect.signature(core._draw_watermark)
    assert sig.parameters['text'].default == 'schatzsuche40.de | Kostenlose Aktienanalyse & Screener'


def test_llms_txt_and_ai_crawler_robots(client):
    for host in ('https://tool.schatzsuche40.de', 'https://compare.schatzsuche40.de'):
        resp = client.get('/llms.txt', base_url=host)
        assert resp.status_code == 200
        assert 'text/markdown' in resp.headers.get('Content-Type', '')
        body = resp.get_data(as_text=True)
        assert '# Schatzsuche 4.0 - Finanztools & Fundamentalanalyse' in body
        assert 'https://tool.schatzsuche40.de/analyse/<TICKER>' in body
        assert 'https://compare.schatzsuche40.de/' in body

        rob = client.get('/robots.txt', base_url=host).get_data(as_text=True)
        for bot in ('GPTBot', 'OAI-SearchBot', 'PerplexityBot', 'ClaudeBot', 'Google-Extended'):
            assert f'User-agent: {bot}' in rob
        assert 'Allow: /llms.txt' in rob


def test_24h_ai_analysis_cache_prevents_duplicate_llm_calls(client, monkeypatch, tmp_path):
    from types import SimpleNamespace
    import ai_logic

    monkeypatch.setattr(ai_logic, "CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    llm_calls = []

    def fake_create(**kwargs):
        llm_calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Starkes Wachstum bei moderatem KGV."))]
        )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: fake_client)

    # First call hits OpenAI and writes cache/ai_analysis_SIE.DE.json
    res1 = client.get('/api/ai-analysis?ticker=SIE.DE')
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1['cached'] is False
    assert data1['verdict'] == "Starkes Wachstum bei moderatem KGV."
    assert len(llm_calls) == 1
    assert (tmp_path / "ai_analysis_SIE.DE.json").exists()

    # Second call within 24h serves from cache without calling OpenAI
    res2 = client.get('/api/ai-analysis?ticker=SIE.DE')
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2['cached'] is True
    assert data2['verdict'] == "Starkes Wachstum bei moderatem KGV."
    assert len(llm_calls) == 1


def test_rate_limiting_protects_ai_and_post_while_keeping_get_routes_unthrottled(client, monkeypatch):
    from app import app, reset_rate_limits
    import ai_logic

    monkeypatch.setattr(ai_logic, "get_cached_ai_analysis", lambda *a, **kw: "Gecachtes KI-Fazit")
    reset_rate_limits()
    app.config['ENABLE_RATE_LIMIT_IN_TESTS'] = True
    try:
        headers_ai = {'X-Forwarded-For': '198.51.100.42'}
        for _ in range(6):
            r = client.get('/api/ai-analysis?ticker=SIE.DE', headers=headers_ai)
            assert r.status_code == 200

        # 7th request within 1 minute from same IP must return HTTP 429
        r_blocked = client.get('/api/ai-analysis?ticker=SIE.DE', headers=headers_ai)
        assert r_blocked.status_code == 429
        assert "Bitte warte einen kurzen Moment – zu viele Anfragen in kurzer Zeit." in r_blocked.get_json()['error']

        # POST rate limit: 15 allowed per minute per IP, 16th returns HTTP 429
        headers_post = {'X-Forwarded-For': '198.51.100.99'}
        for _ in range(15):
            rp = client.post('/', data={'ticker': ''}, headers=headers_post)
            assert rp.status_code in (200, 302)
        rp_blocked = client.post('/', data={'ticker': ''}, headers=headers_post)
        assert rp_blocked.status_code == 429
        assert "Bitte warte einen kurzen Moment – zu viele Anfragen in kurzer Zeit." in rp_blocked.get_json()['error']

        # Normal GET routes must NEVER be throttled even for a rate-limited IP
        for path in ('/analyse/SIE.DE', '/screener', '/sitemap.xml', '/robots.txt', '/llms.txt'):
            rg = client.get(path, headers=headers_ai, base_url='https://tool.schatzsuche40.de')
            assert rg.status_code == 200
    finally:
        app.config.pop('ENABLE_RATE_LIMIT_IN_TESTS', None)
        reset_rate_limits()
