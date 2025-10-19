# Data gatherer agent
from cfb_prop_predictor.types import GatheredData, OddsData
from cfb_prop_predictor.utils.play_scraper import scrape_rotowire_props
from Utilis.dk_scraper import scrape_draftkings_player_props
from Utilis.llm_extractor import extract_props
import os
from typing import Optional


async def _scrape_dk_player_data(player: str, prop_type: str):
    """Launch Playwright and call the DraftKings scraper to retrieve rich data.

    Returns the dict emitted by `scrape_draftkings_player_props` or None.
    """
    try:
        from playwright.async_api import async_playwright
        import shutil
        async with async_playwright() as p:
            headed_requested = os.environ.get('PLAYWRIGHT_HEADED', '0') in ('1', 'true', 'True')
            can_head = bool(os.environ.get('DISPLAY')) or bool(shutil.which('Xvfb'))
            if headed_requested and not can_head:
                headed = False
            else:
                headed = headed_requested and can_head
            browser = await p.chromium.launch(headless=(not headed))
            page = await browser.new_page()
            try:
                dk_result = await scrape_draftkings_player_props(page, player, prop_type)
            finally:
                await page.close()
                await browser.close()
        return dk_result
    except Exception:
        return None


async def gather_data(game: str, player: Optional[str], prop_type: str) -> GatheredData:
    """
    Gathers data by scraping live odds and stats from DraftKings.
    """
    print(f"[DataGatherer] Starting data gathering for {player}...")

    scraped_data = None
    odds_data = None
    player_stats = None
    team_stats = None

    if player:
        # Prefer faster Rotowire proxy unless explicit DK fallback is enabled
        enable_dk = os.getenv('ENABLE_DK_FALLBACK', '0').lower() in ('1', 'true', 'yes')
        scraped_data = None
        if not enable_dk:
            # try the project's Rotowire proxy (faster, already tuned)
            try:
                prop_keyword = prop_type.split('_')[1]
                rw = await scrape_rotowire_props(player, prop_keyword)
                if rw:
                    # normalize to the rich dict shape
                    scraped_data = {
                        'name': player,
                        'position': None,
                        'team_name': None,
                        'team_abbrev': None,
                        'opponent_name': None,
                        'opponent_abbrev': None,
                        'league': None,
                        'start_time': None,
                        'odds_data': OddsData(**rw)
                    }
            except Exception:
                scraped_data = None

        if scraped_data is None and enable_dk:
            scraped_data = await _scrape_dk_player_data(player, prop_type)

    if scraped_data:
        print(f"[DataGatherer] Successfully scraped data for {player} from DK.")
        odds_data = scraped_data.get('odds_data')

        player_stats = {
            "name": scraped_data.get("name", player),
            "position": scraped_data.get("position", "N/A"),
            "team_name": scraped_data.get("team_name"),
            "team_abbrev": scraped_data.get("team_abbrev"),
            "league": scraped_data.get("league"),
            "opponent_name": scraped_data.get("opponent_name"),
            "opponent_abbrev": scraped_data.get("opponent_abbrev"),
            "start_time": scraped_data.get("start_time"),
            "season_stats": {},
            "last_five_games": []
        }

        team_stats = {
            "name": scraped_data.get("team_name"),
            "league": scraped_data.get("league"),
            "offensive_rank": "N/A",
            "defensive_rank": "N/A"
        }
    else:
        print(f"[DataGatherer] Could not find any data for {player}.")
        player_stats = {"name": player}
        team_stats = {"name": "N/A"}

    return GatheredData(
        odds_data=odds_data,
        player_stats=player_stats,
        team_stats=team_stats
    )

