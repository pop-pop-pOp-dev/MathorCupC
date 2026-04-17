from __future__ import annotations

from pathlib import Path
import pandas as pd
from models.patient_state import build_patient_state_table
from models.intervention_optimizer import optimize_population
from reporting.export_results import save_frame


def run_stage_05_optimize(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
    patient_state = build_patient_state_table(df)
    phlegm = df[df['constitution_label'] == 5].copy()
    plans = optimize_population(phlegm, config['clinical_rules'], config['intervention'])
    if not plans.empty:
        plans = plans.merge(patient_state[['sample_id', 'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi']], on='sample_id', how='left')
    stage_dir = run_dir / 'optimization'
    save_frame(patient_state, stage_dir / 'patient_state_table.csv')
    save_frame(plans, stage_dir / 'phlegm_patient_plans.csv')
    sample_cases = plans[plans['sample_id'].isin([1, 2, 3])].copy() if not plans.empty else plans
    save_frame(sample_cases, stage_dir / 'sample_1_2_3_plans.csv')
    return plans
