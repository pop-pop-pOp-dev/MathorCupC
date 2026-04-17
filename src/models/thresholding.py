from __future__ import annotations

import numpy as np
import pandas as pd


def search_risk_thresholds_with_grid(
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    grid_points: int = 60,
) -> tuple[float, float, pd.DataFrame]:
    low_grid = np.linspace(score.quantile(0.05), score.quantile(0.70), grid_points)
    high_grid = np.linspace(score.quantile(0.30), score.quantile(0.95), grid_points)
    best: tuple[float, float] | None = None
    best_obj = -1e18
    records: list[dict] = []
    low_mask = low_anchor == 1
    high_mask = high_anchor == 1
    for t1 in low_grid:
        for t2 in high_grid:
            if t2 <= t1:
                continue
            low_ok = float((score[low_mask] < t1).mean()) if low_mask.any() else 0.0
            high_ok = float((score[high_mask] >= t2).mean()) if high_mask.any() else 0.0
            margin = float(t2 - t1)
            obj = 0.45 * low_ok + 0.45 * high_ok + 0.10 * margin / 100.0
            records.append(
                {
                    't1': float(t1),
                    't2': float(t2),
                    'low_ok': low_ok,
                    'high_ok': high_ok,
                    'margin': margin,
                    'objective': float(obj),
                }
            )
            if obj > best_obj:
                best_obj = obj
                best = (float(t1), float(t2))
    fallback = (float(score.quantile(0.33)), float(score.quantile(0.67)))
    return *(best or fallback), pd.DataFrame(records)


def search_risk_thresholds(score: pd.Series, low_anchor: pd.Series, high_anchor: pd.Series, grid_points: int = 60) -> tuple[float, float]:
    t1, t2, _ = search_risk_thresholds_with_grid(score, low_anchor, high_anchor, grid_points=grid_points)
    return t1, t2


def assign_risk_tier(score: pd.Series, t1: float, t2: float) -> pd.Series:
    tiers = pd.Series('medium', index=score.index)
    tiers.loc[score < t1] = 'low'
    tiers.loc[score >= t2] = 'high'
    return tiers
