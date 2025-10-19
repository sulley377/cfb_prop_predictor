import re
import json
from typing import Optional, Any, Dict, List
from playwright.async_api import Page, Response
from cfb_prop_predictor.types import OddsData
from Utilis.provider_parser import extract_prop_from_candidate

# ---
# --- NEW PARSER FUNCTION ---
# ---
def parse_dk_json_payload(payload: Dict[str, Any], league: str, prop_type: str) -> List[Dict[str, Any]]:
    """
    Parses a pre-loaded DK JSON blob for all player props.
    This avoids live scraping and uses local sample data.
    """
    all_props_list = []
    # e.g., "passing" from "player_passing_yards"
    prop_identifier = prop_type.split('_')[1] if '_' in prop_type else prop_type

    # Use the *same* walk function from your original scraper
    def walk(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for it in o:
                yield from walk(it)

    for candidate in walk(payload):
        name = (candidate.get('name') or candidate.get('playerName') or '')
        if not name:
            continue

        prop_val = extract_prop_from_candidate(candidate, prop_identifier)
        
        if prop_val is not None:
            team_name = candidate.get("teamName", candidate.get("team"))
            opp_name = candidate.get("opponentName", candidate.get("opponent"))

            if not team_name or not opp_name:
                participants = [p.get('name') for p in candidate.get('participants', []) if p.get('name')]
                if len(participants) == 2:
                    team_name = team_name or participants[0]
                    opp_name = opp_name or participants[1]

            prop_dict = {
                "name": name,
                "position": candidate.get("position", "N/A"),
                "team_name": team_name,
                "team_abbrev": candidate.get("teamAbbreviation"),
                "opponent_name": opp_name,
                "opponent_abbrev": candidate.get("opponentAbbreviation"),
                "start_time": candidate.get("startDate") or candidate.get("startTimeISO"),
                "league": league,
                "market_name": prop_type.replace('_', ' ').title(),
                "prop_line": prop_val
            }
            all_props_list.append(prop_dict)

    if not all_props_list:
        print(f"WARNING(dk-parser): Could not find any props in the sample JSON.")
        return []

    print(f"DEBUG(dk-parser): Extracted {len(all_props_list)} raw props from sample JSON.")
    
    # De-duplicate
    unique_props = { (p['name'], p['prop_line']) : p for p in all_props_list }.values()
    final_list = list(unique_props)
    
    print(f"DEBUG(dk-parser): Returning {len(final_list)} unique props.")
    return final_list

# ---
# --- YOUR EXISTING FUNCTIONS (scan_all_draftkings_props, etc.) ---
# ---
# (Keep all your other functions below this new one)

# ---
# --- NEW SCANNER FUNCTION (with Network Interception) ---
# ---

async def scan_all_draftkings_props(page: Page, league: str, prop_type: str) -> List[Dict[str, Any]]:
    """
    Scans a DraftKings page for ALL available player props for a given market
    by intercepting the site's internal API (XHR/Fetch) calls.
    """
    
    # 1. Navigate to the correct page
    url = f"https://sportsbook.draftkings.com/leagues/football/{league.lower()}"
    if league.lower() == 'cfb':
        url = "https://sportsbook.draftkings.com/leagues/football/ncaaf"
    
    print(f"DEBUG(dk): Navigating to {url} to scan all props...")

    # This list will be populated by our network response handler
    all_props_list = []
    
    # e.g., "passing" from "player_passing_yards"
    prop_identifier = prop_type.split('_')[1] if '_' in prop_type else prop_type

    # 2. Define the response handler
    async def handle_response(response: Response):
        """Listen for and parse API calls that contain prop data."""
        # We are looking for the API calls that return 'offers' or 'events'
        if "/offers/" not in response.url and "/events/" not in response.url:
            return
            
        if response.request.resource_type not in ["xhr", "fetch"]:
            return

        try:
            obj = await response.json()
        except Exception:
            return # Not a valid JSON response

        # Use the *same* walk function from your original scraper
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

            # Use your existing prop extractor to find the line
            prop_val = extract_prop_from_candidate(candidate, prop_identifier)
            
            if prop_val is not None:
                team_name = candidate.get("teamName", candidate.get("team"))
                opp_name = candidate.get("opponentName", candidate.get("opponent"))

                if not team_name or not opp_name:
                    participants = [p.get('name') for p in candidate.get('participants', []) if p.get('name')]
                    if len(participants) == 2:
                        team_name = team_name or participants[0]
                        opp_name = opp_name or participants[1]

                prop_dict = {
                    "name": name,
                    "position": candidate.get("position", "N/A"),
                    "team_name": team_name,
                    "team_abbrev": candidate.get("teamAbbreviation"),
                    "opponent_name": opp_name,
                    "opponent_abbrev": candidate.get("opponentAbbreviation"),
                    "start_time": candidate.get("startDate") or candidate.get("startTimeISO"),
                    "league": league,
                    "market_name": prop_type.replace('_', ' ').title(),
                    "prop_line": prop_val
                }
                all_props_list.append(prop_dict)

    # 3. Register the listener *before* navigating
    page.on('response', handle_response)
    
    # 4. Navigate and wait for the page to load and make API calls
    try:
        await page.goto(url, wait_until='networkidle', timeout=10000)
    except Exception:
        print("DEBUG(dk): Networkidle failed, trying domcontentloaded...")
        await page.goto(url, wait_until='domcontentloaded', timeout=10000)
    
    # Give listeners a moment to fire
    await page.wait_for_timeout(3000) 
    
    # 5. Unregister the listener (Note: Playwright Python doesn't have 'off', so we skip this)
    # page.off('response', handle_response)

    if not all_props_list:
        print(f"WARNING(dk): Network interception found no matching API calls. Trying HTML content fallback...")
        # --- FALLBACK: Try the old HTML content method ---
        # (This is the logic from the previous step)
        content = await page.content()
        js_objects = re.findall(r"(\{[\s\S]{100,200000}?\})", content)
        print(f"DEBUG(dk) [Fallback]: found {len(js_objects)} js_objects candidates")
        for idx, txt in enumerate(js_objects):
            try:
                obj = json.loads(txt)
            except Exception:
                continue

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

                prop_val = extract_prop_from_candidate(candidate, prop_identifier)
                
                if prop_val is not None:
                    team_name = candidate.get("teamName", candidate.get("team"))
                    opp_name = candidate.get("opponentName", candidate.get("opponent"))

                    if not team_name or not opp_name:
                        participants = [p.get('name') for p in candidate.get('participants', []) if p.get('name')]
                        if len(participants) == 2:
                            team_name = team_name or participants[0]
                            opp_name = opp_name or participants[1]

                    prop_dict = {
                        "name": name,
                        "position": candidate.get("position", "N/A"),
                        "team_name": team_name,
                        "team_abbrev": candidate.get("teamAbbreviation"),
                        "opponent_name": opp_name,
                        "opponent_abbrev": candidate.get("opponentAbbreviation"),
                        "start_time": candidate.get("startDate") or candidate.get("startTimeISO"),
                        "league": league,
                        "market_name": prop_type.replace('_', ' ').title(),
                        "prop_line": prop_val
                    }
                    all_props_list.append(prop_dict)

    if not all_props_list:
        print(f"WARNING(dk): All scraping methods failed. No props found.")
        return []

    print(f"DEBUG(dk): Extracted {len(all_props_list)} raw props.")
    
    # De-duplicate
    unique_props = { (p['name'], p['prop_line']) : p for p in all_props_list }.values()
    final_list = list(unique_props)
    
    print(f"DEBUG(dk): Returning {len(final_list)} unique props.")
    return final_list


# ---
# --- YOUR ORIGINAL FUNCTIONS (UNCHANGED) ---
# ---
# (Your original extract_prop_from_candidate and scrape_draftkings_player_props
# functions remain here, exactly as they were)
# ---

def extract_prop_from_candidate(candidate: Dict[str, Any], prop_identifier: str) -> Optional[float]:
    """Given a player-like candidate dict, pick the best prop value using sportsbook-priority.
    (This is your original function)
    """
    # ... (your original implementation) ...
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
    priority = ['draftkings_', 'fanduel_', 'mgm_', 'caesars_', 'espnbet_', 'betrivers_', 'hardrock_']
    def score_key(kv):
        k, _ = kv
        lk = k.lower()
        for i, p in enumerate(priority):
            if p in lk:
                return (0, i)
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


async def scrape_draftkings_player_props(page: Page, player_name: str, prop_type: str) -> Optional[OddsData]:
    """Attempt to scrape a DraftKings-style sportsbook page for a player's prop.
    (This is your original function)
    """
    # ... (your original implementation) ...
    urls = [
        'https://sportsbook.draftkings.com/',
        'https://sportsbook.draftkings.com/odds',
    ]
    target = player_name.strip().lower()
    target_last = target.split()[-1] if target else ''
    prop_identifier = prop_type.split('_')[1] if '_' in prop_type else prop_type
    for url in urls:
        try:
            await page.goto(url, wait_until='networkidle')
        except Exception:
            try:
                await page.goto(url, wait_until='domcontentloaded')
            except Exception:
                continue
        content = await page.content()
        js_objects = re.findall(r"(\{[\s\S]{100,200000}?\})", content)
        print(f"DEBUG(dk): found {len(js_objects)} js_objects candidates")
        for idx, txt in enumerate(js_objects[:30]):
            try:
                obj = json.loads(txt)
            except Exception:
                continue
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
                        return OddsData(prop_line=prop_val, over_odds=None, under_odds=None)
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
                        m = re.search(r"-?\d+\.?\d*", text)
                        if m:
                            try:
                                val = float(m.group(0))
                                return OddsData(prop_line=val, over_odds=None, under_odds=None)
                            except Exception:
                                continue
            except Exception:
                continue
    return None

