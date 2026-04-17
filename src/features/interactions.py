from __future__ import annotations

import pandas as pd


def build_interaction_features(feature_df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=feature_df.index)
    out['tanshi_x_low_activity'] = feature_df['constitution_tanshi_dominance'] * feature_df['low_activity_flag']
    out['tanshi_x_bmi_deviation'] = feature_df['constitution_tanshi_dominance'] * feature_df['dev_bmi']
    out['metabolic_x_low_activity'] = feature_df['metabolic_deviation_total'] * feature_df['low_activity_flag']
    return out
