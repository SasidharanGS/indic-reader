import pytest

from app.config import Settings
from app.providers.ocr.base import OCRProvider, OCRResult
from app.providers.ocr.paddle import PaddleOCRProvider
from app.providers.registry import (
    UnknownBackendError,
    get_ocr_provider,
    get_tts_provider,
)
from app.providers.tts.base import Audio, TTSProvider
from app.providers.tts.indic_parler import IndicParlerProvider


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


def test_default_backends_are_registered():
    # Instantiating these is cheap — the heavy model import is deferred to use.
    assert isinstance(get_ocr_provider("paddle"), PaddleOCRProvider)
    assert isinstance(get_tts_provider("indic_parler"), IndicParlerProvider)


def test_unwired_backend_raises_clearly():
    with pytest.raises(UnknownBackendError, match="surya"):
        get_ocr_provider("surya")
    with pytest.raises(UnknownBackendError, match="indicf5"):
        get_tts_provider("indicf5")
