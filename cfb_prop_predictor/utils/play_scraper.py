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
	import os

	prop_type = f"player_{prop_keyword}_yards"

	async with async_playwright() as p:
		# Respect PLAYWRIGHT_HEADED env var to run a headed browser if needed
		import shutil
		headed_requested = os.environ.get('PLAYWRIGHT_HEADED', '0') in ('1', 'true', 'True')
		# Only actually run headed if an X server or Xvfb is available
		can_head = bool(os.environ.get('DISPLAY')) or bool(shutil.which('Xvfb'))
		if headed_requested and not can_head:
			print("NOTICE: PLAYWRIGHT_HEADED requested but no DISPLAY or Xvfb found; falling back to headless mode.")
			headed = False
		else:
			headed = headed_requested and can_head
		# If headed is True launch with headless=False; otherwise headless=True
		browser = await p.chromium.launch(headless=(not headed))
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
