import pandas as pd
from features.activity_features import build_activity_features


def test_activity_risk_monotonicity():
    df = pd.DataFrame({'adl_total': [10, 20], 'iadl_total': [10, 20], 'activity_total': [20, 40]})
    feats = build_activity_features(df)
    assert feats.loc[0, 'activity_risk'] > feats.loc[1, 'activity_risk']
