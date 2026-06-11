import sys
import os

# Add to path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graphic_generator import render_viral_list, render_dividend_calendar
from src.reel_generator import build_reel_mp4

def run_test():
    print("🧪 [TEST] Starting headless render test on server...")
    
    # 1. Test AI Infographic Graphic rendering
    c = {
        'headline': 'TEST RENDERING', 
        'subheadline': 'Headless Server Test', 
        'highlight_value': '100% STABIL', 
        'highlight_label': 'AUF AWS', 
        'card_points': [
            '1. FFMPEG: Ist erfolgreich installiert und einsatzbereit.',
            '2. OpenAI TTS: Generiert hochwertigen onyx Sprachkommentar.',
            '3. Whisper-1: Liefert präzise Wort-Zeitstempel.',
            '4. MoviePy: Animiert den langsamen Kamera-Zoom.',
            '5. Nginx CDN: Liefert das Video direkt an Meta aus.'
        ]
    }
    
    os.makedirs('static/temp_social', exist_ok=True)
    img_path = 'static/temp_social/test_ai.png'
    video_path = 'static/temp_social/test_ai.mp4'
    
    print("🎨 [TEST] Rendering graphic image...")
    render_viral_list(c, img_path)
    print(f"✅ [TEST] Image rendered and saved at: {img_path}")
    
    # 2. Test video rendering with voiceover & subtitles
    print("📹 [TEST] Rendering video with MoviePy and FFMPEG...")
    build_reel_mp4(
        script_text='Dieser exklusive Testlauf beweist, dass die gesamte serverbasierte Reels-Maschine auf dem AWS Server vollautomatisch und fehlerfrei funktioniert.',
        background_image_path=img_path,
        output_mp4_path=video_path,
        silent=False
    )
    print(f"✅ [TEST] Video rendered and saved at: {video_path}")
    print("🎉 [TEST] ALL HEADLESS TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test()
