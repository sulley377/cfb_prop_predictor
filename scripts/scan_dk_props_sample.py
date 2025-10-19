#!/usr/bin/env python3
"""
Sample runner for scan_all_draftkings_props.
Requires Playwright to be installed and browsers available (run `playwright install`).
"""
import asyncio
import os
import json
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Utilis.dk_scraper import scan_all_draftkings_props
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        results = await scan_all_draftkings_props(page)
        await browser.close()
        print(json.dumps([{
            'name': r.get('name'),
            'prop': r.get('prop_identifier'),
            'value': r.get('prop_value'),
            'team': r.get('team_abbrev'),
            'opp': r.get('opponent_abbrev'),
            'league': r.get('league')
        } for r in results][:200], indent=2))

if __name__ == '__main__':
    asyncio.run(main())
