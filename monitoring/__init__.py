"""Monitoring for Dr. Mundo (Phase 9a).

Two concerns, both purely additive (they never change an answer):
  - `usage`: per-request token accounting via a wrapper around the OpenAI client.
  - `mlflow_logger`: one MLflow run per `DrMundoService.handle()` call.
"""

from monitoring.usage import (
    MODEL_PRICING,
    UsageTotals,
    estimate_cost,
    track_usage,
    wrap_client,
)

__all__ = [
    "MODEL_PRICING",
    "UsageTotals",
    "estimate_cost",
    "track_usage",
    "wrap_client",
]
