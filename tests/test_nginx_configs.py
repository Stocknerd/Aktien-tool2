import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARE_NGINX = ROOT / "configs" / "compare.nginx"
DEPLOY_SCRIPT = ROOT / "deploy.sh"


def _compare_csp_directives():
    config = COMPARE_NGINX.read_text()
    match = re.search(r'add_header Content-Security-Policy "([^"]+)"', config)
    assert match

    directives = {}
    for raw_directive in match.group(1).split(";"):
        tokens = raw_directive.strip().split()
        if tokens:
            directives[tokens[0]] = set(tokens[1:])
    return config, directives


def test_compare_nginx_allows_runtime_dependencies_in_correct_directives():
    config, directives = _compare_csp_directives()

    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "https://www.googletagmanager.com" in directives["script-src"]
    assert "https://s3.tradingview.com" in directives["script-src"]
    assert "https://fonts.googleapis.com" in directives["style-src"]
    assert "https://fonts.gstatic.com" in directives["font-src"]
    assert "https://www.google-analytics.com" in directives["connect-src"]
    assert "https://*.google-analytics.com" in directives["connect-src"]
    assert "https://s.tradingview.com" in directives["frame-src"]
    assert "https://www.tradingview.com" in directives["frame-src"]


def test_compare_nginx_retains_clickjacking_protection():
    _, directives = _compare_csp_directives()

    assert directives["frame-ancestors"] == {
        "'self'",
        "https://schatzsuche40.de",
        "https://*.schatzsuche40.de",
    }


def test_compare_search_api_stays_same_origin():
    _, directives = _compare_csp_directives()

    assert "'self'" in directives["connect-src"]
    assert "https://tool.schatzsuche40.de" not in directives["connect-src"]


def test_deploy_installs_compare_nginx_config():
    script = DEPLOY_SCRIPT.read_text()

    assert 'configs/compare.nginx' in script
    assert 'backup_and_install_nginx_config "compare"' in script
    assert 'available="/etc/nginx/sites-available/$name"' in script
    assert 'if ! sudo nginx -t; then' in script
    assert 'restore_nginx_configs' in script
    assert 'sudo systemctl reload nginx' in script
