from app.text.lang_detect import detect_lang, detect_script, is_code_mixed


def test_detects_hindi_devanagari():
    assert detect_script("नमस्ते दुनिया।") == "devanagari"
    assert detect_lang("नमस्ते दुनिया।") == "hi"


def test_detects_tamil():
    assert detect_lang("வணக்கம் உலகம்.") == "ta"


def test_detects_telugu():
    assert detect_lang("నమస్కారం ప్రపంచం.") == "te"


def test_detects_english():
    assert detect_script("Hello world.") == "latin"
    assert detect_lang("Hello world.") == "en"


def test_empty_text_defaults_to_english():
    assert detect_lang("") == "en"
    assert detect_lang("123 — !!") == "en"


def test_code_mix_detection_and_dominant_script():
    text = "मैं office जा रहा हूँ"
    assert is_code_mixed(text) is True
    assert detect_lang(text) == "hi"
    assert is_code_mixed("Hello world") is False
