from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.stability import bootstrap_latent_loadings, bootstrap_latent_state_stability, latent_state_stability_from_loadings_boot
from models.latent_state import fit_latent_state


def _build_df(n: int = 24) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        rng.normal(size=(n, 18)),
        columns=[
            'constitution_pinghe',
            'constitution_qixu',
            'constitution_yangxu',
            'constitution_yinxu',
            'constitution_tanshi',
            'constitution_shire',
            'constitution_xueyu',
            'constitution_qiyu',
            'constitution_tebing',
            'adl_total',
            'iadl_total',
            'activity_total',
            'activity_risk',
            'lipid_deviation_total',
            'metabolic_deviation_total',
            'dev_bmi',
            'dev_fasting_glucose',
            'dev_uric_acid',
        ],
    )


def test_latent_stability_from_boot_matches_full_path():
    risk_model = {
        'latent_state': {
            'view_weights': {'constitution': 0.35, 'activity': 0.25, 'metabolic': 0.40},
            'view_extraction': 'pca',
            'second_order': {'method': 'pca_one_component'},
            'report_ci_level': 0.95,
        }
    }
    df = _build_df()
    fit_latent_state(df, risk_model)
    n_boot = 5
    boot = bootstrap_latent_loadings(df, risk_model, n_boot=n_boot, seed=99)
    from_boot = latent_state_stability_from_loadings_boot(boot, risk_model)
    full = bootstrap_latent_state_stability(df, risk_model, n_boot=n_boot, seed=99)
    pd.testing.assert_frame_equal(
        from_boot.sort_values('feature').reset_index(drop=True),
        full.sort_values('feature').reset_index(drop=True),
        check_dtype=False,
    )
