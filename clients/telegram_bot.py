"""Telegram bot client (v0) — quick single-page reads + book mode.

Run it locally (needs the model backends):

    TELEGRAM_BOT_TOKEN=... uv run --extra models python -m clients.telegram_bot

Quick read: send a photo with no active book → recognized text + narration.
Book mode: /newbook <title>, then photos add pages; /listen plays the next page
and resumes where you stopped; /restart replays from page 1; /endbook exits.

Audio is sent via ``reply_audio`` (WAV); true voice notes would need OGG/Opus.
"""

from __future__ import annotations

import asyncio
import io
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.audio.wav import to_wav_bytes
from app.book import BookService
from app.config import Settings, get_settings
from app.pipeline import Pipeline
from app.store.db import init_db

logger = logging.getLogger(__name__)

# Telegram's message limit is 4096 chars; leave headroom for the preview.
MAX_TEXT_PREVIEW = 3500

START_MESSAGE = (
    "📖 Indic Reader\n\n"
    "• Send a photo of a page → I read it back (text + audio).\n"
    "• /newbook <title> — start a book; your photos then add pages.\n"
    "• /listen — play the next page (resumes where you stopped).\n"
    "• /restart — replay from page 1.   /endbook — leave book mode.\n\n"
    "Tip: caption a photo with a language hint like 'hi', 'ta' or 'te'."
)


def build_reply(
    pipeline: Pipeline, image: bytes, lang_hint: str | None = None
) -> tuple[str, bytes | None, str | None]:
    """Run the pipeline → (recognized_text, wav_bytes | None, tts_error). Testable."""
    result = pipeline.run(image, lang_hint=lang_hint)
    wav = to_wav_bytes(result.audio) if result.audio is not None else None
    return result.text, wav, result.tts_error


def _active_book(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int | None:
    return context.bot_data.setdefault("active_books", {}).get(chat_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_MESSAGE)


async def newbook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    title = " ".join(context.args).strip() if context.args else "Untitled book"
    service: BookService = context.bot_data["book_service"]
    book = await asyncio.to_thread(service.create_book, title)
    context.bot_data.setdefault("active_books", {})[update.effective_chat.id] = book.id
    await update.message.reply_text(
        f'📖 Started "{book.title}" (#{book.id}). Send photos to add pages, then /listen.'
    )


async def endbook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data.setdefault("active_books", {}).pop(update.effective_chat.id, None)
    await update.message.reply_text("Closed the book. Photos are quick single-page reads again.")


async def listen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    book_id = _active_book(context, update.effective_chat.id)
    if book_id is None:
        await update.message.reply_text("No active book. Start one with /newbook <title>.")
        return
    service: BookService = context.bot_data["book_service"]
    result = await asyncio.to_thread(service.play_next, book_id)
    if result is None:
        await update.message.reply_text("🔚 End of the book. /restart to play from the beginning.")
        return
    page, wav = result
    await update.message.reply_text(f"▶️ Page {page.page_no}")
    if wav is not None:
        await update.message.reply_audio(
            audio=io.BytesIO(wav), filename=f"page{page.page_no}.wav", title="Indic Reader"
        )


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    book_id = _active_book(context, update.effective_chat.id)
    if book_id is None:
        await update.message.reply_text("No active book. Start one with /newbook <title>.")
        return
    service: BookService = context.bot_data["book_service"]
    await asyncio.to_thread(service.restart, book_id)
    await update.message.reply_text("⏮️ Back to the start. /listen to play page 1.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    photo = message.photo[-1]  # largest available size
    tg_file = await photo.get_file()
    image = bytes(await tg_file.download_as_bytearray())
    lang_hint = (message.caption or "").strip() or None

    book_id = _active_book(context, update.effective_chat.id)
    if book_id is not None:
        service: BookService = context.bot_data["book_service"]
        page = await asyncio.to_thread(service.add_page, book_id, image, lang_hint)
        await message.reply_text(f"✅ Added page {page.page_no}. Send more, or /listen.")
        return

    # Quick single-page read.
    pipeline: Pipeline = context.bot_data["pipeline"]
    text, wav, tts_error = await asyncio.to_thread(build_reply, pipeline, image, lang_hint)
    await message.reply_text(text[:MAX_TEXT_PREVIEW] or "(no text recognized)")
    if wav is not None:
        await message.reply_audio(audio=io.BytesIO(wav), filename="page.wav", title="Indic Reader")
    elif tts_error:
        await message.reply_text(f"⚠️ Audio unavailable: {tts_error[:300]}")


def build_application(
    token: str | None = None,
    pipeline: Pipeline | None = None,
    book_service: BookService | None = None,
    settings: Settings | None = None,
) -> Application:
    """Construct the Telegram application with handlers, pipeline, and book service."""
    settings = settings or get_settings()
    token = token or settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.bot_data["pipeline"] = pipeline or Pipeline(settings=settings)
    application.bot_data["book_service"] = book_service or BookService(
        init_db(check_same_thread=False), settings=settings
    )
    application.bot_data["active_books"] = {}

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newbook", newbook))
    application.add_handler(CommandHandler("listen", listen))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("endbook", endbook))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_application().run_polling()


if __name__ == "__main__":
    main()
