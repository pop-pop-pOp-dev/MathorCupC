import pandas as pd

from models.risk_score import build_diagnosis_anchor_flags, build_risk_feature_matrix, fit_risk_model


RISK_CONFIG = {
    'risk_score': {
        'model_type': 'anchor_front_logistic',
        'features': {
            'base': [
                'constitution_factor',
                'activity_factor',
                'metabolic_deviation_total',
                'activity_total',
                'activity_risk',
                'constitution_tanshi',
                'dev_bmi',
                'dev_fasting_glucose',
                'dev_uric_acid',
                'age_group',
                'background_risk',
                'lipid_deviation_total',
                'latent_state_h',
            ],
            'interactions': {
                'tanshi_x_low_activity': ['constitution_tanshi', 'low_activity_flag'],
                'age_x_activity_risk': ['age_group', 'activity_risk'],
                'latent_x_activity_risk': ['latent_state_h', 'activity_risk'],
            },
        },
        'cv_folds': 3,
        'candidate_cs': [0.1, 1.0],
        'penalty': 'l2',
        'scoring': 'roc_auc',
    }
}


def build_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            'constitution_factor': [0.2, 0.4, 0.6, 0.8, 0.1, 0.9],
            'activity_factor': [0.8, 0.7, 0.5, 0.3, 0.9, 0.2],
            'metabolic_deviation_total': [0.2, 0.4, 0.5, 0.6, 0.1, 0.7],
            'activity_total': [65, 60, 55, 35, 70, 30],
            'activity_risk': [0.2, 0.3, 0.4, 0.7, 0.1, 0.8],
            'constitution_tanshi': [40, 45, 55, 70, 35, 80],
            'dev_bmi': [0.2, 0.3, 0.4, 0.8, 0.1, 0.9],
            'dev_fasting_glucose': [0.1, 0.2, 0.2, 0.5, 0.0, 0.6],
            'dev_uric_acid': [0.0, 0.1, 0.2, 0.4, 0.0, 0.5],
            'age_group': [1, 2, 3, 4, 1, 5],
            'background_risk': [0.1, 0.2, 0.3, 0.4, 0.05, 0.45],
            'low_activity_flag': [0, 0, 0, 1, 0, 1],
            'lipid_deviation_total': [0.0, 0.0, 0.3, 0.6, 0.0, 0.8],
            'latent_state_h': [15, 20, 35, 70, 10, 85],
            'hyperlipidemia_label': [0, 0, 1, 1, 0, 1],
        }
    )


def test_front_feature_matrix_excludes_diagnostic_vars():
    x = build_risk_feature_matrix(build_df(), RISK_CONFIG)
    assert 'lipid_deviation_total' not in x.columns
    assert 'latent_state_h' not in x.columns
    assert 'latent_x_activity_risk' not in x.columns


def test_anchor_flags_follow_diagnosis_logic():
    anchors = build_diagnosis_anchor_flags(build_df())
    assert anchors['high_anchor'].sum() == 3
    assert anchors['low_anchor'].sum() == 3


def test_anchor_front_model_runs_without_leakage_features():
    artifacts = fit_risk_model(build_df(), RISK_CONFIG, seed=7)
    assert artifacts.metadata['model_type'] == 'anchor_front_logistic'
    assert artifacts.metadata['probability_calibration'] in {'none', 'sigmoid', 'isotonic'}
    assert 'lipid_deviation_total' not in artifacts.coefficients['feature'].tolist()
    assert 'latent_state_h' not in artifacts.coefficients['feature'].tolist()
    assert artifacts.score_frame['risk_prob'].between(0, 1).all()
    assert artifacts.score_frame['continuous_risk_score'].between(0, 100).all()
