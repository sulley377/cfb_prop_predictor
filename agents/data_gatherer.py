# In agents/data_gatherer.py
from cfb_prop_predictor.types import GatheredData, OddsData
# --- IMPORT OUR NEW API SCRAPER ---
from Utilis.api_scraper import fetch_props_from_api
from Utilis.dk_scraper import parse_dk_json_payload
from typing import List, Dict, Any
import os
import json

# --- THIS IS NOW A SYNC FUNCTION (no async/await) ---
def gather_data(league: str, prop_type: str) -> GatheredData:
    """
    Gathers data by scraping all available props for a given league and prop_type
    using the direct DraftKings API, with fallback to local sample data.
    """
    print(f"[DataGatherer] Starting data gathering for ALL props: {league} / {prop_type}...")

    # --- TRY API FIRST, FALLBACK TO SAMPLE DATA ---
    scraped_props_list = []
    try:
        scraped_props_list = fetch_props_from_api(league, prop_type)
        if scraped_props_list:
            print(f"[DataGatherer] Successfully fetched {len(scraped_props_list)} props from API.")
        else:
            print(f"[DataGatherer] API returned no props, falling back to sample data...")
            scraped_props_list = _load_sample_data(league, prop_type)
    except Exception as e:
        print(f"[DataGatherer] API failed ({e}), falling back to sample data...")
        scraped_props_list = _load_sample_data(league, prop_type)

    if not scraped_props_list:
        print(f"[DataGatherer] Could not find any props for {league} / {prop_type}.")

    # We return the 'all_props' key, which the mapper will read.
    return GatheredData(
        odds_data=None,       # No longer used at top level
        player_stats=None,  # No longer used at top level
        team_stats=None,    # No longer used at top level
        all_props=scraped_props_list # NEW: Pass the full list
    )

def _load_sample_data(league: str, prop_type: str) -> List[Dict[str, Any]]:
    """
    Fallback helper to load and parse a local sample JSON file.
    """
    print(f"[DataGatherer] Loading local sample data...")
    try:
        # Build a path from this file to the sample file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sample_path = os.path.join(base_dir, '..', 'tests', 'samples', 'dk_sample.json')

        with open(sample_path, 'r') as f:
            payload = json.load(f)

        # Parse the sample data
        props_list = parse_dk_json_payload(payload, league, prop_type)
        print(f"[DataGatherer] Parsed {len(props_list)} props from sample file.")
        return props_list
    except Exception as e:
        print(f"[DataGatherer] Error loading sample data: {e}")
        return []

