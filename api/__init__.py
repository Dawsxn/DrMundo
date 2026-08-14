"""FastAPI service layer.

Exposes Dr. Mundo over HTTP. The API is a thin wrapper: it validates the request,
delegates to `DrMundoService.handle`, and serialises the grounded Answer plus the
reasoning trace and guardrail metadata. All intelligence lives in the agent/guardrail
modules -- this layer only speaks HTTP.
"""
