from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from evaluation.diagnostics import build_basic_diagnostics, build_stability_overview
from evaluation.evidence import (
    ablate_risk_models,
    benchmark_risk_models,
    benchmark_leakage_designs,
    build_optimization_mechanism_outputs,
    build_problem_bridge_evidence,
    build_threshold_explanation_outputs,
    build_optimization_baseline_comparison,
    risk_model_significance,
    summarize_risk_evidence,
)
from evaluation.robustness import summarize_optimization_robustness
from evaluation.report_metrics import compact_metric_table
from reporting.export_results import save_frame, save_payload
from reporting.figures import (
    plot_constitution_contribution_bar,
    plot_optimization_budget_shift,
    plot_problem_bridge_heatmap,
    plot_sample_plan_paths,
    plot_strategy_mapping_heatmap,
    plot_threshold_bootstrap_distributions,
    plot_tier_feature_gradient,
    plot_workflow_overview,
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_stage_06_validate(df: pd.DataFrame, plans: pd.DataFrame, config: dict, run_dir: Path) -> None:
    diagnostics = build_basic_diagnostics(df)
    strategy_map = _read_json(run_dir / 'optimization' / 'strategy_mapping_summary.json')
    if strategy_map:
        diagnostics['strategy_mapping'] = strategy_map
    pareto_frontier_path = run_dir / 'optimization' / 'pareto_frontier_summary.csv'
    if pareto_frontier_path.exists():
        pareto_frontier = pd.read_csv(pareto_frontier_path)
        diagnostics['pareto_frontier'] = pareto_frontier.to_dict(orient='records')
    robustness = summarize_optimization_robustness(plans)
    latent_summary = _read_json(run_dir / 'latent' / 'latent_stability_summary.json')
    risk_summary = _read_json(run_dir / 'risk' / 'risk_threshold_summary.json')
    rule_summary = _read_json(run_dir / 'rules' / 'rule_stability_summary.json')
    budget_evidence = _read_json(run_dir / 'optimization' / 'pareto_budget_evidence.json')
    threshold_grid = pd.read_csv(run_dir / 'risk' / 'risk_threshold_grid.csv') if (run_dir / 'risk' / 'risk_threshold_grid.csv').exists() else pd.DataFrame()
    threshold_boot = pd.read_csv(run_dir / 'risk' / 'risk_threshold_bootstrap.csv') if (run_dir / 'risk' / 'risk_threshold_bootstrap.csv').exists() else pd.DataFrame()
    plans_budget_grid = pd.read_csv(run_dir / 'optimization' / 'phlegm_patient_plans_budget_grid.csv') if (run_dir / 'optimization' / 'phlegm_patient_plans_budget_grid.csv').exists() else pd.DataFrame()
    if budget_evidence:
        diagnostics['budget_evidence'] = budget_evidence
    stability_overview = build_stability_overview(latent_summary, risk_summary, rule_summary)
    risk_tier_summary_path = run_dir / 'risk' / 'risk_tier_summary.csv'
    risk_cv_metrics_path = run_dir / 'risk' / 'risk_model_cv_metrics.csv'
    risk_calibration_path = run_dir / 'risk' / 'risk_model_calibration.csv'
    anchor_monotonicity_path = run_dir / 'risk' / 'risk_anchor_monotonicity.csv'
    risk_evidence = summarize_risk_evidence(
        pd.read_csv(risk_tier_summary_path) if risk_tier_summary_path.exists() else pd.DataFrame(),
        pd.read_csv(risk_cv_metrics_path) if risk_cv_metrics_path.exists() else pd.DataFrame(),
        pd.read_csv(risk_calibration_path) if risk_calibration_path.exists() else pd.DataFrame(),
        pd.read_csv(anchor_monotonicity_path) if anchor_monotonicity_path.exists() else pd.DataFrame(),
        risk_summary,
    )
    if risk_evidence:
        diagnostics['risk_evidence'] = risk_evidence
    model_benchmark = benchmark_risk_models(df, config['risk_model'], seed=int(config.get('seed', 20260417)))
    risk_ablation = ablate_risk_models(df, config['risk_model'], seed=int(config.get('seed', 20260417)))
    risk_significance = risk_model_significance(df, config['risk_model'], seed=int(config.get('seed', 20260417)))
    leakage_benchmark, leakage_significance = benchmark_leakage_designs(df, config['risk_model'], seed=int(config.get('seed', 20260417)))
    bridge_outputs = build_problem_bridge_evidence(df, config['risk_model'])
    threshold_story = build_threshold_explanation_outputs(df, threshold_grid, threshold_boot, risk_summary)
    optimization_baseline_long, optimization_baseline_summary, optimization_significance = build_optimization_baseline_comparison(
        df,
        plans,
        config,
    )
    optimization_mechanism = build_optimization_mechanism_outputs(df, plans, plans_budget_grid, config)
    if not risk_ablation.empty:
        diagnostics['risk_ablation_rows'] = int(len(risk_ablation))
    if not risk_significance.empty:
        diagnostics['risk_significance_rows'] = int(len(risk_significance))
    if not leakage_benchmark.empty:
        diagnostics['leakage_design_rows'] = int(len(leakage_benchmark))
    if bridge_outputs.get('problem_bridge_summary'):
        diagnostics['problem_bridge'] = bridge_outputs['problem_bridge_summary']
    if not optimization_baseline_summary.empty:
        diagnostics['optimization_baselines'] = optimization_baseline_summary.to_dict(orient='records')

    stage_dir = run_dir / 'validation'
    save_payload(diagnostics, stage_dir / 'diagnostics.json')
    save_frame(compact_metric_table(diagnostics), stage_dir / 'diagnostics_table.csv')
    save_payload(stability_overview, stage_dir / 'stability_overview.json')
    save_payload(risk_evidence, stage_dir / 'risk_evidence_summary.json')
    save_frame(model_benchmark, stage_dir / 'risk_model_benchmark.csv')
    save_frame(risk_ablation, stage_dir / 'risk_model_ablation.csv')
    save_frame(risk_significance, stage_dir / 'risk_model_significance.csv')
    save_frame(leakage_benchmark, stage_dir / 'risk_leakage_benchmark.csv')
    save_frame(leakage_significance, stage_dir / 'risk_leakage_significance.csv')
    save_frame(bridge_outputs['view_semantics'], stage_dir / 'problem_bridge_view_semantics.csv')
    save_frame(bridge_outputs['second_order_dimensionality'], stage_dir / 'problem_bridge_second_order_dimensionality.csv')
    save_frame(bridge_outputs['latent_risk_bridge'], stage_dir / 'problem_bridge_latent_risk_bridge.csv')
    save_frame(bridge_outputs['scalar_ranking_utility'], stage_dir / 'problem_bridge_scalar_ranking_utility.csv')
    save_frame(bridge_outputs['problem_bridge_role_map'], stage_dir / 'problem_bridge_role_map.csv')
    save_payload(bridge_outputs['problem_bridge_summary'], stage_dir / 'problem_bridge_summary.json')
    save_frame(threshold_story['threshold_selected_row'], stage_dir / 'risk_threshold_selected_row.csv')
    save_frame(threshold_story['threshold_bootstrap_intervals'], stage_dir / 'risk_threshold_bootstrap_intervals.csv')
    save_frame(threshold_story['threshold_alignment'], stage_dir / 'risk_threshold_alignment.csv')
    save_frame(threshold_story['risk_tier_feature_gradient'], stage_dir / 'risk_tier_feature_gradient.csv')
    save_frame(threshold_story['risk_tier_feature_gradient_long'], stage_dir / 'risk_tier_feature_gradient_long.csv')
    save_frame(optimization_baseline_long, stage_dir / 'optimization_baseline_patient_level.csv')
    save_frame(optimization_baseline_summary, stage_dir / 'optimization_baseline_summary.csv')
    save_frame(optimization_significance, stage_dir / 'optimization_significance.csv')
    save_frame(optimization_mechanism['optimization_constraint_profile'], stage_dir / 'optimization_constraint_profile.csv')
    save_frame(optimization_mechanism['optimization_driver_summary'], stage_dir / 'optimization_driver_summary.csv')
    save_frame(optimization_mechanism['optimization_budget_strategy_shift'], stage_dir / 'optimization_budget_strategy_shift.csv')
    save_frame(optimization_mechanism['optimization_sample_explanations'], stage_dir / 'optimization_sample_explanations.csv')
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
    if config['runtime'].get('plots', False):
        plot_workflow_overview(stage_dir / 'workflow_overview.png')
        constitution_contrib_path = run_dir / 'latent' / 'constitution_contributions_to_latent.csv'
        if constitution_contrib_path.exists():
            plot_constitution_contribution_bar(pd.read_csv(constitution_contrib_path), run_dir / 'latent' / 'constitution_contribution_bar.png')
        if not bridge_outputs['latent_risk_bridge'].empty:
            plot_problem_bridge_heatmap(bridge_outputs['latent_risk_bridge'], stage_dir / 'problem_bridge_heatmap.png')
        if not threshold_boot.empty:
            plot_threshold_bootstrap_distributions(threshold_boot, stage_dir / 'risk_threshold_bootstrap_distributions.png')
        if not threshold_story['risk_tier_feature_gradient_long'].empty:
            plot_tier_feature_gradient(threshold_story['risk_tier_feature_gradient_long'], stage_dir / 'risk_tier_feature_gradient.png')
        if not optimization_mechanism['optimization_driver_summary'].empty:
            plot_strategy_mapping_heatmap(optimization_mechanism['optimization_driver_summary'], stage_dir / 'optimization_strategy_heatmap.png')
        if not optimization_mechanism['optimization_budget_strategy_shift'].empty:
            plot_optimization_budget_shift(optimization_mechanism['optimization_budget_strategy_shift'], stage_dir / 'optimization_budget_shift.png')
        if not optimization_mechanism['optimization_sample_explanations'].empty:
            plot_sample_plan_paths(optimization_mechanism['optimization_sample_explanations'], stage_dir / 'sample_1_2_3_plan_paths.png')
