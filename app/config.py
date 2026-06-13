"""Env-driven configuration and backend selection.

See ARCHITECTURE.md §4 — the pipeline never names a concrete provider; it reads
these backend strings and asks the registry for an implementation.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, populated from environment / ``.env``.

    Defaults match the documented free, local stack (``paddle`` + ``indic_parler``).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    ocr_backend: str = "paddle"  # paddle | surya | sarvam_vision
    tts_backend: str = "indic_parler"  # indic_parler | indicf5 | bulbul
    llm_backend: str = "none"  # none | sarvam_m | sarvam_translate
    device: str = "mps"  # mps | cuda | cpu

    sarvam_api_key: str | None = None
    telegram_bot_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
