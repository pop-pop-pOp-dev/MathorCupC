from __future__ import annotations

import pandas as pd
from domain.constitution_logic import constitution_argmax_label

CONSTITUTION_SCORE_COLUMNS = [
    'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
    'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
]


def build_constitution_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    row_sum = df[CONSTITUTION_SCORE_COLUMNS].sum(axis=1).replace(0, 1)
    out['constitution_tanshi_dominance'] = df['constitution_tanshi'] / row_sum
    out['constitution_pinghe_protective'] = df['constitution_pinghe'] / row_sum
    out['constitution_label_argmax_mismatch'] = (constitution_argmax_label(df) != df['constitution_label']).astype(int)
    out['phlegm_dampness_label_flag'] = (df['constitution_label'] == 5).astype(int)
    return out
