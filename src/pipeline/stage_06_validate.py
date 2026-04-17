from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from evaluation.diagnostics import build_basic_diagnostics, build_stability_overview
from evaluation.robustness import summarize_optimization_robustness
from evaluation.report_metrics import compact_metric_table
from reporting.export_results import save_frame, save_payload


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_stage_06_validate(df: pd.DataFrame, plans: pd.DataFrame, run_dir: Path) -> None:
    diagnostics = build_basic_diagnostics(df)
    strategy_map = _read_json(run_dir / 'optimization' / 'strategy_mapping_summary.json')
    if strategy_map:
        diagnostics['strategy_mapping'] = strategy_map
    robustness = summarize_optimization_robustness(plans)
    latent_summary = _read_json(run_dir / 'latent' / 'latent_stability_summary.json')
    risk_summary = _read_json(run_dir / 'risk' / 'risk_threshold_summary.json')
    rule_summary = _read_json(run_dir / 'rules' / 'rule_stability_summary.json')
    stability_overview = build_stability_overview(latent_summary, risk_summary, rule_summary)

    stage_dir = run_dir / 'validation'
    save_payload(diagnostics, stage_dir / 'diagnostics.json')
    save_frame(compact_metric_table(diagnostics), stage_dir / 'diagnostics_table.csv')
    save_payload(stability_overview, stage_dir / 'stability_overview.json')
    save_frame(
        compact_metric_table(
            {
                'latent_bootstrap_samples': latent_summary.get('bootstrap_samples'),
                'risk_bootstrap_samples': risk_summary.get('bootstrap_samples'),
                'rule_bootstrap_samples': rule_summary.get('bootstrap_samples'),
                'rule_selection_frequency_threshold': rule_summary.get('selection_frequency_threshold'),
            }
        ),
        stage_dir / 'stability_overview_table.csv',
    )
    if not robustness.empty:
        save_frame(robustness, stage_dir / 'optimization_robustness.csv')
