import streamlit as st
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cfb_prop_predictor.workflow import run_workflow_sync

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="CFB Prop Predictor",
    page_icon="🏈",
    layout="wide"
)

# --- UI Components ---
st.title("🏈 CFB Prop Predictor")
st.markdown("An AI-powered agent workflow to analyze and predict college football player props.")
import streamlit as st
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cfb_prop_predictor.workflow import run_workflow_sync

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="CFB Prop Predictor",
    page_icon="🏈",
    layout="wide"
)

# --- UI Components ---
st.title("🏈 CFB Prop Predictor")
st.markdown("An AI-powered agent workflow to analyze and predict college football player props.")

st.sidebar.header("Prediction Inputs")
game = st.sidebar.text_input("Game (e.g., Alabama vs Georgia):", "Alabama vs Georgia")
player = st.sidebar.text_input("Player Name:", "Jalen Milroe")
prop_type = st.sidebar.selectbox(
    "Prop Type:",
    ["player_passing_yards", "player_rushing_yards", "player_receiving_yards"],
    index=0
)

# Persist DraftKings toggle in session_state and URL query params
if 'enable_dk' not in st.session_state:
    q = st.query_params
    st.session_state['enable_dk'] = q.get('enable_dk', ['0'])[0] in ('1', 'true', 'True')

def _on_toggle():
    params = dict(st.query_params)
    params['enable_dk'] = '1' if st.session_state['enable_dk'] else '0'
    st.experimental_set_query_params(**params)

enable_dk = st.sidebar.checkbox(
    "Enable DraftKings fallback (may be slower)",
    value=st.session_state.get('enable_dk', False),
    key='enable_dk',
    on_change=_on_toggle,
)

if st.sidebar.button("▶️ Run Prediction"):
    request = {
        "game": game,
        "player": player,
        "prop_type": prop_type
    }

    with st.spinner("🔍 Agent is scraping live odds and running analysis..."):
        try:
            # Export env var so agents/data_gatherer can detect DraftKings fallback
            if enable_dk:
                os.environ['ENABLE_DK_FALLBACK'] = '1'
            else:
                os.environ.pop('ENABLE_DK_FALLBACK', None)

            result = run_workflow_sync(request)

            # Display results
            prediction = result.get('prediction', {})
            analysis = result.get('analysis', {})
            gathered_data = result.get('gathered_data', {})

            st.header(f"Prediction for {player}")

            col1, col2, col3 = st.columns(3)

            rec = prediction.get('recommended_bet', 'N/A')
            prop_line = ''
            try:
                prop_line = gathered_data.get('odds_data', {}).get('prop_line', '')
            except Exception:
                prop_line = ''

            col1.metric(
                label="Recommendation",
                value=f"{rec.upper()} {prop_line if prop_line is not None else ''}"
            )

            col2.metric(label="Confidence", value=f"{prediction.get('confidence', 'N/A')}%")
            col3.metric(label="Projected Value", value=prediction.get('projected_value', 'N/A'), delta=f"{prediction.get('edge', 'N/A')} edge")

            st.subheader("📝 Reasoning & Analysis")
            st.info(analysis.get('summary', 'No summary available'))

            with st.expander("Show Detailed Data"):
                st.write("**Risk Factors Identified:**")
                for risk in analysis.get('risk_factors', []):
                    st.write(f"- {risk}")
                st.write("---")
                st.json(result)

        except Exception as e:
            st.error(f"An error occurred during the workflow: {e}")

# Note about bot protection
st.markdown(
    """
    **Bot protection / scraping note:**

    Some sportsbooks (DraftKings, FanDuel, PrizePicks, etc.) use bot-protection (for example PerimeterX) that can block headless/browser automation. If the DraftKings fallback is enabled you may see slower responses or no data when running from this dev container. Recommended options if scraping is blocked:

    - Run the Streamlit app locally from a machine with a normal browser session (not headless) and enable the toggle.
    - Capture and provide sample API/GraphQL payloads from a real browser session so we can add snapshot-based unit tests.
    - Use an authenticated browser context/session that passes the protection.

    The toggle persists in the URL so you can share a link with the fallback enabled.
    """
)


