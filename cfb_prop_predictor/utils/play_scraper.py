"""Proxy to the top-level Utilis/play_scraper.py so imports via
`cfb_prop_predictor.utils.play_scraper` succeed.
"""
from __future__ import annotations

# Import everything from the top-level Utilis.play_scraper
from Utilis.play_scraper import *  # type: ignore

__all__ = [name for name in dir() if not name.startswith('_')]


# Provide the interface expected by agents/data_gatherer.py
async def scrape_rotowire_props(player_name: str, prop_keyword: str):
	"""Async wrapper that launches Playwright, navigates to Rotowire, and
	calls the low-level `scrape_player_props` function exported from
	`Utilis.play_scraper`.

	Returns a dict with keys matching `OddsData` or None.
	"""
	from playwright.async_api import async_playwright

	prop_type = f"player_{prop_keyword}_yards"

	async with async_playwright() as p:
		browser = await p.chromium.launch(headless=True)
		page = await browser.new_page()
		try:
			# call the imported function from Utilis.play_scraper
			result = await scrape_player_props(page, player_name, prop_type)  # type: ignore
		finally:
			await page.close()
			await browser.close()

	if not result:
		return None

	# Normalize result attributes/names to the dict expected by agents
	prop_line = None
	over = None
	under = None
	for attr in ("propLine", "prop_line", "propline", "line"):
		if hasattr(result, attr):
			prop_line = float(getattr(result, attr))
			break
	for attr in ("overOdds", "over_odds", "over"):
		if hasattr(result, attr):
			over = getattr(result, attr)
			break
	for attr in ("underOdds", "under_odds", "under"):
		if hasattr(result, attr):
			under = getattr(result, attr)
			break

	return {"prop_line": prop_line, "over_odds": over, "under_odds": under}
