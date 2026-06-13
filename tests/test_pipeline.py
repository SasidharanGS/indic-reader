from app.config import Settings
from app.pipeline import Pipeline
from app.providers.ocr.base import Block, OCRResult
from app.providers.tts.base import Audio
from app.providers.tts.mock import MockTTSProvider

MOCK_SETTINGS = Settings(_env_file=None, ocr_backend="mock", tts_backend="mock")


class FakeOCR:
    """OCR stub returning fixed text, to drive chunking deterministically."""

    def __init__(self, text: str) -> None:
        self.text = text

    def extract(self, image: bytes, lang_hint: str | None = None) -> OCRResult:
        return OCRResult(text=self.text, lang="en", confidence=1.0, blocks=[Block(self.text)])


class CountingTTS(MockTTSProvider):
    """Mock TTS that records how many times it was asked to synthesize."""

    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, text, lang, voice=None, speed=1.0) -> Audio:
        self.calls += 1
        return super().synthesize(text, lang, voice=voice, speed=speed)


def test_run_produces_text_and_audio_with_mocks():
    pipe = Pipeline(settings=MOCK_SETTINGS)
    result = pipe.run(b"image-bytes")
    assert result.text
    assert result.lang == "en"
    assert result.chunks
    assert result.audio.duration_s > 0


def test_lang_hint_overrides_detection():
    pipe = Pipeline(ocr=FakeOCR("नमस्ते दुनिया।"), tts=CountingTTS(), settings=MOCK_SETTINGS)
    result = pipe.run(b"x", lang_hint="hi")
    assert result.lang == "hi"


def test_multi_sentence_text_is_chunked():
    pipe = Pipeline(
        ocr=FakeOCR("One. Two. Three. Four."),
        tts=CountingTTS(),
        settings=MOCK_SETTINGS,
        max_chars=10,
    )
    result = pipe.run(b"x")
    assert len(result.chunks) > 1
    assert all(len(c) <= 10 for c in result.chunks)


def test_second_run_hits_cache_and_skips_resynthesis():
    tts = CountingTTS()
    pipe = Pipeline(ocr=FakeOCR("One. Two. Three."), tts=tts, settings=MOCK_SETTINGS, max_chars=8)
    first = pipe.run(b"x")
    calls_after_first = tts.calls
    assert calls_after_first == len(first.chunks)
    assert first.cache_hits == 0

    second = pipe.run(b"x")
    assert second.cache_hits == len(second.chunks)
    assert tts.calls == calls_after_first  # no new synthesis
