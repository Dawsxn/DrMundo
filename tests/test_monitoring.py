"""Unit tests for the Phase 9a monitoring layer (no network / no API key needed).

Uses a fake OpenAI-shaped client to prove the wrapper records `resp.usage` into the
active `track_usage()` context, is a no-op outside one, passes responses through
unchanged, and that cost estimation matches the published rates.
"""

import pytest

from monitoring.usage import (
    MODEL_PRICING,
    UsageTotals,
    estimate_cost,
    track_usage,
    wrap_client,
)


# --------------------------------------------------------------- fake OpenAI client
class _Usage:
    def __init__(self, prompt, completion=0):
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = prompt + completion


class _Resp:
    def __init__(self, usage):
        self.usage = usage
        self.marker = "unchanged"


class _Completions:
    def create(self, **kwargs):
        return _Resp(_Usage(100, 50))


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class _Embeddings:
    def create(self, **kwargs):
        return _Resp(_Usage(8, 0))


class _FakeClient:
    def __init__(self):
        self.chat = _Chat()
        self.embeddings = _Embeddings()
        self.other_attr = "passthrough"


# --------------------------------------------------------------- UsageTotals + cost
def test_usage_totals_aggregate_and_per_model():
    u = UsageTotals()
    u.record("gpt-4o-mini", 100, 50)
    u.record("gpt-4o-mini", 10, 5)
    u.record("text-embedding-3-small", 8, 0)

    assert u.prompt_tokens == 118
    assert u.completion_tokens == 55
    assert u.total_tokens == 173
    assert u.n_calls == 3
    assert u.by_model["gpt-4o-mini"] == {"prompt": 110, "completion": 55, "total": 165, "calls": 2}
    assert u.by_model["text-embedding-3-small"]["total"] == 8


def test_estimate_cost_matches_published_rates():
    u = UsageTotals()
    u.record("gpt-4o-mini", 1000, 2000)
    u.record("text-embedding-3-small", 500, 0)
    expected = (
        1000 * MODEL_PRICING["gpt-4o-mini"]["input"] / 1_000_000
        + 2000 * MODEL_PRICING["gpt-4o-mini"]["output"] / 1_000_000
        + 500 * MODEL_PRICING["text-embedding-3-small"]["input"] / 1_000_000
    )
    assert estimate_cost(u) == pytest.approx(expected)


def test_estimate_cost_handles_dated_model_id():
    u = UsageTotals()
    u.record("gpt-4o-mini-2024-07-18", 1000, 0)  # dated variant -> base pricing
    assert estimate_cost(u) == pytest.approx(1000 * 0.15 / 1_000_000)


def test_estimate_cost_ignores_unknown_model():
    u = UsageTotals()
    u.record("some-future-model", 1000, 1000)
    assert estimate_cost(u) == 0.0


# --------------------------------------------------------------- client wrapper
def test_wrapper_records_usage_inside_context():
    client = wrap_client(_FakeClient())
    with track_usage() as usage:
        r1 = client.chat.completions.create(model="gpt-4o-mini", messages=[])
        r2 = client.embeddings.create(model="text-embedding-3-small", input=["x"])

    # Responses pass through untouched (additive wrapper).
    assert r1.marker == "unchanged" and r2.marker == "unchanged"
    assert usage.prompt_tokens == 108
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 158
    assert usage.n_calls == 2
    assert set(usage.by_model) == {"gpt-4o-mini", "text-embedding-3-small"}


def test_wrapper_is_noop_outside_context():
    client = wrap_client(_FakeClient())
    # No active track_usage() -> recording must not raise and response is returned.
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[])
    assert resp.marker == "unchanged"


def test_wrapper_delegates_unknown_attributes():
    client = wrap_client(_FakeClient())
    assert client.other_attr == "passthrough"


def test_nested_contexts_are_isolated():
    client = wrap_client(_FakeClient())
    with track_usage() as outer:
        client.chat.completions.create(model="gpt-4o-mini", messages=[])
        with track_usage() as inner:
            client.chat.completions.create(model="gpt-4o-mini", messages=[])
        assert inner.n_calls == 1
        # After the inner context exits, the outer accumulator is active again.
        client.chat.completions.create(model="gpt-4o-mini", messages=[])
    assert outer.n_calls == 2
