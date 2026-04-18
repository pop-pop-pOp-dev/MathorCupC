import pandas as pd

from evaluation.evidence import (
    ablate_risk_models,
    benchmark_leakage_designs,
    build_problem_bridge_evidence,
    risk_model_significance,
)


RISK_CONFIG = {
    'risk_score': {
        'model_type': 'anchor_front_logistic',
        'calibration_bins': 5,
        'probability_calibration': 'auto',
        'calibration_selection_metric': 'brier_score',
        'weights': {
            'latent_state': 0.22,
            'lipid_deviation_total': 0.18,
            'metabolic_deviation_total': 0.16,
            'activity_risk': 0.14,
            'constitution_tanshi': 0.18,
            'background_risk': 0.12,
        },
        'interaction_weights': {
            'tanshi_x_low_activity': 0.06,
            'tanshi_x_bmi_deviation': 0.07,
            'metabolic_x_low_activity': 0.07,
        },
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
            ],
            'interactions': {
                'tanshi_x_low_activity': ['constitution_tanshi', 'low_activity_flag'],
                'tanshi_x_bmi_deviation': ['constitution_tanshi', 'dev_bmi'],
                'metabolic_x_low_activity': ['metabolic_deviation_total', 'low_activity_flag'],
                'age_x_activity_risk': ['age_group', 'activity_risk'],
            },
        },
        'cv_folds': 3,
        'candidate_cs': [0.1, 1.0],
        'penalty': 'l2',
        'scoring': 'roc_auc',
    }
}


def build_df(n: int = 24) -> pd.DataFrame:
    rows = []
    for i in range(n):
        high = int(i % 3 != 0)
        rows.append(
            {
                'constitution_factor': 0.2 + 0.03 * i + 0.3 * high,
                'activity_factor': 0.9 - 0.02 * i - 0.2 * high,
                'metabolic_deviation_total': 0.1 + 0.02 * i + 0.2 * high,
                'activity_total': 70 - i + (0 if high else 5),
                'activity_risk': 0.2 + 0.02 * i + 0.1 * high,
                'constitution_tanshi': 35 + i + 8 * high,
                'latent_state_h': 0.4 + 0.05 * i + 0.4 * high,
                'dev_bmi': 0.1 + 0.02 * i + 0.1 * high,
                'dev_fasting_glucose': 0.05 + 0.01 * i + 0.08 * high,
                'dev_uric_acid': 0.0 + 0.015 * i + 0.1 * high,
                'age_group': 1 + (i % 5),
                'background_risk': 0.1 + 0.02 * (i % 5) + 0.05 * high,
                'low_activity_flag': int(70 - i < 40),
                'tanshi_x_low_activity': (35 + i + 8 * high) * int(70 - i < 40),
                'tanshi_x_bmi_deviation': (35 + i + 8 * high) * (0.1 + 0.02 * i + 0.1 * high),
                'metabolic_x_low_activity': (0.1 + 0.02 * i + 0.2 * high) * int(70 - i < 40),
                'lipid_deviation_total': 0.0 if not high else 0.5 + 0.05 * i,
                'hyperlipidemia_label': high,
            }
        )
    return pd.DataFrame(rows)


def test_risk_ablation_outputs_multiple_variants():
    out = ablate_risk_models(build_df(), RISK_CONFIG, seed=7)
    assert not out.empty
    assert {'完整主模型', '去体质信息', '去活动信息', '去代谢信息', '去背景信息', '去交互项'} <= set(out['label'])
    assert 'delta_vs_full_full_sample_diagnosis_auc' in out.columns


def test_risk_significance_outputs_comparison_rows():
    out = risk_model_significance(build_df(), RISK_CONFIG, seed=7, n_boot=60)
    assert not out.empty
    assert {'baseline_or_ablation', 'metric', 'observed_improvement', 'ci_lower', 'ci_upper', 'p_value_two_sided'} <= set(out.columns)
    assert {'旧版手工加权', '连续严重度 Ridge'} <= set(out['baseline_or_ablation'])


def test_problem_bridge_outputs_have_expected_frames():
    df = build_df()
    df['risk_prob'] = (df['hyperlipidemia_label'] * 0.6 + 0.2).clip(0, 1)
    df['continuous_risk_score'] = df['risk_prob'] * 100
    df['reference_severity'] = df['metabolic_deviation_total']
    out = build_problem_bridge_evidence(df, RISK_CONFIG)
    assert not out['view_semantics'].empty
    assert not out['latent_risk_bridge'].empty
    assert 'scalar_ranking_utility' in out


def test_leakage_benchmark_returns_strict_and_wide_rows():
    benchmark, significance = benchmark_leakage_designs(build_df(), RISK_CONFIG, seed=7)
    assert {'严格前置预警模型', '宽松含血脂模型'} <= set(benchmark['label'])
    assert not significance.empty
