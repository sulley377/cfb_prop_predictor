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
    """
    Maps the 'result' object to a list of table rows.

    This version reads from the 'gathered_data.all_props' list
    provided by the new auto-scanner.
    """
    if not result:
        return []

    # Get the list of props from the new key
    if isinstance(gathered_data, dict):
        props_list = gathered_data.get('all_props', [])
    else:
        props_list = getattr(gathered_data, 'all_props', []) or []
    
    mapped_rows = []
    
    # Loop over each prop and build a row
    for prop in props_list:
        try:
            # 'prop' is the rich dictionary from your scraper
            player_name = prop.get('name', 'N/A')
            position = prop.get('position', 'N/A')
            team = prop.get('team_abbrev', prop.get('team_name', 'N/A'))
            opponent = prop.get('opponent_abbrev', prop.get('opponent_name', 'N/A'))
            
            start_time_iso = prop.get('start_time')
            start_time_str = _format_datetime_human(start_time_iso)
            
            market = prop.get('market_name', 'N/A')
            # prop_line may be under several keys depending on scraper; check common ones
            prop_line = prop.get('prop_line') or prop.get('prop_value') or (prop.get('odds_data').prop_line if prop.get('odds_data') and hasattr(prop.get('odds_data'), 'prop_line') else 'N/A')
            market_with_line = f"{market} ({prop_line})" if prop_line != 'N/A' else market

            league = prop.get('league', 'N/A')
            
            row = {
                'player': player_name,
                'position': position,
                'team': team,
                'opponent': opponent,
                'datetime': start_time_str,
                'market': market_with_line,
                'prediction_score': 0, # Prediction is bypassed for scanner
                'rotowire': 'N/A',
                'hit_rate': 'N/A',
                'league': league
            }
            mapped_rows.append(row)
        
        except Exception as e:
            print(f"Error mapping prop to row: {e}")
            continue
            
    return mapped_rows


if __name__ == '__main__':
    print('mapper module ok')
