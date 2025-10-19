import streamlit as st
import sys
import os
from datetime import datetime

# Adjust path to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from cfb_prop_predictor.workflow import run_workflow_sync
    from dashboard.mapper import _rows_from_gathered
    # dashboard.renderer is optional — use mapper + native Streamlit if not present
except ImportError:
    st.error("Failed to import workflow modules. Make sure you are in the correct environment.")
    st.stop()

# --- App Configuration ---
st.set_page_config(
    page_title="CFB Prop Predictor",
    page_icon="🏈",
    layout="wide",
)

# --- App State ---
# Use the new st.query_params API
default_league = st.query_params.get("league", "CFB")
default_prop = st.query_params.get("prop", "player_passing_yards")

# --- League Filter Callback ---
def _on_league_change():
    """Update query params when the league filter changes."""
    league = st.session_state.get('league_filter', 'CFB')
    st.query_params["league"] = league
    # No rerun needed, Streamlit reruns on widget change

# --- Caching ---
@st.cache_data(ttl=600) # Cache for 10 minutes
def load_market_data(league: str, prop_type: str):
    """
    Cached function to run the workflow.
    This runs automatically when the app loads or filters change.
    """
    print(f"Cache miss. Running workflow for {league} / {prop_type}...")
    try:
        result = run_workflow_sync(league=league, prop_type=prop_type)
        return result
    except Exception as e:
        print(f"Error running workflow: {e}")
        return {"error": str(e)}

# --- Sidebar ---
with st.sidebar:
    # Use a local static icon bundled with the dashboard to avoid remote fetch issues
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'icons', 'check.svg')
    if os.path.exists(logo_path):
        st.image(logo_path)
    else:
        # Fallback to a small emoji if the file isn't present
        st.markdown("# 🏈")
    st.header("Filters")
    
    st.selectbox(
        "League",
        ("CFB", "NFL"),
        key='league_filter',
        index=0 if default_league == "CFB" else 1,
        on_change=_on_league_change,
    )
    
    prop_type = st.selectbox(
        "Prop Type",
        ("player_passing_yards", "player_rushing_yards", "player_receiving_yards"),
        key='prop_type_filter',
        index=0
    )

# --- Main Page ---
st.title("🏈 CFB Prop Predictor")
st.markdown("An AI-powered agent workflow to analyze and predict college/NFL player props.")

st.header("Live Market Snapshot")

# --- Automatic Workflow Execution ---
# Get filter values from session state
current_league = st.session_state.get('league_filter', 'CFB')
current_prop = st.session_state.get('prop_type_filter', 'player_passing_yards')

# Automatically run the workflow.
# Streamlit will use the cached result if filters haven't changed.
with st.spinner(f"Scanning {current_league} {current_prop.split('_')[1]} props..."):
    result = load_market_data(league=current_league, prop_type=current_prop)

# --- Display Results ---
if "error" in result:
    st.error(f"Failed to load data: {result['error']}")
elif result:
    gathered_data = result.get("gathered_data", {})
    
    # Map the list of props to table rows
    rows = _rows_from_gathered(gathered_data, request=None, result=result)
    
    if not rows:
        st.warning(f"No props found for {current_league} {current_prop.split('_')[1]}.")
    else:
        st.success(f"Found {len(rows)} props.")
        
        # Build the table with configured columns
        column_config = {
            "player": st.column_config.TextColumn("Player"),
            "prediction_score": st.column_config.ProgressColumn(
                "Prediction",
                format="%d%%",
                min_value=0,
                max_value=100,
                help="Prediction confidence (0-100). Bypassed for scanner.",
            ),
        }
        
        # Use st.dataframe to render the table
        st.dataframe(
            rows,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

    # Show detailed data in an expander
    with st.expander("Show Detailed Data (Raw JSON)"):
        st.json(result)
else:
    st.info("Workflow returned no result.")


