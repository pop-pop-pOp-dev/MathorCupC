from __future__ import annotations

import numpy as np
import pandas as pd

from models.latent_state import fit_latent_state, loadings_to_long, project_latent_state
from models.rule_mining import extract_minimal_rules
from models.thresholding import assign_risk_tier, search_risk_thresholds, search_risk_thresholds_with_grid


def _ci_bounds(series: pd.Series, ci_level: float = 0.95) -> tuple[float, float]:
    alpha = max(0.0, min(1.0, 1.0 - ci_level))
    lower = float(series.quantile(alpha / 2.0))
    upper = float(series.quantile(1.0 - alpha / 2.0))
    return lower, upper


def bootstrap_latent_loadings(df: pd.DataFrame, risk_config: dict, n_boot: int = 20, seed: int = 20260417) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict] = []
    for i in range(n_boot):
        sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
        sampled = df.loc[sample_idx].reset_index(drop=True)
        result = fit_latent_state(sampled, risk_config)
        detailed = loadings_to_long(result.loadings)
        detailed.insert(0, 'bootstrap_id', i)
        records.extend(detailed.to_dict(orient='records'))
    return pd.DataFrame(records)


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


def bootstrap_latent_score_stability(
    df: pd.DataFrame,
    risk_config: dict,
    n_boot: int = 20,
    seed: int = 20260417,
    top_quantile: float = 0.20,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    reference = fit_latent_state(df, risk_config).frame
    ref_top_mask = reference['latent_state_h'] >= reference['latent_state_h'].quantile(max(0.0, min(1.0, 1.0 - top_quantile)))
    records: list[dict] = []
    for i in range(n_boot):
        sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
        sampled = df.loc[sample_idx].reset_index(drop=True)
        fitted = fit_latent_state(sampled, risk_config)
        projected = project_latent_state(df, fitted.view_models, risk_config)
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


def bootstrap_latent_state_stability(df: pd.DataFrame, risk_config: dict, n_boot: int = 20, seed: int = 20260417) -> pd.DataFrame:
    detailed = bootstrap_latent_loadings(df, risk_config, n_boot=n_boot, seed=seed)
    summary = summarize_latent_bootstrap(detailed, ci_level=float(risk_config['latent_state'].get('report_ci_level', 0.95)))
    out = summary.groupby('feature', as_index=False).agg(
        mean_abs_loading=('mean_abs_loading', 'mean'),
        std_abs_loading=('mean_abs_loading', 'std'),
    )
    return out.rename(columns={'std_abs_loading': 'std'})


def search_threshold_grid(score: pd.Series, low_anchor: pd.Series, high_anchor: pd.Series, grid_points: int = 60) -> pd.DataFrame:
    _, _, grid = search_risk_thresholds_with_grid(score, low_anchor, high_anchor, grid_points=grid_points)
    return grid


def bootstrap_threshold_stability(score: pd.Series, low_anchor: pd.Series, high_anchor: pd.Series, n_boot: int = 20, seed: int = 20260417) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    idx = np.arange(len(score))
    for i in range(n_boot):
        sample = rng.choice(idx, size=len(idx), replace=True)
        t1, t2 = search_risk_thresholds(score.iloc[sample].reset_index(drop=True), low_anchor.iloc[sample].reset_index(drop=True), high_anchor.iloc[sample].reset_index(drop=True))
        records.append({'bootstrap_id': i, 't1': t1, 't2': t2, 'threshold_gap': float(t2 - t1)})
    return pd.DataFrame(records)


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


def bootstrap_rule_stability(
    df: pd.DataFrame,
    max_rule_size: int = 3,
    min_coverage: float = 0.20,
    min_purity: float = 0.60,
    n_boot: int = 20,
    seed: int = 20260417,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict] = []
    for i in range(n_boot):
        sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
        sampled = df.loc[sample_idx].reset_index(drop=True)
        rules = extract_minimal_rules(
            sampled,
            max_rule_size=max_rule_size,
            min_coverage=min_coverage,
            min_purity=min_purity,
        )
        if rules.empty:
            continue
        rules = rules.copy()
        rules['bootstrap_id'] = i
        rules['selected_flag'] = 1
        records.extend(rules.to_dict(orient='records'))
    return pd.DataFrame(records)


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
