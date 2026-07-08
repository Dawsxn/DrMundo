"""Per-request token-usage accounting (Phase 9a).

Every OpenAI call on the request path reports token usage on its response: the ReAct chat
loop (`agent/loop.py`), the input-guard classifier (`guardrails/input_guard.py`), and the
query-embedding lookup (`db/search.py`). Rather than thread `resp.usage` back through
every return type, we wrap the shared OpenAI client so each call records its usage into a
per-request accumulator stored in a `contextvars.ContextVar`.

This is deliberately additive: the wrapper returns each response object untouched, so the
numbers/answers the agent produces never change. When no `track_usage()` block is active,
recording is a no-op.

    from monitoring.usage import track_usage, estimate_cost
    with track_usage() as usage:
        ...                       # anything that calls get_openai_client()
    cost = estimate_cost(usage)   # USD, from the per-model token counts
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional

# Published USD list prices per 1M tokens (edit here if OpenAI's rates change). These are
# the only two models Dr. Mundo calls.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}
_PER = 1_000_000  # MODEL_PRICING is quoted per this many tokens


@dataclass
class UsageTotals:
    """Accumulated token usage for one request, aggregate + per-model."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    n_calls: int = 0
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, model: Optional[str], prompt: int, completion: int) -> None:
        model = model or "unknown"
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.n_calls += 1
        slot = self.by_model.setdefault(
            model, {"prompt": 0, "completion": 0, "total": 0, "calls": 0}
        )
        slot["prompt"] += prompt
        slot["completion"] += completion
        slot["total"] += prompt + completion
        slot["calls"] += 1


# Holds the accumulator for the current request; None when nothing is tracking.
_current: contextvars.ContextVar[Optional[UsageTotals]] = contextvars.ContextVar(
    "dr_mundo_usage", default=None
)


@contextmanager
def track_usage() -> Iterator[UsageTotals]:
    """Collect token usage from every wrapped OpenAI call made inside this block."""
    acc = UsageTotals()
    token = _current.set(acc)
    try:
        yield acc
    finally:
        _current.reset(token)


def _record(usage, model: Optional[str]) -> None:
    acc = _current.get()
    if acc is None or usage is None:
        return
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    acc.record(model, prompt, completion)


def _base_model(model: str) -> str:
    """Map a dated model id (e.g. 'gpt-4o-mini-2024-07-18') to its pricing key."""
    for known in MODEL_PRICING:
        if model.startswith(known):
            return known
    return model


def estimate_cost(usage: UsageTotals) -> float:
    """Estimate USD cost from per-model token counts and `MODEL_PRICING`.

    Unknown models contribute nothing (cost is a best-effort estimate, not a bill)."""
    total = 0.0
    for model, t in usage.by_model.items():
        rate = MODEL_PRICING.get(model) or MODEL_PRICING.get(_base_model(model))
        if not rate:
            continue
        total += t["prompt"] * rate["input"] / _PER
        total += t["completion"] * rate["output"] / _PER
    return round(total, 8)


# ------------------------------------------------------------- client wrapper
class _Completions:
    def __init__(self, real):
        self._real = real

    def create(self, *args, **kwargs):
        resp = self._real.create(*args, **kwargs)
        _record(getattr(resp, "usage", None), kwargs.get("model"))
        return resp


class _Chat:
    def __init__(self, real):
        self._real = real

    @property
    def completions(self):
        return _Completions(self._real.completions)


class _Embeddings:
    def __init__(self, real):
        self._real = real

    def create(self, *args, **kwargs):
        resp = self._real.create(*args, **kwargs)
        _record(getattr(resp, "usage", None), kwargs.get("model"))
        return resp


class TrackedClient:
    """Transparent proxy over an OpenAI client that records token usage per call.

    Only the two endpoints Dr. Mundo uses (`chat.completions`, `embeddings`) are
    instrumented; every other attribute passes straight through to the real client."""

    def __init__(self, real):
        self._real = real

    @property
    def chat(self):
        return _Chat(self._real.chat)

    @property
    def embeddings(self):
        return _Embeddings(self._real.embeddings)

    def __getattr__(self, name):
        # Only reached for attributes not defined on the proxy (e.g. _real is set in
        # __init__, so this won't recurse) -> delegate to the wrapped client.
        return getattr(self._real, name)


def wrap_client(client):
    """Wrap an OpenAI client so calls made inside a `track_usage()` block are counted."""
    return TrackedClient(client)
