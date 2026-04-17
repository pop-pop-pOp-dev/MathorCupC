from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from models.latent_state import CONSTITUTION_VIEW


def univariate_constitution_vs_label(
    df: pd.DataFrame,
    label_col: str = 'hyperlipidemia_label',
    seed: int = 20260417,
) -> pd.DataFrame:
    """Univariate association of each constitution score with binary label (问题一：九种体质对发病风险贡献度)."""
    if label_col not in df.columns:
        return pd.DataFrame(
            columns=['constitution_feature', 'coefficient', 'odds_ratio', 'direction', 'n_samples', 'n_positive']
        )
    y = pd.to_numeric(df[label_col], errors='coerce').fillna(0).astype(int)
    if y.nunique() < 2:
        return pd.DataFrame(
            columns=['constitution_feature', 'coefficient', 'odds_ratio', 'direction', 'n_samples', 'n_positive']
        )
    rows: list[dict] = []
    for col in CONSTITUTION_VIEW:
        if col not in df.columns:
            continue
        x = pd.to_numeric(df[col], errors='coerce').fillna(0.0).to_frame()
        scaler = StandardScaler()
        xs = scaler.fit_transform(x)
        model = LogisticRegression(
            C=1.0,
            solver='lbfgs',
            max_iter=2000,
            random_state=seed,
        )
        model.fit(xs, y)
        coef = float(model.coef_[0][0])
        rows.append(
            {
                'constitution_feature': col,
                'coefficient': coef,
                'odds_ratio': float(np.exp(coef)),
                'direction': 'risk_up' if coef >= 0 else 'risk_down',
                'n_samples': int(len(df)),
                'n_positive': int(y.sum()),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values('coefficient', key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def constitution_contribution_frame(loadings: pd.DataFrame) -> pd.DataFrame:
    if 'constitution_factor' not in loadings.columns:
        return pd.DataFrame(columns=['constitution_feature', 'loading', 'abs_share', 'direction'])
    cols = [c for c in CONSTITUTION_VIEW if c in loadings.index]
    if not cols:
        return pd.DataFrame(columns=['constitution_feature', 'loading', 'abs_share', 'direction'])
    series = loadings.loc[cols, 'constitution_factor'].astype(float)
    denom = float(series.abs().sum()) + 1e-12
    out = pd.DataFrame(
        {
            'constitution_feature': series.index.astype(str),
            'loading': series.values,
            'abs_share': series.abs().values / denom,
            'direction': np.where(series.values >= 0.0, 'risk_up', 'risk_down'),
        }
    )
    return out.sort_values('abs_share', ascending=False).reset_index(drop=True)
