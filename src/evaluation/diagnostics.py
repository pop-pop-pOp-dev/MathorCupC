from __future__ import annotations

import pandas as pd


def build_basic_diagnostics(df: pd.DataFrame) -> dict:
    diagnostics = {
        'n_samples': int(len(df)),
        'risk_tier_distribution': {str(k): int(v) for k, v in df['risk_tier'].value_counts().items()} if 'risk_tier' in df else {},
        'phlegm_patient_count': int((df['constitution_label'] == 5).sum()) if 'constitution_label' in df else 0,
    }
    if 'latent_state_h' in df:
        diagnostics['latent_state_summary'] = {
            'mean': float(df['latent_state_h'].mean()),
            'std': float(df['latent_state_h'].std(ddof=0)),
            'min': float(df['latent_state_h'].min()),
            'max': float(df['latent_state_h'].max()),
        }
    if 'continuous_risk_score' in df:
        diagnostics['continuous_risk_score_summary'] = {
            'mean': float(df['continuous_risk_score'].mean()),
            'std': float(df['continuous_risk_score'].std(ddof=0)),
            'min': float(df['continuous_risk_score'].min()),
            'max': float(df['continuous_risk_score'].max()),
        }
    if 'low_anchor' in df and 'high_anchor' in df:
        diagnostics['anchor_counts'] = {
            'low_anchor_count': int(df['low_anchor'].sum()),
            'high_anchor_count': int(df['high_anchor'].sum()),
        }
    return diagnostics


def build_stability_overview(latent_summary: dict | None, risk_summary: dict | None, rule_summary: dict | None) -> dict:
    return {
        'latent': latent_summary or {},
        'risk': risk_summary or {},
        'rules': rule_summary or {},
    }
