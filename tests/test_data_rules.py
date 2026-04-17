import pandas as pd
from domain.clinical_thresholds import derive_hyperlipidemia_label_by_rules, derive_lipid_type_by_rules
from domain.constitution_logic import constitution_argmax_mismatch_count


def test_label_rule_derivation():
    df = pd.DataFrame({
        'tc': [5.0, 6.5, 5.0],
        'tg': [1.0, 1.0, 2.0],
        'ldl_c': [2.5, 2.5, 2.5],
        'hdl_c': [1.2, 1.2, 1.2],
    })
    labels = derive_hyperlipidemia_label_by_rules(df)
    assert labels.tolist() == [0, 1, 1]
    lipid_type = derive_lipid_type_by_rules(df)
    assert lipid_type.tolist() == [0, 1, 2]


def test_constitution_mismatch_uses_any_max_score():
    df = pd.DataFrame({
        'constitution_label': [1, 2, 3],
        'constitution_pinghe': [10, 5, 1],
        'constitution_qixu': [10, 5, 1],
        'constitution_yangxu': [1, 6, 2],
        'constitution_yinxu': [0, 0, 0],
        'constitution_tanshi': [0, 0, 0],
        'constitution_shire': [0, 0, 0],
        'constitution_xueyu': [0, 0, 0],
        'constitution_qiyu': [0, 0, 0],
        'constitution_tebing': [0, 0, 0],
    })
    assert constitution_argmax_mismatch_count(df) == 1
