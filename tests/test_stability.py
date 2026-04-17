from pathlib import Path

import numpy as np
import pandas as pd

from evaluation.stability import (
    bootstrap_latent_loadings,
    bootstrap_latent_score_stability,
    bootstrap_rule_stability,
    bootstrap_threshold_stability,
    summarize_latent_bootstrap,
    summarize_latent_score_stability,
    summarize_rule_stability,
    summarize_threshold_stability,
)


RISK_CONFIG = {
    'latent_state': {
        'view_weights': {'constitution': 0.35, 'activity': 0.25, 'metabolic': 0.40},
        'report_ci_level': 0.95,
    }
}


def build_latent_df(n: int = 18) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(rng.normal(size=(n, 18)), columns=[
        'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
        'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing',
        'adl_total', 'iadl_total', 'activity_total', 'activity_risk',
        'lipid_deviation_total', 'metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid'
    ])


def build_rule_df() -> pd.DataFrame:
    return pd.DataFrame({
        'sample_id': [1, 2, 3, 4, 5, 6],
        'phlegm_dampness_label_flag': [1, 1, 1, 0, 0, 1],
        'constitution_tanshi': [70, 65, 30, 20, 10, 72],
        'activity_total': [30, 35, 70, 60, 50, 38],
        'dev_bmi': [1, 1, 0, 0, 0, 1],
        'dev_tg': [1, 1, 0, 0, 0, 1],
        'dev_ldl_c': [1, 0, 0, 0, 0, 1],
        'latent_state_h': [90, 80, 20, 10, 5, 92],
        'lipid_deviation_total': [4, 3, 0, 0, 0, 4],
        'metabolic_deviation_total': [2, 2, 0, 0, 0, 2],
        'risk_tier': ['high', 'high', 'low', 'low', 'medium', 'high'],
    })


def test_latent_bootstrap_outputs_expected_columns():
    df = build_latent_df()
    boot = bootstrap_latent_loadings(df, RISK_CONFIG, n_boot=4, seed=0)
    assert {'bootstrap_id', 'feature', 'factor_name', 'loading', 'abs_loading'} <= set(boot.columns)
    summary = summarize_latent_bootstrap(boot)
    assert {'factor_name', 'feature', 'mean_loading', 'mean_abs_loading', 'sign_consistency'} <= set(summary.columns)


def test_latent_score_stability_runs():
    df = build_latent_df()
    detail = bootstrap_latent_score_stability(df, RISK_CONFIG, n_boot=4, seed=0)
    assert {'bootstrap_id', 'factor_name', 'pearson_corr', 'spearman_corr'} <= set(detail.columns)
    summary = summarize_latent_score_stability(detail)
    assert {'factor_name', 'pearson_mean', 'spearman_mean'} <= set(summary.columns)


def test_threshold_stability_summary_runs():
    score = pd.Series([10, 20, 30, 70, 80, 90])
    low_anchor = pd.Series([1, 1, 0, 0, 0, 0])
    high_anchor = pd.Series([0, 0, 0, 1, 1, 1])
    boot = bootstrap_threshold_stability(score, low_anchor, high_anchor, n_boot=4, seed=0)
    summary = summarize_threshold_stability(boot)
    assert {'metric', 'mean', 'std', 'ci_lower', 'ci_upper'} <= set(summary.columns)


def test_rule_bootstrap_stability_runs():
    df = build_rule_df()
    boot = bootstrap_rule_stability(df, n_boot=4, seed=0)
    assert 'rule' in boot.columns
    summary = summarize_rule_stability(boot, n_boot=4)
    assert {'rule', 'selection_frequency', 'coverage_mean', 'purity_mean', 'lift_mean'} <= set(summary.columns)
