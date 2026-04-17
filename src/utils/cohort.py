"""统一痰湿/干预子群口径，避免 stage 间定义漂移。"""

from __future__ import annotations

import pandas as pd


def phlegm_intervention_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """问题三优化对象：优先使用题面一致的痰湿标签列，否则回退体质主标签。"""
    if 'phlegm_dampness_label_flag' in df.columns:
        mask = pd.to_numeric(df['phlegm_dampness_label_flag'], errors='coerce').fillna(0).astype(int) == 1
        return df.loc[mask].copy()
    if 'constitution_label' in df.columns:
        return df[df['constitution_label'] == 5].copy()
    return df.iloc[0:0].copy()
