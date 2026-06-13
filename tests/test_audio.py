import pytest

from app.audio.cache import AudioCache, chunk_key
from app.audio.concat import concat
from app.providers.tts.base import Audio


def test_chunk_key_is_stable_and_sensitive():
    a = chunk_key("hello", voice=None, backend="mock", speed=1.0)
    assert a == chunk_key("hello", voice=None, backend="mock", speed=1.0)
    assert a != chunk_key("hello", voice="ravi", backend="mock", speed=1.0)
    assert a != chunk_key("hello", voice=None, backend="bulbul", speed=1.0)
    assert a != chunk_key("world", voice=None, backend="mock", speed=1.0)


def test_audio_cache_roundtrip():
    cache = AudioCache()
    key = "k"
    assert cache.get(key) is None
    assert key not in cache
    clip = Audio(sample_rate=16000, duration_s=1.0, samples=b"abc")
    cache.set(key, clip)
    assert key in cache
    assert cache.get(key) is clip
    assert len(cache) == 1


def test_concat_joins_samples_and_sums_duration():
    clips = [
        Audio(sample_rate=16000, duration_s=1.0, samples=b"aa"),
        Audio(sample_rate=16000, duration_s=0.5, samples=b"bb"),
    ]
    out = concat(clips)
    assert out.samples == b"aabb"
    assert out.duration_s == 1.5
    assert out.sample_rate == 16000


def test_concat_rejects_empty():
    with pytest.raises(ValueError):
        concat([])


def test_concat_rejects_mismatched_sample_rate():
    with pytest.raises(ValueError):
        concat(
            [
                Audio(sample_rate=16000, duration_s=1.0, samples=b""),
                Audio(sample_rate=22050, duration_s=1.0, samples=b""),
            ]
        )
