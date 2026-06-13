# Indic Reader

*Take a photo of a page → AI reads it aloud. Indian languages included.*

A personal scan-to-speech reader for "listening" to physical books — especially Indian-language print that has no audiobook. Snap a page (or a whole book), get natural narration you can pause and resume.

**Status:** Working end-to-end — M0–M4 done: provider-swappable pipeline (PaddleOCR + Indic Parler-TTS, verified on real models), a Telegram bot, book mode with resume, optional OCR preprocessing, and a benchmark harness with a Sarvam Bulbul adapter. See the docs below.

## Why

Existing apps each miss half the problem: great English book-listening but weak/robotic Indian voices (Speechify, NaturalReader), great voices but no physical-page scanning (ElevenLabs Reader), or single-page accessibility utilities with no real book experience (Seeing AI, Lookout). Nothing nails *scan a physical Indian-language book → natural narration → resume-able audiobook*.

## Default stack (personal use)

Everything runs locally and free by default; the pipeline is provider-swappable so the Sarvam sovereign stack can be dropped in later via a config flag.

| Stage | Default (free, local) | Swap-in later |
|---|---|---|
| OCR | PaddleOCR | Sarvam Vision (best Indic OCR, ₹0.5/page) |
| TTS | AI4Bharat Indic Parler-TTS | AI4Bharat IndicF5 (max quality) / Sarvam Bulbul |
| Client | Telegram bot (v0) | PWA / Flutter app |

## Running the default backends (M1)

The OCR/TTS models are heavy, so they live in an optional `models` extra rather
than the base install — `uv sync` and CI stay light. Install them when you want
the real stack:

```bash
uv sync --extra models   # PaddleOCR + Indic Parler-TTS (torch, transformers, …)
```

Then run one page through the pipeline (`--extra models` keeps the models in the
environment while running):

```bash
OCR_BACKEND=paddle TTS_BACKEND=indic_parler \
    uv run --extra models python scripts/demo_page.py path/to/page.jpg --lang hi --out out.wav
```

Selecting a backend without the `models` extra installed raises a clear error
naming the command above.

## Telegram bot (v0)

Drive the pipeline from your phone — send a photo, get the recognized text +
narration back:

```bash
export TELEGRAM_BOT_TOKEN=<token from @BotFather>
uv run --extra models python -m clients.telegram_bot
```

**Quick read:** send a page photo (optionally caption it with a language hint
like `hi` / `ta`). The bot replies with the recognized text and a WAV.

**Book mode:** `/newbook <title>` starts a book; photos you then send are added
as pages. `/listen` plays the next page (one clip per page) and resumes where
you stopped; `/restart` replays from page 1; `/endbook` leaves book mode. Books,
pages, and synthesized audio are persisted (SQLite + `data/audio_cache/`), so
audio is reused and playback resumes across restarts.

## Documentation

- [`DESIGN.md`](./DESIGN.md) — problem, goals, scope, chosen config, UX flows, risks.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — components, provider interfaces, data flow, model configs, persistence, swap-to-Sarvam, repo layout, milestones.

Background research (market teardown + cost/open-source analysis) lives in the sibling `research` folder: `cost-and-open-source-stack.md` and `scan-to-speech-competitor-teardown.md`.

## Roadmap

- **M0** ✅ Backend skeleton: provider interfaces, registry, config, SQLite init.
- **M1** ✅ Core loop: PaddleOCR + Indic Parler-TTS, one image → audio.
- **M2** ✅ Telegram bot (photo → text + audio). *First genuinely usable build.*
- **M3** ✅ Book mode: multi-page capture, on-disk audio cache, resume, persistence.
- **M4** ✅ Benchmark harness (CER / latency / RTF) + Sarvam **Bulbul** TTS adapter. *(Sarvam Vision OCR — a batch API — tracked in [#30](https://github.com/SasidharanGS/indic-reader/issues/30).)*
- **M5** — App (PWA/Flutter) + optional LLM summarize/translate (stretch).

Also shipped: optional OCR preprocessing (deskew / contrast / crop) via `PREPROCESS_IMAGES=true`.
