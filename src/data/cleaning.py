from __future__ import annotations

import pandas as pd

INTEGER_COLUMNS = [
    'sample_id', 'constitution_label', 'hyperlipidemia_label', 'lipid_abnormality_type',
    'age_group', 'sex', 'smoking_history', 'drinking_history'
]


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        out[col] = pd.to_numeric(out[col], errors='raise')
    for col in INTEGER_COLUMNS:
        out[col] = out[col].astype(int)
    return out


def validate_shape(df: pd.DataFrame, expected_rows: int, expected_cols: int) -> None:
    if len(df) != expected_rows:
        raise ValueError(f'Expected {expected_rows} rows, got {len(df)}')
    if df.shape[1] != expected_cols:
        raise ValueError(f'Expected {expected_cols} columns, got {df.shape[1]}')


def validate_no_missing(df: pd.DataFrame) -> None:
    if df.isna().any().any():
        raise ValueError('Dataset contains missing values')


def clean_dataset(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    out = coerce_types(df)
    validate_shape(out, schema['row_count_expected'], schema['column_count_expected'])
    validate_no_missing(out)
    return out
