from __future__ import annotations

from pathlib import Path
import pandas as pd
from models.patient_state import build_patient_state_table
from utils.cohort import phlegm_intervention_cohort
from utils.perf import resolve_n_jobs
from models.intervention_optimizer import optimize_population
from models.strategy_mapping import build_strategy_mapping_tables
from reporting.export_results import save_frame, save_payload


def run_stage_05_optimize(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    patient_state = build_patient_state_table(df)
    phlegm = phlegm_intervention_cohort(df)
    plans = optimize_population(phlegm, config['clinical_rules'], config['intervention'], n_jobs=resolve_n_jobs(config))
    if not plans.empty:
        plans = plans.merge(patient_state[['sample_id', 'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi']], on='sample_id', how='left')
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
    save_frame(patient_state, stage_dir / 'patient_state_table.csv')
    save_frame(plans, stage_dir / 'phlegm_patient_plans.csv')
    sample_cases = plans[plans['sample_id'].isin([1, 2, 3])].copy() if not plans.empty else plans
    save_frame(sample_cases, stage_dir / 'sample_1_2_3_plans.csv')
    return plans
