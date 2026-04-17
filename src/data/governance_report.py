from __future__ import annotations

from typing import Dict, Any
import pandas as pd
from domain.clinical_thresholds import derive_hyperlipidemia_label_by_rules
from domain.constitution_logic import constitution_argmax_mismatch_count


def build_governance_report(df: pd.DataFrame) -> Dict[str, Any]:
    derived = derive_hyperlipidemia_label_by_rules(df)
    label_rule_match = int((derived == df['hyperlipidemia_label']).all())
    activity_identity_match = int(((df['adl_total'] + df['iadl_total']) == df['activity_total']).all())
    return {
        'row_count': int(len(df)),
        'column_count': int(df.shape[1]),
        'missing_values_total': int(df.isna().sum().sum()),
        'activity_identity_match': label_rule_match if False else activity_identity_match,
        'label_rule_match': label_rule_match,
        'constitution_label_argmax_mismatch_count': constitution_argmax_mismatch_count(df),
        'hyperlipidemia_distribution': {str(k): int(v) for k, v in df['hyperlipidemia_label'].value_counts().sort_index().items()},
        'constitution_distribution': {str(k): int(v) for k, v in df['constitution_label'].value_counts().sort_index().items()},
    }
