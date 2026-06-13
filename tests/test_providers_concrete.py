"""The concrete providers' missing-dependency path.

In CI (no ML extras installed) these run and confirm a clear, actionable error.
On a machine where the extras *are* installed, they skip — we don't want a unit
test to download multi-GB models.
"""

import importlib.util

import pytest

from app.providers.errors import MissingBackendDependencyError
from app.providers.registry import get_ocr_provider, get_tts_provider

_paddle_installed = importlib.util.find_spec("paddleocr") is not None
_parler_installed = importlib.util.find_spec("parler_tts") is not None


@pytest.mark.skipif(_paddle_installed, reason="paddle extra installed; missing-dep path not hit")
def test_paddle_without_deps_raises_install_hint():
    provider = get_ocr_provider("paddle")
    with pytest.raises(MissingBackendDependencyError, match="uv sync --extra models"):
        provider.extract(b"not-a-real-image")


@pytest.mark.skipif(_parler_installed, reason="parler extra installed; missing-dep path not hit")
def test_parler_without_deps_raises_install_hint():
    provider = get_tts_provider("indic_parler")
    with pytest.raises(MissingBackendDependencyError, match="uv sync --extra models"):
        provider.synthesize("hello", lang="en")
