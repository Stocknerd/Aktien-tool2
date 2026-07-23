import os
import requests
import json
import uuid
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from moviepy import *
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import COLORS, FONT_PATHS, BASE_DIR
from src.content_generator import client

# Audio and SFX source files (local library configuration)
AUDIO_DIR = os.path.join(BASE_DIR, "audio_library")

REEL_SIZE = (1080, 1920)
REEL_FPS = 30
REEL_SAFE_X = 90


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, TypeError):
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def _text_width(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    return box[2] - box[0]


def _wrap_hook(draw, text, font, max_width, max_lines=3):
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines or any(_text_width(draw, line, font) > max_width for line in lines):
        return None
    return lines


def _prepare_reel_background(background_image_path, destination_path, *, hook_text=None):
    """Normalize every Reel frame and render one mobile-safe visual hook."""

    with Image.open(background_image_path) as source:
        contained = ImageOps.contain(source.convert("RGB"), REEL_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", REEL_SIZE, COLORS.get("background", (11, 30, 33)))
    canvas.paste(
        contained,
        ((REEL_SIZE[0] - contained.width) // 2, (REEL_SIZE[1] - contained.height) // 2),
    )

    if hook_text is not None:
        hook = str(hook_text).strip()
        if not hook or len(hook) > 40 or "\n" in hook or "\r" in hook:
            raise ValueError("Reel hook must be single-line text with at most 40 characters")
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=10))
        shade = Image.new("RGBA", REEL_SIZE, (4, 10, 18, 180))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        hook_font_path = FONT_PATHS.get("Outfit-Bold.ttf", "arial.ttf")
        lines = None
        hook_font = None
        for size in range(92, 53, -2):
            candidate_font = _font(hook_font_path, size)
            candidate_lines = _wrap_hook(draw, hook.upper(), candidate_font, 900, max_lines=3)
            if candidate_lines is not None:
                hook_font = candidate_font
                lines = candidate_lines
                break
        if hook_font is None or lines is None:
            raise ValueError("Reel hook does not fit the mobile safe area")
        line_height = max(
            draw.textbbox((0, 0), line, font=hook_font, stroke_width=3)[3]
            for line in lines
        ) + 18
        start_y = 450 - ((len(lines) - 1) * line_height // 2)
        for index, line in enumerate(lines):
            draw.text(
                (REEL_SIZE[0] // 2, start_y + index * line_height),
                line,
                font=hook_font,
                fill=(247, 247, 247),
                stroke_width=3,
                stroke_fill=(4, 10, 18),
                anchor="mm",
            )

    draw = ImageDraw.Draw(canvas)
    gold = COLORS.get("primary", (201, 162, 39))
    draw.rectangle((85, 85, REEL_SIZE[0] - 85, REEL_SIZE[1] - 85), outline=gold, width=2)
    draw.rectangle((100, 100, REEL_SIZE[0] - 100, REEL_SIZE[1] - 100), outline=gold, width=1)
    destination = os.fspath(destination_path)
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    canvas.save(destination, "PNG")
    canvas.close()
    return destination


def _layout_karaoke_words(words, *, active_index, font_path, frame_size=REEL_SIZE, base_font_size=55):
    """Return a two-line, pixel-bounded karaoke layout for mobile playback."""

    width, height = frame_size
    max_width = width - (2 * REEL_SAFE_X)
    scratch = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(scratch)
    chosen = None
    for font_size in range(base_font_size, 31, -2):
        regular = _font(font_path, font_size)
        bold = _font(font_path, int(font_size * 1.05))
        lines = [[]]
        line_widths = [0.0]
        valid = True
        space_width = _text_width(draw, " ", regular)
        for index, word in enumerate(words):
            text = str(word.word).strip().upper()
            font = bold if index == active_index else regular
            word_width = _text_width(draw, text, font)
            if word_width > max_width:
                valid = False
                break
            addition = word_width if not lines[-1] else space_width + word_width
            if line_widths[-1] + addition > max_width:
                if len(lines) == 2:
                    valid = False
                    break
                lines.append([])
                line_widths.append(0.0)
                addition = word_width
            lines[-1].append((index, text, font, word_width))
            line_widths[-1] += addition
        if valid:
            chosen = (font_size, regular, lines, line_widths, space_width)
            break
    scratch.close()
    if chosen is None:
        raise ValueError("karaoke words do not fit the two-line mobile safe area")

    font_size, regular, lines, line_widths, space_width = chosen
    line_height = int(font_size * 1.35)
    block_height = len(lines) * line_height
    start_y = int(height * 0.72 - block_height / 2)
    items = []
    for line_index, line in enumerate(lines):
        x = (width - line_widths[line_index]) / 2
        y = start_y + line_index * line_height
        for item_index, text, font, word_width in line:
            if items and items[-1]["line"] == line_index:
                x += space_width
            bbox = font.getbbox(text, stroke_width=2)
            item_height = bbox[3] - bbox[1]
            items.append(
                {
                    "text": text,
                    "font": font,
                    "active": item_index == active_index,
                    "line": line_index,
                    "left": int(x),
                    "top": int(y),
                    "right": int(x + word_width),
                    "bottom": int(y + item_height),
                }
            )
            x += word_width
    left = max(REEL_SAFE_X, min(item["left"] for item in items) - 22)
    right = min(width - REEL_SAFE_X, max(item["right"] for item in items) + 22)
    top = max(0, min(item["top"] for item in items) - 18)
    bottom = min(height, max(item["bottom"] for item in items) + 24)
    return {
        "items": items,
        "box": (left, top, right, bottom),
        "line_count": len(lines),
        "font_size": font_size,
    }


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
    """Draw a mobile-safe karaoke group without clipping long German words."""

    current_word_idx = -1
    for index, word in enumerate(words_data):
        if word.start <= t <= word.end:
            current_word_idx = index
            break
    if current_word_idx == -1:
        return img

    group_size = 3
    group_start = (current_word_idx // group_size) * group_size
    group_end = min(group_start + group_size, len(words_data))
    group = words_data[group_start:group_end]
    layout = _layout_karaoke_words(
        group,
        active_index=current_word_idx - group_start,
        font_path=font_path,
        frame_size=img.size,
        base_font_size=base_font_size,
    )

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(layout["box"], radius=18, fill=(11, 30, 33, 190))
    composed = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(composed)
    for item in layout["items"]:
        draw.text(
            (item["left"], item["top"]),
            item["text"],
            font=item["font"],
            fill="#C9A227" if item["active"] else "white",
            stroke_width=2,
            stroke_fill="black",
        )
    return composed


def ensure_bg_music(mood=None):
    """
    Ensures that a local library of copyright-free background music exists,
    downloads missing curated tracks from a reliable GitHub repository,
    and returns the path to a selected track based on requested mood/variety.
    """
    import random
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    MOODS = {
        "action": [
            "Action_Preview_1.mp3",
            "action_preview_2.mp3",
            "action_preview_3.mp3",
            "action_preview_4.mp3",
            "action_preview_5.mp3"
        ],
        "chill": [
            "chill_preview_1.mp3",
            "chill_preview_2.mp3",
            "chill_preview_3.mp3",
            "chill_preview_4.mp3",
            "chill_preview_5.mp3",
            "chill_preview_6.mp3"
        ],
        "cool": [
            "cool_preview_1.mp3",
            "cool_preview_2.mp3",
            "cool_preview_3.mp3",
            "cool_preview_4.mp3",
            "cool_preview_5.mp3",
            "cool_preview_6.mp3"
        ],
        "happy": [
            "happy_preview_1.mp3",
            "happy_preview_2.mp3",
            "happy_preview_3.mp3",
            "happy_preview_4.mp3",
            "happy_preview_5.mp3",
            "happy_preview_6.mp3",
            "happy_preview_7.mp3",
            "happy_preview_8.mp3"
        ],
        "light": [
            "light_preview_1.mp3",
            "light_preview_2.mp3",
            "light_preview_3.mp3",
            "light_preview_4.mp3",
            "light_preview_5.mp3"
        ],
        "contemplative": [
            "contemplative_preview_1.mp3"
        ],
        "dark": [
            "dark_preview_1.mp3",
            "dark_preview_2.mp3",
            "dark_preview_4.mp3",
            "dark_preview_5.mp3"
        ]
    }
    
    TRACKS_TO_DOWNLOAD = []
    for tracks in MOODS.values():
        TRACKS_TO_DOWNLOAD.extend(tracks)
    
    # Download any missing tracks from the curated list
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
    for track in TRACKS_TO_DOWNLOAD:
        local_path = os.path.join(AUDIO_DIR, track)
        if not os.path.exists(local_path) or os.path.getsize(local_path) < 1000:
            url = f"https://raw.githubusercontent.com/mluedke2/app-preview-music/master/{track}"
            try:
                print(f"MUSIC: Downloading missing track {track}...")
                r = requests.get(url, headers=headers, timeout=20)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
            except Exception as e:
                print(f"WARNING: Could not download {track}: {e}")
                
    # Check existing MP3 files in the library
    existing_tracks = []
    if os.path.exists(AUDIO_DIR):
        existing_tracks = [
            os.path.join(AUDIO_DIR, f)
            for f in os.listdir(AUDIO_DIR)
            if f.lower().endswith(".mp3") and os.path.getsize(os.path.join(AUDIO_DIR, f)) > 1000
        ]
            
    # If we still have no tracks, try downloading from the old Pixabay fallback link just in case
    if not existing_tracks:
        print("MUSIC: Falling back to old Pixabay music download...")
        local_music = os.path.join(BASE_DIR, "background_finance.mp3")
        old_url = "https://cdn.pixabay.com/download/audio/2022/03/24/audio_c8c8a73467.mp3"
        try:
            r = requests.get(old_url, headers=headers, timeout=20)
            r.raise_for_status()
            with open(local_music, 'wb') as f:
                f.write(r.content)
            existing_tracks.append(local_music)
        except Exception as e:
            print(f"WARNING: Old Pixabay music fallback download failed: {e}")
            
    # If we still have no tracks, return None
    if not existing_tracks:
        print("WARNING: Background music library is empty and downloads failed. Reel will have no music.")
        return None
        
    # Return a track matching requested mood, or fallback to random
    if mood and mood in MOODS:
        allowed_names = set(MOODS[mood])
        mood_tracks = [t for t in existing_tracks if os.path.basename(t) in allowed_names]
        if mood_tracks:
            selected_track = random.choice(mood_tracks)
            print(f"MUSIC: Selected background track for mood '{mood}': {os.path.basename(selected_track)}")
            return selected_track
            
    selected_track = random.choice(existing_tracks)
    print(f"MUSIC: Selected random background track: {os.path.basename(selected_track)}")
    return selected_track

def build_reel_mp4(
    script_text,
    background_image_path,
    output_mp4_path,
    silent=False,
    duration=10.0,
    mood=None,
    hook_text=None,
):
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
    
    run_id = uuid.uuid4().hex
    prepared_background_path = os.path.join(temp_dir, f"prepared_{run_id}.png")
    _prepare_reel_background(
        background_image_path,
        prepared_background_path,
        hook_text=hook_text,
    )
    background_image_path = prepared_background_path

    audio_path = os.path.join(temp_dir, f"reel_audio_{run_id}.mp3") if not silent else None
    
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
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        left = (new_w - w) / 2
        top = (new_h - h) / 2
        img = img.crop((left, top, left + w, top + h))
        
        # 2. Draw Karaoke Subtitles (only if not silent)
        if not silent and words_data:
            img = draw_karaoke_subtitles(img, t, words_data, font_path)
        
        # 3. Add a mobile-safe progress bar above platform caption overlays.
        draw = ImageDraw.Draw(img)
        bar_height = 10
        bar_left = REEL_SAFE_X
        bar_right = w - REEL_SAFE_X
        bar_top = h - 120
        bar_width = int((bar_right - bar_left) * progress)
        draw.rounded_rectangle(
            (bar_left, bar_top, bar_right, bar_top + bar_height),
            radius=5,
            fill=(43, 63, 68),
        )
        if bar_width > 0:
            draw.rounded_rectangle(
                (bar_left, bar_top, bar_left + bar_width, bar_top + bar_height),
                radius=5,
                fill=COLORS["primary"],
            )
            
        # Run garbage collection periodically (every 2 seconds) to prevent memory leak
        if int(t * REEL_FPS) % (2 * REEL_FPS) == 0:
            import gc
            gc.collect()
            
        res = np.array(img)
        img.close()
        return res

    video_clip = img_clip.transform(animate_frame)
    if audio_clip:
        video_clip = video_clip.with_audio(audio_clip)
    
    # 3. Add background music
    music_path = ensure_bg_music(mood=mood)
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
    video_clip.write_videofile(output_mp4_path, fps=REEL_FPS, codec="libx264", audio_codec="aac" if video_clip.audio else None, preset="veryfast", threads=1, logger=None)
    print(f"REEL: Video created successfully! ({output_mp4_path})")
    
    # Cleanup temp audio
    try:
        if audio_clip:
            audio_clip.close()
        video_clip.close()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(prepared_background_path):
            os.remove(prepared_background_path)
    except Exception as e:
        print(f"WARNING: Clean-up error: {e}")

    return output_mp4_path

if __name__ == "__main__":
    # Test script for video synthesis
    test_script = "Willkommen bei Schatzsuche 4.0! Wusstest du, dass der Zinseszins dein stärkster Partner beim Vermögensaufbau ist? Wenn du monatlich nur 150€ in einen breit gestreuten ETF investierst, arbeitet dein Geld Tag und Nacht für dich. Über dreißig Jahre wächst dein Erspartes exponentiell! Starte noch heute deinen Sparplan. Folge Schatzsuche 4.0 für clevere Finanztipps!"
    build_reel_mp4(test_script, "evergreen_test.png", "reel_test.mp4")
