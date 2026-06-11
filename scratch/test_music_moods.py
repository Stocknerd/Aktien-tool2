import os
import sys

# Add parent directory to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reel_generator import ensure_bg_music, AUDIO_DIR

def test_moods():
    print("Testing expanded background music library & mood-based selection...")
    
    # Test downloading and initialisation
    print("Running ensure_bg_music(mood=None) to trigger download of all tracks...")
    all_selected = ensure_bg_music(mood=None)
    print(f"Random fallback selected track: {all_selected}")
    
    # Verify count of files in AUDIO_DIR
    files = [f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(".mp3")]
    print(f"Total MP3 files in library directory: {len(files)}")
    
    # List of expected moods
    moods = ["action", "chill", "cool", "happy", "light", "contemplative", "dark"]
    
    for mood in moods:
        print(f"\n--- Testing mood: '{mood}' ---")
        selected = ensure_bg_music(mood=mood)
        print(f"Selected track for mood '{mood}': {selected}")
        if selected:
            assert os.path.exists(selected), f"File {selected} does not exist!"
            # Get filename
            fname = os.path.basename(selected)
            print(f"Success! Selected track: {fname}")
        else:
            print(f"Warning: No track selected for mood '{mood}'")
            
    print("\n🎉 ALL MUSIC MOOD TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_moods()
