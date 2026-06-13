"""Optional LLM provider contract (ARCHITECTURE.md §4). Off by default."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Processes text for summarize | translate | define tasks."""

    def process(self, text: str, task: str) -> str: ...
