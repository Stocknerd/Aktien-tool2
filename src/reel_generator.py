import os
import requests
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import *
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import COLORS, FONT_PATHS, BASE_DIR
from src.content_generator import client

# Audio and SFX source files
MUSIC_FILE = "background_finance.mp3"
MUSIC_URL = "https://cdn.pixabay.com/download/audio/2022/03/24/audio_c8c8a73467.mp3" 

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_speech_and_words(text, output_mp3_path):
    """
    Generates voiceover using OpenAI TTS and transcripts word timestamps using Whisper.
    """
    print(f"TTS: Generating voiceover via tts-1 (voice: onyx)...")
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx", 
        input=text
    )
    response.write_to_file(output_mp3_path)

    print("WHISPER: Transcribing word timestamps...")
    with open(output_mp3_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"]
        )
    return transcript.words

def draw_karaoke_subtitles(img, t, words_data, font_path, base_font_size=55):
    """
    TikTok/CapCut-Style karaoke subtitles centered at the lower part of the screen.
    Displays small groups of words, highlighting the current word in brand gold,
    with a dark semi-transparent rounded background.
    """
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    current_word_idx = -1
    for i, w in enumerate(words_data):
        if w.start <= t <= w.end:
            current_word_idx = i
            break
            
    if current_word_idx == -1:
        return img

    # Group of words (typically 4)
    group_size = 4
    group_start = (current_word_idx // group_size) * group_size
    group_end = min(group_start + group_size, len(words_data))
    
    words_to_draw = []
    for i in range(group_start, group_end):
        word_text = words_data[i].word.upper()
        is_active = (i == current_word_idx)
        # Highlight active word in brand gold (201, 162, 39)
        words_to_draw.append({
            "text": word_text,
            "color": "#C9A227" if is_active else "white",
            "active": is_active
        })
    
    try:
        font = ImageFont.truetype(font_path, base_font_size)
        font_bold = ImageFont.truetype(font_path, int(base_font_size * 1.05))
    except:
        font = ImageFont.load_default()
        font_bold = font

    total_text = " ".join([w["text"] for w in words_to_draw])
    bbox = draw.textbbox((0, 0), total_text, font=font)
    total_w = bbox[2] - bbox[0]
    
    current_x = (width - total_w) / 2
    y_pos = height * 0.72  # Positioned beautifully in the lower third
    
    # Transparent dark background bar
    padding = 20
    bar_left = max(20, current_x - padding)
    bar_right = min(width - 20, current_x + total_w + padding)
    bar_top = y_pos - padding
    bar_bottom = y_pos + base_font_size + padding
    
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [bar_left, bar_top, bar_right, bar_bottom],
        radius=16, fill=(11, 30, 33, 180) # Brand background color with opacity
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    for w_obj in words_to_draw:
        w_text = w_obj["text"] + " "
        use_font = font_bold if w_obj["active"] else font
        # Outline for crisp text
        for adj, b_idx in [(-2,-2), (2,-2), (-2,2), (2,2), (0,-2), (0,2), (-2,0), (2,0)]:
            draw.text((current_x + adj, y_pos + b_idx), w_text, font=use_font, fill="black")
        draw.text((current_x, y_pos), w_text, font=use_font, fill=w_obj["color"])
        w_bbox = draw.textbbox((0, 0), w_text, font=use_font)
        current_x += (w_bbox[2] - w_bbox[0])

    return img

def ensure_bg_music():
    """Tries to find the background music locally or copies it from videoautomation."""
    local_music = os.path.join(BASE_DIR, MUSIC_FILE)
    if os.path.exists(local_music) and os.path.getsize(local_music) > 1000:
        return local_music
        
    # Try copying from videoautomation Dropbox folder if nearby
    dropbox_path = "c:/Users/fhofm/Dropbox/videoautomation/background_finance.mp3"
    if os.path.exists(dropbox_path):
        print(f"MUSIC: Copying music file from {dropbox_path}...")
        try:
            with open(dropbox_path, "rb") as sf, open(local_music, "wb") as df:
                df.write(sf.read())
            return local_music
        except Exception as e:
            print(f"WARNING: Could not copy music file: {e}")
            
    # Download fallback
    print(f"MUSIC: Downloading licensing-free music from {MUSIC_URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
    try:
        r = requests.get(MUSIC_URL, headers=headers, timeout=20)
        r.raise_for_status()
        with open(local_music, 'wb') as f:
            f.write(r.content)
        print("MUSIC: Download successful!")
        return local_music
    except Exception as e:
        print(f"WARNING: Music download failed: {e}. Reel will have no background music.")
        return None

def build_reel_mp4(script_text, background_image_path, output_mp4_path, silent=False, duration=10.0):
    """
    Creates a 9:16 vertical video Reel:
    - If silent=False: Voiceover TTS & Word-level Karaoke Subtitles
    - If silent=True: Pure infographic video, no voiceover, no subtitles, exactly `duration` long (default 10s)
    - Pan/Zoom slow animation on background image
    - Double golden border drawn on the moving frame
    - Background music overlay & audio fade
    - Progress bar at the bottom
    """
    temp_dir = os.path.join(BASE_DIR, "temp_assets")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_path = os.path.join(temp_dir, "reel_audio.mp3") if not silent else None
    
    if not silent:
        # 1. Voiceover TTS & Timestamps
        words_data = generate_speech_and_words(script_text, audio_path)
        audio_clip = AudioFileClip(audio_path)
        video_duration = audio_clip.duration + 0.5 # Add small buffer
    else:
        words_data = []
        audio_clip = None
        video_duration = duration
    
    img_clip = ImageClip(background_image_path).with_duration(video_duration)
    font_path = FONT_PATHS.get("Outfit-Bold.ttf", "arial.ttf")
    
    # Determine camera style (e.g. slow zoom in)
    def animate_frame(get_frame, t):
        progress = t / video_duration
        img_array = get_frame(t)
        h, w = img_array.shape[:2]
        
        # 1. Apply slow camera zoom-in (1.0 to 1.08)
        zoom_factor = 1.0 + (0.08 * progress)
        img = Image.fromarray(img_array)
        new_w, new_h = int(w * zoom_factor), int(h * zoom_factor)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - w) / 2
        top = (new_h - h) / 2
        img = img.crop((left, top, left + w, top + h))
        
        # 2. Draw Karaoke Subtitles (only if not silent)
        if not silent and words_data:
            img = draw_karaoke_subtitles(img, t, words_data, font_path)
        
        # 3. Add dynamic red/gold progress bar at the bottom
        draw = ImageDraw.Draw(img)
        bar_height = 12
        bar_width = int(w * progress)
        if bar_width > 0:
            # Gold progress bar (201, 162, 39)
            draw.rectangle([0, h - bar_height, bar_width, h], fill=COLORS["primary"])
            
        return np.array(img)

    video_clip = img_clip.transform(animate_frame)
    if audio_clip:
        video_clip = video_clip.with_audio(audio_clip)
    
    # 3. Add background music
    music_path = ensure_bg_music()
    if music_path and os.path.exists(music_path):
        print(f"MUSIC: Mixing background music...")
        try:
            bg_music = AudioFileClip(music_path).with_effects([
                afx.AudioLoop(duration=video_duration),
                afx.MultiplyVolume(0.08) # Muted background volume
            ])
            if video_clip.audio:
                video_clip = video_clip.with_audio(CompositeAudioClip([video_clip.audio, bg_music]))
            else:
                video_clip = video_clip.with_audio(bg_music)
        except Exception as e:
            print(f"WARNING: Background music mix failed: {e}")
            
    # Apply fade transitions
    video_clip = video_clip.with_effects([vfx.CrossFadeIn(0.4), vfx.CrossFadeOut(0.4)])
    
    # Render final MP4
    print(f"REEL: Rendering {'SILENT ' if silent else ''}final MP4 to {output_mp4_path}...")
    video_clip.write_videofile(output_mp4_path, fps=30, codec="libx264", audio_codec="aac" if video_clip.audio else None)
    print(f"REEL: Video created successfully! ({output_mp4_path})")
    
    # Cleanup temp audio
    try:
        if audio_clip:
            audio_clip.close()
        video_clip.close()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        print(f"WARNING: Clean-up error: {e}")

    return output_mp4_path

if __name__ == "__main__":
    # Test script for video synthesis
    test_script = "Willkommen bei Schatzsuche 4.0! Wusstest du, dass der Zinseszins dein stärkster Partner beim Vermögensaufbau ist? Wenn du monatlich nur 150€ in einen breit gestreuten ETF investierst, arbeitet dein Geld Tag und Nacht für dich. Über dreißig Jahre wächst dein Erspartes exponentiell! Starte noch heute deinen Sparplan. Folge Schatzsuche 4.0 für clevere Finanztipps!"
    build_reel_mp4(test_script, "evergreen_test.png", "reel_test.mp4")
