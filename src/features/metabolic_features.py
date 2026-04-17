from __future__ import annotations

import pandas as pd


def build_metabolic_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out['age_risk'] = (df['age_group'] - 1) / 4.0
    out['male_flag'] = (df['sex'] == 1).astype(int)
    out['smoking_flag'] = df['smoking_history'].astype(int)
    out['drinking_flag'] = df['drinking_history'].astype(int)
    out['background_risk'] = (out['age_risk'] + 0.3 * out['smoking_flag'] + 0.3 * out['drinking_flag']) / 1.6
    return out
