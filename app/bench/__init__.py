"""Benchmark metrics and harness (ARCHITECTURE.md §10)."""

from app.bench.metrics import cer, edit_distance, real_time_factor

__all__ = ["cer", "edit_distance", "real_time_factor"]
