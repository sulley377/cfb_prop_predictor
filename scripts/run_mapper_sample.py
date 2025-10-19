#!/usr/bin/env python3
import os
import sys
import json
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cfb_prop_predictor.workflow import run_workflow_sync
from dashboard.mapper import _rows_from_gathered


def safe_serialize(obj):
    """Recursively convert SimpleNamespace and other non-JSON types into serializable representations."""
    # Primitive types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    # SimpleNamespace -> dict
    if isinstance(obj, SimpleNamespace):
        return safe_serialize(obj.__dict__)
    # dict-like
    if isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    # lists/tuples
    if isinstance(obj, list):
        return [safe_serialize(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(safe_serialize(v) for v in obj)
    # Fallback: try to get __dict__ or fallback to repr
    if hasattr(obj, '__dict__'):
        try:
            return safe_serialize(obj.__dict__)
        except Exception:
            pass
    return repr(obj)


def main():
    req = {"game": "Alabama vs Georgia", "player": "Jalen Milroe", "prop_type": "player_passing_yards"}

    # Ensure consistent fallback setting
    os.environ.pop('ENABLE_DK_FALLBACK', None)

    print("Running workflow for sample request:\n", json.dumps(req, indent=2))
    # Extract league and prop_type from req
    league = "cfb"  # Assuming CFB for this sample
    prop_type = req["prop_type"]
    result = run_workflow_sync(league, prop_type)
    print('\n--- RAW RESULT (sanitized) ---')
    print(json.dumps(safe_serialize(result), indent=2))

    gathered = (result.get('gathered_data') or {})
    rows = _rows_from_gathered(gathered, request=req, result=result)
    print('\n--- MAPPED ROWS ---')
    print(json.dumps(safe_serialize(rows), indent=2))


if __name__ == '__main__':
    main()
