import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.pipeline import Pipeline
from clients.telegram_bot import (
    build_application,
    build_reply,
    handle_photo,
    listen,
    newbook,
)

MOCK_SETTINGS = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")
FAKE_TOKEN = "123456789:AAEhBOI-fake-token-for-tests-only"


def _mock_pipeline() -> Pipeline:
    return Pipeline(settings=MOCK_SETTINGS)


def _photo_update(caption=None, chat_id=1):
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"image-bytes"))
    photo = MagicMock()
    photo.get_file = AsyncMock(return_value=tg_file)
    message = MagicMock()
    message.photo = [photo]
    message.caption = caption
    message.reply_text = AsyncMock()
    message.reply_audio = AsyncMock()
    update = MagicMock(message=message)
    update.effective_chat.id = chat_id
    return update, message


# --- quick read ------------------------------------------------------------


def test_build_reply_returns_text_and_wav():
    text, wav, tts_error = build_reply(_mock_pipeline(), b"image-bytes", lang_hint="hi")
    assert text
    assert tts_error is None
    assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"


def test_handle_photo_quick_read_replies_with_text_and_audio():
    update, message = _photo_update(caption="hi")
    context = MagicMock(bot_data={"pipeline": _mock_pipeline()})
    asyncio.run(handle_photo(update, context))
    message.reply_text.assert_awaited_once()
    message.reply_audio.assert_awaited_once()


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
    update, message = _photo_update()
    context = MagicMock(bot_data={"pipeline": pipeline})
    asyncio.run(handle_photo(update, context))
    assert message.reply_text.await_count == 2  # text + "audio unavailable" note
    message.reply_audio.assert_not_awaited()


# --- book mode -------------------------------------------------------------


def test_newbook_sets_active_book():
    service = MagicMock()
    service.create_book.return_value = MagicMock(id=5, title="My Book")
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock(message=message)
    update.effective_chat.id = 1
    context = MagicMock(args=["My", "Book"], bot_data={"book_service": service})

    asyncio.run(newbook(update, context))

    assert context.bot_data["active_books"][1] == 5
    message.reply_text.assert_awaited_once()


def test_listen_without_active_book_prompts_newbook():
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock(message=message)
    update.effective_chat.id = 1
    context = MagicMock(bot_data={"book_service": MagicMock()})

    asyncio.run(listen(update, context))

    assert "No active book" in message.reply_text.call_args.args[0]


def test_listen_plays_next_page_audio():
    service = MagicMock()
    service.play_next.return_value = (MagicMock(page_no=1), b"RIFF....WAVEfake")
    message = MagicMock()
    message.reply_text = AsyncMock()
    message.reply_audio = AsyncMock()
    update = MagicMock(message=message)
    update.effective_chat.id = 1
    context = MagicMock(bot_data={"book_service": service, "active_books": {1: 5}})

    asyncio.run(listen(update, context))

    service.play_next.assert_called_once_with(5)
    message.reply_audio.assert_awaited_once()


def test_photo_adds_page_when_book_active():
    service = MagicMock()
    service.add_page.return_value = MagicMock(page_no=3)
    update, message = _photo_update()
    context = MagicMock(bot_data={"book_service": service, "active_books": {1: 5}})

    asyncio.run(handle_photo(update, context))

    service.add_page.assert_called_once()
    message.reply_text.assert_awaited_once()
    message.reply_audio.assert_not_awaited()  # pages are played later via /listen


# --- wiring ----------------------------------------------------------------


def test_build_application_wires_handlers():
    app = build_application(token=FAKE_TOKEN, pipeline=_mock_pipeline(), book_service=MagicMock())
    assert app.bot_data["book_service"] is not None
    # /start, /newbook, /listen, /restart, /endbook, photo
    assert len(app.handlers[0]) == 6


def test_build_application_requires_token():
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        build_application(settings=Settings(_env_file=None, telegram_bot_token=None))
