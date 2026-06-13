import pytest

from app.config import Settings
from app.providers.ocr.base import OCRProvider, OCRResult
from app.providers.registry import (
    UnknownBackendError,
    get_ocr_provider,
    get_tts_provider,
)
from app.providers.tts.base import Audio, TTSProvider


def test_mock_ocr_selected_by_name():
    provider = get_ocr_provider("mock")
    assert isinstance(provider, OCRProvider)
    result = provider.extract(b"image-bytes", lang_hint="hi")
    assert isinstance(result, OCRResult)
    assert result.lang == "hi"
    assert result.text


def test_mock_tts_selected_by_name():
    provider = get_tts_provider("mock")
    assert isinstance(provider, TTSProvider)
    audio = provider.synthesize("hello world", lang="en")
    assert isinstance(audio, Audio)
    assert audio.duration_s > 0


def test_selection_falls_back_to_settings():
    settings = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")
    assert isinstance(get_ocr_provider(settings=settings), OCRProvider)
    assert isinstance(get_tts_provider(settings=settings), TTSProvider)


def test_unimplemented_backend_raises_clearly():
    with pytest.raises(UnknownBackendError, match="paddle"):
        get_ocr_provider("paddle")
    with pytest.raises(UnknownBackendError, match="bulbul"):
        get_tts_provider("bulbul")
