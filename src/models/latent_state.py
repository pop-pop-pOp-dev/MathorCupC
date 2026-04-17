from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.decomposition import FactorAnalysis, PCA
from sklearn.preprocessing import StandardScaler

CONSTITUTION_VIEW = [
    'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
    'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
]
ACTIVITY_VIEW = ['adl_total', 'iadl_total', 'activity_total', 'activity_risk']
METABOLIC_VIEW = ['lipid_deviation_total', 'metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid']


@dataclass
class LatentViewModel:
    factor_name: str
    columns: list[str]
    mean_: np.ndarray
    scale_: np.ndarray
    loadings: pd.Series
    explained_variance_ratio: float
    extraction_method: str


@dataclass
class LatentStateResult:
    frame: pd.DataFrame
    loadings: pd.DataFrame
    view_diagnostics: pd.DataFrame
    view_models: Dict[str, LatentViewModel]
    second_order: pd.DataFrame = field(default_factory=pd.DataFrame)
    second_order_method: str = ''


def _minmax_100(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min() + 1e-9) * 100


def _explained_ratio_reconstruction(x_scaled: np.ndarray, scores_1d: np.ndarray, components: np.ndarray) -> float:
    """Fraction of total squared signal captured by rank-1 reconstruction scores @ components."""
    recon = np.outer(scores_1d, components)
    return float(1.0 - np.sum((x_scaled - recon) ** 2) / (np.sum(x_scaled**2) + 1e-12))


def _fit_first_component(
    df: pd.DataFrame,
    columns: list[str],
    factor_name: str,
    invert: bool = False,
    extraction: str = 'factor_analysis',
) -> tuple[pd.Series, pd.Series, LatentViewModel]:
    x = df[columns].copy()
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    method_used = extraction
    loadings: pd.Series
    comp: np.ndarray
    ev: float

    if extraction == 'factor_analysis':
        try:
            fa = FactorAnalysis(n_components=1, random_state=0, max_iter=3000, tol=0.01)
            comp = fa.fit_transform(x_scaled).ravel()
            loadings = pd.Series(np.asarray(fa.components_[0], dtype=float), index=columns, name=factor_name)
            ev = _explained_ratio_reconstruction(x_scaled, comp, np.asarray(fa.components_[0], dtype=float))
        except Exception:
            extraction = 'pca_fallback'
            pca = PCA(n_components=1, random_state=0)
            comp = pca.fit_transform(x_scaled).ravel()
            loadings = pd.Series(np.asarray(pca.components_[0], dtype=float), index=columns, name=factor_name)
            ev = float(pca.explained_variance_ratio_[0])
            method_used = 'pca_fallback'
    else:
        pca = PCA(n_components=1, random_state=0)
        comp = pca.fit_transform(x_scaled).ravel()
        loadings = pd.Series(np.asarray(pca.components_[0], dtype=float), index=columns, name=factor_name)
        ev = float(pca.explained_variance_ratio_[0])
        method_used = 'pca'

    if invert:
        comp = -comp
        loadings = -loadings
    if loadings.abs().max() > 0 and loadings.loc[loadings.abs().idxmax()] < 0:
        comp = -comp
        loadings = -loadings

    scale_values = scaler.scale_
    if scale_values is None:
        scale_values = np.ones(len(columns), dtype=float)
    safe_scale = np.where(scale_values == 0, 1.0, scale_values)
    model = LatentViewModel(
        factor_name=factor_name,
        columns=columns,
        mean_=np.asarray(scaler.mean_, dtype=float),
        scale_=np.asarray(safe_scale, dtype=float),
        loadings=loadings,
        explained_variance_ratio=float(ev),
        extraction_method=method_used,
    )
    return pd.Series(comp, index=df.index, name=factor_name), loadings, model


def _project_view(df: pd.DataFrame, model: LatentViewModel) -> pd.Series:
    x = df[model.columns].copy().to_numpy(dtype=float)
    x_scaled = (x - model.mean_) / model.scale_
    projected = x_scaled @ model.loadings.loc[model.columns].to_numpy(dtype=float)
    return pd.Series(projected, index=df.index, name=model.factor_name)


def _second_order_combine(
    df: pd.DataFrame,
    scores: dict[str, pd.Series],
    risk_config: dict,
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """二阶综合隐状态：默认对三个一阶因子得分再做一维 PCA（可识别载荷），可选退回配置权重。"""
    latent_cfg = risk_config.get('latent_state', {})
    so_cfg = latent_cfg.get('second_order', {}) if isinstance(latent_cfg.get('second_order'), dict) else {}
    method = str(so_cfg.get('method', 'pca_one_component')).lower()

    fb = pd.to_numeric(scores['constitution_factor'], errors='coerce').fillna(0.0)
    fa = pd.to_numeric(scores['activity_factor'], errors='coerce').fillna(0.0)
    fm = pd.to_numeric(scores['metabolic_factor'], errors='coerce').fillna(0.0)
    Z = np.column_stack([fb.to_numpy(), fa.to_numpy(), fm.to_numpy()])
    Zs = (Z - Z.mean(axis=0, keepdims=True)) / (Z.std(axis=0, keepdims=True) + 1e-9)

    if method == 'fixed_weights':
        weights = latent_cfg.get('view_weights', {'constitution': 0.35, 'activity': 0.25, 'metabolic': 0.40})
        raw = (
            float(weights['constitution']) * fb
            + float(weights['activity']) * fa
            + float(weights['metabolic']) * fm
        )
        table = pd.DataFrame(
            [
                {'term': 'constitution_factor', 'value': float(weights['constitution']), 'method': 'fixed_weights'},
                {'term': 'activity_factor', 'value': float(weights['activity']), 'method': 'fixed_weights'},
                {'term': 'metabolic_factor', 'value': float(weights['metabolic']), 'method': 'fixed_weights'},
            ]
        )
    else:
        pca = PCA(n_components=1, random_state=0)
        raw_arr = pca.fit_transform(Zs).ravel()
        raw = pd.Series(raw_arr, index=fb.index)
        comp0 = np.asarray(pca.components_[0], dtype=float)
        if 'lipid_deviation_total' in df.columns:
            c = np.corrcoef(raw.to_numpy(dtype=float), pd.to_numeric(df['lipid_deviation_total'], errors='coerce').fillna(0.0).to_numpy(dtype=float))[0, 1]
            if not np.isnan(c) and c < 0:
                raw = -raw
                comp0 = -comp0
        table = pd.DataFrame(
            [
                {'term': 'constitution_factor', 'value': float(comp0[0]), 'method': 'pca_one_component'},
                {'term': 'activity_factor', 'value': float(comp0[1]), 'method': 'pca_one_component'},
                {'term': 'metabolic_factor', 'value': float(comp0[2]), 'method': 'pca_one_component'},
                {'term': 'explained_variance_ratio', 'value': float(pca.explained_variance_ratio_[0]), 'method': 'pca_one_component'},
            ]
        )

    latent_scaled = _minmax_100(raw)
    out = pd.DataFrame(
        {
            'constitution_factor': fb,
            'activity_factor': fa,
            'metabolic_factor': fm,
            'latent_state_raw': raw,
            'latent_state_h': latent_scaled,
        },
        index=raw.index,
    )
    return raw.rename('latent_state_raw'), out, table


def fit_latent_state(df: pd.DataFrame, risk_config: dict) -> LatentStateResult:
    latent_cfg = risk_config.get('latent_state', risk_config)
    extraction = str(latent_cfg.get('view_extraction', 'factor_analysis')).lower()

    constitution_score, constitution_loadings, constitution_model = _fit_first_component(
        df,
        CONSTITUTION_VIEW,
        factor_name='constitution_factor',
        invert=False,
        extraction=extraction,
    )
    activity_score, activity_loadings, activity_model = _fit_first_component(
        df,
        ACTIVITY_VIEW,
        factor_name='activity_factor',
        invert=True,
        extraction=extraction,
    )
    metabolic_score, metabolic_loadings, metabolic_model = _fit_first_component(
        df,
        METABOLIC_VIEW,
        factor_name='metabolic_factor',
        invert=False,
        extraction=extraction,
    )
    scores: dict[str, pd.Series] = {
        'constitution_factor': constitution_score,
        'activity_factor': activity_score,
        'metabolic_factor': metabolic_score,
    }
    _, frame, second_order = _second_order_combine(df, scores, risk_config)
    loadings = pd.concat(
        [
            constitution_loadings.rename('constitution_factor'),
            activity_loadings.rename('activity_factor'),
            metabolic_loadings.rename('metabolic_factor'),
        ],
        axis=1,
    ).fillna(0.0)
    view_diagnostics = pd.DataFrame(
        [
            {
                'factor_name': 'constitution_factor',
                'n_features': len(CONSTITUTION_VIEW),
                'explained_variance_ratio': constitution_model.explained_variance_ratio,
                'extraction_method': constitution_model.extraction_method,
            },
            {
                'factor_name': 'activity_factor',
                'n_features': len(ACTIVITY_VIEW),
                'explained_variance_ratio': activity_model.explained_variance_ratio,
                'extraction_method': activity_model.extraction_method,
            },
            {
                'factor_name': 'metabolic_factor',
                'n_features': len(METABOLIC_VIEW),
                'explained_variance_ratio': metabolic_model.explained_variance_ratio,
                'extraction_method': metabolic_model.extraction_method,
            },
        ]
    )
    so_method = str(latent_cfg.get('second_order', {}).get('method', 'pca_one_component')) if isinstance(latent_cfg.get('second_order'), dict) else 'pca_one_component'
    return LatentStateResult(
        frame=frame,
        loadings=loadings,
        view_diagnostics=view_diagnostics,
        view_models={
            'constitution_factor': constitution_model,
            'activity_factor': activity_model,
            'metabolic_factor': metabolic_model,
        },
        second_order=second_order,
        second_order_method=so_method,
    )


def project_latent_state(df: pd.DataFrame, view_models: Dict[str, LatentViewModel], risk_config: dict) -> pd.DataFrame:
    scores = {
        'constitution_factor': _project_view(df, view_models['constitution_factor']),
        'activity_factor': _project_view(df, view_models['activity_factor']),
        'metabolic_factor': _project_view(df, view_models['metabolic_factor']),
    }
    _, frame, _ = _second_order_combine(df, scores, risk_config)
    return frame


def loadings_to_long(loadings: pd.DataFrame) -> pd.DataFrame:
    return (
        loadings.rename_axis('feature')
        .reset_index()
        .melt(id_vars='feature', var_name='factor_name', value_name='loading')
        .assign(abs_loading=lambda x: x['loading'].abs())
    )


def constitution_shares_on_first_factor(loadings: pd.DataFrame) -> pd.DataFrame:
    """九种体质在一阶体质因子上的相对贡献（载荷绝对值占比）。"""
    cols = [c for c in CONSTITUTION_VIEW if c in loadings.index and 'constitution_factor' in loadings.columns]
    if not cols:
        return pd.DataFrame(columns=['constitution_feature', 'loading', 'abs_share'])
    s = loadings.loc[cols, 'constitution_factor'].astype(float)
    denom = float(s.abs().sum() + 1e-12)
    out = pd.DataFrame(
        {
            'constitution_feature': s.index.astype(str),
            'loading': s.values,
            'abs_share': s.abs().values / denom,
        }
    )
    return out.sort_values('abs_share', ascending=False).reset_index(drop=True)
