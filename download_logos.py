"""
Logo Downloader für Aktien-Tool
================================
Lädt Firmenlogos für Unternehmen aus stock_data.csv herunter.

Verbesserungen gegenüber dem Original:
- Angepasst für lokales Windows-System (kein Google Colab)
- Modernere APIs und Methoden
- Besseres Error Handling
- Progress Bar mit tqdm
- Konfigurierbare Quellen
- Automatisches Überspringen bereits vorhandener Logos
- Detailliertes Logging
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================================
# KONFIGURATION
# ================================

# Pfade
SCRIPT_DIR = Path(__file__).parent
CSV_PATH = SCRIPT_DIR / 'stock_data.csv'
OUTPUT_FOLDER = SCRIPT_DIR / 'static' / 'logos'
LOG_FILE = SCRIPT_DIR / 'logs' / 'logo_download.log'

# Download-Einstellungen
SKIP_EXISTING = True  # Vorhandene Logos überspringen
DELAY_BETWEEN_REQUESTS = 1.0  # Sekunden zwischen Anfragen
TIMEOUT = 10  # Timeout für Requests in Sekunden
MAX_RETRIES = 3  # Maximale Anzahl der Wiederholungsversuche

# Wörter, die aus Unternehmensnamen entfernt werden sollen
REMOVE_WORDS = [
    "LTD", "LIMITED", "INC", "INCORPORATED", "CORP", "CORPORATION",
    "SA", "PLC", "CLASS A", "CLASS B", "CLASS C",
    "HOLDINGS", "HOLDING", "GROUP", "CO", "S.A.", "LLC",
    "INTERNATIONAL", "& CO", "N.V.", "AG", "SE", "GMBH",
    "PUBLIC", "COMPANY", "THE", "AND", "OF"
]

# ================================
# LOGGING SETUP
# ================================

LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================================
# HELPER FUNCTIONS
# ================================

def create_session() -> requests.Session:
    """Erstellt eine Session mit Retry-Logik."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Standard Headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    return session


def clean_company_name(name: str) -> str:
    """
    Bereinigt Unternehmensnamen durch Entfernen unnötiger Zusätze.
    
    Args:
        name: Ursprünglicher Unternehmensname
        
    Returns:
        Bereinigter Name
    """
    if pd.isna(name):
        return ""
    
    name = str(name).upper()
    
    # Entferne gefundene Wörter
    for word in REMOVE_WORDS:
        name = re.sub(rf'\b{word}\b', '', name, flags=re.IGNORECASE)
    
    # Entferne doppelte Leerzeichen und trimme
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name.title()


def get_logo_from_clearbit(symbol: str, company_name: str, session: requests.Session) -> Optional[str]:
    """
    Versucht, das Logo von Clearbit zu beziehen.
    Clearbit bietet eine einfache API für Firmenlogos.
    
    Args:
        symbol: Ticker-Symbol
        company_name: Unternehmensname
        session: Requests Session
        
    Returns:
        Logo URL oder None
    """
    # Versuche verschiedene Domain-Varianten
    potential_domains = [
        f"{company_name.lower().replace(' ', '')}.com",
        f"{symbol.lower()}.com",
    ]
    
    for domain in potential_domains:
        try:
            logo_url = f'https://logo.clearbit.com/{domain}'
            response = session.head(logo_url, timeout=TIMEOUT, allow_redirects=True)
            
            if response.status_code == 200:
                logger.debug(f"Clearbit: Logo gefunden für {domain}")
                return logo_url
        except Exception as e:
            logger.debug(f"Clearbit: Fehler bei {domain}: {e}")
            continue
    
    return None


def get_logo_from_wikipedia(company_name: str, session: requests.Session) -> Optional[str]:
    """
    Findet das Logo über Wikipedia.
    
    Args:
        company_name: Unternehmensname
        session: Requests Session
        
    Returns:
        Logo URL oder None
    """
    try:
        # Wikipedia API Suche
        search_url = (
            f'https://en.wikipedia.org/w/api.php?'
            f'action=query&list=search&srsearch={urllib.parse.quote(company_name)}'
            f'&format=json&srlimit=3'
        )
        
        response = session.get(search_url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        if 'query' not in data or 'search' not in data['query']:
            return None
        
        # Versuche die ersten Treffer
        for result in data['query']['search'][:3]:
            page_title = result['title']
            wiki_url = f'https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title)}'
            
            try:
                page_response = session.get(wiki_url, timeout=TIMEOUT)
                page_response.raise_for_status()
                
                soup = BeautifulSoup(page_response.text, 'html.parser')
                
                # Suche in der Infobox
                infobox = soup.find('table', class_=lambda x: x and 'infobox' in x)
                if infobox:
                    img_tag = infobox.find('img')
                    if img_tag and 'src' in img_tag.attrs:
                        logo_url = 'https:' + img_tag['src']
                        
                        # Filtere keine echten Logos (z.B. Flaggen, Icons)
                        if any(x in logo_url.lower() for x in ['logo', 'wordmark']):
                            logger.debug(f"Wikipedia: Logo gefunden für {page_title}")
                            return logo_url
                        
            except Exception as e:
                logger.debug(f"Wikipedia: Fehler bei Seite {page_title}: {e}")
                continue
        
    except Exception as e:
        logger.debug(f"Wikipedia: Fehler bei {company_name}: {e}")
    
    return None


def get_logo_from_yahoo_finance(symbol: str, session: requests.Session) -> Optional[str]:
    """
    Versucht, das Logo von Yahoo Finance zu beziehen.
    
    Args:
        symbol: Ticker-Symbol
        session: Requests Session
        
    Returns:
        Logo URL oder None
    """
    try:
        # Yahoo Finance verwendet ein CDN für Logos
        # Format: https://s.yimg.com/cv/apiv2/default/logos/{symbol}.png
        logo_url = f"https://s.yimg.com/cv/apiv2/default/logos/{symbol}.png"
        
        response = session.head(logo_url, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            logger.debug(f"Yahoo Finance: Logo gefunden für {symbol}")
            return logo_url
            
    except Exception as e:
        logger.debug(f"Yahoo Finance: Fehler bei {symbol}: {e}")
    
    return None


def get_logo_from_companieslogo(company_name: str, session: requests.Session) -> Optional[str]:
    """
    Versucht, das Logo von companieslogo.com zu beziehen.
    
    Args:
        company_name: Unternehmensname
        session: Requests Session
        
    Returns:
        Logo URL oder None
    """
    try:
        # Einfache Suche nach Firmennamen
        search_name = company_name.lower().replace(' ', '-')
        logo_url = f"https://companieslogo.com/img/orig/{search_name}.png"
        
        response = session.head(logo_url, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            logger.debug(f"CompaniesLogo: Logo gefunden für {company_name}")
            return logo_url
            
    except Exception as e:
        logger.debug(f"CompaniesLogo: Fehler bei {company_name}: {e}")
    
    return None


def download_logo(
    company_name: str,
    symbol: str,
    output_folder: Path,
    session: requests.Session,
    skip_existing: bool = True
) -> Dict[str, any]:
    """
    Lädt das Logo für ein Unternehmen herunter.
    
    Args:
        company_name: Name des Unternehmens
        symbol: Ticker-Symbol
        output_folder: Zielordner für Logos
        session: Requests Session
        skip_existing: Vorhandene Logos überspringen
        
    Returns:
        Dictionary mit Ergebnis (success, source, message)
    """
    # Prüfe, ob bereits vorhanden
    output_file = output_folder / f"{symbol}.png"
    if skip_existing and output_file.exists():
        return {
            'success': True,
            'source': 'existing',
            'message': 'Logo bereits vorhanden'
        }
    
    clean_name = clean_company_name(company_name)
    
    # Versuche verschiedene Quellen in Reihenfolge
    sources = [
        # ('Clearbit', lambda: get_logo_from_clearbit(symbol, clean_name, session)),
        ('Yahoo Finance', lambda: get_logo_from_yahoo_finance(symbol, session)),
        ('Wikipedia', lambda: get_logo_from_wikipedia(clean_name, session)),
        ('CompaniesLogo', lambda: get_logo_from_companieslogo(clean_name, session)),
    ]
    
    for source_name, get_logo_func in sources:
        try:
            logo_url = get_logo_func()
            
            if logo_url:
                # Download des Logos
                response = session.get(logo_url, timeout=TIMEOUT, stream=True)
                response.raise_for_status()
                
                # Speichere das Logo
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"✓ {symbol}: Logo von {source_name} heruntergeladen")
                return {
                    'success': True,
                    'source': source_name,
                    'message': f'Logo von {source_name} heruntergeladen'
                }
                
        except Exception as e:
            logger.debug(f"{source_name}: Fehler für {symbol}: {e}")
            continue
    
    # Kein Logo gefunden
    logger.warning(f"✗ {symbol} ({company_name}): Kein Logo gefunden")
    return {
        'success': False,
        'source': None,
        'message': 'Kein Logo in allen Quellen gefunden'
    }


# ================================
# MAIN FUNCTION
# ================================

def main():
    """Hauptfunktion zum Herunterladen der Logos."""
    
    logger.info("=" * 60)
    logger.info("Logo Downloader gestartet")
    logger.info("=" * 60)
    
    # Prüfe CSV-Datei
    if not CSV_PATH.exists():
        logger.error(f"CSV-Datei nicht gefunden: {CSV_PATH}")
        return
    
    # Erstelle Ausgabeordner
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Lade CSV
    logger.info(f"Lade Daten aus {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    
    # Prüfe erforderliche Spalten
    required_columns = ['Symbol', 'Langname']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        logger.error(f"Fehlende Spalten in CSV: {missing_columns}")
        return
    
    # Filtere NaN-Werte
    df = df.dropna(subset=['Symbol'])
    
    total_companies = len(df)
    logger.info(f"Gefunden: {total_companies} Unternehmen")
    
    # Erstelle Session
    session = create_session()
    
    # Statistiken
    stats = {
        'total': total_companies,
        'success': 0,
        'existing': 0,
        'failed': 0,
        'by_source': {}
    }
    
    failed_companies = []
    
    # Verarbeite alle Unternehmen
    logger.info(f"\nStarte Download (SKIP_EXISTING={SKIP_EXISTING})...\n")
    
    for _, row in tqdm(df.iterrows(), total=total_companies, desc="Logos herunterladen"):
        symbol = str(row['Symbol']).strip()
        company_name = str(row.get('Langname', row.get('Security', symbol)))
        
        result = download_logo(
            company_name=company_name,
            symbol=symbol,
            output_folder=OUTPUT_FOLDER,
            session=session,
            skip_existing=SKIP_EXISTING
        )
        
        if result['success']:
            stats['success'] += 1
            if result['source'] == 'existing':
                stats['existing'] += 1
            else:
                source = result['source']
                stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
        else:
            stats['failed'] += 1
            failed_companies.append({
                'Symbol': symbol,
                'Langname': company_name
            })
        
        # Verzögerung nur bei echten Anfragen, um Rate Limits einzuhalten
        if result['source'] != 'existing':
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Ausgabe der Ergebnisse
    logger.info("\n" + "=" * 60)
    logger.info("ZUSAMMENFASSUNG")
    logger.info("=" * 60)
    logger.info(f"Gesamt:              {stats['total']}")
    logger.info(f"Erfolgreich:         {stats['success']}")
    logger.info(f"  - Bereits vorhanden: {stats['existing']}")
    logger.info(f"  - Neu heruntergeladen: {stats['success'] - stats['existing']}")
    logger.info(f"Fehlgeschlagen:      {stats['failed']}")
    logger.info("")
    
    if stats['by_source']:
        logger.info("Downloads nach Quelle:")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {source}: {count}")
    
    # Speichere fehlgeschlagene Unternehmen
    if failed_companies:
        failed_file = SCRIPT_DIR / 'logos_failed.csv'
        failed_df = pd.DataFrame(failed_companies)
        failed_df.to_csv(failed_file, index=False, encoding='utf-8-sig')
        logger.info(f"\nFehlgeschlagene Downloads gespeichert in: {failed_file}")
        logger.info(f"Anzahl: {len(failed_companies)}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Logo Download abgeschlossen!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
