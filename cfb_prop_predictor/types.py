from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class OddsData(BaseModel):
    prop_line: float
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None


class MatchupOdds(BaseModel):
    awayTeam: str
    homeTeam: str
    spread: Dict[str, Any]
    moneyline: Dict[str, Any]
    total: Dict[str, Any]


class GatheredData(BaseModel):
    odds_data: Optional[OddsData]
    # Historically this repo used plain dicts for player/team stats, but
    # agent code expects attribute access (e.g., `.name` or `.defensive_rank`).
    # Allow Any here so callers can pass SimpleNamespace-like objects or dicts
    # without Pydantic coercion removing attribute access.
    player_stats: Optional[Any]
    team_stats: Optional[Any]
    # When running the scanner workflow, gather_data will populate `all_props`.
    all_props: Optional[List[Dict[str, Any]]] = None


class AnalysisOutput(BaseModel):
    key_metrics: Dict[str, Any]
    risk_factors: list
    summary: str


class PredictionOutput(BaseModel):
    recommended_bet: str
    projected_value: float
    edge: float
    confidence: int
