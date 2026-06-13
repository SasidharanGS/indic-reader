import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.pipeline import Pipeline
from clients.telegram_bot import build_application, build_reply, handle_photo

MOCK_SETTINGS = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")
FAKE_TOKEN = "123456789:AAEhBOI-fake-token-for-tests-only"


def _mock_pipeline() -> Pipeline:
    return Pipeline(settings=MOCK_SETTINGS)


def test_build_reply_returns_text_and_wav():
    text, wav, tts_error = build_reply(_mock_pipeline(), b"image-bytes", lang_hint="hi")
    assert text
    assert tts_error is None
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"  # valid WAV header


def test_handle_photo_replies_with_text_and_audio():
    pipeline = _mock_pipeline()

    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"image-bytes"))
    photo = MagicMock()
    photo.get_file = AsyncMock(return_value=tg_file)

    message = MagicMock()
    message.photo = [photo]
    message.caption = "hi"
    message.reply_text = AsyncMock()
    message.reply_audio = AsyncMock()

    update = MagicMock(message=message)
    context = MagicMock(bot_data={"pipeline": pipeline})

    asyncio.run(handle_photo(update, context))

    message.reply_text.assert_awaited_once()
    assert message.reply_text.call_args.args[0]  # non-empty recognized text
    message.reply_audio.assert_awaited_once()


def test_build_application_wires_handlers():
    app = build_application(token=FAKE_TOKEN, pipeline=_mock_pipeline())
    assert app.bot_data["pipeline"] is not None
    assert len(app.handlers[0]) == 2  # /start + photo handler


def test_build_application_requires_token():
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        build_application(settings=Settings(_env_file=None, telegram_bot_token=None))


def test_handle_photo_degrades_to_text_when_audio_missing():
    from app.pipeline import PageResult

    pipeline = MagicMock()
    pipeline.run.return_value = PageResult(
        text="recognized text",
        lang="en",
        chunks=["recognized text"],
        audio=None,
        cache_hits=0,
        tts_error="model is gated",
    )

    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"img"))
    photo = MagicMock()
    photo.get_file = AsyncMock(return_value=tg_file)

    message = MagicMock()
    message.photo = [photo]
    message.caption = None
    message.reply_text = AsyncMock()
    message.reply_audio = AsyncMock()

    update = MagicMock(message=message)
    context = MagicMock(bot_data={"pipeline": pipeline})

    asyncio.run(handle_photo(update, context))

    assert message.reply_text.await_count == 2  # recognized text + "audio unavailable" note
    message.reply_audio.assert_not_awaited()
