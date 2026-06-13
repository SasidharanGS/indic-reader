"""Unit tests for per-language speaker selection (no model needed)."""

from app.providers.tts.indic_parler import _SPEAKERS, _description_for


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
