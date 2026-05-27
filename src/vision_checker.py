import os
import base64
from openai import OpenAI

client = OpenAI()

def encode_image_base64(image_path):
    """Encodes a local image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def perform_vision_check(image_path):
    """
    Sends the generated infographic to GPT-5.5 Vision API to check contrast,
    readability, alignment, logo placement, and brand compliance.
    """
    print(f"VISION: Performing AI Vision Review for {os.path.basename(image_path)}...")
    if not os.path.exists(image_path):
        print("ERROR: Image file does not exist for vision check.")
        return {"rating": 0, "feedback": "File not found."}
        
    model_name = os.getenv("OPENAI_VISION_MODEL", "gpt-5.5")
    try:
        base64_image = encode_image_base64(image_path)
        
        system_prompt = """
        Du bist ein extrem kritischer Art Director für die Finanz-Marke 'Schatzsuche 4.0'.
        Analysiere die übertragene Infografik (9:16 Format) im Detail hinsichtlich:
        1. Lesbarkeit & Kontrast (Ist der Text scharf, kontrastreich und ohne Überlappungen lesbar?)
        2. Layout & Ausrichtung (Sind Abstände harmonisch, Boxen abgerundet, Logo gut zentriert?)
        3. Design-Konsistenz (Entspricht das edle Dunkel-Petrol/Gold-Design der Marken-Farbpalette?)
        
        Bewerte das Design auf einer Skala von 1 bis 10 (10 = Perfekt, veröffentlichungsreif).
        Gib detailliertes, ehrliches Feedback.
        
        Antworte im folgenden JSON-Format:
        {
          "rating": 9,
          "readability_status": "Exzellent / Gut / Verbesserungswürdig",
          "contrast_ok": true,
          "brand_alignment_ok": true,
          "feedback_details": "Deine detaillierten Beobachtungen...",
          "suggestions": "Praktische Verbesserungsvorschläge (z.B. 'Headline etwas kürzen', 'Mehr Padding in Box 2')."
        }
        """
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Überprüfe bitte diese frisch generierte Infografik auf Lesbarkeit und Ästhetik."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        print(f"VISION: Review complete! Rating: {result.get('rating')}/10 | Readability: {result.get('readability_status')}")
        return result
        
    except Exception as e:
        print(f"WARNING: Vision check failed: {e}")
        return {
            "rating": -1,
            "readability_status": "Error",
            "contrast_ok": False,
            "brand_alignment_ok": False,
            "feedback_details": f"API Error: {str(e)}",
            "suggestions": "Keine Vorschläge verfügbar."
        }

if __name__ == "__main__":
    # Test vision review
    if os.path.exists("evergreen_test.png"):
        perform_vision_check("evergreen_test.png")
