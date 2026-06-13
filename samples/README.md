# Benchmark samples

Drop your own test material here (real book scans are yours to add — they aren't
committed). The benchmark scripts read from this layout.

## OCR (`scripts/bench_ocr.py`)

`samples/pages/`, one set of files per page sharing a stem:

```
samples/pages/ta_ponniyin_p1.png    # the page image (required)
samples/pages/ta_ponniyin_p1.txt    # hand-typed ground truth (optional; needed for CER)
samples/pages/ta_ponniyin_p1.lang   # language hint, e.g. "ta" (optional)
```

Run:

```bash
uv run --extra models python scripts/bench_ocr.py --samples samples/pages --backends paddle
# once the Sarvam adapter lands: --backends paddle,sarvam_vision
```

## TTS (`scripts/bench_tts.py`)

A prompts file, one prompt per line as `<lang>\t<text>` (tab-separated; language
defaults to `en` if omitted), e.g. `samples/tts.tsv`:

```
hi	नमस्ते, यह एक परीक्षण है।
ta	வணக்கம், இது ஒரு சோதனை.
en	Hello, this is a benchmark prompt.
```

Run:

```bash
uv run --extra models python scripts/bench_tts.py --texts samples/tts.tsv --backends indic_parler
```

Each script prints per-sample numbers and a per-backend summary (CER + latency
for OCR; latency + real-time factor for TTS), so you can compare the open stack
against Sarvam Vision / Bulbul on the *same* inputs.
