import pandas as pd
from models.risk_score import build_continuous_risk_score
from models.thresholding import assign_risk_tier, search_risk_thresholds, search_risk_thresholds_with_grid


RISK_CONFIG = {
    'risk_score': {
        'model_type': 'legacy_weighted',
        'weights': {
            'latent_state': 0.30,
            'lipid_deviation_total': 0.35,
            'metabolic_deviation_total': 0.15,
            'activity_risk': 0.10,
            'constitution_tanshi': 0.05,
            'background_risk': 0.05,
        },
        'interaction_weights': {
            'tanshi_x_low_activity': 0.08,
            'tanshi_x_bmi_deviation': 0.06,
            'metabolic_x_low_activity': 0.05,
        },
    }
}


def build_risk_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'latent_state_h': [10, 20, 30, 70, 80, 90],
            'lipid_deviation_total': [0, 0.2, 0.3, 1.0, 1.4, 1.8],
            'metabolic_deviation_total': [0.1, 0.2, 0.1, 0.8, 1.0, 1.2],
            'activity_risk': [0.1, 0.2, 0.3, 0.7, 0.8, 0.9],
            'constitution_tanshi': [20, 30, 40, 60, 70, 80],
            'background_risk': [0.1, 0.1, 0.2, 0.3, 0.4, 0.5],
            'tanshi_x_low_activity': [0, 0, 0.1, 0.4, 0.7, 0.8],
            'tanshi_x_bmi_deviation': [0, 0.1, 0.1, 0.5, 0.6, 0.7],
            'metabolic_x_low_activity': [0, 0, 0.1, 0.4, 0.6, 0.7],
        }
    )


def test_threshold_search_orders_thresholds():
    score = pd.Series([10, 20, 30, 70, 80, 90])
    low_anchor = pd.Series([1, 1, 0, 0, 0, 0])
    high_anchor = pd.Series([0, 0, 0, 1, 1, 1])
    t1, t2 = search_risk_thresholds(score, low_anchor, high_anchor, grid_points=10)
    tiers = assign_risk_tier(score, t1, t2)
    assert t1 < t2
    assert set(tiers.unique()) <= {'low', 'medium', 'high'}


def test_threshold_grid_outputs_objective_surface():
    score = pd.Series([10, 20, 30, 70, 80, 90])
    low_anchor = pd.Series([1, 1, 0, 0, 0, 0])
    high_anchor = pd.Series([0, 0, 0, 1, 1, 1])
    t1, t2, grid = search_risk_thresholds_with_grid(score, low_anchor, high_anchor, grid_points=8)
    assert t1 < t2
    assert {'t1', 't2', 'low_ok', 'high_ok', 'margin', 'objective'} <= set(grid.columns)
    assert not grid.empty


def test_risk_score_breakdown_contains_components():
    df = build_risk_df()
    out = build_continuous_risk_score(df, RISK_CONFIG)
    expected = {
        'score_latent_state', 'score_lipid_deviation_total', 'score_metabolic_deviation_total',
        'score_activity_risk', 'score_constitution_tanshi', 'score_background_risk',
        'score_tanshi_x_low_activity', 'score_tanshi_x_bmi_deviation', 'score_metabolic_x_low_activity',
        'continuous_risk_score'
    }
    assert expected <= set(out.columns)
    assert out['continuous_risk_score'].between(0, 100).all()
