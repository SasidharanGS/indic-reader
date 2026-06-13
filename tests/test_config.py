from app.config import Settings


def test_defaults_match_documented_local_stack():
    s = Settings(_env_file=None)
    assert s.ocr_backend == "paddle"
    assert s.tts_backend == "indic_parler"
    assert s.llm_backend == "none"
    assert s.device == "mps"
    assert s.sarvam_api_key is None


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OCR_BACKEND", "mock")
    monkeypatch.setenv("DEVICE", "cuda")
    monkeypatch.setenv("SARVAM_API_KEY", "secret")
    s = Settings(_env_file=None)
    assert s.ocr_backend == "mock"
    assert s.device == "cuda"
    assert s.sarvam_api_key == "secret"
