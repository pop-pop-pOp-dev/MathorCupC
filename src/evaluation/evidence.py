from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from domain.intervention_rules import build_patient_response_profile, fit_transition_calibration, tolerance_capacity
from models.intervention_optimizer import _build_action_space, _build_pair_data, _build_stage_action_map, _build_transition_tables
from models.risk_score import build_diagnosis_anchor_flags, fit_risk_model
from utils.cohort import phlegm_intervention_cohort


def _safe_binary_label(df: pd.DataFrame) -> pd.Series | None:
    if 'hyperlipidemia_label' not in df.columns:
        return None
    y = pd.to_numeric(df['hyperlipidemia_label'], errors='coerce').fillna(0).astype(int)
    return y if y.nunique() > 1 else None


def _extract_metric(frame: pd.DataFrame, metric: str) -> float | None:
    if frame.empty or 'metric' not in frame.columns or 'value' not in frame.columns:
        return None
    subset = frame.loc[frame['metric'] == metric, 'value']
    if subset.empty:
        return None
    return float(subset.iloc[0])


def _safe_prob(series: pd.Series | np.ndarray) -> np.ndarray:
    values = pd.to_numeric(pd.Series(series), errors='coerce').fillna(0.0).to_numpy(dtype=float)
    return np.clip(values, 1e-6, 1 - 1e-6)


def _binary_metric(y_true: pd.Series, y_prob: np.ndarray, metric: str) -> float:
    y = y_true.astype(int)
    p = _safe_prob(y_prob)
    if metric == 'roc_auc':
        return float(roc_auc_score(y, p))
    if metric == 'pr_auc':
        return float(average_precision_score(y, p))
    if metric == 'brier_score':
        return float(brier_score_loss(y, p))
    if metric == 'log_loss':
        return float(log_loss(y, p))
    raise ValueError(f'Unknown metric: {metric}')


def _paired_bootstrap_metric_improvement(
    y_true: pd.Series,
    main_prob: np.ndarray,
    comp_prob: np.ndarray,
    metric: str,
    *,
    n_boot: int = 400,
    seed: int = 20260417,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    y = y_true.astype(int).reset_index(drop=True)
    main = _safe_prob(main_prob)
    comp = _safe_prob(comp_prob)
    n = len(y)
    boot: list[float] = []

    def _improvement(a: np.ndarray, b: np.ndarray, yy: pd.Series) -> float:
        ma = _binary_metric(yy, a, metric)
        mb = _binary_metric(yy, b, metric)
        if metric in {'roc_auc', 'pr_auc'}:
            return float(ma - mb)
        return float(mb - ma)

    observed = _improvement(main, comp, y)
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        yy = y.iloc[idx].reset_index(drop=True)
        if yy.nunique() < 2:
            continue
        boot.append(_improvement(main[idx], comp[idx], yy))
    if not boot:
        return {
            'observed_improvement': observed,
            'mean_bootstrap_improvement': observed,
            'ci_lower': observed,
            'ci_upper': observed,
            'p_value_two_sided': 1.0,
        }
    boot_arr = np.asarray(boot, dtype=float)
    p_two_sided = float(2.0 * min((boot_arr <= 0.0).mean(), (boot_arr >= 0.0).mean()))
    return {
        'observed_improvement': observed,
        'mean_bootstrap_improvement': float(boot_arr.mean()),
        'ci_lower': float(np.quantile(boot_arr, 0.025)),
        'ci_upper': float(np.quantile(boot_arr, 0.975)),
        'p_value_two_sided': p_two_sided,
    }


def _paired_mean_difference_ci(values: np.ndarray, *, n_boot: int = 400, seed: int = 20260417) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return float('nan'), float('nan'), float('nan')
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(int(n_boot)):
        idx = rng.integers(0, arr.size, size=arr.size)
        means.append(float(arr[idx].mean()))
    boot = np.asarray(means, dtype=float)
    return float(arr.mean()), float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def _calibration_ece(calibration: pd.DataFrame) -> tuple[float | None, float | None]:
    required = {'sample_count', 'calibration_gap'}
    if calibration.empty or not required.issubset(calibration.columns):
        return None, None
    weights = pd.to_numeric(calibration['sample_count'], errors='coerce').fillna(0.0).to_numpy(dtype=float)
    gaps = pd.to_numeric(calibration['calibration_gap'], errors='coerce').fillna(0.0).abs().to_numpy(dtype=float)
    denom = float(weights.sum())
    if denom <= 0.0:
        return None, None
    ece = float(np.dot(weights, gaps) / denom)
    mce = float(gaps.max()) if len(gaps) else None
    return ece, mce


def summarize_risk_evidence(
    tier_summary: pd.DataFrame,
    cv_metrics: pd.DataFrame,
    calibration: pd.DataFrame,
    anchor_monotonicity: pd.DataFrame,
    threshold_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        'roc_auc': _extract_metric(cv_metrics, 'roc_auc'),
        'pr_auc': _extract_metric(cv_metrics, 'pr_auc'),
        'brier_score': _extract_metric(cv_metrics, 'brier_score'),
        'log_loss': _extract_metric(cv_metrics, 'log_loss'),
    }
    ece, mce = _calibration_ece(calibration)
    summary['expected_calibration_error'] = ece
    summary['max_calibration_error'] = mce

    if not anchor_monotonicity.empty and {'group', 'mean_score'}.issubset(anchor_monotonicity.columns):
        anchor_map = {
            str(row['group']): float(row['mean_score'])
            for _, row in anchor_monotonicity.iterrows()
        }
        low_mean = anchor_map.get('low_anchor')
        high_mean = anchor_map.get('high_anchor')
        summary['low_anchor_mean_score'] = low_mean
        summary['high_anchor_mean_score'] = high_mean
        if low_mean is not None and high_mean is not None:
            summary['anchor_mean_score_gap'] = float(high_mean - low_mean)
            summary['anchor_order_correct'] = bool(high_mean > low_mean)

    if not tier_summary.empty and {'risk_tier', 'confirmed_rate', 'avg_latent_state', 'sample_count'}.issubset(tier_summary.columns):
        tier_map = tier_summary.set_index('risk_tier')
        low_rate = float(tier_map.loc['low', 'confirmed_rate']) if 'low' in tier_map.index else None
        med_rate = float(tier_map.loc['medium', 'confirmed_rate']) if 'medium' in tier_map.index else None
        high_rate = float(tier_map.loc['high', 'confirmed_rate']) if 'high' in tier_map.index else None
        summary['tier_confirmed_rate_monotone'] = bool(
            low_rate is not None and med_rate is not None and high_rate is not None and low_rate <= med_rate <= high_rate
        )
        summary['low_confirmed_rate'] = low_rate
        summary['medium_confirmed_rate'] = med_rate
        summary['high_confirmed_rate'] = high_rate
        if low_rate is not None and high_rate is not None:
            summary['high_vs_low_confirmed_rate_gap'] = float(high_rate - low_rate)
        low_latent = float(tier_map.loc['low', 'avg_latent_state']) if 'low' in tier_map.index else None
        high_latent = float(tier_map.loc['high', 'avg_latent_state']) if 'high' in tier_map.index else None
        if low_latent is not None and high_latent is not None:
            summary['high_vs_low_latent_gap'] = float(high_latent - low_latent)

    if threshold_summary:
        threshold_gap = (((threshold_summary.get('threshold_summary') or {}).get('threshold_gap') or {}).get('mean'))
        if threshold_gap is not None:
            summary['mean_threshold_gap'] = float(threshold_gap)
    return summary


def _build_risk_variant_config(
    risk_config: dict[str, Any],
    *,
    model_type: str,
    drop_base: tuple[str, ...] = (),
    drop_interactions: tuple[str, ...] = (),
) -> dict[str, Any]:
    cfg = deepcopy(risk_config)
    risk_section = cfg.get('risk_score', cfg)
    risk_section['model_type'] = model_type
    features = deepcopy(risk_section.get('features', {}))
    base = [str(x) for x in features.get('base', []) if str(x) not in set(drop_base)]
    interactions = {
        str(name): [str(t) for t in terms]
        for name, terms in (features.get('interactions', {}) or {}).items()
        if str(name) not in set(drop_interactions)
    }
    if base:
        features['base'] = base
    if interactions or 'interactions' in features:
        features['interactions'] = interactions
    risk_section['features'] = features
    return cfg


def _run_risk_variant(
    df: pd.DataFrame,
    risk_config: dict[str, Any],
    *,
    model_type: str,
    label: str,
    drop_base: tuple[str, ...] = (),
    drop_interactions: tuple[str, ...] = (),
    seed: int = 20260417,
) -> tuple[dict[str, Any], np.ndarray | None]:
    cfg = _build_risk_variant_config(
        risk_config,
        model_type=model_type,
        drop_base=drop_base,
        drop_interactions=drop_interactions,
    )
    y = _safe_binary_label(df)
    anchors = build_diagnosis_anchor_flags(df)
    artifacts = fit_risk_model(df, cfg, seed=seed)
    score_frame = artifacts.score_frame
    prob = None
    row: dict[str, Any] = {
        'model_type': model_type,
        'label': label,
        'n_features': int((artifacts.metadata or {}).get('n_features', 0)),
        'train_cv_roc_auc': _extract_metric(artifacts.cv_metrics, 'roc_auc'),
        'train_cv_pr_auc': _extract_metric(artifacts.cv_metrics, 'pr_auc'),
        'train_cv_brier_score': _extract_metric(artifacts.cv_metrics, 'brier_score'),
        'train_cv_log_loss': _extract_metric(artifacts.cv_metrics, 'log_loss'),
    }
    if 'risk_prob' in score_frame.columns:
        prob = _safe_prob(score_frame['risk_prob'])
    if y is not None and prob is not None:
        row['full_sample_diagnosis_auc'] = float(roc_auc_score(y, prob))
        row['full_sample_diagnosis_pr_auc'] = float(average_precision_score(y, prob))
        row['full_sample_brier'] = float(brier_score_loss(y, prob))
        row['full_sample_log_loss'] = float(log_loss(y, prob))
    score = pd.to_numeric(score_frame.get('continuous_risk_score'), errors='coerce').fillna(0.0)
    low_anchor_mask = anchors['low_anchor'] == 1
    high_anchor_mask = anchors['high_anchor'] == 1
    low_mean = float(score[low_anchor_mask].mean()) if int(low_anchor_mask.sum()) else np.nan
    high_mean = float(score[high_anchor_mask].mean()) if int(high_anchor_mask.sum()) else np.nan
    row['low_anchor_mean_score'] = low_mean
    row['high_anchor_mean_score'] = high_mean
    row['anchor_gap'] = float(high_mean - low_mean) if np.isfinite(low_mean) and np.isfinite(high_mean) else np.nan
    row['probability_calibration'] = str((artifacts.metadata or {}).get('probability_calibration', 'none'))
    return row, prob


def benchmark_risk_models(df: pd.DataFrame, risk_config: dict[str, Any], seed: int = 20260417) -> pd.DataFrame:
    variants = [
        ('anchor_front_logistic', '主模型', (), ()),
        ('legacy_weighted', '旧版手工加权', (), ()),
        ('severity_ridge', '连续严重度 Ridge', (), ()),
    ]
    rows: list[dict[str, Any]] = []
    for model_type, label, drop_base, drop_inter in variants:
        row, _ = _run_risk_variant(
            df,
            risk_config,
            model_type=model_type,
            label=label,
            drop_base=drop_base,
            drop_interactions=drop_inter,
            seed=seed,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def ablate_risk_models(df: pd.DataFrame, risk_config: dict[str, Any], seed: int = 20260417) -> pd.DataFrame:
    variants = [
        ('anchor_front_logistic', '完整主模型', (), ()),
        ('anchor_front_logistic', '去体质信息', ('constitution_factor', 'constitution_tanshi'), ('tanshi_x_low_activity', 'tanshi_x_bmi_deviation')),
        ('anchor_front_logistic', '去活动信息', ('activity_factor', 'activity_total', 'activity_risk'), ('tanshi_x_low_activity', 'metabolic_x_low_activity', 'age_x_activity_risk')),
        ('anchor_front_logistic', '去代谢信息', ('metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid'), ('tanshi_x_bmi_deviation', 'metabolic_x_low_activity')),
        ('anchor_front_logistic', '去背景信息', ('age_group', 'background_risk'), ('age_x_activity_risk',)),
        ('anchor_front_logistic', '去交互项', (), tuple((risk_config.get('risk_score', risk_config).get('features', {}).get('interactions', {}) or {}).keys())),
    ]
    rows: list[dict[str, Any]] = []
    for model_type, label, drop_base, drop_inter in variants:
        row, _ = _run_risk_variant(
            df,
            risk_config,
            model_type=model_type,
            label=label,
            drop_base=drop_base,
            drop_interactions=drop_inter,
            seed=seed,
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    baseline = out.iloc[0]
    for metric in ['full_sample_diagnosis_auc', 'full_sample_diagnosis_pr_auc', 'full_sample_brier', 'full_sample_log_loss', 'anchor_gap']:
        if metric in out.columns:
            if metric in {'full_sample_diagnosis_auc', 'full_sample_diagnosis_pr_auc', 'anchor_gap'}:
                out[f'delta_vs_full_{metric}'] = out[metric] - float(baseline.get(metric, np.nan))
            else:
                out[f'delta_vs_full_{metric}'] = float(baseline.get(metric, np.nan)) - out[metric]
    return out


def risk_model_significance(df: pd.DataFrame, risk_config: dict[str, Any], seed: int = 20260417, n_boot: int = 400) -> pd.DataFrame:
    y = _safe_binary_label(df)
    if y is None:
        return pd.DataFrame()
    variants = [
        ('anchor_front_logistic', '主模型', (), ()),
        ('legacy_weighted', '旧版手工加权', (), ()),
        ('severity_ridge', '连续严重度 Ridge', (), ()),
        ('anchor_front_logistic', '去体质信息', ('constitution_factor', 'constitution_tanshi'), ('tanshi_x_low_activity', 'tanshi_x_bmi_deviation')),
        ('anchor_front_logistic', '去活动信息', ('activity_factor', 'activity_total', 'activity_risk'), ('tanshi_x_low_activity', 'metabolic_x_low_activity', 'age_x_activity_risk')),
        ('anchor_front_logistic', '去代谢信息', ('metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid'), ('tanshi_x_bmi_deviation', 'metabolic_x_low_activity')),
        ('anchor_front_logistic', '去背景信息', ('age_group', 'background_risk'), ('age_x_activity_risk',)),
    ]
    pred_map: dict[str, np.ndarray] = {}
    for model_type, label, drop_base, drop_inter in variants:
        _, prob = _run_risk_variant(
            df,
            risk_config,
            model_type=model_type,
            label=label,
            drop_base=drop_base,
            drop_interactions=drop_inter,
            seed=seed,
        )
        if prob is not None:
            pred_map[label] = prob
    if '主模型' not in pred_map:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for label, prob in pred_map.items():
        if label == '主模型':
            continue
        for metric in ['roc_auc', 'pr_auc', 'brier_score', 'log_loss']:
            sig = _paired_bootstrap_metric_improvement(y, pred_map['主模型'], prob, metric, n_boot=n_boot, seed=seed)
            rows.append(
                {
                    'baseline_or_ablation': label,
                    'metric': metric,
                    **sig,
                }
            )
    return pd.DataFrame(rows)


def summarize_budget_evidence(pareto_frontier: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if pareto_frontier.empty:
        return pd.DataFrame(), {}
    out = pareto_frontier.sort_values('budget_cap').reset_index(drop=True).copy()
    out['delta_budget'] = out['budget_cap'].diff()
    out['delta_mean_final_tanshi'] = -out['mean_final_tanshi'].diff()
    out['delta_mean_final_latent'] = -out['mean_final_latent'].diff()
    out['tanshi_improvement_per_100_budget'] = np.where(
        out['delta_budget'].fillna(0.0) > 0.0,
        out['delta_mean_final_tanshi'] / (out['delta_budget'] / 100.0),
        np.nan,
    )
    out['latent_improvement_per_100_budget'] = np.where(
        out['delta_budget'].fillna(0.0) > 0.0,
        out['delta_mean_final_latent'] / (out['delta_budget'] / 100.0),
        np.nan,
    )
    tanshi_total_gain = float(out['mean_final_tanshi'].iloc[0] - out['mean_final_tanshi'].iloc[-1])
    latent_total_gain = float(out['mean_final_latent'].iloc[0] - out['mean_final_latent'].iloc[-1])
    marginal = out['delta_mean_final_tanshi'].dropna().to_numpy(dtype=float)
    summary = {
        'budget_levels': [float(x) for x in out['budget_cap'].tolist()],
        'feasible_plan_count_stable': bool(out['feasible_plan_count'].nunique() == 1),
        'tanshi_total_improvement_from_min_budget': tanshi_total_gain,
        'latent_total_improvement_from_min_budget': latent_total_gain,
        'diminishing_returns_on_tanshi': bool(np.all(np.diff(marginal) <= 1e-9)) if len(marginal) >= 2 else None,
    }
    return out, summary


def summarize_primary_plan_feasibility(plans: pd.DataFrame) -> pd.DataFrame:
    if plans.empty or 'status' not in plans.columns:
        return pd.DataFrame()
    work = plans.copy()
    work['is_feasible'] = (work['status'] == 'ok').astype(int)
    group_cols = [c for c in ['risk_tier', 'age_group'] if c in work.columns]
    if not group_cols:
        group_cols = ['status']
    summary = work.groupby(group_cols, as_index=False).agg(
        total_samples=('sample_id', 'count'),
        feasible_count=('is_feasible', 'sum'),
        mean_tanshi=('constitution_tanshi', 'mean'),
        mean_activity_total=('activity_total', 'mean'),
    )
    summary['feasible_share'] = summary['feasible_count'] / summary['total_samples'].clip(lower=1)
    return summary.sort_values(group_cols).reset_index(drop=True)


def _enumerate_heuristic_baselines_for_row(
    row: pd.Series,
    clinical_rules: dict[str, Any],
    intervention_config: dict[str, Any],
    calibration: dict[str, Any] | None,
    budget_cap: float,
) -> dict[str, dict[str, Any]]:
    actions = _build_action_space(row, clinical_rules, intervention_config)
    if not actions:
        return {}
    stage_actions = _build_stage_action_map(actions)
    if sorted(stage_actions.keys()) != [0, 1, 2]:
        return {}
    pair_data, _ = _build_pair_data(actions, stage_actions, max_intensity_jump=int(intervention_config.get('max_intensity_jump', 1)))
    transition_tables = _build_transition_tables(row, actions, clinical_rules, intervention_config, calibration)
    scenarios = list(transition_tables.keys())
    response_profile = build_patient_response_profile(row, calibration)
    tolerance_limit = float(tolerance_capacity(row['activity_total'], int(row['age_group']), intervention_config['tolerance']))
    max_total_burden = max(tolerance_limit * max(len(stage_actions), 1), 1.0)
    cost_coeffs = np.asarray([float(a['cost']) for a in actions], dtype=float)
    burden_coeffs = np.asarray([float(a['burden']) for a in actions], dtype=float)
    edge_penalty = {(int(p['from_idx']), int(p['to_idx'])): float(p['penalty']) for p in pair_data}
    next_adj: dict[int, list[int]] = {}
    for p in pair_data:
        next_adj.setdefault(int(p['from_idx']), []).append(int(p['to_idx']))
    s1 = set(stage_actions[1])
    s2 = set(stage_actions[2])
    latent_start = float(row['latent_state_h'])
    tanshi_start = float(row['constitution_tanshi'])
    nominal_key = 'nominal' if 'nominal' in transition_tables else scenarios[0]
    best_cost: tuple[Any, dict[str, Any]] | None = None
    best_burden: tuple[Any, dict[str, Any]] | None = None

    for i0 in stage_actions[0]:
        for i1 in next_adj.get(i0, []):
            if i1 not in s1:
                continue
            for i2 in next_adj.get(i1, []):
                if i2 not in s2:
                    continue
                selected = [i0, i1, i2]
                total_cost = float(cost_coeffs[selected].sum())
                total_burden = float(burden_coeffs[selected].sum())
                if total_cost > budget_cap + 1e-9 or total_burden > max_total_burden + 1e-9:
                    continue
                if any(float(burden_coeffs[idx]) > tolerance_limit + 1e-9 for idx in selected):
                    continue
                scenario_ok = True
                worst_case_tanshi = -np.inf
                for s in scenarios:
                    gain_lat = float(sum(transition_tables[s][idx][0] for idx in selected))
                    gain_tan = float(sum(transition_tables[s][idx][1] for idx in selected))
                    if gain_lat > latent_start + 1e-9 or gain_tan > tanshi_start + 1e-9:
                        scenario_ok = False
                        break
                    worst_case_tanshi = max(worst_case_tanshi, float(max(0.0, tanshi_start - gain_tan)))
                if not scenario_ok:
                    continue
                nominal_latent_gain = float(sum(transition_tables[nominal_key][idx][0] for idx in selected))
                nominal_tanshi_gain = float(sum(transition_tables[nominal_key][idx][1] for idx in selected))
                smoothness = float(edge_penalty.get((i0, i1), 0.0) + edge_penalty.get((i1, i2), 0.0))
                record = {
                    'sample_id': int(row['sample_id']),
                    'status': 'ok',
                    'final_latent_state': float(max(0.0, latent_start - nominal_latent_gain)),
                    'final_tanshi_score': float(max(0.0, tanshi_start - nominal_tanshi_gain)),
                    'total_cost': total_cost,
                    'total_burden': total_burden,
                    'worst_case_objective': float(worst_case_tanshi),
                    'profile_activity_to_tanshi': float(response_profile['activity_to_tanshi']),
                    'profile_activity_to_latent': float(response_profile['activity_to_latent']),
                    'profile_tanshi_to_latent': float(response_profile['tanshi_to_latent']),
                    'plan': [(int(actions[idx]['tcm_level']), int(actions[idx]['intensity']), int(actions[idx]['frequency'])) for idx in selected],
                    'first_stage_tcm': float(actions[i0]['tcm_level']),
                    'first_stage_intensity': float(actions[i0]['intensity']),
                    'first_stage_frequency': float(actions[i0]['frequency']),
                }
                cost_key = (total_cost, total_burden, worst_case_tanshi)
                burden_key = (total_burden, total_cost, worst_case_tanshi)
                if best_cost is None or cost_key < best_cost[0]:
                    best_cost = (cost_key, record)
                if best_burden is None or burden_key < best_burden[0]:
                    best_burden = (burden_key, record)
    out: dict[str, dict[str, Any]] = {}
    if best_cost is not None:
        out['min_cost_feasible'] = best_cost[1]
    if best_burden is not None:
        out['min_burden_feasible'] = best_burden[1]
    return out


def build_optimization_baseline_comparison(
    df: pd.DataFrame,
    plans: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if plans.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    phlegm = phlegm_intervention_cohort(df)
    if phlegm.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    intervention_cfg = config['intervention']
    budget_cap = float(intervention_cfg.get('pareto_primary_budget', config['clinical_rules']['budget']['six_month_total_max']))
    calibration = fit_transition_calibration(phlegm, intervention_cfg)
    opt = plans.copy()
    opt['arm'] = 'optimized'
    keep_cols = [
        'sample_id', 'arm', 'status', 'final_latent_state', 'final_tanshi_score', 'total_cost', 'total_burden',
        'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi',
    ]
    long_rows = [opt[keep_cols].copy()]
    baseline_rows: list[dict[str, Any]] = []
    for _, row in phlegm.iterrows():
        sample_id = int(row['sample_id'])
        shared = {
            'sample_id': sample_id,
            'risk_tier': row.get('risk_tier'),
            'activity_total': float(row.get('activity_total', np.nan)),
            'age_group': float(row.get('age_group', np.nan)),
            'constitution_tanshi': float(row.get('constitution_tanshi', np.nan)),
        }
        baseline_map = _enumerate_heuristic_baselines_for_row(row, config['clinical_rules'], intervention_cfg, calibration, budget_cap)
        for arm in ['min_cost_feasible', 'min_burden_feasible']:
            if arm in baseline_map:
                baseline_rows.append({**shared, 'arm': arm, **baseline_map[arm]})
            else:
                baseline_rows.append({**shared, 'arm': arm, 'status': 'infeasible'})
    if baseline_rows:
        long_rows.append(pd.DataFrame(baseline_rows))
    long_df = pd.concat(long_rows, ignore_index=True, sort=False)
    summary = long_df.groupby('arm', as_index=False).agg(
        total_samples=('sample_id', 'count'),
        feasible_count=('status', lambda s: int((pd.Series(s) == 'ok').sum())),
        mean_final_tanshi=('final_tanshi_score', 'mean'),
        mean_final_latent=('final_latent_state', 'mean'),
        mean_total_cost=('total_cost', 'mean'),
        mean_total_burden=('total_burden', 'mean'),
    )
    summary['feasible_share'] = summary['feasible_count'] / summary['total_samples'].clip(lower=1)

    sig_rows: list[dict[str, Any]] = []
    optimized = long_df[(long_df['arm'] == 'optimized') & (long_df['status'] == 'ok')].set_index('sample_id')
    for arm in ['min_cost_feasible', 'min_burden_feasible']:
        baseline = long_df[(long_df['arm'] == arm) & (long_df['status'] == 'ok')].set_index('sample_id')
        common = optimized.index.intersection(baseline.index)
        if common.empty:
            continue
        for metric in ['final_tanshi_score', 'final_latent_state', 'total_cost', 'total_burden']:
            diffs = baseline.loc[common, metric].to_numpy(dtype=float) - optimized.loc[common, metric].to_numpy(dtype=float)
            mean_diff, ci_low, ci_high = _paired_mean_difference_ci(diffs)
            try:
                p_value = float(wilcoxon(diffs).pvalue) if np.any(np.abs(diffs) > 1e-12) else 1.0
            except ValueError:
                p_value = 1.0
            sig_rows.append(
                {
                    'baseline_arm': arm,
                    'metric': metric,
                    'n_paired': int(len(common)),
                    'mean_baseline_minus_optimized': mean_diff,
                    'ci_lower': ci_low,
                    'ci_upper': ci_high,
                    'p_value': p_value,
                }
            )
    return long_df, summary, pd.DataFrame(sig_rows)
