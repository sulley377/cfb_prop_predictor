## Purpose
This file gives targeted, actionable guidance for AI coding agents working in the All-Props-no-bets repo (cfb_prop_predictor). It focuses on the real, discoverable patterns, run steps, and integration points so an agent can be productive immediately.

## Big picture
- UI: `dashboard/streamlit_app.py` — Streamlit front-end that builds a request dict and calls `run_workflow_sync` from `cfb_prop_predictor.workflow`.
- Agents: `agents/` contains three small agents:
  - `data_gatherer.py` (async) — scrapes live prop odds (uses `Utilis/play_scraper.py`) and returns a `GatheredData` shape.
  - `analyzer.py` (sync) — consumes `GatheredData` and produces `AnalysisOutput` (key_metrics, risk_factors, summary).
  - `predictor.py` (sync) — consumes `AnalysisOutput` and returns a `PredictionOutput` (recommended_bet, projected_value, edge, confidence).
- Utilities: `Utilis/play_scraper.py` — Playwright async scrapers for Rotowire (player props and matchup odds).

Note: Several modules import from the package name `cfb_prop_predictor` (e.g., `from cfb_prop_predictor.types import ...`). `dashboard/streamlit_app.py` temporarily modifies `sys.path` to include the repo root so these imports resolve during Streamlit runs. Keep that pattern in mind when running or importing modules.

## Data flow (concrete example)
1. Streamlit builds a request: {"game":"Alabama vs Georgia","player":"Jalen Milroe","prop_type":"player_passing_yards"}.
2. `run_workflow_sync(request)` is expected to coordinate agents and return a dict with keys: `gathered_data`, `analysis`, `prediction`.
3. `data_gatherer.gather_data` (async) calls `Utilis/play_scraper.scrape_rotowire_props(player, prop_keyword)` where `prop_keyword` is derived via `prop_type.split('_')[1]`.
4. `analyzer.analyze` reads `GatheredData.odds_data.prop_line` and `team_stats.defensive_rank` to populate `risk_factors`.
5. `predictor.predict` computes a `projected_value` currently as `prop_line * 1.05` and uses simple confidence heuristics.

## Key patterns and conventions (discoverable)
- Agents are tiny, single-purpose modules. Follow existing function names and signatures: `gather_data(game, player, prop_type) -> GatheredData` (async); `analyze(data, prop_type) -> AnalysisOutput`; `predict(analysis) -> PredictionOutput`.
- The code uses plain dict placeholders for player/team stats in `data_gatherer.py` rather than Pydantic models — expect `player_stats` to be a dict until `cfb_prop_predictor.types` is implemented.
- Playwright scrapers are async and depend on CSS selectors like `.prop-lines-table tbody` and `.line-cell .line`. Matching logic expects exact player name equality (see `play_scraper.py`).
- `prop_type` strings follow the `player_<kind>_yards` convention. Agents pull the second token via `split('_')[1]` — keep that when adding new prop types.

## Integration points & external deps
- Rotowire scraping via Playwright: `playwright` is in `requirements.txt`. Remember to run `playwright install` (browsers) when setting up locally.
- Streamlit for UI (`streamlit` in requirements).
- Other libraries in `requirements.txt`: `pydantic`, `python-dotenv`, `aiohttp`, `pandas`, `numpy`, `pytest`.

## Known repo gaps and constraints
- Missing package modules: code references `cfb_prop_predictor.types` and `cfb_prop_predictor.workflow` but there is no `cfb_prop_predictor/` package directory in the repo root. The Streamlit app works around imports by inserting the repo root onto `sys.path`.
  - Actionable: When implementing features, either add a `cfb_prop_predictor/` package (preferred) with `__init__.py`, `types.py`, `workflow.py`, or preserve the `sys.path` trick and run Streamlit from the repo root.
- Many functions include `NOTE` placeholders (historical stats not implemented, simple heuristics). Expect to replace placeholders with real data ingestion and modeling when adding features.

## Run & debug notes (how contributors run things)
- Install deps: `pip install -r requirements.txt`.
- Playwright browsers: run `playwright install` after installing the package.
- Run the UI: from the project root run Streamlit against `dashboard/streamlit_app.py` so its `sys.path` tweak works.
- Tests: `pytest` is listed, but there are no tests currently. Add tests that assert the agent function contracts and `run_workflow_sync` behavior.

## Examples for code changes (use these when editing)
- To add a new prop kind, preserve the `prop_type` format and reuse `prop_type.split('_')[1]` in `data_gatherer.py`.
- When scraping, match player names exactly or add fuzzy matching in `Utilis/play_scraper.py` (current code uses exact equality via `.strip() == player_name`).
- When changing outputs returned to Streamlit, keep the top-level dict keys `gathered_data`, `analysis`, `prediction` since `streamlit_app.py` expects them.

## When to run unit vs. integration tests
- Unit tests: logic inside `analyzer.py` and `predictor.py` (pure functions) — mock `GatheredData` and `AnalysisOutput` structures.
- Integration tests: `data_gatherer` + `play_scraper` require Playwright; mark them as integration tests and skip in CI unless Playwright and browsers are installed.

If anything above is unclear or you'd like me to expand an example (e.g., exact `types.py` shapes or a sample `workflow.py`), tell me which piece to flesh out and I'll update this file.
