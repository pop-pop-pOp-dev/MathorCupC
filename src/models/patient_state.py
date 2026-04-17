from __future__ import annotations

import pandas as pd


def build_patient_state_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'sample_id', 'constitution_label', 'constitution_tanshi', 'activity_total', 'age_group',
        'bmi', 'uric_acid', 'fasting_glucose', 'smoking_history', 'drinking_history',
        'latent_state_h', 'continuous_risk_score', 'risk_tier'
    ]
    out = df[cols].copy()
    out['is_phlegm_patient'] = (out['constitution_label'] == 5).astype(int)
    return out
