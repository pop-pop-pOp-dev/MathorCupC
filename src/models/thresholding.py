from __future__ import annotations

import numpy as np
import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').fillna(0.0)
    return (values - values.min()) / (values.max() - values.min() + 1e-9)


def assign_risk_tier(score: pd.Series, t1: float, t2: float) -> pd.Series:
    tiers = pd.Series('medium', index=score.index)
    tiers.loc[score < t1] = 'low'
    tiers.loc[score >= t2] = 'high'
    return tiers


def _group_stats(severity: pd.Series, tiers: pd.Series) -> dict[str, float]:
    normalized = _normalize(severity)
    frame = pd.DataFrame({'severity': normalized, 'risk_tier': tiers})
    shares = frame['risk_tier'].value_counts(normalize=True)
    means = frame.groupby('risk_tier')['severity'].mean()
    variances = frame.groupby('risk_tier')['severity'].var(ddof=0).fillna(0.0)
    overall_mean = float(frame['severity'].mean())
    between = 0.0
    within = 0.0
    for tier_name in ['low', 'medium', 'high']:
        share = float(shares.get(tier_name, 0.0))
        mean_value = float(means.get(tier_name, overall_mean))
        variance_value = float(variances.get(tier_name, 0.0))
        between += share * (mean_value - overall_mean) ** 2
        within += share * variance_value
    monotonic_flag = float(
        means.get('low', overall_mean) <= means.get('medium', overall_mean) <= means.get('high', overall_mean)
    )
    return {
        'low_share': float(shares.get('low', 0.0)),
        'medium_share': float(shares.get('medium', 0.0)),
        'high_share': float(shares.get('high', 0.0)),
        'mean_low_severity': float(means.get('low', overall_mean)),
        'mean_medium_severity': float(means.get('medium', overall_mean)),
        'mean_high_severity': float(means.get('high', overall_mean)),
        'between_group_dispersion': float(between),
        'within_group_dispersion': float(within),
        'severity_gap': float(means.get('high', overall_mean) - means.get('low', overall_mean)),
        'monotonic_flag': monotonic_flag,
    }


def _search_risk_thresholds_vectorized(
    s: np.ndarray,
    sev: np.ndarray,
    low_m: np.ndarray,
    high_m: np.ndarray,
    low_grid: np.ndarray,
    high_grid: np.ndarray,
    min_group_share: float,
    score_range: float,
) -> tuple[tuple[float, float] | None, float, list[dict[str, float | int]]]:
    """向量化阈值网格：与原先双重循环同一目标函数形式。"""
    eps = 1e-12
    G1, G2 = len(low_grid), len(high_grid)
    n = len(s)
    S = s.reshape(1, 1, n)
    sev_b = np.broadcast_to(sev.reshape(1, 1, n), (G1, G2, n))
    is_low = np.broadcast_to(S < low_grid.reshape(G1, 1, 1), (G1, G2, n))
    is_high = np.broadcast_to(S >= high_grid.reshape(1, G2, 1), (G1, G2, n))
    is_med = ~(is_low | is_high)
    low_share = is_low.mean(axis=2)
    medium_share = is_med.mean(axis=2)
    high_share = is_high.mean(axis=2)
    mean_low = (sev_b * is_low).sum(axis=2) / (is_low.sum(axis=2) + eps)
    mean_medium = (sev_b * is_med).sum(axis=2) / (is_med.sum(axis=2) + eps)
    mean_high = (sev_b * is_high).sum(axis=2) / (is_high.sum(axis=2) + eps)
    overall_mean = float(sev.mean())
    var_low = ((sev_b - mean_low[..., None]) ** 2 * is_low).sum(axis=2) / (is_low.sum(axis=2) + eps)
    var_med = ((sev_b - mean_medium[..., None]) ** 2 * is_med).sum(axis=2) / (is_med.sum(axis=2) + eps)
    var_high = ((sev_b - mean_high[..., None]) ** 2 * is_high).sum(axis=2) / (is_high.sum(axis=2) + eps)
    between = (
        low_share * (mean_low - overall_mean) ** 2
        + medium_share * (mean_medium - overall_mean) ** 2
        + high_share * (mean_high - overall_mean) ** 2
    )
    within = low_share * var_low + medium_share * var_med + high_share * var_high
    severity_gap = mean_high - mean_low
    monotonic_flag = ((mean_low <= mean_medium) & (mean_medium <= mean_high)).astype(float)
    if low_m.any():
        sl = s[low_m]
        low_ok_1d = np.array([float((sl < float(t1v)).mean()) for t1v in low_grid])
    else:
        low_ok_1d = np.zeros(len(low_grid), dtype=float)
    low_ok_2d = np.broadcast_to(low_ok_1d[:, None], low_share.shape)
    if high_m.any():
        sh = s[high_m]
        high_ok_1d = np.array([float((sh >= float(t2v)).mean()) for t2v in high_grid])
    else:
        high_ok_1d = np.zeros(len(high_grid), dtype=float)
    high_ok_2d = np.broadcast_to(high_ok_1d[None, :], high_share.shape)
    valid = high_grid.reshape(1, G2) > low_grid.reshape(G1, 1)
    margin = (high_grid.reshape(1, G2) - low_grid.reshape(G1, 1)) / score_range
    min_share = np.minimum(np.minimum(low_share, medium_share), high_share)
    compactness = np.maximum(0.0, 1.0 - np.minimum(within / 0.25, 1.0))
    balance_bonus = np.minimum(1.0, min_share / max(min_group_share, 1e-6))
    feasible = ((min_share >= min_group_share) & (monotonic_flag > 0.0)).astype(int)
    objective = (
        0.20 * low_ok_2d
        + 0.20 * high_ok_2d
        + 0.20 * severity_gap
        + 0.15 * between
        + 0.10 * compactness
        + 0.05 * margin
        + 0.05 * balance_bonus
        + 0.05 * monotonic_flag
    )
    penalty = 0.50 + 0.25 * np.maximum(0.0, min_group_share - min_share)
    objective = np.where(feasible.astype(bool), objective, objective - penalty)
    objective = np.where(valid, objective, -np.inf)
    flat = np.where(np.isfinite(objective), objective, -np.inf)
    if not np.any(np.isfinite(flat)):
        best: tuple[float, float] | None = None
    else:
        best_idx = np.unravel_index(int(np.argmax(flat)), flat.shape)
        best = (float(low_grid[best_idx[0]]), float(high_grid[best_idx[1]]))
    records: list[dict[str, float | int]] = []
    for i, t1v in enumerate(low_grid):
        for j, t2v in enumerate(high_grid):
            if float(t2v) <= float(t1v):
                continue
            rec = {
                't1': float(t1v),
                't2': float(t2v),
                'low_ok': float(low_ok_2d[i, j]),
                'high_ok': float(high_ok_2d[i, j]),
                'margin': float(t2v - t1v),
                'objective': float(objective[i, j]),
                'low_share': float(low_share[i, j]),
                'medium_share': float(medium_share[i, j]),
                'high_share': float(high_share[i, j]),
                'mean_low_severity': float(mean_low[i, j]),
                'mean_medium_severity': float(mean_medium[i, j]),
                'mean_high_severity': float(mean_high[i, j]),
                'between_group_dispersion': float(between[i, j]),
                'within_group_dispersion': float(within[i, j]),
                'severity_gap': float(severity_gap[i, j]),
                'monotonic_flag': float(monotonic_flag[i, j]),
                'feasible': int(feasible[i, j]),
            }
            records.append(rec)
    return best, 0.0, records


def search_risk_thresholds_with_grid(
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    grid_points: int = 60,
    severity: pd.Series | None = None,
    min_group_share: float = 0.10,
) -> tuple[float, float, pd.DataFrame]:
    score = pd.to_numeric(score, errors='coerce').fillna(0.0)
    severity = _normalize(severity if severity is not None else score)
    score_range = float(score.max() - score.min()) + 1e-9
    low_grid = np.linspace(float(score.quantile(0.05)), float(score.quantile(0.70)), grid_points)
    high_grid = np.linspace(float(score.quantile(0.30)), float(score.quantile(0.95)), grid_points)
    s = score.to_numpy(dtype=float)
    sev = severity.to_numpy(dtype=float)
    low_m = (low_anchor == 1).to_numpy()
    high_m = (high_anchor == 1).to_numpy()
    best, _, records_list = _search_risk_thresholds_vectorized(
        s, sev, low_m, high_m, low_grid, high_grid, min_group_share, score_range
    )
    fallback = (float(score.quantile(0.33)), float(score.quantile(0.67)))
    best_pair = best if best is not None else fallback
    return *best_pair, pd.DataFrame(records_list)


def search_risk_thresholds(
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    grid_points: int = 60,
    severity: pd.Series | None = None,
    min_group_share: float = 0.10,
) -> tuple[float, float]:
    t1, t2, _ = search_risk_thresholds_with_grid(
        score,
        low_anchor,
        high_anchor,
        grid_points=grid_points,
        severity=severity,
        min_group_share=min_group_share,
    )
    return t1, t2
