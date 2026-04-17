from __future__ import annotations

import pandas as pd


def summarize_optimization_robustness(plan_df: pd.DataFrame) -> pd.DataFrame:
    if plan_df.empty:
        return pd.DataFrame()
    cols = [c for c in ['final_latent_state', 'final_tanshi_score', 'total_cost', 'total_burden'] if c in plan_df.columns]
    return plan_df[cols].agg(['mean', 'std', 'min', 'max']).T.reset_index().rename(columns={'index': 'metric'})
