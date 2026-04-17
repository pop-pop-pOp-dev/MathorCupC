from __future__ import annotations

import pandas as pd

CONSTITUTION_SCORE_COLUMNS = [
    'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
    'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
]


def constitution_argmax_label(df: pd.DataFrame) -> pd.Series:
    max_idx = df[CONSTITUTION_SCORE_COLUMNS].idxmax(axis=1)
    label_map = {name: idx + 1 for idx, name in enumerate(CONSTITUTION_SCORE_COLUMNS)}
    return max_idx.map(label_map).astype(int)


def constitution_label_matches_any_max_score(df: pd.DataFrame) -> pd.Series:
    max_scores = df[CONSTITUTION_SCORE_COLUMNS].max(axis=1)
    label_columns = {idx + 1: name for idx, name in enumerate(CONSTITUTION_SCORE_COLUMNS)}
    label_scores = df.apply(lambda row: row[label_columns[int(row['constitution_label'])]], axis=1)
    return label_scores == max_scores


def constitution_argmax_mismatch_count(df: pd.DataFrame) -> int:
    return int((~constitution_label_matches_any_max_score(df)).sum())
