import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from src.config import BRAND_PROFILE, PORTFOLIO_PROFILE, DISCLAIMERS, COLORS_HEX

# Load environment variables from .env file if present
load_dotenv()

# Instantiate standard OpenAI client (using a fallback dummy key to prevent crashes on import in local development)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "dummy-key-for-local-import"))

def generate_structured_content(topic, template_type="evergreen"):
    """
    Calls OpenAI Chat Completion to generate a cohesive set of copy and prompts,
    enforcing brand tone, portfolio guidelines, color schemes, and no absolute euro amounts.
    """
    # Build context injections
    brand_context = f"""
    Marken-Kontext für '{BRAND_PROFILE.get('brand_name', 'Schatzsuche 4.0')}':
    - Webseite: {BRAND_PROFILE.get('website', 'schatzsuche40.de')}
    - Tonalität: {BRAND_PROFILE.get('tone', 'professionell, verständlich, nahbar')}
    - Themenfokus: {", ".join(BRAND_PROFILE.get('typical_topics', []))}
    - Farbwelt: Primär Gold ({COLORS_HEX.get('primary')}), Akzent Petrol ({COLORS_HEX.get('accent')}), Hintergrund Dunkel-Petrol ({COLORS_HEX.get('background')})
    - Disclaimer: "{DISCLAIMERS.get('short_disclaimer', 'Keine Anlageberatung.')}"
    """

    portfolio_rules = f"""
    Portfolio-Richtlinien (WICHTIG):
    - Investmentstil: {PORTFOLIO_PROFILE.get('investment_style', 'Langfristig')}
    - Relevante Holdings: {", ".join([h['name'] for h in PORTFOLIO_PROFILE.get('holdings', [])])}
    - SENSIBLE DATEN REGELN: NIEMALS absolute Eurobeträge des persönlichen Vermögens erwähnen (z.B. NICHT 'Mein 50.000€ Depot'). Nutze stattdessen Prozent-Angaben (z.B. '70% ETFs, 20% Immobilien') oder rein hypothetische Sparbeispiele (z.B. 'Wer 150€ monatlich investiert...').
    - BLACKLIST (Strenge Verbote): {", ".join(PORTFOLIO_PROFILE.get('blacklist', {}).get('untrusted_assets', []))}. Keine Heilsversprechen oder 'Schnell reich werden' Taktiken!
    """

    if template_type == "viral_list":
        system_prompt = f"""
        Du bist der Elite-Finanz-Content-Strategist für die deutsche Marke '{BRAND_PROFILE.get('brand_name', 'Schatzsuche 4.0')}' (Webseite: {BRAND_PROFILE.get('website', 'schatzsuche40.de')}).
        Deine Aufgabe ist es, für das Thema "{topic}" ein hochprofessionelles, visuell und inhaltlich konsistentes Infografik- und Reel-Inhaltspaket im Format einer **Faktenliste mit Highlight-Box** (Elterngeld-Stil) zu erstellen.
        
        {brand_context}
        
        {portfolio_rules}
        
        WICHTIGE ANFORDERUNGEN AN DIE GRAFIK-ELEMENTE (Faktenliste-Stil):
        - Die Headline (Überschrift ganz oben) muss extrem knackig sein (max. 40 Zeichen, z. B. 'Elterngeld Kürzungen 2026').
        - Die Subheadline (Kategorie/Sektionstext direkt unter H1) darf max. 30 Zeichen lang sein (z. B. 'Hypothetisches Sparpaket').
        - Die Zentral-Highlight-Box zeigt eine markante, emotionale oder wichtige Kennzahl:
          - highlight_value: Eine sehr große, fette Zahl oder ein Wert (max. 15 Zeichen, z. B. '350 MIO. €' oder '100.000 €').
          - highlight_label: Ein kurzes Schlagwort darunter (max. 15 Zeichen, z. B. 'WENIGER?' oder 'IM DEPOT?').
        - Die Fakten-Liste (card_points) MUSS GENAU 5 reichhaltige, extrem aussagekräftige und hoch-informative Punkte enthalten.
          - JEDER Punkt muss im exakten Format '"Titel: Beschreibung"' ausgegeben werden!
          - Der Titel (vor dem Doppelpunkt) ist fett gedruckt, extrem knackig und enthält oft Geldbeträge oder kurze Kernaussagen (max. 30 Zeichen, z. B. '100 € weniger/Monat' oder '70% in Welt-ETFs').
          - Die Beschreibung (nach dem Doppelpunkt) liefert den konkreten Kontext, ist informativ und fachlich tief (max. 150 Zeichen, z. B. 'wenn der Höchstbetrag von 1.800€ auf 1.700€ sinkt und dadurch Familien massiv finanziell entlastet werden, um private Altersvorsorge zu stärken').
          - Das System ordnet jedem Punkt automatisch ein passendes Icon (euro, calendar, time, percent, people, star) zu.
        
        WICHTIGE ANFORDERUNGEN AN DAS REEL:
        - Der gesprochene Reel-Sprechtext (reel_script) muss exakt 60-80 Wörter umfassen (für 30-45 Sekunden Video). Keine Szenenüberschriften, reiner gesprochener Text.
        - HOOK-REGEL: Der Text MUSS direkt mit einem extrem fesselnden Satz beginnen (z. B. eine provokante Frage oder schockierende Statistik). Es darf ABSOLUT KEINE Begrüßung enthalten sein (z. B. KEIN 'Willkommen bei...', 'Hallo...', 'In diesem Video...', 'Heute schauen wir uns...'). Starte direkt mit dem brennenden Thema!
        
        Antworte AUSSCHLIESSLICH im folgenden validen JSON-Format:
        {{
          "headline": "Knackige H1 (max 40 Zeichen)",
          "subheadline": "Unterstützende Subline (max 30 Zeichen)",
          "highlight_value": "Großer Wert für Box (max 15 Zeichen)",
          "highlight_label": "Label für Box (max 15 Zeichen)",
          "card_points": [
            "Titel 1 (max 30 Chars): Beschreibung 1 (max 150 Chars)",
            "Titel 2 (max 30 Chars): Beschreibung 2 (max 150 Chars)",
            "Titel 3 (max 30 Chars): Beschreibung 3 (max 150 Chars)",
            "Titel 4 (max 30 Chars): Beschreibung 4 (max 150 Chars)",
            "Titel 5 (max 30 Chars): Beschreibung 5 (max 150 Chars)"
          ],
          "dalle_prompt": "Detaillierter Prompt für ein 9:16 Bild (max. 3 Farbnuancen: warmes Gold, dunkles Petrol, Offwhite). Keine Menschen, keine Gesichter.",
          "caption_ig": "Instagram-Caption, die direkt mit einer extrem packenden Frage oder These (Hook) beginnt, um Kommentare zu provozieren, gefolgt von strukturierten Absätzen, Emojis, Hashtags, CTA und dem rechtlichen Disclaimer.",
          "caption_tiktok": "Kurze, knackige TikTok-Caption.",
          "caption_shorts": "Spannende YouTube Shorts Caption.",
          "reel_script": "Sprechtext für das Video-Voiceover (60-80 Wörter). Startet direkt mit der Hook, absolut keine Begrüßungen!"
        }}
        """
    else:
        system_prompt = f"""
        Du bist der Elite-Finanz-Content-Strategist für die deutsche Marke '{BRAND_PROFILE.get('brand_name', 'Schatzsuche 4.0')}'.
        Deine Aufgabe ist es, für das Thema "{topic}" ein hochprofessionelles, visuell und inhaltlich konsistentes Infografik- und Reel-Inhaltspaket zu schnüren.
        
        {brand_context}
        
        {portfolio_rules}
        
        WICHTIGE ANFORDERUNGEN AN DIE GRAFIK-ELEMENTE:
        - Die Headline (Überschrift) muss extrem knackig und aussagekräftig sein. Sie darf maximal 40 Zeichen lang sein!
        - Die Subheadline darf maximal 60 Zeichen lang sein.
        - Die 3 Kernaussagen (card_points) müssen kurz und präzise sein (maximal 105 Zeichen pro Punkt!). Sie beschreiben die wichtigsten Lektionen oder Schritte zum Thema.
        
        WICHTIGE ANFORDERUNGEN AN DAS REEL:
        - Der gesprochene Reel-Text (reel_script) muss exakt 60-80 Wörter umfassen (ideal für ein 30-45 Sekunden Reel). Er muss fesselnd sein, ohne Abschnitte oder Szenenüberschriften im Text. Es muss reines gesprochenes Deutsch sein.
        - HOOK-REGEL: Der Text MUSS direkt mit einem extrem fesselnden Satz beginnen (z. B. eine provokante Frage oder schockierende Statistik). Es darf ABSOLUT KEINE Begrüßung enthalten sein (z. B. KEIN 'Willkommen bei...', 'Hallo...', 'In diesem Video...', 'Heute schauen wir uns...').
        
        Antworte AUSSCHLIESSLICH im folgenden validen JSON-Format:
        {{
          "headline": "Knackige H1 (max 40 Zeichen, z.B. 'Zinseszins verstehen')",
          "subheadline": "Unterstützende Subline (max 60 Zeichen)",
          "card_points": [
            "Punkt 1 (max 105 Zeichen, prägnant, lösungsorientiert)",
            "Punkt 2 (max 105 Zeichen, faktenbasiert, verständlich)",
            "Punkt 3 (max 105 Zeichen, handlungsauffordernd)"
          ],
          "dalle_prompt": "Detaillierter Prompt für ein 9:16 Bild. Beschreibe eine ästhetische, leicht geheimnisvolle oder hochmoderne Finanz-Metapher. Verwende Farben wie warmes Gold und dunkles Petrol. KEINE Menschen, KEINE Gesichter. Nur hochwertige, dreidimensionale, filmisch beleuchtete Konzeptkunst.",
          "caption_ig": "Instagram-Caption, die direkt mit einer extrem packenden Frage oder These (Hook) beginnt, um Kommentare zu provozieren, gefolgt von strukturierten Absätzen, Emojis, Hashtags, CTA und dem rechtlichen Disclaimer am Ende.",
          "caption_tiktok": "Kurze, knackige TikTok-Caption mit Hook, Emojis und Top-Hashtags.",
          "caption_shorts": "Spannende YouTube Shorts Caption inklusive kurzer Beschreibung.",
          "reel_script": "Der fließende, laut gesprochene Sprechtext für das Video-Voiceover (60-80 Wörter). Startet direkt mit der Hook, absolut keine Begrüßungen!"
        }}
        """

    # We use gpt-4o which is highly capable and standard for structured JSON output
    # Fallback to model in .env if any, else gpt-4o
    model_name = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.5")
    
    print(f"CONTENT: Generiere Content für '{topic}' (Modell: {model_name})...")
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Erstelle das Inhaltspaket für das Thema: {topic} (Template-Typ: {template_type})"}
        ],
        response_format={"type": "json_object"}
    )
    
    content = json.loads(response.choices[0].message.content)
    print(f"CONTENT: Erfolgreich generiert! Headline: '{content.get('headline')}'")
    return content

if __name__ == "__main__":
    # Test generation
    test_res = generate_structured_content("Warum ETF-Sparpläne die beste Basis sind", "evergreen")
    print(json.dumps(test_res, indent=2))
