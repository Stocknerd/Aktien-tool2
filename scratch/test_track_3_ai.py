#!/usr/bin/env python3
import sys
import os
import random
import time
import argparse
from datetime import datetime

# Add root directory to path to allow importing correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.config import BASE_DIR
from src.graphic_generator import render_pure_ai_infographic
from src.reel_generator import build_reel_mp4
from src.content_generator import generate_structured_content
from src.social_reels_autoposter import EVERGREEN_FINANCIAL_TOPICS

def run_test_track_3(topic=None):
    print("🧪 [TEST RUN - TRACK 3] Starting AI Infographic test run...")
    
    if not topic:
        # Pick a random topic from the evergreen list
        topic = random.choice(EVERGREEN_FINANCIAL_TOPICS)
    
    print(f"💡 Topic selected: '{topic}'")
    
    # 1. GPT Copywriting
    print("✍️ Generating copy via GPT...")
    content = generate_structured_content(topic, template_type="viral_list")
    
    print("\n📝 Copy generated successfully:")
    print(f"--- HEADLINE: {content.get('headline')} ---")
    print(f"--- SUBHEADLINE: {content.get('subheadline')} ---")
    print(f"--- HIGHLIGHT VALUE: {content.get('highlight_value')} ---")
    print(f"--- HIGHLIGHT LABEL: {content.get('highlight_label')} ---")
    print(f"--- CARD POINTS ({len(content.get('card_points', []))}):")
    for pt in content.get("card_points", []):
        print(f"  * {pt}")
    
    public_dir = os.path.join(BASE_DIR, "static", "temp_social")
    os.makedirs(public_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    image_filename = f"test_track_3_ai_{timestamp}.png"
    video_filename = f"test_track_3_ai_{timestamp}.mp4"
    image_path = os.path.join(public_dir, image_filename)
    video_path = os.path.join(public_dir, video_filename)
    
    # 2. Render Image using premium gpt-image-2 model
    print("\n🎨 Rendering premium AI infographic via gpt-image-2...")
    render_pure_ai_infographic(content, image_path)
    print(f"✅ Image rendered and saved at: {image_path}")
    
    # 3. Render Silent Video (Musik + Zoom)
    print("\n📹 Rendering silent zoom video with FFMPEG...")
    build_reel_mp4(
        script_text=None,
        background_image_path=image_path,
        output_mp4_path=video_path,
        silent=True,
        duration=10.0
    )
    print(f"✅ Video rendered and saved at: {video_path}")
    
    print("\n🎉 TEST RUN OF TRACK 3 COMPLETED SUCCESSFULLY!")
    print(f"🖼️ View Image: https://tool.schatzsuche40.de/static/temp_social/{image_filename}")
    print(f"🎥 View Video: https://tool.schatzsuche40.de/static/temp_social/{video_filename}")
    print(f"💬 Generated Instagram Caption:\n{content.get('caption_ig')}\n")
    
    return image_filename, video_filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test run for Track 3 AI Infographics")
    parser.add_argument("--topic", type=str, default=None, help="Explicit topic override")
    args = parser.parse_args()
    
    run_test_track_3(args.topic)
