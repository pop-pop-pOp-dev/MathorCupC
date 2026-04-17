from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

DEFAULT_BASE_FEATURES = [
    'latent_state_h',
    'lipid_deviation_total',
    'metabolic_deviation_total',
    'activity_risk',
    'constitution_tanshi',
    'background_risk',
]
DEFAULT_INTERACTIONS = {
    'tanshi_x_low_activity': ['constitution_tanshi', 'low_activity_flag'],
    'tanshi_x_bmi_deviation': ['constitution_tanshi', 'dev_bmi'],
    'metabolic_x_low_activity': ['metabolic_deviation_total', 'low_activity_flag'],
    'latent_x_activity_risk': ['latent_state_h', 'activity_risk'],
}
DEFAULT_CANDIDATE_CS = [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 10.0]

PenaltyType = Literal['l1', 'l2']
SolverType = Literal['liblinear', 'lbfgs']
ClassWeightType = Literal['balanced'] | dict[int, float] | None


@dataclass
class RiskModelArtifacts:
    score_frame: pd.DataFrame
    coefficients: pd.DataFrame
    cv_metrics: pd.DataFrame
    calibration: pd.DataFrame
    metadata: dict[str, Any]


def normalize_series(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min() + 1e-9)


def _sigmoid(values: pd.Series | np.ndarray) -> pd.Series:
    arr = np.asarray(values, dtype=float)
    return pd.Series(1.0 / (1.0 + np.exp(-arr)))


def _resolve_risk_section(risk_config: dict) -> dict:
    return risk_config.get('risk_score', risk_config)


def _resolve_threshold_section(risk_config: dict) -> dict:
    return risk_config.get('thresholds', {})


def _build_legacy_risk_score(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    weights = risk_config['risk_score']['weights']
    iweights = risk_config['risk_score']['interaction_weights']
    parts = {
        'score_latent_state': normalize_series(df['latent_state_h']) * weights['latent_state'],
        'score_lipid_deviation_total': normalize_series(df['lipid_deviation_total']) * weights['lipid_deviation_total'],
        'score_metabolic_deviation_total': normalize_series(df['metabolic_deviation_total']) * weights['metabolic_deviation_total'],
        'score_activity_risk': normalize_series(df['activity_risk']) * weights['activity_risk'],
        'score_constitution_tanshi': normalize_series(df['constitution_tanshi']) * weights['constitution_tanshi'],
        'score_background_risk': normalize_series(df['background_risk']) * weights['background_risk'],
        'score_tanshi_x_low_activity': normalize_series(df['tanshi_x_low_activity']) * iweights['tanshi_x_low_activity'],
        'score_tanshi_x_bmi_deviation': normalize_series(df['tanshi_x_bmi_deviation']) * iweights['tanshi_x_bmi_deviation'],
        'score_metabolic_x_low_activity': normalize_series(df['metabolic_x_low_activity']) * iweights['metabolic_x_low_activity'],
    }
    out = pd.DataFrame(parts, index=df.index)
    raw_score = out.sum(axis=1)
    out['continuous_risk_score'] = normalize_series(raw_score) * 100
    out['risk_logit'] = normalize_series(raw_score) * 6 - 3
    out['risk_prob'] = normalize_series(raw_score)
    return out


def build_severity_target(df: pd.DataFrame, risk_config: dict) -> pd.Series:
    """连续临床严重度目标：不依赖二分类确诊标签，用于结构风险回归。"""
    risk_section = _resolve_risk_section(risk_config)
    sm = risk_section.get('severity_model', {}) if isinstance(risk_section.get('severity_model'), dict) else {}
    tw = sm.get(
        'target_weights',
        {'lipid_deviation_total': 0.45, 'metabolic_deviation_total': 0.35, 'activity_risk': 0.20},
    )
    terms: list[pd.Series] = []
    for col, w in tw.items():
        if col not in df.columns or float(w) == 0.0:
            continue
        terms.append(normalize_series(pd.to_numeric(df[col], errors='coerce').fillna(0.0)) * float(w))
    if not terms:
        return pd.Series(0.0, index=df.index, dtype=float)
    return pd.concat(terms, axis=1).sum(axis=1).rename('severity_target')


def _build_severity_calibration_table(y_true: pd.Series, y_pred: pd.Series, bins: int = 10) -> pd.DataFrame:
    y_true = pd.to_numeric(y_true, errors='coerce').fillna(0.0).reset_index(drop=True)
    y_pred = pd.to_numeric(y_pred, errors='coerce').fillna(0.0).reset_index(drop=True)
    frame = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    rank = frame['y_pred'].rank(method='first', pct=True)
    bin_id = np.minimum((rank * bins).astype(int), bins - 1)
    frame['bin_id'] = bin_id
    grouped = frame.groupby('bin_id', as_index=False).agg(
        sample_count=('y_true', 'size'),
        predicted_mean=('y_pred', 'mean'),
        observed_mean=('y_true', 'mean'),
    )
    grouped['calibration_gap'] = grouped['predicted_mean'] - grouped['observed_mean']
    return grouped


def fit_severity_ridge_model(df: pd.DataFrame, risk_config: dict, seed: int = 20260417) -> RiskModelArtifacts:
    risk_section = _resolve_risk_section(risk_config)
    sm = risk_section.get('severity_model', {}) if isinstance(risk_section.get('severity_model'), dict) else {}
    y = build_severity_target(df, risk_config)
    x = build_risk_feature_matrix(df, risk_config)
    exclude = list(sm.get('exclude_from_x', ['lipid_deviation_total', 'metabolic_deviation_total']))
    for col in exclude:
        if col in x.columns:
            x = x.drop(columns=[col])
    if x.empty:
        legacy_score = _build_legacy_risk_score(df, risk_config)
        return RiskModelArtifacts(
            score_frame=legacy_score,
            coefficients=pd.DataFrame(columns=['feature', 'coefficient', 'odds_ratio', 'abs_standardized_weight']),
            cv_metrics=pd.DataFrame(columns=['metric', 'value']),
            calibration=pd.DataFrame(columns=['bin_id', 'sample_count', 'predicted_mean', 'observed_rate', 'calibration_gap']),
            metadata={'model_type': 'severity_ridge_fallback'},
        )

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    x_frame = pd.DataFrame(x_scaled, columns=x.columns, index=df.index)

    alphas = sm.get('alphas')
    if alphas is None:
        alpha_list = [10**k for k in range(-2, 4)]
    else:
        alpha_list = [float(a) for a in alphas]

    cv_folds = int(min(max(2, int(sm.get('cv_folds', 5))), len(df)))
    cv = KFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    ridge = RidgeCV(alphas=alpha_list, cv=cv)
    ridge.fit(x_scaled, y.to_numpy(dtype=float))
    pred = ridge.predict(x_scaled)
    pred_series = pd.Series(pred, index=df.index, name='severity_pred')

    cv_r2: list[float] = []
    cv_mae: list[float] = []
    for train_idx, test_idx in cv.split(x_scaled):
        rs = RidgeCV(alphas=alpha_list, cv=KFold(3, shuffle=True, random_state=seed))
        rs.fit(x_scaled[train_idx], y.iloc[train_idx].to_numpy(dtype=float))
        pt = rs.predict(x_scaled[test_idx])
        yt = y.iloc[test_idx].to_numpy(dtype=float)
        cv_r2.append(float(r2_score(yt, pt)))
        cv_mae.append(float(mean_absolute_error(yt, pt)))
    cv_metrics = pd.DataFrame(
        [
            {'metric': 'cv_r2_mean', 'value': float(np.mean(cv_r2))},
            {'metric': 'cv_mae_mean', 'value': float(np.mean(cv_mae))},
            {'metric': 'train_r2', 'value': float(r2_score(y.to_numpy(dtype=float), pred))},
        ]
    )
    calibration_bins = int(risk_section.get('calibration_bins', 10))
    calibration = _build_severity_calibration_table(y, pred_series, bins=calibration_bins)
    calibration = calibration.rename(columns={'observed_mean': 'observed_rate'})

    coef = pd.Series(ridge.coef_, index=x.columns)
    abs_weights = coef.abs()
    weight_sum = float(abs_weights.sum()) + 1e-12
    coefficients = pd.DataFrame(
        {
            'feature': list(coef.index),
            'coefficient': coef.to_numpy(dtype=float),
            'odds_ratio': np.nan,
            'abs_standardized_weight': abs_weights.to_numpy(dtype=float) / weight_sum,
            'direction': np.where(coef.to_numpy(dtype=float) >= 0.0, 'severity_up', 'severity_down'),
            'feature_mean': np.asarray(scaler.mean_, dtype=float),
            'feature_scale': np.asarray(scaler.scale_, dtype=float),
        }
    ).sort_values('abs_standardized_weight', ascending=False).reset_index(drop=True)

    risk_prob = normalize_series(pred_series)
    continuous = risk_prob * 100.0
    score_frame = x_frame.mul(coef, axis=1).rename(columns=lambda c: f'score_{c}')
    score_frame['risk_logit'] = pred_series
    score_frame['risk_prob'] = risk_prob
    score_frame['continuous_risk_score'] = continuous

    metadata: dict[str, Any] = {
        'model_type': 'severity_ridge',
        'alpha': float(ridge.alpha_),
        'cv_folds': cv_folds,
        'n_features': int(x.shape[1]),
        'severity_target_weights': sm.get('target_weights', {}),
    }
    if 'hyperlipidemia_label' in df.columns:
        try:
            y_bin = pd.to_numeric(df['hyperlipidemia_label'], errors='coerce').fillna(0).astype(int)
            if y_bin.nunique() > 1:
                metadata['external_diagnosis_auc'] = float(roc_auc_score(y_bin, pred_series))
        except Exception:
            metadata['external_diagnosis_auc'] = None

    return RiskModelArtifacts(
        score_frame=score_frame,
        coefficients=coefficients,
        cv_metrics=cv_metrics,
        calibration=calibration,
        metadata=metadata,
    )


def _coerce_interaction_spec(interactions: Any) -> dict[str, list[str]]:
    if isinstance(interactions, dict):
        return {str(name): [str(x) for x in terms] for name, terms in interactions.items()}
    if isinstance(interactions, list):
        out: dict[str, list[str]] = {}
        for item in interactions:
            if isinstance(item, dict) and 'name' in item and 'terms' in item:
                out[str(item['name'])] = [str(x) for x in item['terms']]
        return out
    return {}


def _resolve_penalty_and_solver(value: Any) -> tuple[PenaltyType, SolverType]:
    penalty_raw = str(value).lower()
    if penalty_raw == 'l2':
        return 'l2', 'lbfgs'
    return 'l1', 'liblinear'


def _coerce_class_weight(value: Any) -> ClassWeightType:
    if value is None:
        return None
    if isinstance(value, str):
        return 'balanced' if value == 'balanced' else None
    if isinstance(value, dict):
        return {int(k): float(v) for k, v in value.items()}
    return 'balanced'


def build_risk_feature_matrix(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    risk_section = _resolve_risk_section(risk_config)
    feature_cfg = risk_section.get('features', {})
    base_features = feature_cfg.get('base', DEFAULT_BASE_FEATURES)
    interaction_spec = _coerce_interaction_spec(feature_cfg.get('interactions', DEFAULT_INTERACTIONS))
    out = pd.DataFrame(index=df.index)
    for feature in base_features:
        if feature in df.columns:
            out[str(feature)] = pd.to_numeric(df[feature], errors='coerce').fillna(0.0)
    for name, terms in interaction_spec.items():
        if name in df.columns:
            out[name] = pd.to_numeric(df[name], errors='coerce').fillna(0.0)
            continue
        if len(terms) != 2 or any(term not in df.columns for term in terms):
            continue
        out[name] = pd.to_numeric(df[terms[0]], errors='coerce').fillna(0.0) * pd.to_numeric(df[terms[1]], errors='coerce').fillna(0.0)
    return out


def _build_cv_predictions(
    x: pd.DataFrame,
    y: pd.Series,
    penalty: PenaltyType,
    solver: SolverType,
    class_weight: ClassWeightType,
    best_c: float,
    max_iter: int,
    cv_folds: int,
    seed: int,
) -> np.ndarray:
    splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    preds = np.zeros(len(x), dtype=float)
    for train_idx, test_idx in splitter.split(x, y):
        scaler = StandardScaler().fit(x.iloc[train_idx])
        x_train = scaler.transform(x.iloc[train_idx])
        x_test = scaler.transform(x.iloc[test_idx])
        model = LogisticRegression(
            penalty=penalty,
            C=best_c,
            solver=solver,
            class_weight=class_weight,
            max_iter=max_iter,
            random_state=seed,
        )
        model.fit(x_train, y.iloc[train_idx])
        preds[test_idx] = model.predict_proba(x_test)[:, 1]
    return preds


def _build_cv_metrics(y_true: pd.Series, y_prob: np.ndarray) -> pd.DataFrame:
    y_true = y_true.astype(int)
    records = [
        {'metric': 'roc_auc', 'value': float(roc_auc_score(y_true, y_prob))},
        {'metric': 'pr_auc', 'value': float(average_precision_score(y_true, y_prob))},
        {'metric': 'brier_score', 'value': float(brier_score_loss(y_true, y_prob))},
    ]
    clipped = np.clip(y_prob, 1e-6, 1 - 1e-6)
    records.append({'metric': 'log_loss', 'value': float(log_loss(y_true, clipped))})
    return pd.DataFrame(records)


def _build_calibration_table(y_true: pd.Series, y_prob: np.ndarray, bins: int = 10) -> pd.DataFrame:
    y_true = y_true.astype(int).reset_index(drop=True)
    frame = pd.DataFrame({'y_true': y_true, 'y_prob': np.clip(y_prob, 1e-6, 1 - 1e-6)})
    rank = frame['y_prob'].rank(method='first', pct=True)
    bin_id = np.minimum((rank * bins).astype(int), bins - 1)
    frame['bin_id'] = bin_id
    grouped = frame.groupby('bin_id', as_index=False).agg(
        sample_count=('y_true', 'size'),
        predicted_mean=('y_prob', 'mean'),
        observed_rate=('y_true', 'mean'),
    )
    grouped['calibration_gap'] = grouped['predicted_mean'] - grouped['observed_rate']
    return grouped


def _select_best_c(
    x: pd.DataFrame,
    y: pd.Series,
    penalty: PenaltyType,
    solver: SolverType,
    class_weight: ClassWeightType,
    candidate_cs: list[float],
    max_iter: int,
    cv_folds: int,
    seed: int,
    scoring: str,
) -> float:
    splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    best_c = candidate_cs[0]
    best_score = -np.inf
    for candidate_c in candidate_cs:
        fold_scores: list[float] = []
        for train_idx, test_idx in splitter.split(x, y):
            scaler = StandardScaler().fit(x.iloc[train_idx])
            x_train = scaler.transform(x.iloc[train_idx])
            x_test = scaler.transform(x.iloc[test_idx])
            model = LogisticRegression(
                penalty=penalty,
                C=float(candidate_c),
                solver=solver,
                class_weight=class_weight,
                max_iter=max_iter,
                random_state=seed,
            )
            model.fit(x_train, y.iloc[train_idx])
            y_prob = model.predict_proba(x_test)[:, 1]
            if scoring == 'roc_auc':
                fold_scores.append(float(roc_auc_score(y.iloc[test_idx], y_prob)))
            elif scoring == 'average_precision':
                fold_scores.append(float(average_precision_score(y.iloc[test_idx], y_prob)))
            else:
                fold_scores.append(-float(log_loss(y.iloc[test_idx], np.clip(y_prob, 1e-6, 1 - 1e-6))))
        mean_score = float(np.mean(fold_scores)) if fold_scores else -np.inf
        if mean_score > best_score:
            best_score = mean_score
            best_c = float(candidate_c)
    return float(best_c)


def fit_risk_model(df: pd.DataFrame, risk_config: dict, seed: int = 20260417) -> RiskModelArtifacts:
    risk_section = _resolve_risk_section(risk_config)
    model_type = str(risk_section.get('model_type', 'severity_ridge')).lower()

    if model_type in {'legacy', 'legacy_weighted'}:
        legacy_score = _build_legacy_risk_score(df, {'risk_score': risk_section} if 'weights' in risk_section else risk_config)
        return RiskModelArtifacts(
            score_frame=legacy_score,
            coefficients=pd.DataFrame(columns=['feature', 'coefficient', 'odds_ratio', 'abs_standardized_weight']),
            cv_metrics=pd.DataFrame(columns=['metric', 'value']),
            calibration=pd.DataFrame(columns=['bin_id', 'sample_count', 'predicted_mean', 'observed_rate', 'calibration_gap']),
            metadata={'model_type': 'legacy_weighted'},
        )

    if model_type in {'severity_ridge', 'ridge_severity', 'continuous_ridge'}:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    if 'hyperlipidemia_label' not in df.columns:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    x = build_risk_feature_matrix(df, risk_config)
    y = pd.to_numeric(df['hyperlipidemia_label'], errors='coerce').fillna(0).astype(int)
    if x.empty or y.nunique() < 2 or y.value_counts().min() < 2:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    penalty, solver = _resolve_penalty_and_solver(risk_section.get('penalty', 'l1'))
    candidate_cs = [float(x) for x in risk_section.get('candidate_cs', DEFAULT_CANDIDATE_CS)]
    max_iter = int(risk_section.get('max_iter', 5000))
    cv_folds = int(min(max(2, risk_section.get('cv_folds', 5)), y.value_counts().min()))
    class_weight = _coerce_class_weight(risk_section.get('class_weight', 'balanced'))
    scoring = str(risk_section.get('scoring', 'neg_log_loss'))
    calibration_bins = int(risk_section.get('calibration_bins', 10))

    best_c = _select_best_c(x, y, penalty, solver, class_weight, candidate_cs, max_iter, cv_folds, seed, scoring)
    scaler = StandardScaler().fit(x)
    x_scaled = scaler.transform(x)

    final_model = LogisticRegression(
        penalty=penalty,
        C=best_c,
        solver=solver,
        class_weight=class_weight,
        max_iter=max_iter,
        random_state=seed,
    )
    final_model.fit(x_scaled, y)

    cv_pred = _build_cv_predictions(x, y, penalty, solver, class_weight, best_c, max_iter, cv_folds, seed)
    cv_metrics = _build_cv_metrics(y, cv_pred)
    calibration = _build_calibration_table(y, cv_pred, bins=calibration_bins)

    standardized = pd.DataFrame(x_scaled, columns=x.columns, index=df.index)
    coef = pd.Series(final_model.coef_[0], index=x.columns)
    score_frame = standardized.mul(coef, axis=1).rename(columns=lambda col: f'score_{col}')
    risk_logit = float(final_model.intercept_[0]) + score_frame.sum(axis=1)
    risk_prob = _sigmoid(risk_logit).set_axis(df.index)
    score_frame['risk_logit'] = risk_logit
    score_frame['risk_prob'] = risk_prob
    score_frame['continuous_risk_score'] = risk_prob * 100

    abs_weights = coef.abs()
    weight_sum = float(abs_weights.sum()) + 1e-12
    coef_values = np.asarray(coef.to_numpy(dtype=float), dtype=float)
    abs_weight_values = np.asarray(abs_weights.to_numpy(dtype=float), dtype=float)
    coefficients = pd.DataFrame(
        {
            'feature': list(coef.index),
            'coefficient': coef_values,
            'odds_ratio': np.exp(coef_values),
            'abs_standardized_weight': abs_weight_values / weight_sum,
            'direction': np.where(coef_values >= 0.0, 'risk_up', 'risk_down'),
            'feature_mean': np.asarray(scaler.mean_, dtype=float),
            'feature_scale': np.asarray(scaler.scale_, dtype=float),
        }
    ).sort_values('abs_standardized_weight', ascending=False).reset_index(drop=True)

    metadata = {
        'model_type': 'logistic_regression',
        'penalty': penalty,
        'best_c': best_c,
        'cv_folds': cv_folds,
        'class_weight': class_weight,
        'n_features': int(x.shape[1]),
    }
    return RiskModelArtifacts(
        score_frame=score_frame,
        coefficients=coefficients,
        cv_metrics=cv_metrics,
        calibration=calibration,
        metadata=metadata,
    )


def build_continuous_risk_score(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    risk_section = _resolve_risk_section(risk_config)
    if str(risk_section.get('model_type', '')).lower() in {'legacy', 'legacy_weighted'}:
        return _build_legacy_risk_score(df, {'risk_score': risk_section})
    return fit_risk_model(df, risk_config).score_frame


def build_reference_severity(df: pd.DataFrame, risk_config: dict) -> pd.Series:
    threshold_cfg = _resolve_threshold_section(risk_config)
    severity_cfg = threshold_cfg.get('severity_features', {})
    if isinstance(severity_cfg, dict) and severity_cfg:
        weights = {str(k): float(v) for k, v in severity_cfg.items()}
    else:
        weights = {
            'lipid_deviation_total': 0.40,
            'metabolic_deviation_total': 0.25,
            'latent_state_h': 0.20,
            'constitution_tanshi': 0.15,
        }
    available = [(name, weight) for name, weight in weights.items() if name in df.columns]
    if not available:
        fallback = normalize_series(df['continuous_risk_score']) if 'continuous_risk_score' in df.columns else pd.Series(0.0, index=df.index, dtype=float)
        return pd.Series(fallback, index=df.index, name='reference_severity', dtype=float)
    pieces = [normalize_series(pd.to_numeric(df[name], errors='coerce').fillna(0.0)) * weight for name, weight in available]
    total_weight = sum(weight for _, weight in available) + 1e-9
    combined_values = np.zeros(len(df), dtype=float)
    for piece in pieces:
        combined_values += np.asarray(piece.to_numpy(dtype=float), dtype=float)
    combined = pd.Series(combined_values / total_weight, index=df.index, name='reference_severity', dtype=float)
    return combined


def build_anchor_flags(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    """锚定子群：用分位与 OR/命中数构造，避免与二分类标签强绑定导致样本为空。"""
    anchors = risk_config.get('anchors', {})
    idx = df.index
    low_hits = pd.Series(0, index=idx, dtype=int)
    high_hits = pd.Series(0, index=idx, dtype=int)

    if 'lipid_deviation_total' in df.columns:
        low_lipid = df['lipid_deviation_total'] <= df['lipid_deviation_total'].quantile(float(anchors.get('low_lipid_quantile', 0.30)))
        high_lipid = df['lipid_deviation_total'] >= df['lipid_deviation_total'].quantile(float(anchors.get('high_lipid_quantile', 0.75)))
        low_hits += low_lipid.astype(int)
        high_hits += high_lipid.astype(int)
    if 'metabolic_deviation_total' in df.columns:
        low_meta = df['metabolic_deviation_total'] <= df['metabolic_deviation_total'].quantile(float(anchors.get('low_metabolic_quantile', 0.35)))
        high_meta = df['metabolic_deviation_total'] >= df['metabolic_deviation_total'].quantile(float(anchors.get('high_metabolic_quantile', 0.70)))
        low_hits += low_meta.astype(int)
        high_hits += high_meta.astype(int)
    if 'activity_total' in df.columns:
        low_act = df['activity_total'] >= float(anchors.get('adequate_activity_cutoff', 60))
        high_act = df['activity_total'] <= float(anchors.get('low_activity_cutoff', 40))
        low_hits += low_act.astype(int)
        high_hits += high_act.astype(int)
    if 'latent_state_h' in df.columns:
        low_lat = df['latent_state_h'] <= df['latent_state_h'].quantile(float(anchors.get('low_latent_quantile', 0.40)))
        high_lat = df['latent_state_h'] >= df['latent_state_h'].quantile(float(anchors.get('high_latent_quantile', 0.65)))
        low_hits += low_lat.astype(int)
        high_hits += high_lat.astype(int)
    if 'constitution_tanshi' in df.columns:
        high_tan = df['constitution_tanshi'] >= float(anchors.get('high_tanshi_absolute', 60))
        high_hits += high_tan.astype(int)

    low_need = int(anchors.get('low_profile_min_hits', 3))
    high_need = int(anchors.get('high_profile_min_hits', 2))
    low_anchor = (low_hits >= low_need).astype(int)
    high_anchor = (high_hits >= high_need).astype(int)

    if bool(anchors.get('high_anchor_phlegm_only', False)) and 'phlegm_dampness_label_flag' in df.columns:
        high_anchor = (high_anchor & (df['phlegm_dampness_label_flag'] == 1)).astype(int)

    return pd.DataFrame({'low_anchor': low_anchor, 'high_anchor': high_anchor})
