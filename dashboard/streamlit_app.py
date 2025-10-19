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

# --- UI Components (hero) ---
def _inject_design_system_tokens():
    # Minimal token mapping from Priceline design-system
    primary = "#0068ef"  # theme.colors.blue
    background = "#edf0f3"  # buttonGray / light background
    text = "#001833"  # theme.text
    border = "#c0cad5"
    radius = "8px"

    # Google Fonts link for Montserrat
    fonts_link = (
        '<link href="https://fonts.googleapis.com/css?family=Montserrat:400,500,600,700&display=swap" rel="stylesheet">'
    )

    css = f"""
    {fonts_link}
    <style>
        :root {{
            --pcln-primary: {primary};
            --pcln-background: {background};
            --pcln-text: {text};
            --pcln-border: {border};
            --pcln-radius: {radius};
        }}
        html, body, [class*="css"] {{
            font-family: Montserrat, 'Helvetica Neue', Arial, sans-serif !important;
            color: var(--pcln-text) !important;
        }}
        .stApp {{
            background-color: var(--pcln-background) !important;
        }}
        .pcln-card {{
            border: 1px solid var(--pcln-border);
            border-radius: var(--pcln-radius);
            padding: 12px;
            background: white;
        }}
        .pcln-primary-btn {{
            background-color: var(--pcln-primary) !important;
            color: #fff !important;
            border-radius: var(--pcln-radius) !important;
        }}
        /* Hero and metric styles */
        .hero {{
            display:flex;
            align-items:center;
            padding: 24px 12px;
            gap: 16px;
        }}
        .hero-logo {{
            font-size:64px;
            line-height:64px;
            margin-right:12px;
        }}
        .hero-title {{
            font-size:42px;
            font-weight:700;
            color: var(--pcln-text);
            margin-bottom:6px;
        }}
        .hero-sub {{
            color: rgba(0,24,51,0.8);
            font-size:16px;
        }}
        .metric-card {{
            background: var(--pcln-primary);
            color: white;
            padding: 14px;
            border-radius: 12px;
        }}
        .metric-card .value {{
            font-size:20px;
            font-weight:700;
        }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)

_inject_design_system_tokens()

hero_html = """
<div class="hero">
    <div class="hero-left">
        <div class="hero-logo">🏈</div>
        <div>
            <div class="hero-title">CFB Prop Predictor</div>
            <div class="hero-sub">An AI-powered agent workflow to analyze and predict college football player props.</div>
        </div>
    </div>
</div>
"""

st.markdown(hero_html, unsafe_allow_html=True)



def _render_compact_table(rows=None):
    # rows: list of dicts with keys used below; fallback to demo rows
    if rows is None:
        rows = [
            {"player": "Jacoby Brissett", "pos": "QB", "team": "ARI", "opp": "GB", "when": "Today 3:25 pm", "market": "Passing Yards", "prediction_pct": 0.22, "rw": 188.22, "hit_rate": "12%"},
            {"player": "Dillon Gabriel", "pos": "QB", "team": "CLE", "opp": "MIA", "when": "Today 12:00 pm", "market": "Passing Yards", "prediction_pct": 0.55, "rw": 168.19, "hit_rate": "55%"},
        ]

    # build HTML table
    table_rows = []
    for r in rows:
        try:
            prog = int(float(r.get('prediction_pct', 0.0)) * 100)
        except Exception:
            prog = 0
        bar = f"<div class='bar-outer'><div class='bar-inner' style='width:{prog}%;'></div></div>"
        hit_badge = f"<div class='hit-badge'>{r.get('hit_rate','')}</div>"
        table_rows.append(
            f"<tr>\n<td class='p-name'>{r.get('player','')}</td>\n<td>{r.get('pos','')}</td>\n<td>{r.get('team','')}</td>\n<td>{r.get('opp','')}</td>\n<td>{r.get('when','')}</td>\n<td>{r.get('market','')}</td>\n<td class='p-bar'>{bar}</td>\n<td class='rw'>{r.get('rw','')}</td>\n<td class='hit'>{hit_badge}</td>\n</tr>"
        )

    html = f"""
    <div class='compact-table-wrapper'>
      <table class='compact-table'>
        <thead>
          <tr>
            <th>Player</th><th>Pos</th><th>Team</th><th>Opp</th><th>Date & Time</th><th>Market</th><th>Prediction</th><th>RW</th><th>Hit Rate</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </div>
    <style>
      .compact-table-wrapper {{ padding: 8px 4px; }}
      .compact-table {{ width:100%; border-collapse:collapse; font-size:13px; color:var(--pcln-text); }}
      .compact-table thead th {{ text-align:left; padding:8px 6px; font-weight:600; color:#42515a; font-size:12px; }}
      .compact-table tbody td {{ padding:8px 6px; border-top:1px solid #eef2f4; vertical-align:middle; }}
      .compact-table tbody tr:hover {{ background: #fbfdff; }}
      .p-name {{ font-weight:600; color:var(--pcln-text); }}
      .bar-outer {{ background:#f1f5f8; border-radius:8px; width:120px; height:12px; }}
      .bar-inner {{ height:12px; background:linear-gradient(90deg, var(--pcln-primary), #8bb7ff); border-radius:8px; }}
      .hit-badge {{ background:#ff6b6b; color:white; padding:4px 8px; border-radius:8px; font-size:12px; display:inline-block; }}
      .rw {{ color:#243b53; font-weight:600; text-align:right; }}
    </style>
    """

    st.markdown(html, unsafe_allow_html=True)


from .mapper import _rows_from_gathered


st.subheader("Live Market Snapshot")
st.info("Run a prediction to populate the live market snapshot.")

st.sidebar.header("Prediction Inputs")

# League filter to allow viewing CFB vs NFL results when available
if 'league_filter' not in st.session_state:
    st.session_state['league_filter'] = st.query_params.get('league', ['CFB'])[0]

league_choice = st.sidebar.selectbox("League:", ["CFB", "NFL", "All"], index=0)
def _on_league_change():
    params = dict(st.query_params)
    params['league'] = league_choice
    st.experimental_set_query_params(**params)
    st.session_state['league_filter'] = league_choice

_on_league_change()

# helper to load local SVGs from dashboard/static/icons
def _load_svg(name: str) -> str:
    try:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'icons'))
        path = os.path.join(base, name)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""

# Sidebar: show calendar icon next to game input
cal_svg = _load_svg('calendar.svg')
col_a, col_b = st.sidebar.columns([1, 18])
if cal_svg:
    col_a.markdown(cal_svg, unsafe_allow_html=True)
game = col_b.text_input("", "Alabama vs Georgia", key='game_input')

player = st.sidebar.text_input("Player Name:", "Jalen Milroe")
prop_type = st.sidebar.selectbox(
    "Prop Type:",
    ["player_passing_yards", "player_rushing_yards", "player_receiving_yards"],
    index=0,
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

            # Show recommendation with check icon if available
            check_svg = _load_svg('check.svg')
            rec_display = f"{rec.upper()} {prop_line if prop_line is not None else ''}"
            if check_svg:
                col1.markdown(f"<div class='pcln-card'><span style='vertical-align:middle'>{check_svg}</span> <strong style='margin-left:8px'>{rec_display}</strong></div>", unsafe_allow_html=True)
            else:
                col1.metric(
                    label="Recommendation",
                    value=rec_display
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

            # Render compact market table from gathered_data
            try:
                rows = _rows_from_gathered(gathered_data, request=request, result=result)
                if rows:
                    _render_compact_table(rows=rows)
                else:
                    st.info("No market rows found in gathered data.")
            except Exception as e:
                st.warning(f"Could not render market table: {e}")

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


