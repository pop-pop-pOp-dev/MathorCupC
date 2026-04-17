from __future__ import annotations

import pandas as pd


def summarize_risk_tiers(df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby('risk_tier').agg(
        sample_count=('sample_id', 'count'),
        avg_latent_state=('latent_state_h', 'mean'),
        avg_activity_total=('activity_total', 'mean'),
        avg_tanshi=('constitution_tanshi', 'mean'),
        confirmed_rate=('hyperlipidemia_label', 'mean'),
    )
    return summary.reset_index()
