"""Benchmark TTS backends: latency, real-time factor, and sample clips.

Reads one prompt per line from a texts file (``<lang>\\t<text>`` or just ``<text>``,
defaulting the language to ``en``). Writes ``<out>/<backend>_<n>.wav`` per prompt.

Usage:
    uv run --extra models python scripts/bench_tts.py \
        --texts samples/tts.tsv --backends indic_parler
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.audio.wav import to_wav_bytes
from app.bench.metrics import real_time_factor
from app.providers.errors import MissingBackendDependencyError
from app.providers.registry import UnknownBackendError, get_tts_provider


def _prompts(texts_file: Path) -> list[tuple[str, str]]:
    prompts: list[tuple[str, str]] = []
    for line in texts_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        lang, _, text = line.partition("\t")
        prompts.append((lang, text) if text else ("en", lang))
    return prompts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texts", default="samples/tts.tsv", help="Prompts file.")
    parser.add_argument("--backends", default="indic_parler", help="Comma-separated TTS backends.")
    parser.add_argument("--out", default="bench_out", help="Directory for sample clips.")
    args = parser.parse_args()

    texts_file = Path(args.texts)
    if not texts_file.is_file():
        raise SystemExit(f"No texts file: {texts_file}")
    prompts = _prompts(texts_file)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'backend':<16}{'lang':<6}{'audio(s)':>10}{'proc(s)':>10}{'RTF':>8}")
    print("-" * 50)
    for backend in [b.strip() for b in args.backends.split(",") if b.strip()]:
        try:
            provider = get_tts_provider(backend)
        except UnknownBackendError as exc:
            print(f"{backend:<16}skip — {exc}")
            continue
        for idx, (lang, text) in enumerate(prompts):
            try:
                started = time.perf_counter()
                audio = provider.synthesize(text, lang=lang)
                elapsed = time.perf_counter() - started
            except MissingBackendDependencyError as exc:
                print(f"{backend:<16}skip — {exc}")
                break
            (out_dir / f"{backend}_{idx}.wav").write_bytes(to_wav_bytes(audio))
            rtf = real_time_factor(elapsed, audio.duration_s)
            print(f"{backend:<16}{lang:<6}{audio.duration_s:>10.2f}{elapsed:>10.2f}{rtf:>8.2f}")


if __name__ == "__main__":
    main()
