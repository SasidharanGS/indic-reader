"""Image preprocessing to improve OCR on real book photos (ARCHITECTURE.md §10).

Grayscale → contrast stretch → deskew → autocrop. Deskew uses the classic
projection-profile method: rotate over a small angle range and pick the angle
that maximizes the variance of the row-sum profile (sharp peaks = text rows
aligned horizontally). Pillow + numpy are base dependencies.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageChops, ImageOps

_BILINEAR = Image.Resampling.BILINEAR


def load_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def to_grayscale(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img)


def enhance_contrast(img: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(img)


def autocrop(img: Image.Image, border: int = 12) -> Image.Image:
    """Trim to the bounding box of non-white content, keeping a small margin."""
    gray = img.convert("L")
    bbox = ImageChops.invert(gray).getbbox()
    if bbox is None:
        return img
    width, height = img.size
    left, top, right, bottom = bbox
    box = (
        max(0, left - border),
        max(0, top - border),
        min(width, right + border),
        min(height, bottom + border),
    )
    return img.crop(box)


def estimate_skew(img: Image.Image, limit: float = 8.0, step: float = 0.5) -> float:
    """Best correction angle (degrees) via projection-profile variance."""
    gray = img.convert("L")
    gray.thumbnail((800, 800))  # estimate on a downscaled copy for speed
    ink = 255.0 - np.asarray(gray, dtype=np.float64)
    base = Image.fromarray(ink.astype(np.uint8))

    best_angle, best_score = 0.0, -1.0
    angle = -limit
    while angle <= limit + 1e-9:
        rotated = np.asarray(base.rotate(angle, resample=_BILINEAR, fillcolor=0), dtype=np.float64)
        score = float(np.var(rotated.sum(axis=1)))
        if score > best_score:
            best_score, best_angle = score, angle
        angle += step
    return best_angle


def deskew(img: Image.Image) -> Image.Image:
    angle = estimate_skew(img)
    if abs(angle) < 0.25:
        return img
    return img.rotate(angle, resample=_BILINEAR, fillcolor=255, expand=True)


def preprocess(data: bytes) -> bytes:
    """Full preprocessing pass; returns PNG bytes ready for OCR."""
    img = enhance_contrast(to_grayscale(load_image(data)))
    img = autocrop(deskew(img))
    out = io.BytesIO()
    img.convert("L").save(out, format="PNG")
    return out.getvalue()
