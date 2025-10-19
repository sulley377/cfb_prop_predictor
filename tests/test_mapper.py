from dashboard.mapper import _rows_from_gathered


def test_rows_from_sample_result():
    sample_result = {
        "gathered_data": {
            "odds_data": None,
            "player_stats": "namespace(name='Jalen Milroe', position='QB', season_stats={'passing_yards': 2800}, last_five_games=[])",
            "team_stats": "namespace(name='Alabama', offensive_rank=10, defensive_rank=25)"
        },
        "analysis": {
            "key_metrics": {
                "player_name": "Jalen Milroe",
                "season_average_placeholder": "Historical player data not yet implemented.",
                "opponent_defensive_rank_placeholder": 25
            },
            "risk_factors": [
                "Could not retrieve live betting odds for this prop.",
                "Facing a strong defense (ranked #25)."
            ],
            "summary": "Analysis for player_passing_yards. Betting line is N/A."
        },
        "prediction": {
            "recommended_bet": "under",
            "projected_value": 0.0,
            "edge": 0.0,
            "confidence": 50
        }
    }

    rows = _rows_from_gathered(sample_result.get('gathered_data'), request={'player': 'Jalen Milroe'}, result=sample_result)
    assert isinstance(rows, list)
    assert len(rows) == 1
    row = rows[0]
    assert row['player'] == 'Jalen Milroe'
    assert row['position'] == 'QB'
    assert row['team'] == 'Alabama'
    assert row['market'] == 'Player Passing Yards'
    assert row['prediction_score'] == 50
