from typing import Any, Dict, Iterable, List, Optional
import re

import os

# Preferred sportsbook order — can be configured via env or extended later
env_priority = os.environ.get('SPORTSBOOK_PRIORITY')
if env_priority:
    DEFAULT_SPORTSBOOK_PRIORITY = [p.strip().lower() for p in env_priority.split(',') if p.strip()]
else:
    DEFAULT_SPORTSBOOK_PRIORITY = [
        'draftkings', 'fanduel', 'mgm', 'caesars', 'espnbet', 'betrivers', 'hardrock'
    ]


def _collect_numeric_values(v: Any) -> List[float]:
    found: List[float] = []
    if isinstance(v, (int, float)):
        found.append(float(v))
    elif isinstance(v, str):
        m = re.search(r"-?\d+\.?\d*", v)
        if m:
            try:
                found.append(float(m.group(0)))
            except Exception:
                pass
    return found


def extract_prop_from_candidate(candidate, prop_identifier: str, sportsbooks: Iterable[str] = DEFAULT_SPORTSBOOK_PRIORITY) -> Optional[float]:
    """Given a dict candidate (player_obj), try to extract the prop value.

    Strategy:
    - Prefer sportsbook-prefixed keys (e.g., 'draftkings_recs') in the order of `sportsbooks`.
    - Fallback to any key that contains the prop_identifier or its 3-letter prefix.
    - Return the first numeric value found for the preferred sportsbook; else any fallback numeric.
    """
    # Allow candidate to be a list (many samples use arrays at top-level)
    if isinstance(candidate, list):
        for it in candidate:
            res = extract_prop_from_candidate(it, prop_identifier, sportsbooks)
            if res is not None:
                return res

    prop_id = prop_identifier.lower()
    short = prop_id[:3]

    # 1) sportsbook-prefixed search
    for book in sportsbooks:
        pref = f"{book}_"
        for k, v in candidate.items():
            lk = k.lower()
            if lk.startswith(pref) and prop_id in lk:
                nums = _collect_numeric_values(v)
                if nums:
                    return nums[0]

    # 2) non-prefixed keys that still contain prop identifier
    for k, v in candidate.items():
        lk = k.lower()
        if prop_id in lk or short in lk:
            nums = _collect_numeric_values(v)
            if nums:
                return nums[0]

    # 3) try nested dicts/lists
    for k, v in candidate.items():
        if isinstance(v, dict):
            res = extract_prop_from_candidate(v, prop_identifier, sportsbooks)
            if res is not None:
                return res
        if isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    res = extract_prop_from_candidate(it, prop_identifier, sportsbooks)
                    if res is not None:
                        return res

    return None
