from __future__ import annotations

from pathlib import Path

import pandas as pd

from evaluation.stability import bootstrap_rule_stability, summarize_rule_stability
from models.rule_mining import build_rule_coverage_matrix, enumerate_candidate_rules, extract_minimal_rules
from reporting.export_results import save_frame, save_payload
from reporting.figures import (
    plot_rule_coverage_waterfall,
    plot_rule_purity_vs_coverage,
    plot_rule_selection_frequency,
)


def run_stage_04_rules(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    rule_config = config['risk_model']['rules']
    runtime = config['runtime']
    max_rule_size = int(rule_config['max_rule_size'])
    min_coverage = float(rule_config['min_coverage'])
    min_purity = float(rule_config['min_purity'])
    n_boot = min(int(rule_config.get('bootstrap_samples', runtime['bootstrap_samples'])), int(runtime['bootstrap_samples']))
    stability_threshold = float(rule_config.get('selection_frequency_threshold', 0.60))

    candidates = enumerate_candidate_rules(
        df,
        max_rule_size=max_rule_size,
        min_coverage=min_coverage,
        min_purity=min_purity,
    )
    rules = extract_minimal_rules(
        df,
        max_rule_size=max_rule_size,
        min_coverage=min_coverage,
        min_purity=min_purity,
    )
    coverage_matrix = build_rule_coverage_matrix(df, rules, candidates)
    rule_bootstrap = bootstrap_rule_stability(
        df,
        max_rule_size=max_rule_size,
        min_coverage=min_coverage,
        min_purity=min_purity,
        n_boot=n_boot,
    )
    rule_stability = summarize_rule_stability(rule_bootstrap, n_boot=n_boot)
    core_rules = rule_stability[rule_stability['selection_frequency'] >= stability_threshold].reset_index(drop=True)

    target = (df['phlegm_dampness_label_flag'] == 1) & (df['risk_tier'] == 'high')
    total_incremental = float(rules['incremental_coverage'].sum()) if not rules.empty and 'incremental_coverage' in rules.columns else 0.0

    stage_dir = run_dir / 'rules'
    save_frame(candidates.drop(columns=['__target__', '__mask__'], errors='ignore'), stage_dir / 'rule_candidates.csv')
    save_frame(rules, stage_dir / 'minimal_rules.csv')
    save_frame(coverage_matrix, stage_dir / 'rule_coverage_matrix.csv')
    save_frame(rule_stability, stage_dir / 'rule_stability.csv')
    save_frame(core_rules, stage_dir / 'core_rules.csv')
    save_payload(
        {
            'target_size': int(target.sum()),
            'candidate_rule_count': int(len(candidates)),
            'selected_rule_count': int(len(rules)),
            'core_rule_count': int(len(core_rules)),
            'total_incremental_coverage': total_incremental,
        },
        stage_dir / 'rule_summary.json',
    )
    save_payload(
        {
            'bootstrap_samples': int(n_boot),
            'selection_frequency_threshold': stability_threshold,
            'top_rules': rule_stability.head(10).to_dict(orient='records'),
        },
        stage_dir / 'rule_stability_summary.json',
    )

    if runtime.get('plots', False):
        plot_rule_selection_frequency(rule_stability, stage_dir / 'rule_selection_frequency.png')
        plot_rule_coverage_waterfall(rules, stage_dir / 'rule_coverage_waterfall.png')
        plot_rule_purity_vs_coverage(candidates.drop(columns=['__target__', '__mask__'], errors='ignore'), stage_dir / 'rule_purity_vs_coverage.png')
    return rules
