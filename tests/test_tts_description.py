"""Unit tests for per-language speaker selection (no model needed)."""

from app.providers.tts.indic_parler import (
    _SPEAKERS,
    _description_for,
    _generation_kwargs,
    _speed_descriptor,
)


def test_description_names_recommended_speaker():
    assert "Rohit" in _description_for("hi")
    assert "Jaya" in _description_for("ta")
    assert "Prakash" in _description_for("te")
    assert "Thoma" in _description_for("en")


def test_unknown_language_falls_back_to_a_named_speaker():
    # Must still name a (stable) speaker rather than leave the voice unconstrained.
    assert "Thoma" in _description_for("zz")


def test_all_mapped_languages_have_a_speaker():
    assert all(_SPEAKERS.values())


def test_speed_descriptor():
    assert _speed_descriptor(1.0) == "moderate"
    assert _speed_descriptor(1.5) == "fast"
    assert _speed_descriptor(0.5) == "slow"


def test_default_speed_description_is_unchanged():
    # speed=1.0 must stay byte-identical to the verified description.
    assert _description_for("hi") == _description_for("hi", 1.0)
    assert "moderate speed and pitch" in _description_for("hi", 1.0)
    assert "fast speed and pitch" in _description_for("hi", 1.5)


def test_generation_kwargs_are_opt_in():
    assert _generation_kwargs(False, 0.7) == {}
    assert _generation_kwargs(True, 0.7) == {"do_sample": True, "temperature": 0.7}
