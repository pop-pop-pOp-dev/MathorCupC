from pathlib import Path

import pandas as pd

from reporting.figures import (
    plot_latent_loading_heatmap,
    plot_latent_loading_stability_forest,
    plot_latent_score_stability_boxplot,
    plot_risk_anchor_overlay,
    plot_risk_component_mean_bar,
    plot_risk_distribution,
    plot_risk_score_by_tier,
    plot_risk_threshold_heatmap,
    plot_rule_coverage_waterfall,
    plot_rule_purity_vs_coverage,
    plot_rule_selection_frequency,
)


def test_figure_smoke(tmp_path: Path):
    risk_df = pd.DataFrame(
        {
            'continuous_risk_score': [10, 20, 30, 60, 70, 80],
            'risk_tier': ['low', 'low', 'medium', 'medium', 'high', 'high'],
            'low_anchor': [1, 1, 0, 0, 0, 0],
            'high_anchor': [0, 0, 0, 0, 1, 1],
            'score_latent_state': [0.1] * 6,
            'score_lipid_deviation_total': [0.2] * 6,
        }
    )
    loadings = pd.DataFrame({'constitution_factor': [0.5, 0.1], 'activity_factor': [0.2, -0.3]}, index=['f1', 'f2'])
    latent_summary = pd.DataFrame(
        {
            'factor_name': ['constitution_factor', 'constitution_factor'],
            'feature': ['f1', 'f2'],
            'mean_abs_loading': [0.5, 0.3],
            'abs_ci_lower': [0.4, 0.2],
            'abs_ci_upper': [0.6, 0.4],
        }
    )
    latent_stability = pd.DataFrame(
        {
            'bootstrap_id': [0, 0, 1, 1],
            'factor_name': ['latent_state_h', 'constitution_factor', 'latent_state_h', 'constitution_factor'],
            'pearson_corr': [0.9, 0.8, 0.88, 0.79],
            'spearman_corr': [0.87, 0.77, 0.85, 0.75],
        }
    )
    grid = pd.DataFrame({'t1': [10, 20], 't2': [40, 50], 'objective': [0.6, 0.7]})
    rules = pd.DataFrame(
        {
            'rule': ['r1', 'r2'],
            'selection_frequency': [0.8, 0.6],
            'incremental_coverage': [0.3, 0.2],
            'selected_order': [1, 2],
            'coverage': [0.5, 0.4],
            'purity': [0.8, 0.7],
            'lift': [2.0, 1.5],
            'size': [1, 2],
        }
    )

    plot_risk_distribution(risk_df, tmp_path / 'risk_dist.png')
    plot_latent_loading_heatmap(loadings, tmp_path / 'latent_heat.png')
    plot_latent_loading_stability_forest(latent_summary, tmp_path / 'latent_forest.png')
    plot_latent_score_stability_boxplot(latent_stability, tmp_path / 'latent_box.png')
    plot_risk_score_by_tier(risk_df, tmp_path / 'risk_box.png')
    plot_risk_threshold_heatmap(grid, tmp_path / 'risk_heat.png')
    plot_risk_anchor_overlay(risk_df, {'low_to_medium_threshold': 25, 'medium_to_high_threshold': 65}, tmp_path / 'risk_anchor.png')
    plot_risk_component_mean_bar(risk_df, tmp_path / 'risk_comp.png')
    plot_rule_selection_frequency(rules, tmp_path / 'rule_freq.png')
    plot_rule_coverage_waterfall(rules, tmp_path / 'rule_cov.png')
    plot_rule_purity_vs_coverage(rules, tmp_path / 'rule_scatter.png')

    assert (tmp_path / 'risk_dist.png').exists()
    assert (tmp_path / 'latent_heat.png').exists()
    assert (tmp_path / 'rule_scatter.png').exists()
