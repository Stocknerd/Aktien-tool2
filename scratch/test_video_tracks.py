import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.content_generator import generate_structured_content
from src.graphic_generator import render_viral_list, generate_dalle_image
from src.reel_generator import build_reel_mp4

def test_track_3():
    print("🚀 TESTING TRACK 3 INTEGRATION (AI INFOGRAPHICS) LOCAL...")
    topic = "Zinseszins: Warum Zeit dein größter Hebel an der Börse ist"
    
    # 1. GPT copywriting (Expanded)
    content = generate_structured_content(topic, template_type="viral_list")
    print(f"✅ Content generated successfully: {json.dumps(content, indent=2, ensure_ascii=False)}")
    
    # Verify schema
    assert "reel_script" in content
    assert len(content["card_points"]) == 5
    
    os.makedirs("output/test_reels", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bg_path = f"output/test_reels/test_bg_{timestamp}.png"
    image_path = f"output/test_reels/test_infographic_{timestamp}.png"
    video_path = f"output/test_reels/test_infographic_{timestamp}.mp4"
    
    # 2. Generate Background image
    print("🎨 Generating AI background illustration via DALL-E...")
    bg_img = generate_dalle_image(content.get("dalle_prompt"), aspect_ratio="9:16")
    bg_img.save(bg_path)
    print(f"✅ Background saved to {bg_path}")
    
    # 3. Render programmatically
    print("✏️ Rendering programmatic infographic on background...")
    render_viral_list(content, image_path, bg_image_path=bg_path)
    print(f"✅ Infographic saved to {image_path}")
    
    # 4. Synthesize video (TTS + Subtitles)
    print("🎙️ Synthesizing Reel video with Voiceover & Subtitles...")
    build_reel_mp4(
        script_text=content["reel_script"],
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=False
    )
    print(f"🎉 TEST SUCCESSFULLY COMPLETED! Video saved to {video_path}")

if __name__ == "__main__":
    try:
        test_track_3()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
