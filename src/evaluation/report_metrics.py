from __future__ import annotations

import pandas as pd


def compact_metric_table(metrics: dict) -> pd.DataFrame:
    return pd.DataFrame({'metric': list(metrics.keys()), 'value': list(metrics.values())})
