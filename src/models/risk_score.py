from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler

DEFAULT_BASE_FEATURES = [
    'constitution_factor',
    'activity_factor',
    'metabolic_deviation_total',
    'activity_total',
    'activity_risk',
    'constitution_tanshi',
    'dev_bmi',
    'dev_fasting_glucose',
    'dev_uric_acid',
    'age_group',
    'background_risk',
]
DEFAULT_INTERACTIONS = {
    'tanshi_x_low_activity': ['constitution_tanshi', 'low_activity_flag'],
    'tanshi_x_bmi_deviation': ['constitution_tanshi', 'dev_bmi'],
    'metabolic_x_low_activity': ['metabolic_deviation_total', 'low_activity_flag'],
    'age_x_activity_risk': ['age_group', 'activity_risk'],
}
DEFAULT_CANDIDATE_CS = [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 10.0]
FORBIDDEN_DIAGNOSTIC_FEATURES = {
    'tc',
    'tg',
    'ldl_c',
    'hdl_c',
    'dev_tc',
    'dev_tg',
    'dev_ldl_c',
    'dev_hdl_c',
    'lipid_deviation_total',
    'hyperlipidemia_label',
    'hyperlipidemia_type_label',
    'latent_state_h',
    'metabolic_factor',
}

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


def _logit_clip(values: pd.Series | np.ndarray) -> np.ndarray:
    arr = np.clip(np.asarray(values, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(arr / (1.0 - arr))


def _resolve_risk_section(risk_config: dict) -> dict:
    return risk_config.get('risk_score', risk_config)


def _resolve_threshold_section(risk_config: dict) -> dict:
    return risk_config.get('thresholds', {})


def _drop_forbidden_diagnostic_features(x: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        col for col in x.columns
        if col not in FORBIDDEN_DIAGNOSTIC_FEATURES and not col.startswith(('score_tc', 'score_tg', 'score_ldl', 'score_hdl'))
    ]
    return x.loc[:, keep_cols].copy()


def build_diagnosis_anchor_flags(df: pd.DataFrame) -> pd.DataFrame:
    if 'hyperlipidemia_label' in df.columns:
        high_anchor = pd.to_numeric(df['hyperlipidemia_label'], errors='coerce').fillna(0).astype(int) == 1
    elif 'lipid_deviation_total' in df.columns:
        high_anchor = pd.to_numeric(df['lipid_deviation_total'], errors='coerce').fillna(0.0) > 0.0
    else:
        lipid_parts = [
            pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            for col in ['dev_tc', 'dev_tg', 'dev_ldl_c', 'dev_hdl_c']
            if col in df.columns
        ]
        high_anchor = pd.concat(lipid_parts, axis=1).sum(axis=1) > 0.0 if lipid_parts else pd.Series(False, index=df.index)
    if 'lipid_deviation_total' in df.columns:
        low_anchor = pd.to_numeric(df['lipid_deviation_total'], errors='coerce').fillna(0.0) <= 1e-9
    else:
        lipid_parts = [
            pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            for col in ['dev_tc', 'dev_tg', 'dev_ldl_c', 'dev_hdl_c']
            if col in df.columns
        ]
        low_anchor = pd.concat(lipid_parts, axis=1).sum(axis=1) <= 1e-9 if lipid_parts else pd.Series(False, index=df.index)
    if 'hyperlipidemia_label' in df.columns:
        low_anchor &= pd.to_numeric(df['hyperlipidemia_label'], errors='coerce').fillna(0).astype(int) == 0
    return pd.DataFrame(
        {
            'low_anchor': low_anchor.astype(int),
            'high_anchor': high_anchor.astype(int),
        },
        index=df.index,
    )


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
    x = _drop_forbidden_diagnostic_features(build_risk_feature_matrix(df, risk_config))
    exclude = list(sm.get('exclude_from_x', ['metabolic_deviation_total']))
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


def fit_anchor_front_model(df: pd.DataFrame, risk_config: dict, seed: int = 20260417) -> RiskModelArtifacts:
    risk_section = _resolve_risk_section(risk_config)
    x = _drop_forbidden_diagnostic_features(build_risk_feature_matrix(df, risk_config))
    anchors = build_diagnosis_anchor_flags(df)
    train_mask = (anchors['low_anchor'] == 1) | (anchors['high_anchor'] == 1)
    y = (anchors.loc[train_mask, 'high_anchor'] == 1).astype(int)
    x_train_full = x.loc[train_mask].copy()
    if x_train_full.empty or y.nunique() < 2 or y.value_counts().min() < 2:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    penalty, solver = _resolve_penalty_and_solver(risk_section.get('penalty', 'l2'))
    candidate_cs = [float(v) for v in risk_section.get('candidate_cs', DEFAULT_CANDIDATE_CS)]
    max_iter = int(risk_section.get('max_iter', 5000))
    cv_folds = int(min(max(2, risk_section.get('cv_folds', 5)), y.value_counts().min()))
    class_weight = _coerce_class_weight(risk_section.get('class_weight', 'balanced'))
    scoring = str(risk_section.get('scoring', 'roc_auc'))
    calibration_bins = int(risk_section.get('calibration_bins', 10))
    calibration_method = str(risk_section.get('probability_calibration', 'auto')).lower()
    calibration_selection_metric = str(risk_section.get('calibration_selection_metric', 'brier_score')).lower()

    best_c = _select_best_c(x_train_full, y, penalty, solver, class_weight, candidate_cs, max_iter, cv_folds, seed, scoring)
    scaler = StandardScaler().fit(x_train_full)
    x_train_scaled = scaler.transform(x_train_full)
    x_all_scaled = scaler.transform(x)
    model = _make_logistic_model(penalty, solver, best_c, class_weight, max_iter, seed)
    model.fit(x_train_scaled, y)

    cv_pred_raw, cv_logit_raw = _build_cv_raw_predictions(x_train_full, y, penalty, solver, class_weight, best_c, max_iter, cv_folds, seed)
    chosen_calibration, calibrator, cv_pred = _select_probability_calibration(
        y,
        cv_pred_raw,
        cv_logit_raw,
        seed,
        calibration_method,
        calibration_selection_metric,
    )
    cv_metrics = _build_cv_metrics(y, cv_pred)
    calibration = _build_calibration_table(y, cv_pred, bins=calibration_bins)

    standardized = pd.DataFrame(x_all_scaled, columns=x.columns, index=df.index)
    coef = pd.Series(model.coef_[0], index=x.columns)
    score_frame = standardized.mul(coef, axis=1).rename(columns=lambda col: f'score_{col}')
    risk_logit = float(model.intercept_[0]) + score_frame.sum(axis=1)
    raw_prob_all = _sigmoid(risk_logit).set_axis(df.index)
    raw_prob_train = _sigmoid(float(model.intercept_[0]) + standardized.loc[train_mask].mul(coef, axis=1).sum(axis=1)).set_axis(y.index)
    if chosen_calibration == 'sigmoid':
        final_calibrator = _fit_sigmoid_calibrator(_logit_clip(raw_prob_train), y, seed)
    elif chosen_calibration == 'isotonic':
        final_calibrator = _fit_isotonic_calibrator(np.asarray(raw_prob_train, dtype=float), y)
    else:
        final_calibrator = None
    risk_prob = pd.Series(
        _apply_calibrator(chosen_calibration, np.asarray(raw_prob_all, dtype=float), _logit_clip(raw_prob_all), final_calibrator),
        index=df.index,
    )
    score_frame['risk_logit'] = risk_logit
    score_frame['risk_prob'] = risk_prob
    score_frame['continuous_risk_score'] = risk_prob * 100

    abs_weights = coef.abs()
    weight_sum = float(abs_weights.sum()) + 1e-12
    coefficients = pd.DataFrame(
        {
            'feature': list(coef.index),
            'coefficient': coef.to_numpy(dtype=float),
            'odds_ratio': np.exp(coef.to_numpy(dtype=float)),
            'abs_standardized_weight': abs_weights.to_numpy(dtype=float) / weight_sum,
            'direction': np.where(coef.to_numpy(dtype=float) >= 0.0, 'risk_up', 'risk_down'),
            'feature_mean': np.asarray(scaler.mean_, dtype=float),
            'feature_scale': np.asarray(scaler.scale_, dtype=float),
        }
    ).sort_values('abs_standardized_weight', ascending=False).reset_index(drop=True)

    metadata = {
        'model_type': 'anchor_front_logistic',
        'penalty': penalty,
        'best_c': best_c,
        'cv_folds': cv_folds,
        'class_weight': class_weight,
        'n_features': int(x.shape[1]),
        'train_anchor_count': int(train_mask.sum()),
        'high_anchor_count': int(anchors['high_anchor'].sum()),
        'low_anchor_count': int(anchors['low_anchor'].sum()),
        'probability_calibration': chosen_calibration,
        'calibration_selection_metric': calibration_selection_metric,
    }
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


def _make_logistic_model(
    penalty: PenaltyType,
    solver: SolverType,
    c_value: float,
    class_weight: ClassWeightType,
    max_iter: int,
    seed: int,
) -> LogisticRegression:
    kwargs: dict[str, Any] = {
        'C': c_value,
        'solver': solver,
        'class_weight': class_weight,
        'max_iter': max_iter,
        'random_state': seed,
    }
    if penalty != 'l2':
        kwargs['penalty'] = penalty
    return LogisticRegression(**kwargs)


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
        if feature in df.columns and feature not in FORBIDDEN_DIAGNOSTIC_FEATURES:
            out[str(feature)] = pd.to_numeric(df[feature], errors='coerce').fillna(0.0)
    for name, terms in interaction_spec.items():
        if name in FORBIDDEN_DIAGNOSTIC_FEATURES or any(term in FORBIDDEN_DIAGNOSTIC_FEATURES for term in terms):
            continue
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
        model = _make_logistic_model(penalty, solver, best_c, class_weight, max_iter, seed)
        model.fit(x_train, y.iloc[train_idx])
        preds[test_idx] = model.predict_proba(x_test)[:, 1]
    return preds


def _build_cv_raw_predictions(
    x: pd.DataFrame,
    y: pd.Series,
    penalty: PenaltyType,
    solver: SolverType,
    class_weight: ClassWeightType,
    best_c: float,
    max_iter: int,
    cv_folds: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    probs = np.zeros(len(x), dtype=float)
    logits = np.zeros(len(x), dtype=float)
    for train_idx, test_idx in splitter.split(x, y):
        scaler = StandardScaler().fit(x.iloc[train_idx])
        x_train = scaler.transform(x.iloc[train_idx])
        x_test = scaler.transform(x.iloc[test_idx])
        model = _make_logistic_model(penalty, solver, best_c, class_weight, max_iter, seed)
        model.fit(x_train, y.iloc[train_idx])
        fold_prob = model.predict_proba(x_test)[:, 1]
        probs[test_idx] = fold_prob
        logits[test_idx] = _logit_clip(fold_prob)
    return probs, logits


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


def _fit_sigmoid_calibrator(raw_logits: np.ndarray, y_true: pd.Series, seed: int) -> LogisticRegression:
    calibrator = LogisticRegression(C=1e6, solver='lbfgs', max_iter=5000, random_state=seed)
    calibrator.fit(raw_logits.reshape(-1, 1), y_true.astype(int).to_numpy(dtype=int))
    return calibrator


def _fit_isotonic_calibrator(raw_probs: np.ndarray, y_true: pd.Series) -> IsotonicRegression:
    calibrator = IsotonicRegression(out_of_bounds='clip')
    calibrator.fit(np.asarray(raw_probs, dtype=float), y_true.astype(int).to_numpy(dtype=int))
    return calibrator


def _apply_calibrator(
    method: str,
    raw_probs: np.ndarray,
    raw_logits: np.ndarray,
    calibrator: Any | None,
) -> np.ndarray:
    if method == 'sigmoid' and calibrator is not None:
        return calibrator.predict_proba(np.asarray(raw_logits, dtype=float).reshape(-1, 1))[:, 1]
    if method == 'isotonic' and calibrator is not None:
        return np.asarray(calibrator.predict(np.asarray(raw_probs, dtype=float)), dtype=float)
    return np.asarray(raw_probs, dtype=float)


def _select_probability_calibration(
    y_true: pd.Series,
    raw_probs: np.ndarray,
    raw_logits: np.ndarray,
    seed: int,
    method_pref: str,
    metric: str,
) -> tuple[str, Any | None, np.ndarray]:
    method_pref = str(method_pref).lower()
    metric = str(metric).lower()
    candidates: list[tuple[str, Any | None, np.ndarray]] = [('none', None, np.asarray(raw_probs, dtype=float))]
    if method_pref in {'auto', 'sigmoid'}:
        sigmoid_cal = _fit_sigmoid_calibrator(raw_logits, y_true, seed)
        sigmoid_pred = _apply_calibrator('sigmoid', raw_probs, raw_logits, sigmoid_cal)
        candidates.append(('sigmoid', sigmoid_cal, sigmoid_pred))
    if method_pref in {'auto', 'isotonic'}:
        isotonic_cal = _fit_isotonic_calibrator(raw_probs, y_true)
        isotonic_pred = _apply_calibrator('isotonic', raw_probs, raw_logits, isotonic_cal)
        candidates.append(('isotonic', isotonic_cal, isotonic_pred))

    def _score(pred: np.ndarray) -> float:
        clipped = np.clip(np.asarray(pred, dtype=float), 1e-6, 1 - 1e-6)
        if metric == 'log_loss':
            return float(log_loss(y_true.astype(int), clipped))
        return float(brier_score_loss(y_true.astype(int), clipped))

    best_method, best_calibrator, best_pred = candidates[0]
    best_score = _score(best_pred)
    for method_name, calibrator, pred in candidates[1:]:
        score = _score(pred)
        if score < best_score - 1e-12:
            best_method, best_calibrator, best_pred, best_score = method_name, calibrator, pred, score
    return best_method, best_calibrator, np.asarray(best_pred, dtype=float)


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
            model = _make_logistic_model(penalty, solver, float(candidate_c), class_weight, max_iter, seed)
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
    model_type = str(risk_section.get('model_type', 'anchor_front_logistic')).lower()

    if model_type in {'legacy', 'legacy_weighted'}:
        legacy_score = _build_legacy_risk_score(df, {'risk_score': risk_section} if 'weights' in risk_section else risk_config)
        return RiskModelArtifacts(
            score_frame=legacy_score,
            coefficients=pd.DataFrame(columns=['feature', 'coefficient', 'odds_ratio', 'abs_standardized_weight']),
            cv_metrics=pd.DataFrame(columns=['metric', 'value']),
            calibration=pd.DataFrame(columns=['bin_id', 'sample_count', 'predicted_mean', 'observed_rate', 'calibration_gap']),
            metadata={'model_type': 'legacy_weighted'},
        )

    if model_type in {'anchor_front_logistic', 'front_anchor_logit', 'prediagnostic_anchor_logit'}:
        return fit_anchor_front_model(df, risk_config, seed=seed)

    if model_type in {'severity_ridge', 'ridge_severity', 'continuous_ridge'}:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    if 'hyperlipidemia_label' not in df.columns:
        return fit_severity_ridge_model(df, risk_config, seed=seed)

    x = _drop_forbidden_diagnostic_features(build_risk_feature_matrix(df, risk_config))
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

    final_model = _make_logistic_model(penalty, solver, best_c, class_weight, max_iter, seed)
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
            'constitution_factor': 0.25,
            'activity_factor': 0.25,
            'metabolic_deviation_total': 0.20,
            'constitution_tanshi': 0.15,
            'activity_risk': 0.15,
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
    """题意对齐：血脂（或诊断）仅用于定义锚点，前置特征仅用于建模。"""
    anchors = build_diagnosis_anchor_flags(df)
    risk_anchor_cfg = risk_config.get('anchors', {})
    if bool(risk_anchor_cfg.get('high_anchor_phlegm_only', False)) and 'phlegm_dampness_label_flag' in df.columns:
        anchors['high_anchor'] = ((anchors['high_anchor'] == 1) & (df['phlegm_dampness_label_flag'] == 1)).astype(int)
    return anchors
