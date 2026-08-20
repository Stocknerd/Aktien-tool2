import ast
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import src.reel_generator as reel_generator
from src.reel_generator import (
    REEL_FPS,
    REEL_SAFE_X,
    REEL_SIZE,
    _layout_karaoke_words,
    _prepare_reel_background,
    build_music_only_reel,
)


def test_reel_background_is_always_normalized_to_native_vertical_size(tmp_path):
    source = tmp_path / "source.png"
    destination = tmp_path / "prepared.png"
    Image.new("RGB", (1024, 1792), "white").save(source)

    _prepare_reel_background(
        source,
        destination,
        hook_text="Chance oder Value Trap?",
    )

    with Image.open(destination) as rendered:
        assert rendered.size == REEL_SIZE
    assert REEL_FPS == 30


def test_reel_hook_keeps_background_sharp_outside_local_text_panel(tmp_path):
    source = tmp_path / "sharp-source.png"
    destination = tmp_path / "prepared.png"
    checkerboard = Image.new("RGB", (2, 2))
    checkerboard.putdata([(0, 0, 0), (255, 255, 255), (255, 255, 255), (0, 0, 0)])
    image = checkerboard.resize(REEL_SIZE, Image.Resampling.NEAREST)
    image.save(source)

    _prepare_reel_background(source, destination, hook_text="Chance oder Value Trap?")

    with Image.open(source) as original, Image.open(destination) as rendered:
        unaffected_box = (160, 1000, 920, 1700)
        assert rendered.crop(unaffected_box).tobytes() == original.crop(unaffected_box).tobytes()


def test_karaoke_layout_keeps_long_german_finance_words_inside_mobile_safe_area():
    words = [
        SimpleNamespace(word="DIVIDENDENWIEDERANLAGE"),
        SimpleNamespace(word="ZINSESZINSEFFEKT"),
        SimpleNamespace(word="STEUERFREIBETRAG"),
    ]

    layout = _layout_karaoke_words(
        words,
        active_index=1,
        font_path="fonts/Outfit-Bold.ttf",
        frame_size=REEL_SIZE,
    )

    assert 1 <= layout["line_count"] <= 2
    assert layout["box"][0] >= REEL_SAFE_X
    assert layout["box"][2] <= REEL_SIZE[0] - REEL_SAFE_X
    for item in layout["items"]:
        assert item["left"] >= REEL_SAFE_X
        assert item["right"] <= REEL_SIZE[0] - REEL_SAFE_X


def test_music_only_reel_never_requests_voice_or_karaoke(monkeypatch):
    captured = {}

    def fake_build_reel_mp4(**kwargs):
        captured.update(kwargs)
        return kwargs["output_mp4_path"]

    monkeypatch.setattr(reel_generator, "build_reel_mp4", fake_build_reel_mp4)

    result = build_music_only_reel(
        background_image_path="picture.png",
        output_mp4_path="reel.mp4",
        duration=15.0,
        mood="happy",
    )

    assert result == "reel.mp4"
    assert captured["script_text"] is None
    assert captured["silent"] is True
    assert captured["music_required"] is True
    assert captured["hook_text"] is None


def test_ai_track_is_wired_to_music_only_reels():
    source = Path("src/social_reels_autoposter.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    run_track = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_track_ai"
    )
    call_names = {
        node.func.id
        for node in ast.walk(run_track)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "build_music_only_reel" in call_names
    assert "build_reel_mp4" not in call_names
