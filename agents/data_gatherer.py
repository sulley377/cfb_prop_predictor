# Data gatherer agent
from cfb_prop_predictor.types import GatheredData, OddsData
from cfb_prop_predictor.utils.play_scraper import scrape_rotowire_props
from Utilis.dk_scraper import scrape_draftkings_player_props
from Utilis.llm_extractor import extract_props
import os
from typing import Optional

async def gather_data(game: str, player: Optional[str], prop_type: str) -> GatheredData:
    """
    Gathers data by scraping live odds and fetching historical stats.
    NOTE: Historical stat fetching is not yet implemented.
    """
    print(f"[DataGatherer] Starting data gathering for {player}...")

    odds_data = None
    if player:
        prop_keyword = prop_type.split('_')[1] # e.g., "passing" from "player_passing_yards"
        odds_data_dict = await scrape_rotowire_props(player, prop_keyword)
        if odds_data_dict:
            odds_data = OddsData(**odds_data_dict)
            print(f"[DataGatherer] Successfully scraped odds for {player}: Line {odds_data.prop_line}")
        else:
            print(f"[DataGatherer] Could not find live odds for {player} on Rotowire.")
            # Optionally try DraftKings as a fallback when enabled via env var
            enable_dk = os.getenv('ENABLE_DK_FALLBACK', '0').lower() in ('1', 'true', 'yes')
            if enable_dk:
                print(f"[DataGatherer] ENABLE_DK_FALLBACK enabled — trying DraftKings for {player}...")
                # Try DraftKings as a fallback
                try:
                    from playwright.async_api import async_playwright
                    async with async_playwright() as p:
                        import shutil
                        headed_requested = os.environ.get('PLAYWRIGHT_HEADED', '0') in ('1', 'true', 'True')
                        can_head = bool(os.environ.get('DISPLAY')) or bool(shutil.which('Xvfb'))
                        if headed_requested and not can_head:
                            print("NOTICE: PLAYWRIGHT_HEADED requested but no DISPLAY or Xvfb found; falling back to headless mode.")
                            headed = False
                        else:
                            headed = headed_requested and can_head
                        browser = await p.chromium.launch(headless=(not headed))
                        page = await browser.new_page()
                        dk_result = await scrape_draftkings_player_props(page, player, prop_type)
                        await page.close()
                        await browser.close()
                except Exception:
                    dk_result = None

                if dk_result:
                    # dk_result is an OddsData model
                    odds_data = dk_result
                    print(f"[DataGatherer] DraftKings provided odds for {player}: Line {odds_data.prop_line}")
                else:
                    print(f"[DataGatherer] Could not find live odds for {player} on DraftKings either.")
                    # As a last resort for demo: try an LLM-assisted extractor using page content or a sample payload
                    use_sample = os.environ.get('USE_SAMPLE_PAYLOAD', '0') in ('1', 'true', 'True')
                    if use_sample:
                        print("[DataGatherer] USE_SAMPLE_PAYLOAD=1 -> attempting LLM extractor on sample payload...")
                        # Load an included sample JSON if present
                        sample_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'samples', 'dk_sample.json')
                        try:
                            with open(sample_path, 'r') as f:
                                sample = f.read()
                        except Exception:
                            sample = None

                        parsed = None
                        try:
                            parsed = extract_props(sample or '', player, prop_type)
                        except Exception:
                            parsed = None

                        if parsed:
                            odds_data = parsed
                            print(f"[DataGatherer] LLM extractor returned a sample odds line: {odds_data.prop_line}")
            else:
                print(f"[DataGatherer] DraftKings fallback disabled (ENABLE_DK_FALLBACK != 1). Skipping.")

    # Placeholder for player and team stats - to be replaced with API calls
    player_stats_placeholder = None
    if player:
        player_stats_placeholder = {
            "name": player,
            "position": "QB", # Placeholder
            "season_stats": {"passing_yards": 2800}, # Placeholder
            "last_five_games": []
        }

    team_stats_placeholder = {
        "name": game.split(' vs ')[0],
        "offensive_rank": 10, # Placeholder
        "defensive_rank": 25  # Placeholder
    }

    return GatheredData(
        odds_data=odds_data,
        player_stats=player_stats_placeholder,
        team_stats=team_stats_placeholder
    )

