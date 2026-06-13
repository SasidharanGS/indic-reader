"""FastAPI entrypoint. Run locally with ``uvicorn app.main:app --reload``."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="Indic Reader", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check that also reports the selected backends."""
    settings = get_settings()
    return {
        "status": "ok",
        "ocr_backend": settings.ocr_backend,
        "tts_backend": settings.tts_backend,
        "llm_backend": settings.llm_backend,
        "device": settings.device,
    }
