import io

from PIL import Image, ImageDraw

from app.config import Settings
from app.imaging.preprocess import (
    autocrop,
    estimate_skew,
    preprocess,
    to_grayscale,
)
from app.pipeline import Pipeline


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_to_grayscale_mode():
    assert to_grayscale(Image.new("RGB", (10, 10), "white")).mode == "L"


def test_autocrop_trims_margins():
    img = Image.new("L", (100, 100), 255)
    ImageDraw.Draw(img).rectangle([40, 40, 60, 60], fill=0)
    cropped = autocrop(img, border=2)
    assert cropped.size[0] < 100 and cropped.size[1] < 100


def test_estimate_skew_straight_image_near_zero():
    img = Image.new("L", (220, 220), 255)
    draw = ImageDraw.Draw(img)
    for y in range(20, 220, 20):
        draw.line([(10, y), (210, y)], fill=0, width=3)
    assert abs(estimate_skew(img)) <= 1.0


def test_preprocess_returns_png_bytes():
    img = Image.new("RGB", (160, 90), "white")
    ImageDraw.Draw(img).text((10, 35), "Hello world", fill="black")
    out = preprocess(_png(img))
    assert out[:8] == b"\x89PNG\r\n\x1a\n"


def test_pipeline_with_preprocess_enabled_runs():
    img = Image.new("RGB", (160, 90), "white")
    ImageDraw.Draw(img).text((10, 35), "Hello world", fill="black")
    settings = Settings(
        _env_file=None, ocr_backend="mock", tts_backend="mock", preprocess_images=True
    )
    result = Pipeline(settings=settings).run(_png(img))
    assert result.text  # preprocessing ran, then mock OCR produced text
