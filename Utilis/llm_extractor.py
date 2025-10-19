import os
import json
from typing import Any, Dict, List, Optional
import re

from cfb_prop_predictor.types import OddsData


def _collect_numbers_from_obj(obj: Any, prop_identifier: str) -> List[float]:
    """Recursively walk obj (dict/list/str) and collect numbers associated with prop_identifier."""
    found: List[float] = []

    def walk(o: Any):
        if isinstance(o, dict):
            for k, v in o.items():
                lk = str(k).lower()
                if prop_identifier in lk or any(tok in lk for tok in [prop_identifier[:3]]):
                    # if v is numeric or contains numeric string -> collect
                    if isinstance(v, (int, float)):
                        found.append(float(v))
                        continue
                    if isinstance(v, str):
                        m = re.search(r"-?\d+\.?\d*", v)
                        if m:
                            try:
                                found.append(float(m.group(0)))
                                continue
                            except Exception:
                                pass
                walk(v)
        elif isinstance(o, list):
            for it in o:
                walk(it)
        elif isinstance(o, str):
            m = re.search(r"-?\d+\.?\d*", o)
            if m:
                try:
                    found.append(float(m.group(0)))
                except Exception:
                    pass

    walk(obj)
    return found


def extract_with_llm_stub(candidates: Any, player_name: str, prop_type: str) -> Optional[OddsData]:
    """A lightweight 'LLM' extractor fallback that scans candidate JSON/html structures for numbers.

    candidates can be a dict, list, or raw string. This stub is deterministic and safe for demos
    when no real LLM API key is available.
    """
    prop_identifier = prop_type.split('_')[1] if '_' in prop_type else prop_type

    # If candidates is a JSON string, try to parse
    if isinstance(candidates, str):
        try:
            obj = json.loads(candidates)
        except Exception:
            # fallback: search the string for numbers near prop keywords
            # look for patterns like 'receiving: 3.5' or 'recs: 3.5'
            m = re.search(rf"(?:{prop_identifier}|{prop_identifier[:3]}|recs|recyds)[^\d\-\n\r]([\-\d\.]+)", candidates, re.IGNORECASE)
            if m:
                try:
                    return OddsData(prop_line=float(m.group(1)), over_odds=None, under_odds=None)
                except Exception:
                    return None
            return None
    else:
        obj = candidates

    # Heuristic scanning
    nums = _collect_numbers_from_obj(obj, prop_identifier)
    if nums:
        # prefer smallest positive reasonable number (like 3.5 for receptions)
        nums_pos = [n for n in nums if n >= 0]
        if nums_pos:
            val = sorted(nums_pos)[0]
        else:
            val = sorted(nums)[0]
        return OddsData(prop_line=val, over_odds=None, under_odds=None)

    return None


def extract_props(candidates: Any, player_name: str, prop_type: str) -> Optional[OddsData]:
    """Top-level extractor: prefer calling a real LLM if OPENAI_API_KEY is present, else use stub.
    """
    # If an OpenAI key is present and openai is installed, we could call it. For safety and to avoid
    # depending on network/keys in CI, default to the stub unless env var FORCE_OPENAI=1 is set.
    use_openai = os.environ.get('FORCE_OPENAI', '0') in ('1', 'true', 'True') and os.environ.get('OPENAI_API_KEY')
    if use_openai:
        try:
            import openai
            # Build a simple prompt - but keep this optional for now
            payload = json.dumps(candidates) if not isinstance(candidates, str) else candidates
            prompt = f"Extract a JSON object with keys prop_line, over_odds, under_odds for player {player_name} and prop {prop_type}.\nData:\n{payload}\n"
            resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=200)
            text = resp['choices'][0]['message']['content']
            # try to parse JSON from response
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                out = json.loads(m.group(0))
                return OddsData(prop_line=out.get('prop_line'), over_odds=out.get('over_odds'), under_odds=out.get('under_odds'))
        except Exception:
            pass

    # Fallback deterministic stub
    return extract_with_llm_stub(candidates, player_name, prop_type)
