from __future__ import annotations

from pathlib import Path

import pandas as pd

from evaluation.stability import (
    bootstrap_latent_loadings,
    bootstrap_latent_score_stability,
    bootstrap_latent_state_stability,
    summarize_latent_bootstrap,
    summarize_latent_score_stability,
)
from models.latent_state import fit_latent_state, loadings_to_long
from reporting.export_results import save_frame, save_payload
from reporting.figures import (
    plot_latent_loading_heatmap,
    plot_latent_loading_stability_forest,
    plot_latent_score_stability_boxplot,
)


def run_stage_02_latent(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    risk_model = config['risk_model']
    runtime = config['runtime']
    n_boot = min(risk_model['latent_state'].get('bootstrap_samples', runtime['bootstrap_samples']), runtime['bootstrap_samples'])
    ci_level = float(risk_model['latent_state'].get('report_ci_level', 0.95))
    top_quantile = float(risk_model['latent_state'].get('stability_top_quantile', 0.20))

    result = fit_latent_state(df, risk_model)
    out = pd.concat([df, result.frame], axis=1)

    loadings_detailed = loadings_to_long(result.loadings)
    latent_boot = bootstrap_latent_loadings(out, risk_model, n_boot=n_boot)
    latent_boot_summary = summarize_latent_bootstrap(latent_boot, ci_level=ci_level)
    score_stability_detail = bootstrap_latent_score_stability(
        out,
        risk_model,
        n_boot=n_boot,
        top_quantile=top_quantile,
    )
    score_stability_summary = summarize_latent_score_stability(score_stability_detail, ci_level=ci_level)
    stability_legacy = bootstrap_latent_state_stability(out, risk_model, n_boot=n_boot)

    stage_dir = run_dir / 'latent'
    save_frame(result.loadings.reset_index().rename(columns={'index': 'feature'}), stage_dir / 'latent_loadings.csv')
    save_frame(loadings_detailed, stage_dir / 'latent_loadings_detailed.csv')
    save_frame(result.view_diagnostics, stage_dir / 'latent_view_diagnostics.csv')
    save_frame(result.frame.reset_index(drop=True), stage_dir / 'latent_state_scores.csv')
    save_frame(stability_legacy, stage_dir / 'latent_stability.csv')
    save_frame(latent_boot, stage_dir / 'latent_bootstrap_loadings.csv')
    save_frame(latent_boot_summary, stage_dir / 'latent_bootstrap_summary.csv')
    save_frame(score_stability_detail, stage_dir / 'latent_score_stability.csv')
    save_frame(score_stability_summary, stage_dir / 'latent_score_stability_summary.csv')
    save_payload(
        {
            'bootstrap_samples': int(n_boot),
            'ci_level': ci_level,
            'top_quantile': top_quantile,
            'explained_variance_ratio': {
                row['factor_name']: float(row['explained_variance_ratio'])
                for _, row in result.view_diagnostics.iterrows()
            },
            'score_stability': {
                row['factor_name']: {
                    'pearson_mean': float(row['pearson_mean']),
                    'spearman_mean': float(row['spearman_mean']),
                }
                for _, row in score_stability_summary.iterrows()
            },
        },
        stage_dir / 'latent_stability_summary.json',
    )

    if runtime.get('plots', False):
        plot_latent_loading_heatmap(result.loadings, stage_dir / 'latent_loading_heatmap.png')
        plot_latent_loading_stability_forest(latent_boot_summary, stage_dir / 'latent_loading_stability_forest.png')
        plot_latent_score_stability_boxplot(score_stability_detail, stage_dir / 'latent_score_stability_boxplot.png')
    return out
