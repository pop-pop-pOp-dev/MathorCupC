from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
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


@dataclass
class LatentStateResult:
    frame: pd.DataFrame
    loadings: pd.DataFrame
    view_diagnostics: pd.DataFrame
    view_models: Dict[str, LatentViewModel]


def _minmax_100(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min() + 1e-9) * 100


def _fit_first_component(
    df: pd.DataFrame,
    columns: list[str],
    factor_name: str,
    invert: bool = False,
) -> tuple[pd.Series, pd.Series, LatentViewModel]:
    x = df[columns].copy()
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    pca = PCA(n_components=1, random_state=0)
    comp = pca.fit_transform(x_scaled).ravel()
    loadings = pd.Series(pca.components_[0], index=columns, name=factor_name)
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
        explained_variance_ratio=float(pca.explained_variance_ratio_[0]),
    )
    return pd.Series(comp, index=df.index, name=factor_name), loadings, model


def _project_view(df: pd.DataFrame, model: LatentViewModel) -> pd.Series:
    x = df[model.columns].copy().to_numpy(dtype=float)
    x_scaled = (x - model.mean_) / model.scale_
    projected = x_scaled @ model.loadings.loc[model.columns].to_numpy(dtype=float)
    return pd.Series(projected, index=df.index, name=model.factor_name)


def _combine_view_scores(scores: dict[str, pd.Series], risk_config: dict) -> pd.DataFrame:
    weights = risk_config['latent_state']['view_weights']
    latent_raw = (
        weights['constitution'] * scores['constitution_factor']
        + weights['activity'] * scores['activity_factor']
        + weights['metabolic'] * scores['metabolic_factor']
    )
    latent_scaled = _minmax_100(latent_raw)
    return pd.DataFrame(
        {
            'constitution_factor': scores['constitution_factor'],
            'activity_factor': scores['activity_factor'],
            'metabolic_factor': scores['metabolic_factor'],
            'latent_state_raw': latent_raw,
            'latent_state_h': latent_scaled,
        },
        index=latent_raw.index,
    )


def fit_latent_state(df: pd.DataFrame, risk_config: dict) -> LatentStateResult:
    constitution_score, constitution_loadings, constitution_model = _fit_first_component(
        df,
        CONSTITUTION_VIEW,
        factor_name='constitution_factor',
    )
    activity_score, activity_loadings, activity_model = _fit_first_component(
        df,
        ACTIVITY_VIEW,
        factor_name='activity_factor',
        invert=True,
    )
    metabolic_score, metabolic_loadings, metabolic_model = _fit_first_component(
        df,
        METABOLIC_VIEW,
        factor_name='metabolic_factor',
    )
    scores = {
        'constitution_factor': constitution_score,
        'activity_factor': activity_score,
        'metabolic_factor': metabolic_score,
    }
    out = _combine_view_scores(scores, risk_config)
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
            },
            {
                'factor_name': 'activity_factor',
                'n_features': len(ACTIVITY_VIEW),
                'explained_variance_ratio': activity_model.explained_variance_ratio,
            },
            {
                'factor_name': 'metabolic_factor',
                'n_features': len(METABOLIC_VIEW),
                'explained_variance_ratio': metabolic_model.explained_variance_ratio,
            },
        ]
    )
    return LatentStateResult(
        frame=out,
        loadings=loadings,
        view_diagnostics=view_diagnostics,
        view_models={
            'constitution_factor': constitution_model,
            'activity_factor': activity_model,
            'metabolic_factor': metabolic_model,
        },
    )


def project_latent_state(df: pd.DataFrame, view_models: Dict[str, LatentViewModel], risk_config: dict) -> pd.DataFrame:
    scores = {
        'constitution_factor': _project_view(df, view_models['constitution_factor']),
        'activity_factor': _project_view(df, view_models['activity_factor']),
        'metabolic_factor': _project_view(df, view_models['metabolic_factor']),
    }
    return _combine_view_scores(scores, risk_config)


def loadings_to_long(loadings: pd.DataFrame) -> pd.DataFrame:
    return (
        loadings.rename_axis('feature')
        .reset_index()
        .melt(id_vars='feature', var_name='factor_name', value_name='loading')
        .assign(abs_loading=lambda x: x['loading'].abs())
    )
