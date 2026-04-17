from __future__ import annotations

import pandas as pd
from domain.clinical_thresholds import deviation_from_interval, uric_acid_deviation


def build_deviation_features(df: pd.DataFrame, clinical_rules: dict) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    lipid_ranges = clinical_rules['lipid_ranges']
    metabolic_ranges = clinical_rules['metabolic_ranges']
    uric_ranges = clinical_rules['uric_acid_ranges']
    tc = pd.Series(df['tc'], index=df.index)
    tg = pd.Series(df['tg'], index=df.index)
    ldl_c = pd.Series(df['ldl_c'], index=df.index)
    hdl_c = pd.Series(df['hdl_c'], index=df.index)
    fasting_glucose = pd.Series(df['fasting_glucose'], index=df.index)
    bmi = pd.Series(df['bmi'], index=df.index)
    out['dev_tc'] = deviation_from_interval(tc, *lipid_ranges['tc'])
    out['dev_tg'] = deviation_from_interval(tg, *lipid_ranges['tg'])
    out['dev_ldl_c'] = deviation_from_interval(ldl_c, *lipid_ranges['ldl_c'])
    out['dev_hdl_c'] = deviation_from_interval(hdl_c, *lipid_ranges['hdl_c'])
    out['dev_fasting_glucose'] = deviation_from_interval(fasting_glucose, *metabolic_ranges['fasting_glucose'])
    out['dev_bmi'] = deviation_from_interval(bmi, *metabolic_ranges['bmi'])
    out['dev_uric_acid'] = uric_acid_deviation(df, tuple(uric_ranges['male']), tuple(uric_ranges['female']))
    out['lipid_deviation_total'] = out[['dev_tc', 'dev_tg', 'dev_ldl_c', 'dev_hdl_c']].sum(axis=1)
    out['metabolic_deviation_total'] = out[['dev_fasting_glucose', 'dev_bmi', 'dev_uric_acid']].sum(axis=1)
    return out
