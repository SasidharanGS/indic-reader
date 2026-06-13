"""Shared provider exceptions."""

from __future__ import annotations


class MissingBackendDependencyError(ImportError):
    """A selected backend's optional (heavy) dependencies are not installed.

    Carries an install hint so the failure is actionable rather than an opaque
    ``ModuleNotFoundError`` deep inside a provider.
    """


class ModelAccessError(RuntimeError):
    """A model could not be downloaded due to access/authentication.

    Typically a gated Hugging Face repo: carries guidance on requesting access
    and authenticating, rather than an opaque 401 traceback.
    """
