"""Telegram bot client (v0) — photo in, recognized text + audio out.

Run it locally (needs the model backends):

    TELEGRAM_BOT_TOKEN=... uv run --extra models python -m clients.telegram_bot

The page audio is sent with ``reply_audio`` (a WAV file). Sending it as a true
Telegram voice note would need OGG/Opus encoding (ffmpeg) — left as a refinement.
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
from app.config import Settings, get_settings
from app.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Telegram's message limit is 4096 chars; leave headroom for the preview.
MAX_TEXT_PREVIEW = 3500

START_MESSAGE = (
    "Send me a photo of a page and I'll read it back to you.\n"
    "Add a caption like 'hi', 'ta' or 'te' to hint the language."
)


def build_reply(
    pipeline: Pipeline, image: bytes, lang_hint: str | None = None
) -> tuple[str, bytes]:
    """Run the pipeline and return (recognized_text, wav_bytes). Pure and testable."""
    result = pipeline.run(image, lang_hint=lang_hint)
    return result.text, to_wav_bytes(result.audio)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_MESSAGE)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    photo = message.photo[-1]  # largest available size
    tg_file = await photo.get_file()
    image = bytes(await tg_file.download_as_bytearray())
    lang_hint = (message.caption or "").strip() or None

    pipeline: Pipeline = context.bot_data["pipeline"]
    # Inference is blocking — keep the event loop responsive.
    text, wav = await asyncio.to_thread(build_reply, pipeline, image, lang_hint)

    await message.reply_text(text[:MAX_TEXT_PREVIEW] or "(no text recognized)")
    await message.reply_audio(audio=io.BytesIO(wav), filename="page.wav", title="Indic Reader")


def build_application(
    token: str | None = None,
    pipeline: Pipeline | None = None,
    settings: Settings | None = None,
) -> Application:
    """Construct the Telegram application with handlers and a shared pipeline."""
    settings = settings or get_settings()
    token = token or settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.bot_data["pipeline"] = pipeline or Pipeline(settings=settings)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_application().run_polling()


if __name__ == "__main__":
    main()
