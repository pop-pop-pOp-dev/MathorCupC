import pandas as pd
from models.rule_mining import build_rule_coverage_matrix, enumerate_candidate_rules, extract_minimal_rules


def build_rule_df() -> pd.DataFrame:
    return pd.DataFrame({
        'sample_id': [1, 2, 3, 4, 5, 6],
        'phlegm_dampness_label_flag': [1, 1, 1, 0, 0, 1],
        'constitution_tanshi': [70, 65, 30, 20, 10, 72],
        'activity_total': [30, 35, 70, 60, 50, 38],
        'dev_bmi': [1, 1, 0, 0, 0, 1],
        'dev_tg': [1, 1, 0, 0, 0, 1],
        'dev_ldl_c': [1, 0, 0, 0, 0, 1],
        'latent_state_h': [90, 80, 20, 10, 5, 92],
        'lipid_deviation_total': [4, 3, 0, 0, 0, 4],
        'metabolic_deviation_total': [2, 2, 0, 0, 0, 2],
        'risk_tier': ['high', 'high', 'low', 'low', 'medium', 'high'],
    })


def test_rule_extraction_returns_core_fields():
    df = build_rule_df()
    out = extract_minimal_rules(df)
    assert isinstance(out, pd.DataFrame)
    assert {'rule', 'coverage', 'purity', 'lift', 'size', 'incremental_coverage', 'selected_order', 'is_core_rule'} <= set(out.columns)


def test_candidate_rule_enumeration_nonempty():
    df = build_rule_df()
    candidates = enumerate_candidate_rules(df)
    assert not candidates.empty
    assert {'rule', 'coverage', 'purity', 'lift', '__mask__'} <= set(candidates.columns)


def test_rule_coverage_matrix_contains_sample_id():
    df = build_rule_df()
    candidates = enumerate_candidate_rules(df)
    selected = extract_minimal_rules(df)
    matrix = build_rule_coverage_matrix(df, selected, candidates)
    assert 'sample_id' in matrix.columns
