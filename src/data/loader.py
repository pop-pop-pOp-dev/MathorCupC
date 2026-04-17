from __future__ import annotations

from pathlib import Path
import warnings
import pandas as pd
from data.schema import DataSchema


def load_raw_excel(project_root: str | Path, relative_path: str) -> pd.DataFrame:
    root = Path(project_root)
    excel_path = root / relative_path
    if excel_path.exists():
        return pd.read_excel(excel_path)
    preview_path = root / 'data' / 'raw' / 'sample_preview.tsv'
    if preview_path.exists():
        warnings.warn(
            f'Raw excel not found at {excel_path}. Falling back to sample preview: {preview_path}',
            RuntimeWarning,
            stacklevel=2,
        )
        return pd.read_csv(preview_path, sep='\t')
    raise FileNotFoundError(f'Raw data not found: {excel_path}')


def standardize_columns(df: pd.DataFrame, schema: DataSchema) -> pd.DataFrame:
    missing = [c for c in schema.column_mapping if c not in df.columns]
    if missing:
        raise ValueError(f'Missing expected columns: {missing}')
    standardized = df.rename(columns=schema.column_mapping).copy()
    standardized = standardized[list(schema.column_mapping.values())]
    return standardized
