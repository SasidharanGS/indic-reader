import base64

import pytest

from app.audio.wav import to_wav_bytes
from app.config import Settings
from app.providers.errors import ModelAccessError
from app.providers.tts import bulbul
from app.providers.tts.base import Audio
from app.providers.tts.bulbul import BulbulProvider, _decode_wav_base64, _target_language


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Stand-in for an httpx client; records calls, returns canned audios."""

    def __init__(self, audios):
        self._audios = audios
        self.calls = []

    def post(self, url, headers=None, json=None):
        self.calls.append((url, headers, json))
        return FakeResponse({"audios": self._audios})


def test_target_language_maps_to_bcp47():
    assert _target_language("hi") == "hi-IN"
    assert _target_language("ta") == "ta-IN"
    assert _target_language("zz") == "en-IN"  # fallback


def test_decode_wav_base64_roundtrip():
    clip = Audio(sample_rate=22050, duration_s=0.0, samples=b"\x01\x02\x03\x04")
    encoded = base64.b64encode(to_wav_bytes(clip)).decode()
    decoded = _decode_wav_base64(encoded)
    assert decoded.sample_rate == 22050
    assert decoded.samples == b"\x01\x02\x03\x04"


def test_synthesize_builds_request_and_decodes_audio():
    clip = Audio(sample_rate=22050, duration_s=0.0, samples=b"\x00\x00" * 50)
    encoded = base64.b64encode(to_wav_bytes(clip)).decode()
    session = FakeSession([encoded])
    provider = BulbulProvider(api_key="secret", session=session)

    audio = provider.synthesize("नमस्ते", lang="hi", speed=1.1)

    url, headers, payload = session.calls[0]
    assert url.endswith("/text-to-speech")
    assert headers["api-subscription-key"] == "secret"
    assert payload["target_language_code"] == "hi-IN"
    assert payload["text"] == "नमस्ते"
    assert payload["pace"] == 1.1
    assert isinstance(audio, Audio)
    assert audio.sample_rate == 22050


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(bulbul, "get_settings", lambda: Settings(_env_file=None))
    provider = BulbulProvider(api_key=None, session=FakeSession([]))
    with pytest.raises(ModelAccessError, match="SARVAM_API_KEY"):
        provider.synthesize("hello", lang="hi")
