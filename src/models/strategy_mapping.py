from __future__ import annotations

import pandas as pd


def _mode_value(series: pd.Series) -> float:
    m = series.dropna().mode()
    if m.empty:
        return float('nan')
    return float(m.iloc[0])


def build_strategy_mapping_tables(plans: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """患者特征 → 推荐方案（众数/样本量）：支撑问题三「匹配规律」叙述。"""
    if plans is None or plans.empty:
        return {
            'by_risk_tier_age': pd.DataFrame(),
            'by_activity_bins': pd.DataFrame(),
        }
    p = plans.copy()
    if 'risk_tier' not in p.columns or 'age_group' not in p.columns:
        return {'by_risk_tier_age': pd.DataFrame(), 'by_activity_bins': pd.DataFrame()}

    by_ra = (
        p.groupby(['risk_tier', 'age_group'], dropna=False)
        .agg(
            sample_count=('sample_id', 'count'),
            first_tcm_mode=('first_stage_tcm', _mode_value),
            first_intensity_mode=('first_stage_intensity', _mode_value),
            first_frequency_mode=('first_stage_frequency', _mode_value),
            mean_total_cost=('total_cost', 'mean'),
            mean_total_burden=('total_burden', 'mean'),
            mean_final_tanshi=('final_tanshi_score', 'mean'),
            mean_final_latent=('final_latent_state', 'mean'),
        )
        .reset_index()
    )

    if 'activity_total' in p.columns:
        p['activity_bin'] = pd.cut(
            pd.to_numeric(p['activity_total'], errors='coerce'),
            bins=[-0.001, 40, 60, 100.001],
            labels=['activity_lt40', 'activity_40_60', 'activity_ge60'],
        )
        by_act = (
            p.groupby(['activity_bin', 'age_group'], dropna=False)
            .agg(
                sample_count=('sample_id', 'count'),
                first_tcm_mode=('first_stage_tcm', _mode_value),
                first_intensity_mode=('first_stage_intensity', _mode_value),
                first_frequency_mode=('first_stage_frequency', _mode_value),
                mean_total_cost=('total_cost', 'mean'),
            )
            .reset_index()
        )
    else:
        by_act = pd.DataFrame()

    return {'by_risk_tier_age': by_ra, 'by_activity_bins': by_act}
