import asyncio
from playwright.async_api import async_playwright, Page
from typing import Optional
from cfb_prop_predictor.types import OddsData, MatchupOdds
import re

async def scrape_player_props(page: Page, player_name: str, prop_type: str) -> Optional[OddsData]:
    """Scrapes Rotowire for a specific player's prop line and odds."""
    await page.goto('https://www.rotowire.com/betting/college-football/player-props.php', wait_until='domcontentloaded')
    
    prop_identifier = prop_type.split('_')[1]  # e.g., 'passing'
    
    locators = page.locator('.prop-lines-table tbody')
    for i in range(await locators.count()):
        section = locators.nth(i)
        header_text_content = await section.locator('tr.table-header td.font-bold').text_content()
        if header_text_content and prop_identifier in header_text_content.lower():
            player_rows = section.locator('tr:not(.table-header)')
            for j in range(await player_rows.count()):
                row = player_rows.nth(j)
                name = await row.locator('a.font-bold').text_content()
                if name and name.strip() == player_name:
                    line = await row.locator('.line-cell .line').text_content()
                    odds_list = await row.locator('.line-cell .odds').all_text_contents()
                    if line and odds_list and len(odds_list) >= 2:
                        return OddsData(
                            propLine=float(line.strip()),
                            overOdds=int(odds_list[0].strip()),
                            underOdds=int(odds_list[1].strip())
                        )
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
