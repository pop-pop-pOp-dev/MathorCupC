from __future__ import annotations

from pathlib import Path

import pandas as pd

from evaluation.calibration import summarize_risk_tiers
from evaluation.stability import (
    bootstrap_threshold_stability,
    bootstrap_tier_distribution,
    search_threshold_grid,
    summarize_threshold_stability,
    summarize_tier_distribution,
)
from models.risk_score import build_anchor_flags, build_reference_severity, fit_risk_model
from models.thresholding import assign_risk_tier, search_risk_thresholds
from reporting.export_results import save_frame, save_payload
from utils.perf import fast_threshold_grid, resolve_n_jobs
from reporting.figures import (
    plot_risk_anchor_overlay,
    plot_risk_component_mean_bar,
    plot_risk_distribution,
    plot_risk_score_by_tier,
    plot_risk_threshold_heatmap,
)


def run_stage_03_risk(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    risk_model = config['risk_model']
    runtime = config['runtime']
    ci_level = float(risk_model['latent_state'].get('report_ci_level', 0.95))
    threshold_cfg = risk_model.get('thresholds', {})
    threshold_boot_n = min(threshold_cfg.get('bootstrap_samples', runtime['bootstrap_samples']), runtime['bootstrap_samples'])
    min_group_share = float(threshold_cfg.get('min_group_share', 0.10))
    n_jobs = resolve_n_jobs(config)
    grid_points = int(threshold_cfg.get('search_grid_points', 60))
    if fast_threshold_grid(config):
        grid_points = max(12, grid_points // 2)

    artifacts = fit_risk_model(df, risk_model, seed=int(config.get('seed', 20260417)))
    risk_df = artifacts.score_frame
    merged = pd.concat([df, risk_df], axis=1)
    merged['reference_severity'] = build_reference_severity(merged, risk_model)
    anchors = build_anchor_flags(merged, risk_model)
    score = risk_df['continuous_risk_score']
    severity = merged['reference_severity']
    t1, t2 = search_risk_thresholds(
        score,
        anchors['low_anchor'],
        anchors['high_anchor'],
        grid_points=grid_points,
        severity=severity,
        min_group_share=min_group_share,
    )
    tiers = assign_risk_tier(score, t1, t2)
    out = pd.concat([merged, anchors], axis=1)
    out['risk_tier'] = tiers

    summary = summarize_risk_tiers(out)
    threshold_grid = search_threshold_grid(
        score,
        anchors['low_anchor'],
        anchors['high_anchor'],
        grid_points=grid_points,
        severity=severity,
        min_group_share=min_group_share,
    )
    threshold_boot = bootstrap_threshold_stability(
        score,
        anchors['low_anchor'],
        anchors['high_anchor'],
        n_boot=threshold_boot_n,
        seed=int(config.get('seed', 20260417)),
        severity=severity,
        min_group_share=min_group_share,
        n_jobs=n_jobs,
    )
    threshold_summary = summarize_threshold_stability(threshold_boot, ci_level=ci_level)
    tier_bootstrap = bootstrap_tier_distribution(score, threshold_boot)
    tier_bootstrap_summary = summarize_tier_distribution(tier_bootstrap, ci_level=ci_level)

    anchor_monotonicity = pd.DataFrame(
        [
            {'group': 'low_anchor', 'mean_score': float(score[anchors['low_anchor'] == 1].mean()) if int(anchors['low_anchor'].sum()) else 0.0},
            {'group': 'high_anchor', 'mean_score': float(score[anchors['high_anchor'] == 1].mean()) if int(anchors['high_anchor'].sum()) else 0.0},
        ]
    )
    tier_severity_summary = out.groupby('risk_tier', as_index=False).agg(
        mean_reference_severity=('reference_severity', 'mean'),
        mean_continuous_risk_score=('continuous_risk_score', 'mean'),
        mean_lipid_deviation_total=('lipid_deviation_total', 'mean'),
        mean_metabolic_deviation_total=('metabolic_deviation_total', 'mean'),
        mean_latent_state_h=('latent_state_h', 'mean'),
        sample_count=('sample_id', 'count'),
    )

    thresholds_payload = {'low_to_medium_threshold': float(t1), 'medium_to_high_threshold': float(t2)}
    anchor_payload = {
        'low_anchor_count': int(anchors['low_anchor'].sum()),
        'high_anchor_count': int(anchors['high_anchor'].sum()),
        'low_anchor_share': float(anchors['low_anchor'].mean()),
        'high_anchor_share': float(anchors['high_anchor'].mean()),
    }

    stage_dir = run_dir / 'risk'
    save_frame(out[['sample_id', 'continuous_risk_score', 'risk_prob', 'risk_logit', 'reference_severity', 'risk_tier', 'low_anchor', 'high_anchor']], stage_dir / 'risk_scores.csv')
    save_frame(summary, stage_dir / 'risk_tier_summary.csv')
    save_frame(threshold_boot, stage_dir / 'risk_threshold_bootstrap.csv')
    save_frame(threshold_grid, stage_dir / 'risk_threshold_grid.csv')
    save_frame(threshold_summary, stage_dir / 'risk_threshold_stability_summary.csv')
    save_frame(tier_bootstrap_summary, stage_dir / 'risk_tier_bootstrap_summary.csv')
    save_frame(out[['sample_id', 'risk_tier'] + [c for c in risk_df.columns if c.startswith('score_')] + ['risk_logit', 'risk_prob', 'continuous_risk_score']], stage_dir / 'risk_score_component_breakdown.csv')
    save_frame(artifacts.coefficients, stage_dir / 'risk_model_coefficients.csv')
    save_frame(artifacts.cv_metrics, stage_dir / 'risk_model_cv_metrics.csv')
    save_frame(artifacts.calibration, stage_dir / 'risk_model_calibration.csv')
    save_frame(anchor_monotonicity, stage_dir / 'risk_anchor_monotonicity.csv')
    save_frame(tier_severity_summary, stage_dir / 'risk_tier_severity_summary.csv')
    save_payload(thresholds_payload, stage_dir / 'risk_thresholds.json')
    save_payload(
        {
            **thresholds_payload,
            'bootstrap_samples': int(threshold_boot_n),
            'ci_level': ci_level,
            'model_metadata': artifacts.metadata,
            'threshold_summary': {
                row['metric']: {
                    'mean': float(row['mean']),
                    'std': float(row['std']),
                    'ci_lower': float(row['ci_lower']),
                    'ci_upper': float(row['ci_upper']),
                }
                for _, row in threshold_summary.iterrows()
            },
        },
        stage_dir / 'risk_threshold_summary.json',
    )
    save_payload(anchor_payload, stage_dir / 'risk_anchor_diagnostics.json')

    if runtime.get('plots', False):
        plot_risk_distribution(out, stage_dir / 'continuous_risk_score.png')
        plot_risk_score_by_tier(out, stage_dir / 'risk_score_by_tier_boxplot.png')
        plot_risk_threshold_heatmap(threshold_grid, stage_dir / 'risk_threshold_heatmap.png')
        plot_risk_anchor_overlay(out, thresholds_payload, stage_dir / 'risk_anchor_overlay.png')
        plot_risk_component_mean_bar(out[['risk_tier'] + [c for c in out.columns if c.startswith('score_')]], stage_dir / 'risk_component_mean_bar.png')
    return out
