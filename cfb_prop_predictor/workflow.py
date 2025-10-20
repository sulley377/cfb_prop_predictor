# cfb_prop_predictor/workflow.py
from typing import Dict, Any

# Try package-style imports; fall back to top-level module imports when running
# from the repository root where the package context may not be set.
try:
    from cfb_prop_predictor.agents.data_gatherer import gather_data
    from cfb_prop_predictor.agents.analyzer import analyze as analyze_fn
    from cfb_prop_predictor.agents.predictor import predict as predict_fn
    from cfb_prop_predictor.types import GatheredData, AnalysisOutput, PredictionOutput
except Exception:
    # Fallback to top-level imports when running from repo root
    from agents.data_gatherer import gather_data  # type: ignore
    from agents.analyzer import analyze as analyze_fn  # type: ignore
    from agents.predictor import predict as predict_fn  # type: ignore
    from cfb_prop_predictor.types import GatheredData, AnalysisOutput, PredictionOutput

def run_workflow(league: str, prop_type: str) -> Dict[str, Any]:
    """
    Runs the full data gathering, analysis, and prediction workflow
    for all available props in a league.
    """
    # 1. Gather Data
    # Pass the 'league' and 'prop_type' arguments from Streamlit
    print(f"[Workflow] Starting gather_data for {league} / {prop_type}")
    gathered_data: GatheredData = gather_data(league=league, prop_type=prop_type)

    # 2. Analyze Data
    # The analyzer agent is built for a *single player*, not a list.
    # We will bypass it for the scanner and return a placeholder AnalysisOutput.
    analysis = AnalysisOutput(
        summary=f"Data gathered for {league}. Analysis/Prediction agents are bypassed for multi-prop scan.",
        key_metrics={},
        risk_factors=[],
    )

    # 3. Get Prediction (bypassed)
    prediction = PredictionOutput(
        recommended_bet="N/A",
        projected_value=0.0,
        edge=0.0,
        confidence=0,
    )

    return {
        # Use .model_dump() if GatheredData is a Pydantic model
        "gathered_data": gathered_data.model_dump() if hasattr(gathered_data, 'model_dump') else gathered_data,
        "analysis": analysis.model_dump(),
        "prediction": prediction.model_dump(),
    }

def run_workflow_sync(league: str, prop_type: str) -> Dict[str, Any]:
    """Synchronous wrapper for the workflow."""
    return run_workflow(league, prop_type)
