"""AI4Bharat Indic Parler-TTS provider (ARCHITECTURE.md §5).

Heavy dependencies (``torch``, ``transformers``, ``parler-tts``, ``numpy``) are
imported lazily and are NOT in the base install. Install them into the venv to
use this backend::

    uv sync --extra models

The voice is chosen by a natural-language **description**. By default we name one
of the model's *recommended speakers* for the detected ``lang`` — the model card
notes this is what keeps the voice consistent and intelligible (without a named
speaker the voice is randomly sampled and often garbled). Pass an explicit
``voice`` description to override. ``speed`` nudges the description's speaking
rate (slow / moderate / fast). Optional ``do_sample``/``temperature`` enable
sampling; both default to the originally verified greedy behavior.
"""

from __future__ import annotations

from app.config import get_settings
from app.providers.errors import MissingBackendDependencyError, ModelAccessError
from app.providers.tts.base import Audio

_INSTALL_HINT = "uv sync --extra models"

MODEL_ID = "ai4bharat/indic-parler-tts"

# Recommended speakers per language (ai4bharat/indic-parler-tts model card).
# Naming one keeps the voice stable and intelligible; omitting it yields a
# random, often garbled voice.
_SPEAKERS = {
    "en": "Thoma",
    "hi": "Rohit",
    "mr": "Sanjay",
    "ne": "Amrita",
    "bn": "Arjun",
    "pa": "Divjot",
    "gu": "Yash",
    "or": "Manas",
    "ta": "Jaya",
    "te": "Prakash",
    "kn": "Suresh",
    "ml": "Anjali",
}
_FALLBACK_SPEAKER = "Thoma"


def _speed_descriptor(speed: float) -> str:
    """Map a speed multiplier to a speaking-rate word for the description."""
    if speed >= 1.15:
        return "fast"
    if speed <= 0.85:
        return "slow"
    return "moderate"


def _description_for(lang: str, speed: float = 1.0) -> str:
    """Build a description naming the recommended speaker for ``lang``.

    At ``speed=1.0`` this is byte-identical to the original verified description.
    """
    speaker = _SPEAKERS.get(lang, _FALLBACK_SPEAKER)
    return (
        f"{speaker}'s voice is clear and natural, at a {_speed_descriptor(speed)} speed "
        "and pitch. The recording is very high quality, with very clear audio and almost "
        "no background noise."
    )


def _generation_kwargs(do_sample: bool, temperature: float) -> dict:
    """Sampling args for ``generate()``; empty (greedy) by default to preserve
    the originally verified output."""
    return {"do_sample": True, "temperature": temperature} if do_sample else {}


def _is_gated_or_auth_error(exc: Exception) -> bool:
    """True when an exception looks like a gated-repo / auth (401) failure."""
    message = str(exc).lower()
    return (
        type(exc).__name__ in {"GatedRepoError", "RepositoryNotFoundError"}
        or "gated" in message
        or "401" in message
        or "restricted" in message
        or "authenticated" in message
    )


class IndicParlerProvider:
    """Synthesizes speech with Indic Parler-TTS; lazy model load on first use."""

    def __init__(
        self,
        device: str | None = None,
        description: str | None = None,
        hf_token: str | None = None,
        do_sample: bool = False,
        temperature: float = 1.0,
    ) -> None:
        self._device = device
        self._description = description  # explicit override; else per-language default
        self._hf_token = hf_token
        self._do_sample = do_sample
        self._temperature = temperature
        self._model = None
        self._tokenizer = None
        self._description_tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise MissingBackendDependencyError(
                f"The 'indic_parler' TTS backend needs extra packages. "
                f"Install with: {_INSTALL_HINT}"
            ) from exc

        if self._device is None:
            if torch.cuda.is_available():
                self._device = "cuda"
            elif torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"

        token = self._hf_token or get_settings().hf_token
        try:
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                MODEL_ID, token=token
            ).to(self._device)
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=token)
            self._description_tokenizer = AutoTokenizer.from_pretrained(
                self._model.config.text_encoder._name_or_path, token=token
            )
        except Exception as exc:
            if _is_gated_or_auth_error(exc):
                raise ModelAccessError(
                    f"{MODEL_ID} is a gated Hugging Face model. Request access at "
                    f"https://huggingface.co/{MODEL_ID} (click 'Agree and access "
                    f"repository'), then authenticate with `uv run hf auth login` "
                    f"or set HF_TOKEN in .env."
                ) from exc
            raise

    def synthesize(
        self, text: str, lang: str, voice: str | None = None, speed: float = 1.0
    ) -> Audio:
        self._ensure_loaded()
        import numpy as np

        description = voice or self._description or _description_for(lang, speed)
        desc = self._description_tokenizer(description, return_tensors="pt").to(self._device)
        prompt = self._tokenizer(text, return_tensors="pt").to(self._device)

        generation = self._model.generate(
            input_ids=desc.input_ids,
            attention_mask=desc.attention_mask,
            prompt_input_ids=prompt.input_ids,
            prompt_attention_mask=prompt.attention_mask,
            **_generation_kwargs(self._do_sample, self._temperature),
        )
        waveform = generation.cpu().numpy().squeeze()
        sample_rate = int(self._model.config.sampling_rate)
        pcm = (np.clip(waveform, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        duration = len(waveform) / sample_rate if sample_rate else 0.0
        return Audio(sample_rate=sample_rate, duration_s=duration, samples=pcm)
