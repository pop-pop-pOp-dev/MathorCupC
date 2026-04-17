from __future__ import annotations

import pandas as pd

from utils.cohort import phlegm_intervention_cohort


def test_phlegm_cohort_prefers_flag():
    df = pd.DataFrame(
        {
            'sample_id': [1, 2, 3],
            'phlegm_dampness_label_flag': [1, 0, 1],
            'constitution_label': [5, 5, 1],
        }
    )
    sub = phlegm_intervention_cohort(df)
    assert list(sub['sample_id']) == [1, 3]


def test_phlegm_cohort_fallback_constitution():
    df = pd.DataFrame({'sample_id': [1, 2], 'constitution_label': [5, 3]})
    sub = phlegm_intervention_cohort(df)
    assert list(sub['sample_id']) == [1]
