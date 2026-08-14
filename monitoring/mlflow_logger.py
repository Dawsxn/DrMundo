"""MLflow logging: one run per `DrMundoService.handle()` call (Phase 9a).

For every request we log latency, token usage + estimated cost, the tool-call trace,
prompt version, and error/grounding status. Logging is best-effort and fully additive:
any failure here (mlflow missing or misconfigured) is swallowed so it can never change or
block an answer. Disable entirely with `DR_MUNDO_MLFLOW=0`.

mlflow is imported lazily inside the log call so importing this module (and therefore the
whole app) never pays mlflow's import cost unless a request is actually logged.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a runtime import cycle (service imports this module)
    from agent.service import ServiceResult

EXPERIMENT_NAME = os.getenv("DR_MUNDO_MLFLOW_EXPERIMENT", "dr_mundo")

# mlflow 3.x put the old file store (./mlruns) in maintenance mode, so default to a
# repo-local SQLite backend. This keeps the app and the UI in sync -- view runs with:
#   mlflow ui --backend-store-uri sqlite:///mlflow.db
# Honour MLFLOW_TRACKING_URI if the operator set one.
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")

_warned = False


def _warn_once(msg: str) -> None:
    global _warned
    if not _warned:
        print(f"[monitoring] MLflow logging unavailable, skipping: {msg}")
        _warned = True


def log_service_result(question: str, result: "ServiceResult") -> None:
    """Log one MLflow run for a completed request. Never raises."""
    try:
        import mlflow
    except Exception as e:  # mlflow not installed / import error
        _warn_once(str(e))
        return
    try:
        _log(mlflow, question, result)
    except Exception as e:  # never let logging break a request
        _warn_once(str(e))


def _log(mlflow, question: str, result: "ServiceResult") -> None:
    answer = result.answer
    usage = result.usage
    report = result.output_report

    tools = [s.action for s in (result.trace or []) if getattr(s, "action", None)]
    grounded = getattr(report, "grounded", True) if report else True
    replaced = getattr(report, "replaced", False) if report else False

    if answer.status == "no_data":
        error_type = "no_data"
    elif not grounded:
        error_type = "ungrounded"
    else:
        error_type = "none"

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    with mlflow.start_run(run_name=f"ask:{answer.status}"):
        mlflow.set_tags(
            {
                "question": question[:250],
                "category": result.category,
                "status": answer.status,
                "path": answer.path or "none",
                "error_type": error_type,
                "grounding_replaced": str(replaced),
            }
        )
        mlflow.log_params(
            {
                "prompt_version": result.prompt_version,
                "category": result.category,
                "status": answer.status,
                "path": answer.path or "none",
                "tools_called": ",".join(tools) or "none",
            }
        )
        mlflow.log_metrics(
            {
                "latency_ms": result.latency_ms,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "n_openai_calls": usage.n_calls,
                "estimated_cost_usd": result.estimated_cost_usd,
                "n_trace_steps": len(result.trace or []),
                "n_tool_calls": len(tools),
                "grounded": 1 if grounded else 0,
                "pii_found": len(result.pii_found or []),
            }
        )
        # Full reasoning trace as an artifact for later inspection.
        trace_payload = [
            {
                "thought": s.thought,
                "action": s.action,
                "action_input": s.action_input,
                "observation": s.observation,
            }
            for s in (result.trace or [])
        ]
        mlflow.log_text(json.dumps(trace_payload, indent=2, default=str), "trace.json")
