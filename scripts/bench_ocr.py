"""Benchmark OCR backends over a sample set: CER vs ground truth + latency.

Sample layout (per page, sharing a stem):
    <samples>/<stem>.png|jpg|...   the page image (required)
    <samples>/<stem>.txt           ground-truth text (optional; needed for CER)
    <samples>/<stem>.lang          language hint, one line (optional)

Usage:
    uv run --extra models python scripts/bench_ocr.py --samples samples/pages --backends paddle
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from app.bench.metrics import cer
from app.providers.errors import MissingBackendDependencyError
from app.providers.registry import UnknownBackendError, get_ocr_provider

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _samples(samples_dir: Path):
    for image in sorted(samples_dir.iterdir()):
        if image.suffix.lower() not in IMAGE_EXTS:
            continue
        gt_file = image.with_suffix(".txt")
        lang_file = image.with_suffix(".lang")
        ground_truth = gt_file.read_text(encoding="utf-8") if gt_file.exists() else None
        lang = lang_file.read_text(encoding="utf-8").strip() if lang_file.exists() else None
        yield image, ground_truth, lang


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", default="samples/pages", help="Directory of sample pages.")
    parser.add_argument("--backends", default="paddle", help="Comma-separated OCR backends.")
    args = parser.parse_args()

    samples_dir = Path(args.samples)
    if not samples_dir.is_dir():
        raise SystemExit(f"No samples directory: {samples_dir}")
    samples = list(_samples(samples_dir))
    if not samples:
        raise SystemExit(f"No images found in {samples_dir}")

    print(f"{'backend':<16}{'sample':<24}{'lang':<6}{'CER':>8}{'latency(s)':>12}")
    print("-" * 66)
    for backend in [b.strip() for b in args.backends.split(",") if b.strip()]:
        try:
            provider = get_ocr_provider(backend)
        except UnknownBackendError as exc:
            print(f"{backend:<16}skip — {exc}")
            continue
        latencies: list[float] = []
        cers: list[float] = []
        for image, ground_truth, lang in samples:
            try:
                started = time.perf_counter()
                result = provider.extract(image.read_bytes(), lang_hint=lang)
                elapsed = time.perf_counter() - started
            except MissingBackendDependencyError as exc:
                print(f"{backend:<16}skip — {exc}")
                break
            latencies.append(elapsed)
            score = cer(_normalize(ground_truth), _normalize(result.text)) if ground_truth else None
            if score is not None:
                cers.append(score)
            shown = f"{score:>8.3f}" if score is not None else f"{'n/a':>8}"
            print(f"{backend:<16}{image.stem:<24}{(lang or '-'):<6}{shown}{elapsed:>12.2f}")
        if latencies:
            avg_cer = f"{sum(cers) / len(cers):>8.3f}" if cers else f"{'n/a':>8}"
            avg_lat = sum(latencies) / len(latencies)
            print(f"{'  ' + backend + ' avg':<46}{avg_cer}{avg_lat:>12.2f}")


if __name__ == "__main__":
    main()
