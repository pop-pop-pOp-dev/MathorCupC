from __future__ import annotations

from pathlib import Path
import pandas as pd
from data.schema import DataSchema


def load_raw_excel(project_root: str | Path, relative_path: str) -> pd.DataFrame:
    return pd.read_excel(Path(project_root) / relative_path)


def standardize_columns(df: pd.DataFrame, schema: DataSchema) -> pd.DataFrame:
    missing = [c for c in schema.column_mapping if c not in df.columns]
    if missing:
        raise ValueError(f'Missing expected columns: {missing}')
    standardized = df.rename(columns=schema.column_mapping).copy()
    standardized = standardized[list(schema.column_mapping.values())]
    return standardized
