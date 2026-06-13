"""AI4Bharat Indic Parler-TTS provider (ARCHITECTURE.md §5).

Heavy dependencies (``torch``, ``transformers``, ``parler-tts``, ``numpy``) are
imported lazily and are NOT in the base install. Install them into the venv to
use this backend::

    uv pip install torch transformers numpy "parler-tts @ git+https://github.com/huggingface/parler-tts.git"

The voice is chosen by a natural-language **description** string (passed as
``voice``), giving a consistent voice across a whole book without a reference
clip. ``speed`` and ``lang`` are accepted for interface compatibility but are not
yet applied (Parler has no direct speed control); both are future refinements.
"""

from __future__ import annotations

from app.providers.errors import MissingBackendDependencyError
from app.providers.tts.base import Audio

_INSTALL_HINT = "uv sync --extra models"

MODEL_ID = "ai4bharat/indic-parler-tts"
DEFAULT_DESCRIPTION = (
    "A clear, natural-sounding speaker reads at a moderate, steady pace, with "
    "high-quality audio and no background noise."
)


class IndicParlerProvider:
    """Synthesizes speech with Indic Parler-TTS; lazy model load on first use."""

    def __init__(self, device: str | None = None, description: str | None = None) -> None:
        self._device = device
        self._description = description or DEFAULT_DESCRIPTION
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

        self._model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL_ID).to(self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self._description_tokenizer = AutoTokenizer.from_pretrained(
            self._model.config.text_encoder._name_or_path
        )

    def synthesize(
        self, text: str, lang: str, voice: str | None = None, speed: float = 1.0
    ) -> Audio:
        self._ensure_loaded()
        import numpy as np

        description = voice or self._description
        desc = self._description_tokenizer(description, return_tensors="pt").to(self._device)
        prompt = self._tokenizer(text, return_tensors="pt").to(self._device)

        generation = self._model.generate(
            input_ids=desc.input_ids,
            attention_mask=desc.attention_mask,
            prompt_input_ids=prompt.input_ids,
            prompt_attention_mask=prompt.attention_mask,
        )
        waveform = generation.cpu().numpy().squeeze()
        sample_rate = int(self._model.config.sampling_rate)
        pcm = (np.clip(waveform, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        duration = len(waveform) / sample_rate if sample_rate else 0.0
        return Audio(sample_rate=sample_rate, duration_s=duration, samples=pcm)
