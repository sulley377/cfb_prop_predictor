# In agents/data_gatherer.py
from cfb_prop_predictor.types import GatheredData, OddsData
# --- IMPORT THE NEW SCANNER FUNCTION ---
from Utilis.dk_scraper import scan_all_draftkings_props 
from Utilis.llm_extractor import extract_props
import os
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, async_playwright
import shutil
import json # <-- Add json import
from Utilis.dk_scraper import parse_dk_json_payload # <-- Import the new parser
from Utilis.api_scraper import fetch_props_from_api # <-- Import the new API scraper

# --- NEW FUNCTION SIGNATURE ---
async def gather_data(league: str, prop_type: str) -> GatheredData:
    """
    Gathers data by scraping all available props for a given league and prop_type.
    """
    print(f"[DataGatherer] Starting data gathering for ALL props: {league} / {prop_type}...")

    # --- This helper call will run the new 'scan_all_draftkings_props' ---
    scraped_props_list = await _scrape_all_dk_props(league, prop_type)

    if not scraped_props_list:
        print(f"[DataGatherer] Could not find any props for {league} / {prop_type}.")

    # We now return a new 'all_props' key, which the mapper will read.
    return GatheredData(
        odds_data=None,       # No longer used at top level
        player_stats=None,  # No longer used at top level
        team_stats=None,    # No longer used at top level
        all_props=scraped_props_list # NEW: Pass the full list
    )

async def _scrape_all_dk_props(league: str, prop_type: str) -> List[Dict[str, Any]]:
    """
    Helper to load and parse a local sample JSON file.
    This avoids brittle live scraping and API issues.
    """
    print(f"[DataGatherer] Loading local sample data (API approach needs more work)...")
    
    # --- Load sample data from your tests ---
    try:
        # Build a path from this file to the sample file
        # (agents/data_gatherer.py -> ../tests/samples/dk_sample.json)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sample_path = os.path.join(base_dir, '..', 'tests', 'samples', 'dk_sample.json') #
        
        with open(sample_path, 'r') as f:
            payload = json.load(f)
            
    except Exception as e:
        print(f"CRITICAL: Could not load sample file '{sample_path}'. Error: {e}")
        return []

    # --- Call the new parser function ---
    # This function is not async, so we just call it and return
    try:
        props_list = parse_dk_json_payload(payload, league, prop_type)
        print(f"[DataGatherer] Parsed {len(props_list)} props from sample file.")
        return props_list
    except Exception as e:
        print(f"Error parsing sample JSON: {e}")
        return []

