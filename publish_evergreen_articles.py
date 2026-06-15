import os
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

WP_URL = "https://schatzsuche40.de/wp-json/wp/v2/posts"
WP_USER = "schatzsuche40"
WP_PASS = "VIhSXAT1tAJagL4dR8LJnHWL"

EVERGREEN_ARTICLES = [
    {
        "title": "Was ist das KGV? – Einfach erklärt für Anfänger",
        "topic": "Das Kurs-Gewinn-Verhältnis (KGV) verstehen, berechnen und interpretieren. Grenzen des KGV und wie man es im Aktien-Screener nutzt.",
        "internal_link": "https://tool.schatzsuche40.de/screener",
        "link_text": "Aktien-Screener"
    },
    {
        "title": "Dividendenrendite verstehen & berechnen: Der ultimative Guide",
        "topic": "Was ist die Dividendenrendite? Wie berechnet man sie? Was ist der Unterschied zwischen Dividendenhöhe und Rendite? Achtung vor Dividendenfallen.",
        "internal_link": "https://tool.schatzsuche40.de/dividenden-kalender",
        "link_text": "Dividenden-Kalender"
    },
    {
        "title": "Die 5 wichtigsten Kennzahlen für die Aktienanalyse",
        "topic": "Vorstellung der 5 Kern-Kennzahlen für Privatanleger: KGV, Dividendenrendite, Eigenkapitalrendite, EBIT-Marge und Verschuldungsgrad.",
        "internal_link": "https://tool.schatzsuche40.de/",
        "link_text": "Aktien-Analyse Tool"
    },
    {
        "title": "ETF vs. Einzelaktien – Was passt am besten zu dir?",
        "topic": "Vergleich zwischen ETFs (breite Diversifikation) und Einzelaktien (Stock Picking). Vor- und Nachteile sowie strategische Ratschläge.",
        "internal_link": "https://tool.schatzsuche40.de/compare",
        "link_text": "Aktien-Vergleichstool"
    },
    {
        "title": "Wie finde ich unterbewertete Aktien? Ein Value-Investing-Leitfaden",
        "topic": "Einführung in das Value Investing (nach Benjamin Graham und Warren Buffett). Sicherheitsmarge (Margin of Safety) und Kennzahlen zur Identifizierung unterbewerteter Aktien.",
        "internal_link": "https://tool.schatzsuche40.de/screener",
        "link_text": "Aktien-Screener"
    },
    {
        "title": "Was bedeuten KUV, KBV & PEG? Das große Kennzahlen-Glossar",
        "topic": "Verständliche Erklärung fortgeschrittener Kennzahlen: Kurs-Umsatz-Verhältnis (KUV), Kurs-Buchwert-Verhältnis (KBV) und Price-to-Earnings-to-Growth (PEG).",
        "internal_link": "https://tool.schatzsuche40.de/",
        "link_text": "Aktien-Tool Homepage"
    }
]

def generate_article_content(client, title, topic, internal_link, link_text):
    print(f"Generating content for: {title}...")
    prompt = f"""
    Schreibe einen ausführlichen, umfassenden und SEO-optimierten Ratgeber-Artikel auf Deutsch mit dem Titel: "{title}".
    
    Thema und Inhalt:
    {topic}
    
    WICHTIGE ANWEISUNGEN:
    1. Der Artikel muss professionell, verständlich und extrem hilfreich für Privatanleger und Anfänger sein.
    2. Verwende eine klare Struktur mit Überschriften (H2 und H3).
    3. Baue an passenden Stellen HTML-Aufzählungslisten (ul/li) oder eine informative HTML-Tabelle ein.
    4. Integriere einen internen Link zu unserem Tool: <a href="{internal_link}">{link_text}</a>. Der Link muss natürlich und sinnvoll im Text eingebettet sein.
    5. Gib praktische Tipps, wie man diese Theorie im Alltag bei der Aktienanalyse anwendet.
    6. Formatiere den gesamten Text in reinem WordPress-kompatiblen HTML (nutze nur <p>, <h2>, <h3>, <ul>, <li>, <strong>, <em>, <table>, <tr>, <td>, <th>, <a>). Verwende KEINE ```html Markdown-Block-Wrapper.
    7. Der Artikel sollte mindestens 800 bis 1200 Wörter umfassen.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein professioneller Finanzjournalist und SEO-Experte für Aktienanalysen."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_excerpt(client, title, content):
    prompt = f"""Schreibe eine packende, SEO-optimierte Metabeschreibung (max. 150 Zeichen) für folgenden Blog-Artikel:
    Titel: {title}
    Inhalt: {content[:1000]}
    
    WICHTIG: Antworte NUR mit der Metabeschreibung. Keine Einleitung, keine Anführungszeichen.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60
    )
    return response.choices[0].message.content.strip()

def publish_to_wordpress(title, content, excerpt):
    post_data = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "status": "publish",  # Sofort veröffentlichen
        "categories": [5],    # Standard-Aktienanalyse-Kategorie
        "tags": []
    }
    
    print(f"Publishing to WordPress: {title}...")
    res = requests.post(
        WP_URL,
        auth=HTTPBasicAuth(WP_USER, WP_PASS),
        json=post_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if res.status_code == 201:
        print(f"[OK] Erfolgreich veroffentlicht! Link: {res.json().get('link')}")
        return True
    else:
        print(f"[ERR] Fehler beim Veroffentlichen: {res.status_code}")
        print(res.text)
        return False

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Fehler: OPENAI_API_KEY nicht gefunden.")
        return
        
    client = OpenAI(api_key=api_key)
    
    for article in EVERGREEN_ARTICLES:
        try:
            content = generate_article_content(
                client, 
                article["title"], 
                article["topic"], 
                article["internal_link"], 
                article["link_text"]
            )
            excerpt = generate_excerpt(client, article["title"], content)
            
            publish_to_wordpress(article["title"], content, excerpt)
            time.sleep(2)  # Kurze Pause zwischen den Posts
        except Exception as e:
            print(f"Fehler bei Artikel '{article['title']}': {e}")

if __name__ == "__main__":
    main()
