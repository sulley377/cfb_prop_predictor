"""Proxy package so `cfb_prop_predictor.agents` resolves to the repo's top-level `agents/` modules.

This keeps the development layout flat while allowing imports like
`from cfb_prop_predictor.agents import analyzer`.
"""
from __future__ import annotations

import sys

# Ensure repo root is on sys.path so top-level 'agents' package is importable
if '' not in sys.path:
    sys.path.insert(0, '')

# Import known submodules from the top-level agents/ directory and expose them here
from agents import analyzer as analyzer  # type: ignore
from agents import data_gatherer as data_gatherer  # type: ignore
from agents import predictor as predictor  # type: ignore

__all__ = ["analyzer", "data_gatherer", "predictor"]
