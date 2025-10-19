import pytest

from cfb_prop_predictor.types import GatheredData, OddsData, AnalysisOutput
class AttrDict(dict):
    """Dict subclass that allows attribute-style access (e.g., obj.key).

    This keeps the repo's analyzer code working (which expects `.name`) while
    still satisfying Pydantic's `dict` type for `player_stats`.
    """
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as e:
            raise AttributeError(item) from e
from cfb_prop_predictor.agents import analyzer, predictor


def make_gathered(prop_line=100.0):
    odds = OddsData(prop_line=prop_line)
    player_stats = AttrDict({"name": "Test Player", "position": "QB"})
    team_stats = AttrDict({"name": "Opponent", "defensive_rank": 30})
    return GatheredData(odds_data=odds, player_stats=player_stats, team_stats=team_stats)


def test_analyzer_basic():
    gd = make_gathered(120.0)
    analysis = analyzer.analyze(gd, "player_passing_yards")
    assert isinstance(analysis, AnalysisOutput)
    assert "prop_line" in analysis.key_metrics


def test_predictor_confidence_and_projection():
    gd = make_gathered(200.0)
    analysis = analyzer.analyze(gd, "player_passing_yards")
    pred = predictor.predict(analysis)
    assert pred.projected_value == round(200.0 * 1.05, 2)
    assert 0 <= pred.confidence <= 100
