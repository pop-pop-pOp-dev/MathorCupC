import numpy as np
import pandas as pd
from models.latent_state import fit_latent_state, loadings_to_long


RISK_CONFIG = {'latent_state': {'view_weights': {'constitution': 0.35, 'activity': 0.25, 'metabolic': 0.40}}}


def build_latent_df(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(rng.normal(size=(n, 18)), columns=[
        'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
        'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing',
        'adl_total', 'iadl_total', 'activity_total', 'activity_risk',
        'lipid_deviation_total', 'metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid'
    ])


def test_latent_state_output_shape_and_range():
    df = build_latent_df()
    result = fit_latent_state(df, RISK_CONFIG)
    assert {'constitution_factor', 'activity_factor', 'metabolic_factor', 'latent_state_raw', 'latent_state_h'} <= set(result.frame.columns)
    assert len(result.frame) == len(df)
    assert float(result.frame['latent_state_h'].min()) >= 0.0
    assert float(result.frame['latent_state_h'].max()) <= 100.0


def test_latent_state_view_diagnostics_present():
    df = build_latent_df()
    result = fit_latent_state(df, RISK_CONFIG)
    assert {'factor_name', 'n_features', 'explained_variance_ratio'} <= set(result.view_diagnostics.columns)
    assert result.view_diagnostics['explained_variance_ratio'].between(0, 1).all()


def test_loadings_to_long_has_expected_columns():
    df = build_latent_df()
    result = fit_latent_state(df, RISK_CONFIG)
    long_df = loadings_to_long(result.loadings)
    assert {'feature', 'factor_name', 'loading', 'abs_loading'} <= set(long_df.columns)
