from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import json
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from src.traffic_metrics import aggregate_metric_totals

CONFIG = Path(os.environ.get(
    'SCHATZSUCHE_ANALYTICS_CONFIG',
    Path.home() / '.config/hermes/analytics/schatzsuche.env',
))
OUT_DIR = Path(os.environ.get(
    'SCHATZSUCHE_TRAFFIC_EXPORT_DIR',
    REPO_ROOT / 'traffic/exports',
))


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            out[key] = value
    return out


def number(value: str):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


cfg = load_env(CONFIG)
creds = service_account.Credentials.from_service_account_file(
    cfg['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=[
        'https://www.googleapis.com/auth/analytics.readonly',
        'https://www.googleapis.com/auth/webmasters.readonly',
    ],
)
session = AuthorizedSession(creds)
property_id = cfg['GA4_PROPERTY_ID']
site_url = cfg['GSC_SITE_URL']


def ga_report(start: date, end: date, metrics: list[str], dimensions: list[str] | None = None,
              limit: int = 10000, dimension_filter: dict | None = None) -> dict:
    dimensions = dimensions or []
    payload: dict = {
        'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
        'metrics': [{'name': name} for name in metrics],
        'dimensions': [{'name': name} for name in dimensions],
        'metricAggregations': ['TOTAL'],
        'limit': str(limit),
        'keepEmptyRows': False,
    }
    if dimension_filter:
        payload['dimensionFilter'] = dimension_filter
    response = session.post(
        f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport',
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    dim_headers = [x['name'] for x in body.get('dimensionHeaders', [])]
    metric_headers = [x['name'] for x in body.get('metricHeaders', [])]
    rows = []
    for row in body.get('rows', []):
        item = {}
        for name, value in zip(dim_headers, row.get('dimensionValues', [])):
            item[name] = value.get('value', '')
        for name, value in zip(metric_headers, row.get('metricValues', [])):
            item[name] = number(value.get('value', '0'))
        rows.append(item)
    provider_totals = {}
    if body.get('totals'):
        for name, value in zip(metric_headers, body['totals'][0].get('metricValues', [])):
            provider_totals[name] = number(value.get('value', '0'))
    totals = aggregate_metric_totals(rows, metric_headers, provider_totals)
    return {'start': start.isoformat(), 'end': end.isoformat(), 'row_count': body.get('rowCount', len(rows)),
            'rows': rows, 'totals': totals}


def gsc_report(start: date, end: date, dimensions: list[str] | None = None,
               row_limit: int = 25000, start_row: int = 0,
               dimension_filter_groups: list[dict] | None = None) -> dict:
    dimensions = dimensions or []
    payload = {
        'startDate': start.isoformat(),
        'endDate': end.isoformat(),
        'dimensions': dimensions,
        'type': 'web',
        'dataState': 'final',
        'rowLimit': row_limit,
        'startRow': start_row,
    }
    if dimension_filter_groups:
        payload['dimensionFilterGroups'] = dimension_filter_groups
    endpoint = (
        'https://www.googleapis.com/webmasters/v3/sites/'
        + quote(site_url, safe='')
        + '/searchAnalytics/query'
    )
    response = session.post(endpoint, json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    rows = []
    for row in body.get('rows', []):
        item = {name: value for name, value in zip(dimensions, row.get('keys', []))}
        for metric in ('clicks', 'impressions', 'ctr', 'position'):
            item[metric] = row.get(metric, 0)
        rows.append(item)
    return {'start': start.isoformat(), 'end': end.isoformat(), 'rows': rows, 'row_count': len(rows),
            'response_aggregation_type': body.get('responseAggregationType')}


def period(end: date, days: int, offset: int = 0) -> tuple[date, date]:
    shifted_end = end - timedelta(days=offset)
    return shifted_end - timedelta(days=days - 1), shifted_end


today = date.today()
ga_end = today - timedelta(days=1)
gsc_end = today - timedelta(days=3)
periods = {
    'ga_current_7': period(ga_end, 7),
    'ga_previous_7': period(ga_end, 7, 7),
    'ga_current_28': period(ga_end, 28),
    'ga_previous_28': period(ga_end, 28, 28),
    'ga_current_90': period(ga_end, 90),
    'gsc_current_7': period(gsc_end, 7),
    'gsc_previous_7': period(gsc_end, 7, 7),
    'gsc_current_28': period(gsc_end, 28),
    'gsc_previous_28': period(gsc_end, 28, 28),
    'gsc_current_90': period(gsc_end, 90),
}

ga_metrics = [
    'totalUsers', 'newUsers', 'sessions', 'engagedSessions', 'engagementRate',
    'screenPageViews', 'screenPageViewsPerSession', 'averageSessionDuration', 'bounceRate',
]
organic_filter = {
    'filter': {
        'fieldName': 'sessionDefaultChannelGroup',
        'stringFilter': {'matchType': 'EXACT', 'value': 'Organic Search', 'caseSensitive': False},
    }
}

export: dict = {
    'generated_at': datetime.now().astimezone().isoformat(),
    'site': site_url,
    'ga4_property_id': property_id,
    'date_policy': {'ga4_end': 'yesterday', 'gsc_end': 'today minus 3 days (final data)'},
    'ga4': {'totals': {}, 'channels_current_28': {}, 'channels_previous_28': {},
            'organic_landing_pages_current_28': {},
            'organic_landing_pages_previous_28': {}, 'daily_current_28': {}},
    'gsc': {'totals': {}, 'queries_current_28': {}, 'queries_previous_28': {},
            'queries_current_90': {}, 'pages_current_28': {}, 'pages_previous_28': {},
            'pages_current_90': {}, 'devices_current_28': {}, 'countries_current_28': {},
            'daily_current_90': {}, 'query_page_current_90': {}, 'target_pages': {}},
}

for key in ('ga_current_7', 'ga_previous_7', 'ga_current_28', 'ga_previous_28', 'ga_current_90'):
    start, end = periods[key]
    export['ga4']['totals'][key.removeprefix('ga_')] = ga_report(start, end, ga_metrics)

start, end = periods['ga_current_28']
prev_start, prev_end = periods['ga_previous_28']
export['ga4']['channels_current_28'] = ga_report(start, end, ga_metrics, ['sessionDefaultChannelGroup'], 100)
export['ga4']['channels_previous_28'] = ga_report(prev_start, prev_end, ga_metrics, ['sessionDefaultChannelGroup'], 100)
export['ga4']['organic_landing_pages_current_28'] = ga_report(
    start, end, ['sessions', 'engagedSessions', 'engagementRate', 'screenPageViews', 'averageSessionDuration'],
    ['landingPagePlusQueryString'], 500, organic_filter)
export['ga4']['organic_landing_pages_previous_28'] = ga_report(
    prev_start, prev_end, ['sessions', 'engagedSessions', 'engagementRate', 'screenPageViews', 'averageSessionDuration'],
    ['landingPagePlusQueryString'], 500, organic_filter)
export['ga4']['daily_current_28'] = ga_report(start, end, ['sessions', 'totalUsers', 'screenPageViews'], ['date'], 100)

for key in ('gsc_current_7', 'gsc_previous_7', 'gsc_current_28', 'gsc_previous_28', 'gsc_current_90'):
    start, end = periods[key]
    export['gsc']['totals'][key.removeprefix('gsc_')] = gsc_report(start, end)

start28, end28 = periods['gsc_current_28']
prev_start28, prev_end28 = periods['gsc_previous_28']
start90, end90 = periods['gsc_current_90']
export['gsc']['queries_current_28'] = gsc_report(start28, end28, ['query'])
export['gsc']['queries_previous_28'] = gsc_report(prev_start28, prev_end28, ['query'])
export['gsc']['queries_current_90'] = gsc_report(start90, end90, ['query'])
export['gsc']['pages_current_28'] = gsc_report(start28, end28, ['page'])
export['gsc']['pages_previous_28'] = gsc_report(prev_start28, prev_end28, ['page'])
export['gsc']['pages_current_90'] = gsc_report(start90, end90, ['page'])
export['gsc']['devices_current_28'] = gsc_report(start28, end28, ['device'])
export['gsc']['countries_current_28'] = gsc_report(start28, end28, ['country'])
export['gsc']['daily_current_90'] = gsc_report(start90, end90, ['date'])
export['gsc']['query_page_current_90'] = gsc_report(start90, end90, ['query', 'page'])

target_pages = {
    'homepage': 'https://schatzsuche40.de/',
    'p2p_platforms': 'https://schatzsuche40.de/die-besten-plattformen/',
    'dividend_growth': 'https://schatzsuche40.de/dividendenwachstum-strategie-guide/',
    'value_investing': 'https://schatzsuche40.de/wie-finde-ich-unterbewertete-aktien-ein-value-investing-leitfaden/',
}
for target_name, target_url in target_pages.items():
    page_filter = [{'groupType': 'and', 'filters': [{
        'dimension': 'page', 'operator': 'equals', 'expression': target_url,
    }]}]
    export['gsc']['target_pages'][target_name] = {
        'url': target_url,
        'current_7': gsc_report(*periods['gsc_current_7'], dimension_filter_groups=page_filter),
        'previous_7': gsc_report(*periods['gsc_previous_7'], dimension_filter_groups=page_filter),
        'current_28': gsc_report(start28, end28, dimension_filter_groups=page_filter),
        'previous_28': gsc_report(prev_start28, prev_end28, dimension_filter_groups=page_filter),
        'current_90': gsc_report(start90, end90, dimension_filter_groups=page_filter),
    }

# Derived query cannibalization candidates: multiple URLs with meaningful evidence.
by_query: dict[str, dict] = defaultdict(lambda: {'pages': set(), 'clicks': 0.0, 'impressions': 0.0})
for row in export['gsc']['query_page_current_90']['rows']:
    q = row.get('query', '')
    by_query[q]['pages'].add(row.get('page', ''))
    by_query[q]['clicks'] += row.get('clicks', 0)
    by_query[q]['impressions'] += row.get('impressions', 0)
candidates = []
for query, value in by_query.items():
    if len(value['pages']) > 1 and value['impressions'] >= 5:
        candidates.append({
            'query': query,
            'page_count': len(value['pages']),
            'pages': sorted(value['pages']),
            'clicks': value['clicks'],
            'impressions': value['impressions'],
        })
export['derived'] = {'cannibalization_candidates_90': sorted(candidates, key=lambda x: (-x['impressions'], x['query']))}


missing_ga4_totals = []
for report_name, report in export['ga4']['totals'].items():
    if not report.get('totals'):
        missing_ga4_totals.append(f'totals.{report_name}')
for report_name, report in export['ga4'].items():
    if report_name != 'totals' and not report.get('totals'):
        missing_ga4_totals.append(report_name)
if missing_ga4_totals:
    raise RuntimeError(
        'GA4 export incomplete; missing provider totals for: '
        + ', '.join(sorted(missing_ga4_totals))
    )

OUT_DIR.mkdir(parents=True, exist_ok=True)
out_path = OUT_DIR / f'TRAFFIC_EXPORT_{today.isoformat()}.json'
out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('export_path=' + str(out_path))
print('export_bytes=' + str(out_path.stat().st_size))
for source in ('ga4', 'gsc'):
    print(source + '_success=true')
