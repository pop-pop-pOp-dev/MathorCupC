from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed, effective_n_jobs

from models.constitution_effects import constitution_contribution_frame
from models.latent_state import fit_latent_state, loadings_to_long, project_latent_state
from models.rule_mining import extract_minimal_rules
from models.thresholding import assign_risk_tier, search_risk_thresholds, search_risk_thresholds_with_grid


def _resolve_parallel_n_jobs(n_jobs: int | None) -> int:
    if n_jobs is None:
        return int(effective_n_jobs(-1))
    return int(effective_n_jobs(int(n_jobs)))


def _ci_bounds(series: pd.Series, ci_level: float = 0.95) -> tuple[float, float]:
    alpha = max(0.0, min(1.0, 1.0 - ci_level))
    lower = float(series.quantile(alpha / 2.0))
    upper = float(series.quantile(1.0 - alpha / 2.0))
    return lower, upper


def _one_bootstrap_latent_loading(i: int, df: pd.DataFrame, risk_config: dict, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 91_337 + i)
    sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
    sampled = df.loc[sample_idx].reset_index(drop=True)
    result = fit_latent_state(sampled, risk_config)
    detailed = loadings_to_long(result.loadings)
    detailed.insert(0, 'bootstrap_id', i)
    return detailed


def bootstrap_latent_loadings(
    df: pd.DataFrame,
    risk_config: dict,
    n_boot: int = 20,
    seed: int = 20260417,
    n_jobs: int | None = None,
) -> pd.DataFrame:
    nj = _resolve_parallel_n_jobs(n_jobs)
    if nj == 1:
        parts = [_one_bootstrap_latent_loading(i, df, risk_config, seed) for i in range(n_boot)]
    else:
        parts = Parallel(n_jobs=nj)(delayed(_one_bootstrap_latent_loading)(i, df, risk_config, seed) for i in range(n_boot))
    return pd.concat(parts, ignore_index=True)


def summarize_latent_bootstrap(loadings_boot: pd.DataFrame, ci_level: float = 0.95) -> pd.DataFrame:
    if loadings_boot.empty:
        return pd.DataFrame(
            columns=[
                'factor_name', 'feature', 'mean_loading', 'std_loading', 'mean_abs_loading',
                'std_abs_loading', 'sign_consistency', 'ci_lower', 'ci_upper', 'abs_ci_lower', 'abs_ci_upper'
            ]
        )

    rows: list[dict] = []
    for (factor_name, feature), group in loadings_boot.groupby(['factor_name', 'feature']):
        loading = group['loading']
        abs_loading = group['abs_loading']
        ci_lower, ci_upper = _ci_bounds(loading, ci_level=ci_level)
        abs_ci_lower, abs_ci_upper = _ci_bounds(abs_loading, ci_level=ci_level)
        sign_consistency = max((loading >= 0).mean(), (loading <= 0).mean())
        rows.append(
            {
                'factor_name': factor_name,
                'feature': feature,
                'mean_loading': float(loading.mean()),
                'std_loading': float(loading.std(ddof=0)),
                'mean_abs_loading': float(abs_loading.mean()),
                'std_abs_loading': float(abs_loading.std(ddof=0)),
                'sign_consistency': float(sign_consistency),
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'abs_ci_lower': abs_ci_lower,
                'abs_ci_upper': abs_ci_upper,
            }
        )
    return pd.DataFrame(rows).sort_values(['factor_name', 'mean_abs_loading'], ascending=[True, False]).reset_index(drop=True)


def _one_bootstrap_latent_score_stability(
    i: int,
    df: pd.DataFrame,
    risk_config: dict,
    reference: pd.DataFrame,
    ref_top_mask: pd.Series,
    top_quantile: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 50_003 + i)
    sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
    sampled = df.loc[sample_idx].reset_index(drop=True)
    fitted = fit_latent_state(sampled, risk_config)
    projected = project_latent_state(df, fitted.view_models, risk_config)
    records: list[dict] = []
    for factor_name in ['constitution_factor', 'activity_factor', 'metabolic_factor', 'latent_state_h']:
        pearson = float(reference[factor_name].corr(projected[factor_name], method='pearson'))
        spearman = float(reference[factor_name].corr(projected[factor_name], method='spearman'))
        records.append(
            {
                'bootstrap_id': i,
                'factor_name': factor_name,
                'pearson_corr': 0.0 if np.isnan(pearson) else pearson,
                'spearman_corr': 0.0 if np.isnan(spearman) else spearman,
            }
        )
    projected_top_mask = projected['latent_state_h'] >= projected['latent_state_h'].quantile(max(0.0, min(1.0, 1.0 - top_quantile)))
    inter = int((ref_top_mask & projected_top_mask).sum())
    union = int((ref_top_mask | projected_top_mask).sum())
    records.append(
        {
            'bootstrap_id': i,
            'factor_name': 'latent_state_top_group',
            'pearson_corr': float(inter / union) if union else 0.0,
            'spearman_corr': float(inter / max(int(ref_top_mask.sum()), 1)),
        }
    )
    return pd.DataFrame(records)


def bootstrap_latent_score_stability(
    df: pd.DataFrame,
    risk_config: dict,
    n_boot: int = 20,
    seed: int = 20260417,
    top_quantile: float = 0.20,
    reference_frame: pd.DataFrame | None = None,
    n_jobs: int | None = None,
) -> pd.DataFrame:
    reference = reference_frame if reference_frame is not None else fit_latent_state(df, risk_config).frame
    ref_top_mask = reference['latent_state_h'] >= reference['latent_state_h'].quantile(max(0.0, min(1.0, 1.0 - top_quantile)))
    nj = _resolve_parallel_n_jobs(n_jobs)
    if nj == 1:
        parts = [
            _one_bootstrap_latent_score_stability(i, df, risk_config, reference, ref_top_mask, top_quantile, seed)
            for i in range(n_boot)
        ]
    else:
        parts = Parallel(n_jobs=nj)(
            delayed(_one_bootstrap_latent_score_stability)(i, df, risk_config, reference, ref_top_mask, top_quantile, seed)
            for i in range(n_boot)
        )
    return pd.concat(parts, ignore_index=True)


def summarize_latent_score_stability(score_stability: pd.DataFrame, ci_level: float = 0.95) -> pd.DataFrame:
    if score_stability.empty:
        return pd.DataFrame(columns=['factor_name', 'pearson_mean', 'pearson_std', 'pearson_ci_lower', 'pearson_ci_upper', 'spearman_mean', 'spearman_std', 'spearman_ci_lower', 'spearman_ci_upper'])
    rows: list[dict] = []
    for factor_name, group in score_stability.groupby('factor_name'):
        pearson_ci_lower, pearson_ci_upper = _ci_bounds(group['pearson_corr'], ci_level=ci_level)
        spearman_ci_lower, spearman_ci_upper = _ci_bounds(group['spearman_corr'], ci_level=ci_level)
        rows.append(
            {
                'factor_name': factor_name,
                'pearson_mean': float(group['pearson_corr'].mean()),
                'pearson_std': float(group['pearson_corr'].std(ddof=0)),
                'pearson_ci_lower': pearson_ci_lower,
                'pearson_ci_upper': pearson_ci_upper,
                'spearman_mean': float(group['spearman_corr'].mean()),
                'spearman_std': float(group['spearman_corr'].std(ddof=0)),
                'spearman_ci_lower': spearman_ci_lower,
                'spearman_ci_upper': spearman_ci_upper,
            }
        )
    return pd.DataFrame(rows).reset_index(drop=True)


def latent_state_stability_from_loadings_boot(loadings_boot: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    """由已算好的载荷 bootstrap 汇总 latent_stability 表，避免重复 fit_latent_state。"""
    if loadings_boot.empty:
        return pd.DataFrame(columns=['feature', 'mean_abs_loading', 'std'])
    summary = summarize_latent_bootstrap(loadings_boot, ci_level=float(risk_config['latent_state'].get('report_ci_level', 0.95)))
    out = summary.groupby('feature', as_index=False).agg(
        mean_abs_loading=('mean_abs_loading', 'mean'),
        std_abs_loading=('mean_abs_loading', 'std'),
    )
    return out.rename(columns={'std_abs_loading': 'std'})


def bootstrap_latent_state_stability(
    df: pd.DataFrame,
    risk_config: dict,
    n_boot: int = 20,
    seed: int = 20260417,
    loadings_boot: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """若传入 loadings_boot（与 n_boot 一致），则不再重复 bootstrap_latent_loadings。"""
    detailed = loadings_boot if loadings_boot is not None else bootstrap_latent_loadings(df, risk_config, n_boot=n_boot, seed=seed)
    return latent_state_stability_from_loadings_boot(detailed, risk_config)


def _one_bootstrap_constitution_contribution(i: int, df: pd.DataFrame, risk_config: dict, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 77_777 + i)
    sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
    sampled = df.loc[sample_idx].reset_index(drop=True)
    result = fit_latent_state(sampled, risk_config)
    contrib = constitution_contribution_frame(result.loadings)
    if contrib.empty:
        return pd.DataFrame()
    contrib = contrib.copy()
    contrib.insert(0, 'bootstrap_id', i)
    return contrib


def bootstrap_constitution_contributions(
    df: pd.DataFrame,
    risk_config: dict,
    n_boot: int = 20,
    seed: int = 20260417,
    n_jobs: int | None = None,
) -> pd.DataFrame:
    nj = _resolve_parallel_n_jobs(n_jobs)
    if nj == 1:
        parts = [_one_bootstrap_constitution_contribution(i, df, risk_config, seed) for i in range(n_boot)]
    else:
        parts = Parallel(n_jobs=nj)(delayed(_one_bootstrap_constitution_contribution)(i, df, risk_config, seed) for i in range(n_boot))
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def summarize_constitution_contributions(contribution_boot: pd.DataFrame, ci_level: float = 0.95) -> pd.DataFrame:
    if contribution_boot.empty:
        return pd.DataFrame(
            columns=[
                'constitution_feature',
                'mean_loading',
                'std_loading',
                'loading_ci_lower',
                'loading_ci_upper',
                'mean_abs_share',
                'std_abs_share',
                'abs_share_ci_lower',
                'abs_share_ci_upper',
                'sign_consistency',
            ]
        )
    rows: list[dict] = []
    for constitution_feature, group in contribution_boot.groupby('constitution_feature'):
        loading_ci_lower, loading_ci_upper = _ci_bounds(group['loading'], ci_level=ci_level)
        share_ci_lower, share_ci_upper = _ci_bounds(group['abs_share'], ci_level=ci_level)
        sign_consistency = max((group['loading'] >= 0).mean(), (group['loading'] <= 0).mean())
        rows.append(
            {
                'constitution_feature': constitution_feature,
                'mean_loading': float(group['loading'].mean()),
                'std_loading': float(group['loading'].std(ddof=0)),
                'loading_ci_lower': loading_ci_lower,
                'loading_ci_upper': loading_ci_upper,
                'mean_abs_share': float(group['abs_share'].mean()),
                'std_abs_share': float(group['abs_share'].std(ddof=0)),
                'abs_share_ci_lower': share_ci_lower,
                'abs_share_ci_upper': share_ci_upper,
                'sign_consistency': float(sign_consistency),
            }
        )
    return pd.DataFrame(rows).sort_values('mean_abs_share', ascending=False).reset_index(drop=True)


def search_threshold_grid(
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    grid_points: int = 60,
    severity: pd.Series | None = None,
    min_group_share: float = 0.10,
) -> pd.DataFrame:
    _, _, grid = search_risk_thresholds_with_grid(
        score,
        low_anchor,
        high_anchor,
        grid_points=grid_points,
        severity=severity,
        min_group_share=min_group_share,
    )
    return grid


def _one_bootstrap_threshold(
    i: int,
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    severity_series: pd.Series | None,
    min_group_share: float,
    seed: int,
) -> dict[str, float | int]:
    rng = np.random.default_rng(seed + 33_221 + i)
    idx = np.arange(len(score))
    sample = rng.choice(idx, size=len(idx), replace=True)
    severity_sample = severity_series.iloc[sample].reset_index(drop=True) if severity_series is not None else None
    t1, t2 = search_risk_thresholds(
        score.iloc[sample].reset_index(drop=True),
        low_anchor.iloc[sample].reset_index(drop=True),
        high_anchor.iloc[sample].reset_index(drop=True),
        severity=severity_sample,
        min_group_share=min_group_share,
    )
    return {'bootstrap_id': i, 't1': t1, 't2': t2, 'threshold_gap': float(t2 - t1)}


def bootstrap_threshold_stability(
    score: pd.Series,
    low_anchor: pd.Series,
    high_anchor: pd.Series,
    n_boot: int = 20,
    seed: int = 20260417,
    severity: pd.Series | None = None,
    min_group_share: float = 0.10,
    n_jobs: int | None = None,
) -> pd.DataFrame:
    severity_series = severity.reset_index(drop=True) if severity is not None else None
    nj = _resolve_parallel_n_jobs(n_jobs)
    if nj == 1:
        rows = [
            _one_bootstrap_threshold(i, score, low_anchor, high_anchor, severity_series, min_group_share, seed)
            for i in range(n_boot)
        ]
    else:
        rows = Parallel(n_jobs=nj)(
            delayed(_one_bootstrap_threshold)(i, score, low_anchor, high_anchor, severity_series, min_group_share, seed)
            for i in range(n_boot)
        )
    return pd.DataFrame(rows)


def summarize_threshold_stability(threshold_boot: pd.DataFrame, ci_level: float = 0.95) -> pd.DataFrame:
    if threshold_boot.empty:
        return pd.DataFrame(columns=['metric', 'mean', 'std', 'ci_lower', 'ci_upper'])
    rows = []
    for metric in ['t1', 't2', 'threshold_gap']:
        series = threshold_boot[metric]
        ci_lower, ci_upper = _ci_bounds(series, ci_level=ci_level)
        rows.append(
            {
                'metric': metric,
                'mean': float(series.mean()),
                'std': float(series.std(ddof=0)),
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
            }
        )
    return pd.DataFrame(rows)


def bootstrap_tier_distribution(
    score: pd.Series,
    threshold_boot: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict] = []
    for row in threshold_boot.itertuples(index=False):
        t1 = float(getattr(row, 't1'))
        t2 = float(getattr(row, 't2'))
        bootstrap_id = int(getattr(row, 'bootstrap_id'))
        tiers = assign_risk_tier(score.reset_index(drop=True), t1, t2)
        dist = tiers.value_counts(normalize=True)
        for tier_name in ['low', 'medium', 'high']:
            records.append(
                {
                    'bootstrap_id': bootstrap_id,
                    'risk_tier': tier_name,
                    'share': float(dist.get(tier_name, 0.0)),
                }
            )
    return pd.DataFrame(records)


def summarize_tier_distribution(tier_bootstrap: pd.DataFrame, ci_level: float = 0.95) -> pd.DataFrame:
    if tier_bootstrap.empty:
        return pd.DataFrame(columns=['risk_tier', 'mean_share', 'std_share', 'ci_lower', 'ci_upper'])
    rows: list[dict] = []
    for risk_tier, group in tier_bootstrap.groupby('risk_tier'):
        ci_lower, ci_upper = _ci_bounds(group['share'], ci_level=ci_level)
        rows.append(
            {
                'risk_tier': risk_tier,
                'mean_share': float(group['share'].mean()),
                'std_share': float(group['share'].std(ddof=0)),
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
            }
        )
    return pd.DataFrame(rows)


def _one_bootstrap_rule(
    i: int,
    df: pd.DataFrame,
    max_rule_size: int,
    min_coverage: float,
    min_purity: float,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 12_345 + i)
    sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
    sampled = df.loc[sample_idx].reset_index(drop=True)
    rules = extract_minimal_rules(
        sampled,
        max_rule_size=max_rule_size,
        min_coverage=min_coverage,
        min_purity=min_purity,
    )
    if rules.empty:
        return pd.DataFrame()
    rules = rules.copy()
    rules['bootstrap_id'] = i
    rules['selected_flag'] = 1
    return rules


def bootstrap_rule_stability(
    df: pd.DataFrame,
    max_rule_size: int = 3,
    min_coverage: float = 0.20,
    min_purity: float = 0.60,
    n_boot: int = 20,
    seed: int = 20260417,
    n_jobs: int | None = None,
) -> pd.DataFrame:
    nj = _resolve_parallel_n_jobs(n_jobs)
    if nj == 1:
        parts = [_one_bootstrap_rule(i, df, max_rule_size, min_coverage, min_purity, seed) for i in range(n_boot)]
    else:
        parts = Parallel(n_jobs=nj)(
            delayed(_one_bootstrap_rule)(i, df, max_rule_size, min_coverage, min_purity, seed) for i in range(n_boot)
        )
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def summarize_rule_stability(rule_bootstrap: pd.DataFrame, n_boot: int, ci_level: float = 0.95) -> pd.DataFrame:
    if rule_bootstrap.empty:
        return pd.DataFrame(columns=['rule', 'selection_frequency', 'coverage_mean', 'coverage_std', 'coverage_ci_lower', 'coverage_ci_upper', 'purity_mean', 'purity_std', 'purity_ci_lower', 'purity_ci_upper', 'lift_mean', 'lift_std', 'lift_ci_lower', 'lift_ci_upper', 'rank_mean'])
    rows: list[dict] = []
    for rule, group in rule_bootstrap.groupby('rule'):
        coverage_ci_lower, coverage_ci_upper = _ci_bounds(group['coverage'], ci_level=ci_level)
        purity_ci_lower, purity_ci_upper = _ci_bounds(group['purity'], ci_level=ci_level)
        lift_ci_lower, lift_ci_upper = _ci_bounds(group['lift'], ci_level=ci_level)
        rows.append(
            {
                'rule': rule,
                'selection_frequency': float(group['bootstrap_id'].nunique() / max(n_boot, 1)),
                'coverage_mean': float(group['coverage'].mean()),
                'coverage_std': float(group['coverage'].std(ddof=0)),
                'coverage_ci_lower': coverage_ci_lower,
                'coverage_ci_upper': coverage_ci_upper,
                'purity_mean': float(group['purity'].mean()),
                'purity_std': float(group['purity'].std(ddof=0)),
                'purity_ci_lower': purity_ci_lower,
                'purity_ci_upper': purity_ci_upper,
                'lift_mean': float(group['lift'].mean()),
                'lift_std': float(group['lift'].std(ddof=0)),
                'lift_ci_lower': lift_ci_lower,
                'lift_ci_upper': lift_ci_upper,
                'rank_mean': float(group.get('selected_order', pd.Series(range(1, len(group) + 1))).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(['selection_frequency', 'purity_mean', 'coverage_mean'], ascending=[False, False, False]).reset_index(drop=True)
