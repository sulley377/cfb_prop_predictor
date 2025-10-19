import asyncio
from playwright.async_api import async_playwright, Page
from typing import Optional
from cfb_prop_predictor.types import OddsData, MatchupOdds
import re
import json

async def scrape_player_props(page: Page, player_name: str, prop_type: str) -> Optional[OddsData]:
    """Scrapes Rotowire for a specific player's prop line and odds.

    This function will try the NFL player-props page first, then fall back to
    the college-football player-props page. Name matching is case-insensitive
    and includes a simple fuzzy fallback that matches last names.
    """
    urls = [
        'https://www.rotowire.com/betting/nfl/player-props.php',
        'https://www.rotowire.com/betting/college-football/player-props.php'
    ]

    prop_identifier = prop_type.split('_')[1]  # e.g., 'passing'
    target_name = player_name.strip().lower()
    target_last = target_name.split()[-1]

    for url in urls:
        try:
            await page.goto(url, wait_until='networkidle')
        except Exception:
            # fallback to domcontentloaded if networkidle is unreliable
            await page.goto(url, wait_until='domcontentloaded')

        # Try to parse embedded JSON data first (Rotowire often injects player data
        # into script blocks as JS objects). This is more reliable for NFL pages
        # which render content client-side.
        try:
            content = await page.content()
            # Find JS `data: [...]` arrays in the page and try to parse them.
            js_arrays = re.findall(r"data:\s*(\[[\s\S]*?\])", content)
            print(f"DEBUG: found {len(js_arrays)} js_arrays")
            for idx, arr_text in enumerate(js_arrays):
                print(f"DEBUG: parsing array #{idx}, len={len(arr_text)}")
                try:
                    data_list = json.loads(arr_text)
                except Exception:
                    # Not strictly JSON or failed to parse; skip
                    print("DEBUG: json.loads failed for an array")
                    continue

                # data_list is expected to be a list of player dicts
                if not isinstance(data_list, list):
                    continue

                for player_obj in data_list:
                    # Basic shape check
                    if not isinstance(player_obj, dict):
                        continue
                    name = (player_obj.get('name') or '').strip()
                    if not name:
                        continue
                    print(f"DEBUG: json player name={name}")

                    name_norm = re.sub(r"[^a-z0-9 ]+", "", name.lower())
                    if name_norm == target_name or target_last in name_norm.split():
                        # Detailed debug for matched candidate so we can inspect available keys/values
                        try:
                            print(f"DEBUG: matched target candidate name={name} (norm={name_norm})")
                            keys = list(player_obj.keys())
                            print(f"DEBUG: player_obj keys count={len(keys)}")
                            # show prop-like keys (rec, yds, pass, rush, td) and market keys
                            interesting = {k: player_obj[k] for k in keys if any(sub in k.lower() for sub in ['rec', 'yds', 'pass', 'rush', 'td', 'mgm', 'draft', 'fanduel', 'underdog', 'caesars', 'bet'])}
                            # Truncate the dump to avoid huge logs
                            try:
                                interesting_json = json.dumps(interesting)
                                print(f"DEBUG: interesting keys and values={interesting_json[:1000]}")
                            except Exception:
                                print(f"DEBUG: interesting keys (non-json)={list(interesting.keys())}")
                            try:
                                full_len = len(json.dumps(player_obj))
                                print(f"DEBUG: player_obj JSON len={full_len}")
                            except Exception:
                                pass
                        except Exception:
                            print("DEBUG: failed to print detailed player_obj info")
                        # Delegate extraction to provider_parser which prefers sportsbook-prefixed keys
                        try:
                            from Utilis.provider_parser import extract_prop_from_candidate
                            prop_val = extract_prop_from_candidate(player_obj, prop_identifier)
                        except Exception:
                            prop_val = None

                        if prop_val is not None:
                            return OddsData(prop_line=prop_val, over_odds=None, under_odds=None)
        except Exception:
            # don't let the JSON fallback crash the scraper; continue to DOM parsing
            pass

        # The page content is rendered by JS; wait for expected containers.
        found_container = False
        selector_candidates = [
            '.prop-lines-table tbody',
            '.props-table tbody',
            'table tbody',
            '.player-props-table tbody'
        ]
        for sel in selector_candidates:
            try:
                await page.wait_for_selector(sel, timeout=3000)
                locators = page.locator(sel)
                found_container = True
                break
            except Exception:
                locators = None

        if not found_container:
            # nothing to parse on this URL, try the next
            continue

        for i in range(await locators.count()):
            section = locators.nth(i)
            # header may be None for some tables
            header_text_content = ''
            if await section.locator('tr.table-header td.font-bold').count():
                header = await section.locator('tr.table-header td.font-bold').text_content()
                header_text_content = header or ''
            if prop_identifier in header_text_content.lower():
                player_rows = section.locator('tr:not(.table-header)')
                for j in range(await player_rows.count()):
                    row = player_rows.nth(j)
                    # name link may be present under different selectors
                    name_el = None
                    if await row.locator('a.font-bold').count():
                        name_el = row.locator('a.font-bold')
                    elif await row.locator('td a').count():
                        name_el = row.locator('td a')

                    if not name_el:
                        continue

                    name_text = (await name_el.text_content() or '').strip()
                    # normalize names: remove punctuation, multiple spaces
                    name_norm = re.sub(r"[^a-z0-9 ]+", "", name_text.lower())
                    target_norm = re.sub(r"[^a-z0-9 ]+", "", target_name)
                    target_last_norm = re.sub(r"[^a-z0-9]+", "", target_last)

                    # Exact match first
                    if name_norm == target_norm:
                        matched = True
                    else:
                        # Containment or last-name match
                        matched = (target_last_norm in name_norm.split()) or (target_norm in name_norm)

                    if matched:
                        # attempt to read the line and odds
                        line = await row.locator('.line-cell .line').text_content() if await row.locator('.line-cell .line').count() else None
                        odds_list = await row.locator('.line-cell .odds').all_text_contents() if await row.locator('.line-cell .odds').count() else []
                        if line:
                            try:
                                prop_line_val = float(line.strip())
                            except Exception:
                                # try to extract float using regex
                                m = re.search(r"[0-9]+\.?[0-9]*", line)
                                prop_line_val = float(m.group(0)) if m else None
                        else:
                            prop_line_val = None

                        over_odds = None
                        under_odds = None
                        if odds_list and len(odds_list) >= 2:
                            try:
                                over_odds = int(odds_list[0].strip())
                                under_odds = int(odds_list[1].strip())
                            except Exception:
                                pass

                        if prop_line_val is not None:
                            return OddsData(prop_line=prop_line_val, over_odds=over_odds, under_odds=under_odds)
    return None

async def scrape_matchup_odds(page: Page, game: str) -> Optional[MatchupOdds]:
    """Scrapes Rotowire for a specific game's matchup odds."""
    await page.goto('https://www.rotowire.com/betting/college-football/odds', wait_until='domcontentloaded')
    
    try:
        away_team_name, home_team_name = [team.strip() for team in game.split('vs.')]
    except ValueError:
        return None # Handle cases where the game string is not formatted correctly

    game_rows = page.locator('.odds-table-container .grid.grid-cols-12')
    for i in range(await game_rows.count()):
        row = game_rows.nth(i)
        teams = await row.locator('.w-full.flex.items-center a.text-sm').all_text_contents()
        if len(teams) >= 2 and away_team_name in teams[0] and home_team_name in teams[1]:
            odds_elements = row.locator('.flex.w-full.justify-end .flex-col')
            
            # Extract text content safely
            spread_away_text = await odds_elements.nth(0).all_text_contents()
            spread_home_text = await odds_elements.nth(1).all_text_contents()
            moneyline_away = await odds_elements.nth(2).text_content()
            moneyline_home = await odds_elements.nth(3).text_content()
            total_over_text = await odds_elements.nth(4).all_text_contents()
            total_under_text = await odds_elements.nth(5).all_text_contents()

            return MatchupOdds(
                awayTeam=teams[0].strip(),
                homeTeam=teams[1].strip(),
                spread={'away': " ".join(spread_away_text), 'home': " ".join(spread_home_text)},
                moneyline={'away': moneyline_away.strip(), 'home': moneyline_home.strip()},
                total={'over': " ".join(total_over_text), 'under': " ".join(total_under_text)}
            )
    return None
# Play scraper utility
