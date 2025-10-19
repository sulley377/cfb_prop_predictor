"""Mapper: convert gathered_data/result into compact table rows.

This implementation accepts dicts, types.SimpleNamespace, or the "SimpleNamespace(...)" style
string that older code sometimes produced. It prefers structured fields when present.
"""

import re
import datetime
from types import SimpleNamespace
from typing import Any, Dict, List


def _parse_namespace_str(ns_string: str, key: str):
    """Parse key=value like patterns from a SimpleNamespace(...) style string.

    Example input: "SimpleNamespace(name='Jalen Milroe', position='QB', team_name='Alabama')"
    Returns the unquoted value or None when not found.
    """
    if not ns_string or not isinstance(ns_string, str):
        return None
    try:
        m = re.search(rf"\b{re.escape(key)}=([^,\)]+)", ns_string)
        if not m:
            return None
        val = m.group(1).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        return val
    except Exception:
        return None


def _format_market_name(analysis_summary: Any):
    """
    Infers market name from a summary string like:
    "Analysis for player_passing_yards"
    """
    if not isinstance(analysis_summary, str):
        return "N/A"
    try:
        # UPDATED REGEX:
        # Makes the trailing period optional and matches the prop name.
        # It looks for "Analysis for " followed by word characters (like 'player_passing_yards')
        match = re.search(r"Analysis for ([\w_]+)", analysis_summary)
        if match:
            # Converts 'player_passing_yards' to 'Player Passing Yards'
            return match.group(1).replace('_', ' ').title()
    except Exception:
        pass
    # Fallback if regex fails
    return "N/A"


def _format_datetime_human(dt_str: str):
    if not dt_str:
        return "N/A"
    try:
        # Support naive ISO and timezone-aware
        dt = datetime.datetime.fromisoformat(dt_str)
        return dt.strftime("%a %m/%d %I:%M %p")
    except Exception:
        return dt_str


def _normalize(obj: Any):
    """Return a dict-like view for dict, SimpleNamespace or string namespace."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, SimpleNamespace):
        return vars(obj)
    if isinstance(obj, str):
        # crude parse of a SimpleNamespace(...) textual repr
        out = {}
        for k in ("name", "position", "team_name", "team_abbrev", "league", "opponent_name", "opponent_abbrev", "start_time"):
            v = _parse_namespace_str(obj, k)
            if v is not None:
                out[k] = v
        return out
    # fallback: try mapping attributes
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("__")}
    except Exception:
        return {}


def _rows_from_gathered(gathered_data, request=None, result=None):
    """Build compact table rows from gathered_data/result.

    Returns a list with a single dict row with keys:
    player, position, team, opponent, datetime, market, prediction_score, rotowire, hit_rate, league
    """
    # gathered_data may be a dict-like with keys 'player_stats' and 'team_stats'
    if not gathered_data:
        gathered_data = {}

    pd_raw = None
    if isinstance(gathered_data, dict):
        pd_raw = gathered_data.get('player_stats')
        td_raw = gathered_data.get('team_stats')
    else:
        pd_raw = getattr(gathered_data, 'player_stats', None)
        td_raw = getattr(gathered_data, 'team_stats', None)

    pd = _normalize(pd_raw)
    td = _normalize(td_raw)

    player = pd.get('name') or pd.get('player') or (request.get('player') if request else None) or 'N/A'
    position = pd.get('position') or 'N/A'
    team = pd.get('team_abbrev') or pd.get('team_name') or td.get('name') or 'N/A'
    opponent = pd.get('opponent_abbrev') or pd.get('opponent_name') or 'N/A'
    start_time = pd.get('start_time') or None
    datetime_human = _format_datetime_human(start_time)

    market = _format_market_name(result.get('analysis', {}).get('summary') if isinstance(result, dict) else None)
    prediction_score = (result.get('prediction', {}).get('confidence') if isinstance(result, dict) else None) or 'N/A'

    row = {
        'player': player,
        'position': position,
        'team': team,
        'opponent': opponent,
        'datetime': datetime_human,
        'market': market,
        'prediction_score': prediction_score,
        'rotowire': 'N/A',
        'hit_rate': 'N/A',
        'league': pd.get('league') or td.get('league') or 'N/A'
    }
    return [row]


if __name__ == '__main__':
    print('mapper module ok')
