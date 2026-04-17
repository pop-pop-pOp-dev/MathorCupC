from __future__ import annotations

import pandas as pd


def build_activity_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out['adl_share'] = df['adl_total'] / df['activity_total'].replace(0, 1)
    out['iadl_share'] = df['iadl_total'] / df['activity_total'].replace(0, 1)
    out['activity_risk'] = (100 - df['activity_total']) / 100.0
    out['low_activity_flag'] = (df['activity_total'] < 40).astype(int)
    out['mid_activity_flag'] = ((df['activity_total'] >= 40) & (df['activity_total'] < 60)).astype(int)
    out['high_activity_flag'] = (df['activity_total'] >= 60).astype(int)
    return out
