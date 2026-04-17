from __future__ import annotations

import numpy as np
import pandas as pd


def deviation_from_interval(series: pd.Series, low: float, high: float, power: float = 1.5) -> pd.Series:
    below = np.maximum(low - series, 0)
    above = np.maximum(series - high, 0)
    scale = max(high - low, 1e-6)
    return ((below + above) / scale) ** power


def uric_acid_deviation(df: pd.DataFrame, male_range: tuple[float, float], female_range: tuple[float, float], power: float = 1.5) -> pd.Series:
    male = df['sex'] == 1
    out = pd.Series(0.0, index=df.index)
    out.loc[male] = deviation_from_interval(df.loc[male, 'uric_acid'], male_range[0], male_range[1], power)
    out.loc[~male] = deviation_from_interval(df.loc[~male, 'uric_acid'], female_range[0], female_range[1], power)
    return out


def derive_hyperlipidemia_label_by_rules(df: pd.DataFrame) -> pd.Series:
    condition = (df['tc'] > 6.2) | (df['tg'] > 1.7) | (df['ldl_c'] > 3.1) | (df['hdl_c'] < 1.04)
    return condition.astype(int)


def derive_lipid_type_by_rules(df: pd.DataFrame) -> pd.Series:
    tc_high = df['tc'] > 6.2
    tg_high = df['tg'] > 1.7
    label = np.zeros(len(df), dtype=int)
    label[(tc_high) & (~tg_high)] = 1
    label[(~tc_high) & (tg_high)] = 2
    label[(tc_high) & (tg_high)] = 3
    return pd.Series(label, index=df.index)
