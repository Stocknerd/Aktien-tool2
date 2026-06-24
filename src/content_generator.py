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
        Deine Aufgabe ist es, für das Thema "{topic}" ein hochprofessionelles, visuell und inhaltlich konsistentes Infografik- und Reel-Inhaltspaket zu schnüren. 
        Die Infografik muss als extrem detaillierter Prompt für das Modell `image-2` (gpt-image-2) unter `image_prompt` beschrieben werden, so dass das Bild in einem Rutsch vollkommen lesbar, strukturiert und fehlerfrei generiert wird.
        
        {brand_context}
        
        {portfolio_rules}
        
        WICHTIGE ANFORDERUNGEN AN DIE GRAFIK-ELEMENTE (PROMPT FÜR image-2):
        - Der Prompt beschreibt eine komplette, hoch-informative 9:16 Hochformat-Infografik für Instagram.
        - Farben: Dunkel-Petrol (#0B1E21) als Hintergrund, warmes Gold (#C9A227) und Off-white (#F7F7F7) als Text- und Elementfarben.
        - Aufbau der Grafik von oben nach unten:
          1. Brand-Header & Thema: Ganz oben links steht "Schatzsuche 4.0 - [Dynamic Category]" in Gold. Daneben ein kleiner Navigator-Kompass. Darunter die Haupt-Headline (große, fette weiße Buchstaben) und eine Subheadline (in Gold). Rechts oben befindet sich ein glühendes, dreidimensionales Icon passend zum Thema (z.B. eine Goldmünze für ETFs, eine Zapfsäule für CO2-Preise).
          2. Fünf strukturierte, nummerierte Sektionen (1 bis 5), untereinander gestapelt in eleganten, goldumrandeten, teiltransparenten Karten:
             - Sektion 1: Ein thematischer Einstieg (z.B. "WAS BESCHLOSSEN IST"). Enthält 3-4 prägnante Stichpunkte mit Checkmark-Häkchen und eine hervorgehobene Kernaussage am Ende.
             - Sektion 2: Detaillierte Zahlen, Spalten oder Fakten (z.B. "SO HOCH IST DER ZUSCHUSS"). Zeigt strukturierte Spalten mit Werten (z.B. Zulagen, Boni) und passenden kleinen Symbolen (Münze, Kind, Geschenk).
             - Sektion 3: Ein anschauliches Rechenbeispiel oder konkretes Szenario (z.B. "BEISPIEL FAMILIE"). Zeigt eine saubere mathematische Auflistung (z.B. '+ 150 € Spar-Zuschuss', '= 1.050 € Jahreszufluss') mit einem großen goldenen Kreis auf der rechten Seite, der das Gesamtergebnis (z.B. '1.050 € pro Jahr') fett hervorhebt.
             - Sektion 4: Ein Haken, Risiko oder wichtiges Detail (z.B. "DER STEUER-HAKEN" oder "WO DER AUFREGER LIEGT"). Eine nummerierte Liste (1 bis 4) mit rechtlichen oder steuerlichen Fallstricken, rechts daneben ein passendes Symbol (z.B. Sanduhr oder Steuerschild), und eine hervorgehobene Warnbox am Ende.
             - Sektion 5: "MEIN FAZIT". Enthält 2 prägnante Fazit-Punkte mit Haken und ein symbolisches Icon (z.B. glühende Glühbirne oder eine Waage).
          3. Interaktiver Footer: Eine Sektion am unteren Ende mit einer Sprechblase und der Frage "WAS DENKST DU: [Themenspezifische Frage, z.B. ECHTER FORTSCHRITT ODER NUR RIESTER 2.0?]" in großen, weißen Buchstaben.
          4. Ganz unten steht im eleganten Gold-Design: "SCHATZSUCHE 4.0" (vollkommen ohne Datums-, Monats- oder Jahresangaben).
        - WICHTIGE REGEL FÜR ZEITLOSIGKEIT (EVERGREENS): Nenne niemals Jahreszahlen (wie 2023, 2024, 2026) oder konkrete Monate in den Texten, Grafiken oder Captions für zeitlose Themen (wie Zinseszins, ETF-Sparpläne, Diversifikation), damit diese dauerhaft aktuell bleiben. Nur bei hochaktuellen, nachrichtenbasierten Themen der laufenden Woche darf ein zeitlicher Bezug genommen werden.
        - Der Prompt muss alle Texte, Überschriften, Zahlenwerte und Formeln exakt in deutschem Text vorgeben und anweisen, dass diese von `image-2` in sauberer, geometrischer, serifenloser Schriftart (ähnlich Outfit und Inter) komplett fehlerfrei gezeichnet werden müssen.
        
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
          "image_prompt": "Der extrem detaillierte und strukturierte Prompt für gpt-image-2 (9:16 Format), der die komplette Infografik mit allen Sektionen, deutschen Texten, Zahlen, Formeln und Icons beschreibt. Keine Platzhalter, sondern den vollen Text ausschreiben!",
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
        Die Infografik muss als detaillierter Prompt für das Modell `image-2` (gpt-image-2) unter `image_prompt` beschrieben werden, so dass das Bild in einem Rutsch generiert wird.
        
        {brand_context}
        
        {portfolio_rules}
        
        WICHTIGE ANFORDERUNGEN AN DIE GRAFIK-ELEMENTE (PROMPT FÜR image-2):
        - Der Prompt beschreibt eine komplette 9:16 Hochformat-Infografik für Instagram.
        - Er verwendet eine ästhetische Finanz-Metapher in warmem Gold und dunklem Petrol (keine echten Gesichter/Menschen).
        - Er muss alle Überschriften und Kernbotschaften exakt in deutschem Text vorgeben, damit diese von `image-2` fehlerfrei gezeichnet werden.
        
        WICHTIGE ANFORDERUNGEN AN DAS REEL:
        - Der gesprochene Reel-Text (reel_script) muss exakt 60-80 Wörter umfassen. Er muss fesselnd sein, reines gesprochenes Deutsch, ohne Begrüßung.
        - HOOK-REGEL: Der Text MUSS direkt mit einem extrem fesselnden Satz beginnen.
        
        Antworte AUSSCHLIESSLICH im folgenden validen JSON-Format:
        {{
          "headline": "Knackige H1 (max 40 Zeichen, z.B. 'Zinseszins verstehen')",
          "subheadline": "Unterstützende Subline (max 60 Zeichen)",
          "card_points": [
            "Punkt 1 (max 105 Zeichen, prägnant, lösungsorientiert)",
            "Punkt 2 (max 105 Zeichen, faktenbasiert, verständlich)",
            "Punkt 3 (max 105 Zeichen, handlungsauffordernd)"
          ],
          "image_prompt": "Detaillierter Prompt für gpt-image-2 (9:16 Format), der das ästhetische Bild mit deutschem Text beschreibt.",
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
