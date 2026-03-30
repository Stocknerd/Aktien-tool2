import os
from openai import OpenAI

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

if __name__ == "__main__":
    # Test block
    test_data = {"KGV": "15.2", "Dividendenrendite": "3.5%", "Umsatzwachstum": "10%"}
    # print(get_ai_verdict("AAPL", "Apple Inc.", test_data))
