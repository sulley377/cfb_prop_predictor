import asyncio
from typing import Dict

try:
    # Agents import via package
    from cfb_prop_predictor.agents import data_gatherer, analyzer, predictor
except Exception:
    # Fallback to top-level agents/ path when running from repo root
    from ..agents import data_gatherer, analyzer, predictor  # type: ignore


def run_workflow_sync(request: Dict) -> Dict:
    """Synchronous wrapper to run the async data gatherer and the sync agents.

    Expected request: {"game":..., "player":..., "prop_type":...}
    Returns dict with keys: gathered_data, analysis, prediction (serialized as dicts)
    """
    game = request.get("game")
    player = request.get("player")
    prop_type = request.get("prop_type")

    gathered = asyncio.run(data_gatherer.gather_data(game, player, prop_type))

    # Convert plain dict placeholders to attribute-accessible objects so
    # existing agents (analyzer) can access `.name` and `.defensive_rank`.
    from types import SimpleNamespace

    if getattr(gathered, 'player_stats', None) and isinstance(gathered.player_stats, dict):
        gathered.player_stats = SimpleNamespace(**gathered.player_stats)
    if getattr(gathered, 'team_stats', None) and isinstance(gathered.team_stats, dict):
        gathered.team_stats = SimpleNamespace(**gathered.team_stats)

    analysis = analyzer.analyze(gathered, prop_type)
    prediction = predictor.predict(analysis)

    # Convert Pydantic models to dicts when necessary
    def to_serializable(obj):
        try:
            return obj.dict()
        except Exception:
            return obj

    return {
        "gathered_data": to_serializable(gathered),
        "analysis": to_serializable(analysis),
        "prediction": to_serializable(prediction),
    }
