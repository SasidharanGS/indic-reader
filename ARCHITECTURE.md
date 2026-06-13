# Indic Reader — Architecture Document

*Companion to `DESIGN.md`. Personal-use, provider-swappable scan-to-speech for Indian languages.*
Version 0.1 · 13 June 2026

## 1. Principles

- **KISS.** One small backend, synchronous where possible, SQLite + files for state. No microservices, no queues until book mode genuinely needs them.
- **Provider-agnostic.** OCR and TTS sit behind interfaces. Open models now; Sarvam API later by config — no pipeline changes.
- **Local-first & private.** Everything runs on my machine by default; cloud is opt-in.
- **Stream early.** Chunk text and synthesize chunk-by-chunk so audio starts fast.

## 2. System overview

```
  ┌──────────────┐      photo / commands      ┌─────────────────────────────┐
  │  Client      │ ─────────────────────────▶ │  Backend (FastAPI, local)   │
  │ Telegram bot │ ◀───────── audio + text ── │                             │
  │ (v0)         │                            │   Pipeline orchestrator     │
  └──────────────┘                            │   ┌───────────────────────┐ │
                                              │   │ OCRProvider  (iface)  │ │──▶ paddle | surya | sarvam_vision
                                              │   ├───────────────────────┤ │
                                              │   │ Text pipeline         │ │  clean → lang-detect → chunk
                                              │   ├───────────────────────┤ │
                                              │   │ TTSProvider  (iface)  │ │──▶ indic_parler | indicf5 | bulbul
                                              │   ├───────────────────────┤ │
                                              │   │ LLMProvider  (opt)    │ │──▶ sarvam_m | sarvam_translate
                                              │   └───────────────────────┘ │
                                              │  Store: SQLite + audio cache│
                                              └─────────────────────────────┘
```

## 3. Components

- **Client (v0: Telegram bot).** Receives a photo, calls the backend, returns a voice note + recognized text. Later replaced/augmented by a PWA/Flutter player for book mode.
- **Backend (FastAPI).** Thin HTTP service exposing OCR, TTS, and book/playback endpoints; hosts the pipeline orchestrator and providers.
- **Pipeline orchestrator.** Glues capture → OCR → text processing → TTS → audio; handles chunking, caching, and book assembly.
- **OCR providers.** Adapters implementing one interface: `paddle` (default), `surya` (layout-heavy), `sarvam_vision` (API, best Indic).
- **Text pipeline.** Cleanup, script/language detection, sentence/paragraph chunking, Indic + code-mix normalization.
- **TTS providers.** Adapters: `indic_parler` (default), `indicf5` (max quality), `bulbul` (Sarvam API).
- **LLM provider (optional).** `sarvam_m` / `sarvam_translate` (open weights) for summarize/translate-then-read. Off by default.
- **Store.** SQLite for metadata/state; filesystem for page images and cached audio.

## 4. Provider interfaces (the contract)

The only thing the pipeline depends on. Swapping a backend = implementing these and setting an env flag.

```python
# providers/ocr/base.py
class OCRProvider(Protocol):
    def extract(self, image: bytes, lang_hint: str | None = None) -> "OCRResult": ...
# OCRResult: { text: str, blocks: list[Block], lang: str, confidence: float }

# providers/tts/base.py
class TTSProvider(Protocol):
    def synthesize(self, text: str, lang: str, voice: str | None = None,
                   speed: float = 1.0) -> "Audio": ...
# Audio: { samples | file_path, sample_rate, duration_s }

# providers/llm/base.py   (optional)
class LLMProvider(Protocol):
    def process(self, text: str, task: str) -> str: ...   # summarize | translate | define
```

**Selection (config-driven):**

```
OCR_BACKEND   = paddle | surya | sarvam_vision      # default: paddle
TTS_BACKEND   = indic_parler | indicf5 | bulbul      # default: indic_parler
LLM_BACKEND   = none | sarvam_m | sarvam_translate   # default: none
SARVAM_API_KEY = <set only when using sarvam_* / bulbul>
DEVICE        = mps | cuda | cpu
```

A `providers/registry.py` maps these strings to classes (simple factory). The pipeline never names a concrete provider.

## 5. Model configs & compute

| Backend | Model | Runtime | Notes |
|---|---|---|---|
| `paddle` | PaddleOCR PP-OCR (per-script: `devanagari`, `ta`, `te`, `kn`, `ml`, `bn`…) | CPU ok, GPU faster | Pick recognizer by detected script |
| `surya` | Surya OCR | GPU preferred | Best layout/reading-order for dense pages |
| `sarvam_vision` | Sarvam Vision (3B) | HTTP API | ₹0.5/page; ≤10 pages/job → batch |
| `indic_parler` | `ai4bharat/indic-parler-tts` (~0.9B) | MPS/CUDA; CPU slow | Voice via text description string; 20 Indic langs |
| `indicf5` | `ai4bharat/IndicF5` | MPS/CUDA | Needs reference audio + transcript per voice; 11 langs |
| `bulbul` | Sarvam Bulbul v3 | HTTP API | ₹15–30/10k chars; REST ≤2500 chars → chunk |

**Compute targets (personal):**
1. **Local default** — Apple Silicon (`DEVICE=mps`) or NVIDIA (`DEVICE=cuda`). Free, private.
2. **No local GPU** — run the backend in a free Colab/Kaggle notebook, expose via `cloudflared`/`ngrok` tunnel; bot points at the tunnel URL.
3. **No compute at all** — hybrid: `sarvam_vision` + `bulbul` (pay-per-use); ~₹1,050–1,950/book.

## 6. Data flow

**Single page (v0)**

```
photo ─▶ OCRProvider.extract ─▶ text
      ─▶ clean() ─▶ detect_lang() ─▶ chunk() ─▶ [c1,c2,…]
      ─▶ for each chunk: TTSProvider.synthesize (cache by hash) ─▶ audio
      ─▶ concat ─▶ voice note back to client
```

**Book (v1)** — same per page, but pages are persisted, processed in the background, audio cached per chunk; the player streams cached chunks in order and writes back the playback position.

## 7. Text pipeline details

- **Clean:** strip headers/footers/page numbers, fix hyphenation/line-wraps, drop OCR noise.
- **Language/script detect:** Unicode-block heuristic per block (Devanagari/Tamil/Telugu/… ranges) → route to correct OCR recognizer and TTS language; fall back to `langid` for ambiguous Latin (English vs Hinglish).
- **Chunk:** split on sentence boundaries incl. the Devanagari danda (`।`) and standard punctuation (use `indic-nlp-library` for Indic sentence splitting); keep chunks within each TTS backend's limit (e.g., Bulbul ≤2500 chars).
- **Normalize:** expand numbers/abbreviations/symbols per language; preserve code-mix (Parler/Bulbul handle Hinglish natively).
- **Reading order:** trust Surya/Sarvam layout when used; for PaddleOCR, sort blocks top-to-bottom, left-to-right.

## 8. Persistence

SQLite (`store/db.py`) + files. Minimal schema:

```
books(id, title, lang, created_at)
pages(id, book_id, page_no, image_path, text, lang, status)
chunks(id, page_id, idx, text, audio_path, voice, backend, hash)
playback(book_id, chunk_id, offset_s, updated_at)
```

Audio cache keyed by `hash(text + voice + tts_backend + speed)` → re-synthesis is skipped on replay and across backend experiments.

## 9. Swapping to the Sarvam stack

No code changes in the pipeline — only:

1. Set `SARVAM_API_KEY`.
2. `OCR_BACKEND=sarvam_vision` and/or `TTS_BACKEND=bulbul`.
3. (Adapters already implement `OCRProvider`/`TTSProvider` via HTTP; they handle Bulbul's 2500-char and Vision's 10-page batch limits internally.)

Recommended progression: start `paddle + indic_parler` (free) → try **hybrid** `sarvam_vision + indicf5` (best Indic OCR, free local TTS) → full Sarvam `sarvam_vision + bulbul` for the "sovereign stack" demo.

## 10. Benchmark harness (the resume artifact)

`scripts/bench_ocr.py` and `scripts/bench_tts.py` run the **same** sample pages through each backend:

- OCR: **Character Error Rate** vs hand-typed ground truth, per language; latency.
- TTS: latency / real-time factor; short clips for subjective naturalness (MOS-style notes).
- Output: a comparison table (paddle vs surya vs sarvam_vision; parler vs indicf5 vs bulbul).

This produces the line that lands the interview: *"provider-agnostic Indic reading pipeline benchmarked against Sarvam's sovereign API."*

## 11. Repo layout

```
indic-reader/
  README.md  DESIGN.md  ARCHITECTURE.md
  pyproject.toml
  app/
    main.py            # FastAPI app + endpoints
    config.py          # env-driven backend selection
    pipeline.py        # capture → ocr → text → tts orchestration
    providers/
      registry.py
      ocr/   base.py  paddle.py  surya.py  sarvam_vision.py
      tts/   base.py  indic_parler.py  indicf5.py  bulbul.py
      llm/   base.py  sarvam.py            # optional
    text/  clean.py  lang_detect.py  chunk.py  normalize.py
    store/ db.py  models.py
    audio/ cache.py  concat.py
    imaging/ preprocess.py               # deskew, crop, contrast
  clients/
    telegram_bot.py    # v0
    web/               # v1 PWA (later)
  scripts/ bench_ocr.py  bench_tts.py
  samples/ pages/  ground_truth/         # test set per language
  .env.example
```

## 12. Build milestones

- **M0 — Skeleton.** FastAPI app, provider interfaces, registry, config, SQLite init.
- **M1 — Core loop.** `paddle` OCR + `indic_parler` TTS + text pipeline; one image → audio file.
- **M2 — v0 usable.** Telegram bot: photo → voice note + recognized text. *(First genuinely useful build.)*
- **M3 — Book mode.** Multi-page capture, chunk streaming, audio cache, SQLite state, resume, speed control.
- **M4 — Benchmark + Sarvam.** `sarvam_vision` and `bulbul` adapters; run the benchmark harness; document results.
- **M5 — App (stretch).** PWA/Flutter player with library and resume; optional LLM summarize/translate.

## 13. Cross-cutting concerns

- **Error handling:** OCR/TTS failures degrade gracefully (return recognized text even if TTS fails; retry API calls with backoff).
- **Config & secrets:** `.env`; never commit API keys. (Keep any `AGENTS.md`/`.claude/` out of git per repo hygiene.)
- **Privacy:** default path keeps images/audio local; cloud backends are explicit opt-in.
- **Observability:** simple structured logs + per-stage timings (feeds the benchmark).
- **Testing:** unit-test text pipeline (chunking/lang-detect) deterministically; smoke-test providers behind a `mock` backend.

## 14. Open technical questions

- Best PaddleOCR recognizer set for *my* target languages — confirm Tamil/Telugu quality on real book scans during M1.
- Parler (description voice) vs IndicF5 (reference voice) as the standing default after listening tests.
- Whether background processing in M3 needs a real task queue or a simple thread/asyncio worker suffices (start simple).
