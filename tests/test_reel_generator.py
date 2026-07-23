from types import SimpleNamespace

from PIL import Image

from src.reel_generator import (
    REEL_FPS,
    REEL_SAFE_X,
    REEL_SIZE,
    _layout_karaoke_words,
    _prepare_reel_background,
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
