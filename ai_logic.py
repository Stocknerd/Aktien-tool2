import os
from openai import OpenAI
from dotenv import load_dotenv

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

def get_ai_long_analysis(ticker, company_name, financial_data):
    """
    Generates a detailed multi-paragraph investment thesis for blog posts.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "<p>Bitte füge deinen OpenAI API Key hinzu, um die detaillierte Aktienanalyse zu generieren.</p>"

    try:
        client = OpenAI(api_key=api_key)
        metrics_str = ", ".join([f"{k}: {v}" for k, v in financial_data.items() if v is not None])
        
        prompt = f"""
        Schreibe einen detaillierten, professionellen und gut lesbaren Blog-Abschnitt über das Unternehmen {company_name} ({ticker}).
        Nutze bei der Bewertung folgende Kennzahlen: {metrics_str}.
        Schreibe 2-3 Absätze in flüssigem Deutsch. Fokus: Was bedeuten diese Zahlen konkret für Aktionäre? Warum ist die Dividende oder Bewertung attraktiv?
        Gehe tief auf das Geschäftsmodell und die aktuelle Marktlage ein. 
        Nutze HTML-Tags wie <strong>, <em> oder <p> für Formatierung. Keine Überschriften (H1/H2). Beginne direkt mit dem Text.
        Zielgruppe: Langfristige Einkommensinvestoren.
        """
        
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=600
        )
        ans = response.choices[0].message.content.strip()
        if not ans or len(ans) < 50:
             # Try a simpler prompt fallback or retry
             print(f"Empty AI long response for {ticker}, returning fallback info.")
             return f"<p>Für <strong>{company_name}</strong> liegen aktuell solide Kennzahlen vor, die auf ein stabiles Geschäftsmodell hindeuten. Investoren schätzen hier besonders die Dividendenrendite und die Marktposition.</p>"
        return ans
    except Exception as e:
        print(f"OpenAI Error for {ticker}: {e}")
        return f"<p>Detaillierte Analyse für {ticker} konnte momentan nicht vollständig generiert werden.</p>"

if __name__ == "__main__":
    # Test block
    test_data = {"KGV": "15.2", "Dividendenrendite": "3.5%", "Umsatzwachstum": "10%"}
    # print(get_ai_verdict("AAPL", "Apple Inc.", test_data))
