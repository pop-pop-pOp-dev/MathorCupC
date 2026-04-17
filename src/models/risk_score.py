from __future__ import annotations

import pandas as pd


def normalize_series(series: pd.Series) -> pd.Series:
    return (series - series.min()) / (series.max() - series.min() + 1e-9)


def build_continuous_risk_score(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
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
    return out


def build_anchor_flags(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
    anchors = risk_config['anchors']
    low_latent_cut = df['latent_state_h'].quantile(anchors['low_latent_quantile'])
    high_latent_cut = df['latent_state_h'].quantile(anchors['high_latent_quantile'])
    low_anchor = (
        (df['hyperlipidemia_label'] == 0)
        & (df['latent_state_h'] <= low_latent_cut)
        & (df['activity_total'] >= anchors['adequate_activity_cutoff'])
    )
    high_anchor = (
        (df['hyperlipidemia_label'] == 1)
        & (df['latent_state_h'] >= high_latent_cut)
        & (df['lipid_deviation_total'] > df['lipid_deviation_total'].median())
    )
    return pd.DataFrame({'low_anchor': low_anchor.astype(int), 'high_anchor': high_anchor.astype(int)})
