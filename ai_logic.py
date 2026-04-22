import os
import requests
import io
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
import json

# Load .env file if it exists
load_dotenv()

def get_ai_verdict(ticker, company_name, financial_data):
    """
    Generiert ein kurzes (max 100 Zeichen) Investment-Fazit mit OpenAI.
    """
    # Use environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        # Check if we are in a dev environment or if the user wants to use a placeholder
        return "KI-Fazit: OpenAI API Key fehlt."

    try:
        client = OpenAI(api_key=api_key)
        
        # Erstelle einen kompakten Prompt mit den Kennzahlen
        metrics_str = ", ".join([f"{k}: {v}" for k, v in financial_data.items() if v is not None])
        
        prompt = f"""
        Analysiere kurz die Aktie {company_name} ({ticker}) basierend auf diesen Kennzahlen: {metrics_str}.
        Schreibe eine aussagekräftige Einschätzung (max. 225 Zeichen) für eine Infografik. 
        Konzentriere dich auf das Wichtigste (z.B. Zusammenspiel von Bewertung, Wachstum und Dividende).
        Antworte NUR mit dem Fazit-Text, ohne Einleitung oder Anführungszeichen.
        """
        
        # Model selection: using gpt-5.4-mini
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=150
        )
        
        verdict = response.choices[0].message.content.strip()
        
        # Hartes Limit auf 250 Zeichen (ca. Faktor 2.5 von vorher 100)
        if len(verdict) > 250:
            verdict = verdict[:247] + "..."
            
        return verdict
    except Exception as e:
        print(f"OpenAI Error for {ticker}: {e}")
        return f"KI-Fazit: Dienst momentan nicht erreichbar."

def get_ai_long_analysis(ticker, company_name, financial_data, business_summary=None):
    """
    Generates a detailed multi-paragraph investment thesis for blog posts.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "<p>Bitte füge deinen OpenAI API Key hinzu, um die detaillierte Aktienanalyse zu generieren.</p>"

    try:
        client = OpenAI(api_key=api_key)
        metrics_str = ", ".join([f"{k}: {v}" for k, v in financial_data.items() if v is not None])
        
        summary_context = f"\nUnternehmens-Hintergrund: {business_summary}\n" if business_summary else ""
        
        prompt = f"""
        Schreibe eine fundierte, professionelle Analyse zum Unternehmen {company_name} ({ticker}) für ein Finanzblog-Publikum.
        {summary_context}
        Nutze folgende Kennzahlen als Basis: {metrics_str}.
        
        Schreibe 2-3 flüssig geschriebene Absätze auf Deutsch. 
        WICHTIG: Klinge menschlich und kompetent. Gehe direkt auf die Substanz ein.
        
        Struktur:
        1. Kurze Einordnung des Geschäftsmodells und der Marktposition.
        2. Einschätzung der Kennzahlen (KGV, Dividende, Wachstum).
        3. Ein kurzes Resümee für langfristige Investoren.

        Formatierung: Nutze ausschließlich <p> Tags für Absätze und <strong> für Hervorhebungen. Keine Überschriften.
        Beginne direkt mit dem ersten <p> Tag.
        """
        
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=800
        )
        ans = response.choices[0].message.content.strip()
        # Clean up any potential markdown code blocks if the AI accidentally adds them
        ans = ans.replace("```html", "").replace("```", "").strip()
        if not ans.startswith("<p>"):
            ans = f"<p>{ans}</p>"
        
        if not ans or len(ans) < 50:
             return f"<p><strong>{company_name}</strong> zeigt derzeit interessante Entwicklungen in den Fundamentaldaten. Besonders die Dividenden-Kontinuität und die Marktstellung machen den Titel für langfristige Portfolios beobachtenswert.</p>"
        return ans
    except Exception as e:
        print(f"OpenAI Error for {ticker}: {e}")
        return f"<p>Detaillierte Analyse für {ticker} konnte momentan nicht vollständig generiert werden.</p>"

def get_ai_excerpt(title, content):
    """
    Generates a short SEO-friendly description/excerpt for the post.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key: return "Aktienanalyse und Screening der aktuellen Marktwerte."
    
    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""Schreibe eine packende SEO-Metabeschreibung (max. 150 Zeichen) für folgenden Blog-Artikel: {title}. 
        WICHTIG: Antworte NUR mit der Beschreibung. KEINE Einleitung wie 'Hier ist...' oder 'Beschreibung:'. 
        Beginne direkt mit dem Text."""
        
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=50
        )
        ans = response.choices[0].message.content.strip()
        # Clean potential prefixes
        for prefix in ["Hier ist ", "Metabeschreibung:", "SEO:", "Beschreibung:"]:
            if ans.lower().startswith(prefix.lower()):
                ans = ans[len(prefix):].strip()
        return ans[:160]
    except Exception as e:
        print(f"Error generating excerpt: {e}")
        return "Täglich frische Aktienanalysen und Dividenden-Checks für dein Depot."

def generate_blog_header_image(stock_names):
    """
    Generates a premium landscape blog header image using DALL-E 3.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key: return None
    
    stocks_str = ", ".join(stock_names)
    prompt = f"A high-quality, professional 16:9 landscape cinematic header image for a financial news blog about the stock market. Abstract, modern, clean lines, financial district at sunrise, glowing trend lines, professional aesthetic, 8k resolution, elegant lighting. No text in the image. Topic related to: {stocks_str}."
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
             img = Image.open(io.BytesIO(img_response.content))
             return img
    except Exception as e:
        print(f"Error generating DALL-E image: {e}")
    return None

def get_ai_comparison_verdict(symbol_a, name_a, data_a, symbol_b, name_b, data_b):
    """
    Generates a concise AI verdict comparing two stocks based on their financial data.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "KI-Vergleich momentan nicht verfügbar (API Key fehlt)."

    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    Du bist ein erfahrener Finanzanalyst. Vergleiche die beiden folgenden Aktien basierend auf ihren Kennzahlen:
    
    Aktie A: {name_a} ({symbol_a})
    Kennzahlen A: {json.dumps(data_a, indent=2)}
    
    Aktie B: {name_b} ({symbol_b})
    Kennzahlen B: {json.dumps(data_b, indent=2)}
    
    Ziehe ein prägnantes Fazit (max. 4-5 Sätze). Welche Aktie wirkt attraktiver? 
    Antworte direkt mit dem Vergleichstext, ohne Einleitung. Nutze deutsche Sprache.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",  # Using gpt-5.4-mini for efficient comparisons
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=400
        )
        ans = response.choices[0].message.content.strip()
        if not ans or len(ans) < 20:
             return f"Basierend auf den Daten zeigen sowohl {symbol_a} als auch {symbol_b} solide Profile, wobei ihre individuellen Stärken in unterschiedlichen Kennzahlen liegen."
        return ans
    except Exception as e:
        print(f"OpenAI Error Comparison {symbol_a} vs {symbol_b}: {e}")
        return "Detaillierter KI-Vergleich konnte momentan nicht vollständig generiert werden."

def get_social_caption(stock_names_str, excerpt):
    """Generiert einen kritischen, zusammenfassenden Social-Media-Post für den gesamten Artikel."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return f"🚨 Neue Analyse online! Wir nehmen {stock_names_str} kritisch unter die Lupe. Jetzt auf schatzsuche40.de lesen. \n\nHinweis: Keine Anlageberatung. #Aktien #Finanzen"

    prompt = f"""
    Schreibe einen packenden, aber kritischen Social-Media-Post (max 280 Zeichen) für einen neuen Blogartikel über diese Aktien: {stock_names_str}.
    Die Kernaussage des Artikels lautet: {excerpt}
    
    Achte UNBEDINGT auf folgende Vorgaben:
    - Werbe nicht zu krass für die Aktien. Bleibe analytisch, sachlich und erwähne auch, dass man genau hinschauen muss.
    - Füge am Ende des Textes IMMER diesen Disclaimer als eigenen Satz hinzu: "Hinweis: Keine Anlageberatung. Führe immer eine eigene Recherche durch."
    - Nutze passend 2-3 Emojis.
    - Füge 3-5 relevante Hashtags hinzu (z.B. #Aktienanalyse #Dividenden).
    - Der Text muss auf Deutsch sein.
    - Keine Platzhalter verwenden.
    """
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
          model="gpt-5.4-mini",
          messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating social caption: {e}")
        return f"📊 Neue Aktien-Analyse online! Wir beleuchten die Fundamentaldaten von {stock_names_str} kritisch im Detail. Jetzt auf schatzsuche40.de lesen.\n\nHinweis: Keine Anlageberatung. #Aktien #Börse"

def get_tool_promotion_caption(is_comparison, names, symbols, financial_texts):
    """Generiert einen kritischen Social-Media-Post für das tägliche Standalone-Feature (mit Link zum Tool)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
         return f"Aktuelle Kennzahlen für {names}. Analysiere selbst auf schatzsuche40.de!\n\nHinweis: Keine Anlageberatung."
         
    if is_comparison:
        prompt_type = f"den Vergleich der fundamentalen Daten der Aktien {names} ({symbols})"
    else:
        prompt_type = f"die aktuelle Bewertung der Aktie {names} ({symbols})"
        
    prompt = f"""
    Schreibe einen packenden, aber objektiven und kritischen Instagram/Facebook-Post (max 280 Zeichen) über {prompt_type}.
    
    Nutze dafür folgende Daten als Grundlage: 
    {financial_texts}
    
    Vorgaben:
    - Verliere keine super lativen Werbekomplimente, bleibe sachlich. Werte nicht in den Himmel loben, nur interpretieren.
    - Baue folgenden Aufruf organisch ein: "Mehr Analysen & dieses Tool findest du auf schatzsuche40.de"
    - Füge als LETZTEN Satz isoliert den Disclaimer hinzu: "Hinweis: Keine Anlageberatung. Bilde dir eine eigene Meinung."
    - Nutze 2-4 Emojis passend zum Thema Börse.
    - Nutze 3-5 relevante Hashtags (z.B. #Aktien #Börse #Investing).
    - Texte in deutscher Sprache.
    """
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
          model="gpt-5.4-mini",
          messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating promotion caption: {e}")
        return f"🧐 {names} ({symbols}) im Check. Wie sind die aktuellen KGV & Margen?\n\n👉 Alle Daten & das Analysetool: schatzsuche40.de\n\nHinweis: Keine Anlageberatung. #Investieren #Börse"

if __name__ == "__main__":
    # Test block
    test_data = {"KGV": "15.2", "Dividendenrendite": "3.5%", "Umsatzwachstum": "10%"}
    # print(get_ai_verdict("AAPL", "Apple Inc.", test_data))
