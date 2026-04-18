from __future__ import annotations

from pathlib import Path
import pandas as pd
from evaluation.evidence import summarize_budget_evidence, summarize_primary_plan_feasibility
from models.patient_state import build_patient_state_table
from utils.cohort import phlegm_intervention_cohort
from utils.perf import resolve_milp_n_jobs
from domain.intervention_rules import fit_transition_calibration
from models.intervention_optimizer import optimize_population
from models.strategy_mapping import build_strategy_mapping_tables
from reporting.export_results import save_frame, save_payload


def run_stage_05_optimize(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    patient_state = build_patient_state_table(df)
    phlegm = phlegm_intervention_cohort(df)
    intervention_cfg = config['intervention']
    milp_jobs = resolve_milp_n_jobs(config)
    budget_levels = [float(v) for v in intervention_cfg.get('budget_levels', [500, 800, 1200, 1500, 2000])]
    primary_budget = float(intervention_cfg.get('pareto_primary_budget', max(budget_levels)))
    calibration = fit_transition_calibration(phlegm, intervention_cfg)
    budget_runs: list[pd.DataFrame] = []
    for budget_cap in budget_levels:
        run = optimize_population(
            phlegm,
            config['clinical_rules'],
            intervention_cfg,
            n_jobs=milp_jobs,
            budget_override=budget_cap,
            optimize_for='pareto_tanshi',
            calibration=calibration,
        )
        if not run.empty:
            run = run.copy()
            run['budget_cap'] = budget_cap
            budget_runs.append(run)
    plans_budget_grid = pd.concat(budget_runs, ignore_index=True) if budget_runs else pd.DataFrame()
    plans = (
        plans_budget_grid.loc[plans_budget_grid['budget_cap'] == primary_budget].copy()
        if not plans_budget_grid.empty
        else optimize_population(
            phlegm,
            config['clinical_rules'],
            intervention_cfg,
            n_jobs=milp_jobs,
            calibration=calibration,
        )
    )
    if not plans.empty:
        plans = plans.merge(patient_state[['sample_id', 'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi']], on='sample_id', how='left')
    if not plans_budget_grid.empty:
        plans_budget_grid = plans_budget_grid.merge(
            patient_state[['sample_id', 'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi']],
            on='sample_id',
            how='left',
        )
    stage_dir = run_dir / 'optimization'
    if not plans.empty:
        mapping = build_strategy_mapping_tables(plans)
        save_frame(mapping['by_risk_tier_age'], stage_dir / 'strategy_mapping_by_risk_tier_age.csv')
        save_frame(mapping['by_activity_bins'], stage_dir / 'strategy_mapping_by_activity_bins.csv')
        save_payload(
            {
                'n_plans': int(len(plans)),
                'risk_tier_age_rows': int(len(mapping['by_risk_tier_age'])),
                'activity_bin_rows': int(len(mapping['by_activity_bins'])),
            },
            stage_dir / 'strategy_mapping_summary.json',
        )
    if not plans_budget_grid.empty:
        pareto_frontier = (
            plans_budget_grid[plans_budget_grid['status'] == 'ok']
            .groupby('budget_cap', as_index=False)
            .agg(
                feasible_plan_count=('sample_id', 'count'),
                mean_final_tanshi=('final_tanshi_score', 'mean'),
                mean_final_latent=('final_latent_state', 'mean'),
                mean_total_cost=('total_cost', 'mean'),
                mean_total_burden=('total_burden', 'mean'),
            )
            .sort_values('budget_cap')
        )
        budget_marginal_gains, budget_evidence = summarize_budget_evidence(pareto_frontier)
        save_frame(plans_budget_grid, stage_dir / 'phlegm_patient_plans_budget_grid.csv')
        save_frame(pareto_frontier, stage_dir / 'pareto_frontier_summary.csv')
        save_frame(budget_marginal_gains, stage_dir / 'pareto_budget_marginal_gains.csv')
        save_payload(budget_evidence, stage_dir / 'pareto_budget_evidence.json')
    feasibility_summary = summarize_primary_plan_feasibility(plans)
    if not feasibility_summary.empty:
        save_frame(feasibility_summary, stage_dir / 'primary_budget_feasibility_by_group.csv')
    save_frame(patient_state, stage_dir / 'patient_state_table.csv')
    save_frame(plans, stage_dir / 'phlegm_patient_plans.csv')
    sample_cases = (
        plans.loc[plans['sample_id'].isin([1, 2, 3])].copy()
        if not plans.empty
        else plans.iloc[0:0].copy()
    )
    save_frame(sample_cases, stage_dir / 'sample_1_2_3_plans.csv')
    return plans
