# Indic Reader — Design Document

*Working title. Take a photo of a page → AI reads it aloud, Indian languages included. Personal use.*
Version 0.1 · 13 June 2026

## 1. Problem

I want to "read" books by listening, including ones with no audiobook, and including Indian-language print. Existing apps are either great at English book-listening but weak/robotic in Indian languages (Speechify, NaturalReader), great voices but no physical-page scanning (ElevenLabs Reader), or single-page accessibility utilities with no real book experience (Seeing AI, Lookout). Nothing nails *scan a physical Indian-language book → natural narration → resume-able audiobook*.

## 2. Goals

- Point phone at a page (or a stack of pages) and get natural-sounding narration.
- First-class **Indian-language** support — Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Bengali, etc. — plus English and code-mixed (Hinglish) text.
- **Book mode**: capture many pages, listen continuously, resume where I left off.
- Runs **free** on my own hardware; my books never leave my machine.
- **Provider-swappable**: open models now, drop in Sarvam's sovereign API (Vision OCR + Bulbul TTS) later by changing a config flag — no rewrite.

## 3. Non-goals (for now)

- Not a commercial product, not multi-user, no accounts/billing.
- Not real-time live-camera reading (capture-then-listen is fine).
- Not a general document/PDF manager; books and pages are the unit.
- No cloud account required to use it (cloud is optional, opt-in).

## 4. User & use cases

Single user (me). Primary scenarios:

- **Quick read** — snap one page, hear it immediately. (The "v0" loop.)
- **Read a book** — photograph chapters over time, build a listenable book, pause/resume across sessions, adjust speed.
- **Mixed-language material** — a page with Hindi + English; it detects script and narrates correctly.

## 5. Scope & phasing

- **v0 — Prove the loop (usable in days).** Telegram bot: send a photo → get a voice note back. PaddleOCR → Indic Parler-TTS. No library, no resume. This is the smallest thing that's actually useful and validates OCR/TTS quality on real pages.
- **v1 — Book mode.** Multi-page capture, continuous playback, chapters, resume position, speed control, audio caching. SQLite-backed state. Still bot-first; optional simple web/app player.
- **Later — Polish & swap.** Benchmark harness (open stack vs Sarvam), hybrid OCR (Sarvam Vision for hard scans), proper mobile app/PWA, optional summarize/translate via open Sarvam LLMs.

## 6. Chosen configuration & rationale (best picks for personal use)

Because this is personal, non-commercial licenses (Coqui, Meta MMS) are *allowed* — so choices are made purely on quality/simplicity, not licensing.

| Decision | Pick | Why |
|---|---|---|
| **Client (v0)** | **Telegram bot** | Works on any phone, zero app-store friction, trivial to build, great capture+playback UX (photo in, voice note out). Best effort-to-value ratio. |
| **Client (v1+)** | PWA or Flutter app | Only once the loop is proven and book mode needs a real player/library. |
| **OCR (default)** | **PaddleOCR** | Free (Apache 2.0), 100+ languages incl. Devanagari/Tamil/Telugu, good layout handling. Strong all-rounder. |
| **OCR (hard scans)** | **Sarvam Vision** (API, opt-in) | Best Indic OCR (84.3% olmOCR, beats Gemini/GPT-4) and *cheap* at ₹0.5/page. Use only when open OCR struggles. |
| **TTS (default)** | **AI4Bharat Indic Parler-TTS** | Apache 2.0, 20 Indic languages + English, voice chosen by text description (no reference clip to manage) → consistent voice across a whole book. Simplest good option. |
| **TTS (max quality)** | **AI4Bharat IndicF5** | Near-human naturalness; needs a reference audio clip + transcript per voice. Use when I want the best sound. |
| **LLM (optional)** | Sarvam-M / Sarvam-Translate (open weights) | For optional summarize/define/translate-then-read. Off by default (KISS). |
| **Compute** | My own computer (Apple Silicon MPS or NVIDIA GPU); free Colab/Kaggle as fallback | Free, private, good enough for one user. |

**Default runtime config:** `OCR=paddle`, `TTS=indic_parler`, fully local. **Best-quality personal config:** `OCR=sarvam_vision` (hybrid, ~₹150/book) + `TTS=indicf5` local. Both reachable by config flags.

## 7. UX flows

**Quick read (v0)**
1. Snap a photo of a page, send to the bot.
2. Bot detects script/language, runs OCR, cleans text, synthesizes audio.
3. Bot replies with a voice note + the recognized text (so I can spot OCR errors).

**Read a book (v1)**
1. Create a book ("Ponniyin Selvan vol.1"), photograph pages as I go.
2. Each page is OCR'd + chunked + synthesized in the background; audio is cached.
3. I hit play; it streams chunk-by-chunk, remembers my position, lets me change speed and skip by sentence/page/chapter.

## 8. Success criteria

- **Quality:** OCR good enough that <~1 obvious error per paragraph on a clean printed page; TTS pleasant enough to listen to for 20+ minutes without fatigue.
- **Latency:** single page → audio in a few seconds on my hardware; book pages process in the background.
- **Reliability:** resume always lands within a sentence of where I stopped.
- **Cost:** ₹0 in default mode; <₹200/book if I opt into Sarvam OCR.
- **Swap test:** flipping to the Sarvam backend requires only env/config changes.

## 9. Assumptions

- I have a computer capable of running ~1B-param models (Apple Silicon or a GPU), or I'll use free Colab/Kaggle for heavier runs.
- Source material is mostly printed (not handwritten); handwriting is out of scope for v0/v1.
- Listening, not perfect transcription, is the goal — minor OCR slips are tolerable.

## 10. Risks & mitigations

- **Indic OCR on real book scans is the hard part** (lighting, curvature, conjunct characters). → Add image pre-processing (deskew, crop, contrast); keep Sarvam Vision as the quality escape hatch.
- **Open TTS naturalness trails Bulbul/ElevenLabs.** → Default to Parler for consistency, offer IndicF5 for quality; A/B and pick per language.
- **Compute/latency on a laptop.** → Chunk + stream audio so playback starts before the whole page is synthesized; cache aggressively.
- **Scope creep into a "real app" too early.** → Stay bot-first until the core loop genuinely delights me.

## 11. Decisions to revisit

- Telegram bot vs a minimal PWA for v0 (bot wins on speed-to-build; revisit if playback control feels limiting).
- Parler vs IndicF5 as the standing default once tested on my actual languages.
- Whether to add the optional LLM layer at all.

See `ARCHITECTURE.md` for components, interfaces, data flow, and the build plan.
