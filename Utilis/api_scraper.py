import requests
import json
from typing import List, Dict, Any, Optional

# ---
# --- THIS IS THE BREAKTHROUGH ---
# ---
# These IDs tell the DK API which league to get.
# 88808 = NFL
# 87637 = CFB
EVENT_GROUP_IDS = {
    "NFL": "88808",
    "CFB": "87637"
}

# These are the category IDs for prop markets
# We can add more here later
CATEGORY_IDS = {
    "player_passing_yards": 1000,
    "player_rushing_yards": 1001,
    "player_receiving_yards": 1002,
}

BASE_URL = "https://sportsbook.draftkings.com/sites/US-NJ-SB/api/v5"

def get_event_group_id(league: str) -> Optional[str]:
    return EVENT_GROUP_IDS.get(league.upper())

def get_category_id(prop_type: str) -> Optional[int]:
    return CATEGORY_IDS.get(prop_type)

def fetch_props_from_api(league: str, prop_type: str) -> List[Dict[str, Any]]:
    """
    Scrapes DraftKings for live props by hitting the internal API directly,
    bypassing Playwright.
    """
    print(f"[api_scraper] Starting direct API scrape for {league} / {prop_type}")
    
    event_group_id = get_event_group_id(league)
    if not event_group_id:
        print(f"[api_scraper] ERROR: No Event Group ID found for league '{league}'")
        return []
        
    category_id = get_category_id(prop_type)
    if not category_id:
        print(f"[api_scraper] ERROR: No Category ID found for prop_type '{prop_type}'")
        return []

    # This logic is adapted from your NFLScraper class
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://sportsbook.draftkings.com/',
        }
        
        # 1. Get all subcategory IDs for this prop type
        url1 = f"{BASE_URL}/eventgroups/{event_group_id}/categories/{category_id}?format=json"
        print(f"[api_scraper] Fetching subcategories from {url1}")
        resp1 = requests.get(url1, headers=headers)
        resp1.raise_for_status() # Raise an exception for bad status codes
        dk_markets = resp1.json().get('eventGroup', {}).get('offerCategories', [])
        
        subcategory_ids = []
        for cat in dk_markets:
            if 'offerSubcategoryDescriptors' in cat:
                for subcat in cat['offerSubcategoryDescriptors']:
                    subcategory_ids.append(subcat['subcategoryId'])
        
        if not subcategory_ids:
            print("[api_scraper] No subcategory IDs found. Prop market might be empty.")
            return []

        print(f"[api_scraper] Found {len(subcategory_ids)} subcategories. Fetching props...")
        
        # 2. Loop over each subcategory and get its props
        all_props = []
        for sub_id in subcategory_ids:
            url2 = f"{BASE_URL}/eventgroups/{event_group_id}/categories/{category_id}/subcategories/{sub_id}?format=json"
            resp2 = requests.get(url2, headers=headers)
            resp2.raise_for_status()
            
            offer_categories = resp2.json().get('eventGroup', {}).get('offerCategories', [])
            
            for cat in offer_categories:
                if 'offerSubcategoryDescriptors' in cat:
                    for subcat in cat['offerSubcategoryDescriptors']:
                        if 'offerSubcategory' in subcat:
                            market_name = subcat.get('name', 'Unknown Market')
                            for offer in subcat['offerSubcategory']['offers']:
                                for market in offer:
                                    if 'participant' not in market['outcomes'][0]:
                                        continue # Not a player prop
                                        
                                    player_name = market['outcomes'][0]['participant']
                                    
                                    # This is the "Over"
                                    o_line = market['outcomes'][0].get('line')
                                    o_odds = market['outcomes'][0].get('oddsAmerican')
                                    
                                    # This is the "Under"
                                    u_line = market['outcomes'][1].get('line')
                                    u_odds = market['outcomes'][1].get('oddsAmerican')

                                    # We only care about the main line (Over/Under are same)
                                    prop_line = o_line 
                                    
                                    prop_dict = {
                                        "name": player_name,
                                        "position": "N/A", # API doesn't provide this here
                                        "team_name": "N/A", # API doesn't provide this here
                                        "opponent_name": "N/A", # API doesn't provide this here
                                        "start_time": market.get('startDate'),
                                        "league": league,
                                        "market_name": market_name,
                                        "prop_line": prop_line,
                                        "over_odds": o_odds,
                                        "under_odds": u_odds
                                    }
                                    all_props.append(prop_dict)

        print(f"[api_scraper] Found {len(all_props)} total props.")
        return all_props
        
    except requests.exceptions.RequestException as e:
        print(f"[api_scraper] ERROR: Direct API call failed. {e}")
        return []
    except Exception as e:
        print(f"[api_scraper] ERROR: Failed to parse API response. {e}")
        return []