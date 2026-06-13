"""Run one page image through the pipeline and write a WAV. Local M1 verification.

Install the default backends first (see README), then:

    OCR_BACKEND=paddle TTS_BACKEND=indic_parler \\
        uv run python scripts/demo_page.py path/to/page.jpg --lang hi --out out.wav

Backends come from config/env, so this exercises whatever OCR_BACKEND /
TTS_BACKEND are set to (defaults: paddle + indic_parler).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.audio.wav import to_wav_bytes
from app.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Image -> recognized text + narration WAV.")
    parser.add_argument("image", help="Path to a page image (jpg/png).")
    parser.add_argument("--lang", default=None, help="Language hint, e.g. hi/ta/te (optional).")
    parser.add_argument("--out", default="out.wav", help="Output WAV path.")
    args = parser.parse_args()

    image = Path(args.image).read_bytes()
    result = Pipeline().run(image, lang_hint=args.lang)

    print(f"Detected language: {result.lang}")
    print(f"Chunks: {len(result.chunks)}")
    print("Recognized text:")
    print(result.text)

    audio = result.audio
    Path(args.out).write_bytes(to_wav_bytes(audio))
    print(f"Wrote {args.out} ({audio.duration_s:.1f}s @ {audio.sample_rate} Hz)")


if __name__ == "__main__":
    main()
