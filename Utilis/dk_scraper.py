import re
import json
from typing import Optional, Any, Dict
from playwright.async_api import Page
from cfb_prop_predictor.types import OddsData
from Utilis.provider_parser import extract_prop_from_candidate
import datetime


def _abbrev(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    try:
        last = name.split()[-1]
        return ''.join([c for c in last.upper() if c.isalpha()])[:3]
    except Exception:
        return (name or '')[:3].upper()


def _iso_from_timestamp(val: Any) -> Optional[str]:
    # Accept numeric epoch (seconds or ms) or ISO-like strings
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # heuristic: if val looks like ms (>1e12) or seconds
        try:
            if val > 1e12:
                ts = val / 1000.0
            else:
                ts = float(val)
            return datetime.datetime.utcfromtimestamp(ts).isoformat() + 'Z'
        except Exception:
            return None
    s = str(val)
    # Try to parse ISO-ish strings
    try:
        # normalize 'Z' into +00:00 for fromisoformat
        dt = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        return dt.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
    except Exception:
        return None


def extract_prop_from_candidate(candidate: Dict[str, Any], prop_identifier: str) -> Optional[float]:
    """Given a player-like candidate dict, pick the best prop value using sportsbook-priority.

    Strategy:
    - Collect candidate keys that look like markets (contain prop fragments or 'rec','yds','pass','rush').
    - Prefer explicit sportsbook-prefixed keys in this order: draftkings_, fanduel_, mgm_, caesars_, espnbet_, betray others.
    - If multiple keys remain, pick the first numeric value encountered.
    """
    # Collect (key_path, value) pairs by walking nested dicts/lists
    keys = []

    def collect(o, prefix=''):
        if isinstance(o, dict):
            for kk, vv in o.items():
                path = f"{prefix}.{kk}" if prefix else kk
                lk = path.lower()
                if any(tok in lk for tok in [prop_identifier, 'rec', 'recs', 'yds', 'pass', 'rush', 'total']):
                    keys.append((path, vv))
                # recurse
                collect(vv, path)
        elif isinstance(o, list):
            for idx, item in enumerate(o):
                collect(item, f"{prefix}[{idx}]")

    collect(candidate)

    if not keys:
        return None

    # Score keys by sportsbook preference
    priority = ['draftkings_', 'fanduel_', 'mgm_', 'caesars_', 'espnbet_', 'betrivers_', 'hardrock_']

    def score_key(kv):
        k, _ = kv
        lk = k.lower()
        for i, p in enumerate(priority):
            if p in lk:
                return (0, i)  # top by presence of preferred book
        # keys with explicit numeric suffix like '_recs' get a medium score
        if re.search(r"\d", lk):
            return (1, 0)
        return (2, 0)

    keys_sorted = sorted(keys, key=score_key)

    for k, v in keys_sorted:
        if v is None or v == '':
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r"-?\d+\.?\d*", v)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    continue

    return None


async def scrape_draftkings_player_props(page: Page, player_name: str, prop_type: str) -> Optional[Dict[str, Any]]:
    """Attempt to scrape a DraftKings-style sportsbook page for a player's prop.

    This is an optimistic, best-effort scraper that mirrors the Rotowire
    JSON/DOM fallback approach: try to parse embedded JSON blobs in the
    client-rendered page first, then fall back to scanning tables/selectors.

    NOTE: DraftKings pages are heavily client-rendered and may use GraphQL
    endpoints. This function tries to find JSON arrays/objects in the page
    and locate keys that match common prop fragments (rec, pass, rush, yds).
    """
    urls = [
        'https://sportsbook.draftkings.com/',
        'https://sportsbook.draftkings.com/odds',
    ]

    target = player_name.strip().lower()
    target_last = target.split()[-1] if target else ''
    prop_identifier = prop_type.split('_')[1] if '_' in prop_type else prop_type

    for url in urls:
        try:
            # keep navigation short to avoid long hangs in restricted environments
            await page.goto(url, wait_until='networkidle', timeout=8000)
        except Exception:
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=8000)
            except Exception:
                # unable to load the sportsbook page quickly; try next URL
                continue

        try:
            content = await page.content()
        except Exception:
            # If we can't fetch content, skip this URL quickly
            continue

        # Try to extract any large JSON-like objects embedded in scripts
        js_objects = re.findall(r"(\{[\s\S]{100,200000}?\})", content)
        print(f"DEBUG(dk): found {len(js_objects)} js_objects candidates")
        for idx, txt in enumerate(js_objects[:30]):
            try:
                obj = json.loads(txt)
            except Exception:
                continue

            # Walk the object to find player-like dicts
            def walk(o):
                if isinstance(o, dict):
                    yield o
                    for v in o.values():
                        yield from walk(v)
                elif isinstance(o, list):
                    for it in o:
                        yield from walk(it)

            for candidate in walk(obj):
                name = (candidate.get('name') or candidate.get('playerName') or '')
                if not name:
                    continue
                name_norm = re.sub(r"[^a-z0-9 ]+", "", name.lower())
                if name_norm == target or target_last in name_norm.split():
                    print(f"DEBUG(dk): matched candidate name={name}")
                    prop_val = extract_prop_from_candidate(candidate, prop_identifier)
                    if prop_val is not None:
                        # Build rich return payload
                        # attempt to discover position/team/opponent/league/start_time
                        position = candidate.get('position') or candidate.get('pos') or candidate.get('positionName')
                        team_name = candidate.get('team') or candidate.get('teamName') or candidate.get('club') or candidate.get('homeTeam') or candidate.get('awayTeam')
                        opponent = None
                        # try common opponent keys
                        for ok in ('opponent', 'opponentName', 'awayTeam', 'homeTeam', 'opponent_team'):
                            if ok in candidate and candidate.get(ok):
                                opponent = candidate.get(ok)
                                break
                        # attempt to detect league/sport
                        league = None
                        for lk in ('league', 'sport', 'competition', 'eventType'):
                            if lk in candidate and candidate.get(lk):
                                league = candidate.get(lk)
                                break
                        # find start time
                        start_time = None
                        for tkey in ('start_time', 'startTime', 'eventTime', 'kickoff', 'start'):
                            if tkey in candidate and candidate.get(tkey):
                                start_time = _iso_from_timestamp(candidate.get(tkey)) or str(candidate.get(tkey))
                                break

                        od = OddsData(prop_line=prop_val, over_odds=None, under_odds=None)

                        return {
                            'name': name,
                            'position': position,
                            'team_name': team_name,
                            'team_abbrev': _abbrev(team_name),
                            'opponent_name': opponent,
                            'opponent_abbrev': _abbrev(opponent),
                            'league': league or ('CFB' if 'college' in prop_type or 'college' in str(candidate).lower() else 'NFL' if 'nfl' in str(candidate).lower() else 'CFB'),
                            'start_time': start_time,
                            'odds_data': od
                        }

        # DOM fallback: search for table rows that contain the player name
        selector_candidates = [
            'table tbody',
            '.market-table tbody',
            '.prop-market tbody',
        ]
        for sel in selector_candidates:
            try:
                await page.wait_for_selector(sel, timeout=2000)
                rows = page.locator(sel + ' tr')
                for i in range(await rows.count()):
                    row = rows.nth(i)
                    text = (await row.text_content() or '').lower()
                    if target in text or target_last in text:
                        # try to extract first number in the row as the line
                        m = re.search(r"-?\d+\.?\d*", text)
                        if m:
                            try:
                                val = float(m.group(0))
                                return {
                                    'name': player_name,
                                    'position': None,
                                    'team_name': None,
                                    'team_abbrev': None,
                                    'opponent_name': None,
                                    'opponent_abbrev': None,
                                    'league': None,
                                    'start_time': None,
                                    'odds_data': OddsData(prop_line=float(m.group(0)), over_odds=None, under_odds=None)
                                }
                            except Exception:
                                continue
            except Exception:
                continue

    return None
