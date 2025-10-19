"""Proxy utilities package to expose top-level `Utilis` modules as `cfb_prop_predictor.utils`.

This keeps existing import paths (e.g. `cfb_prop_predictor.utils.play_scraper`) working while the
repo's layout remains flat.
"""
import sys

# Ensure repo root is on sys.path
if '' not in sys.path:
    sys.path.insert(0, '')

from Utilis import play_scraper as play_scraper  # type: ignore

__all__ = ["play_scraper"]
