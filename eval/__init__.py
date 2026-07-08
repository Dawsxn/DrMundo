"""Offline eval harness for Dr. Mundo (Phase 9b).

Drives cases through `DrMundoService.handle` (not the HTTP layer) and scores routing,
catalog match, coverage/OOP correctness, refusals, and latency. Supports prompt-variant
ablation. See `run_eval.py` for the CLI and `scoring.py` for the (pure) scoring logic.
"""
