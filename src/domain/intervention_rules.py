from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_TRANSITION_CALIBRATION = {
    'reference_weekly_minutes': 150.0,
    'min_activity_to_tanshi': 0.12,
    'min_activity_to_latent': 0.08,
    'min_tanshi_to_latent': 0.20,
}


def stage_exercise_cost(intensity: int, frequency: int, months: int, single_cost: dict) -> float:
    return months * 4 * frequency * float(single_cost[intensity])


def stage_tcm_cost(level: int, months: int, monthly_cost: dict) -> float:
    return months * float(monthly_cost[level])


def tolerance_capacity(activity_total: float, age_group: int, tolerance_config: dict) -> float:
    return float(tolerance_config['base_capacity']) + float(tolerance_config['activity_weight']) * float(activity_total) - float(tolerance_config['age_weight']) * float(age_group)


def burden_score(intensity: int, frequency: int, prev_intensity: int | None, prev_frequency: int | None, burden_config: dict) -> float:
    score = burden_config['intensity_weight'] * intensity + burden_config['frequency_weight'] * frequency
    if prev_intensity is not None:
        score += burden_config['change_intensity_weight'] * abs(intensity - prev_intensity)
    if prev_frequency is not None:
        score += burden_config['change_frequency_weight'] * abs(frequency - prev_frequency)
    return float(score)


def _get_transition_config(intervention_config: dict | None) -> dict[str, float]:
    cfg = dict(DEFAULT_TRANSITION_CALIBRATION)
    if intervention_config:
        extra = intervention_config.get('transition_calibration', {})
        for key, value in extra.items():
            cfg[str(key)] = float(value)
    return cfg


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').fillna(0.0)


def _solve_least_squares(target: pd.Series, features: pd.DataFrame) -> dict[str, float]:
    x = np.asarray(features, dtype=float)
    y = np.asarray(_safe_numeric(target), dtype=float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {str(name): float(value) for name, value in zip(features.columns, coef)}


def fit_transition_calibration(reference_df: pd.DataFrame | None, intervention_config: dict | None = None) -> dict[str, Any]:
    cfg = _get_transition_config(intervention_config)
    if reference_df is None or reference_df.empty:
        return {
            'source': 'default',
            'tanshi_model': {},
            'latent_model': {},
            'config': cfg,
        }

    required = {'activity_total', 'age_group', 'constitution_tanshi', 'latent_state_h'}
    if not required.issubset(reference_df.columns):
        return {
            'source': 'default',
            'tanshi_model': {},
            'latent_model': {},
            'config': cfg,
        }

    work = reference_df.copy()
    work['activity_total'] = _safe_numeric(work['activity_total'])
    work['age_group'] = _safe_numeric(work['age_group'])
    work['constitution_tanshi'] = _safe_numeric(work['constitution_tanshi'])
    work['latent_state_h'] = _safe_numeric(work['latent_state_h'])
    work['metabolic_deviation_total'] = _safe_numeric(work['metabolic_deviation_total']) if 'metabolic_deviation_total' in work.columns else 0.0
    work['lipid_deviation_total'] = _safe_numeric(work['lipid_deviation_total']) if 'lipid_deviation_total' in work.columns else 0.0
    work['age_risk'] = (work['age_group'] - 1.0) / 4.0
    work['latent_ratio'] = work['latent_state_h'] / 100.0
    work['tanshi_ratio'] = work['constitution_tanshi'] / 100.0

    tanshi_features = pd.DataFrame(
        {
            'intercept': 1.0,
            'activity_total': work['activity_total'],
            'activity_age_interaction': work['activity_total'] * work['age_risk'],
            'activity_tanshi_interaction': work['activity_total'] * work['tanshi_ratio'],
            'metabolic_deviation_total': work['metabolic_deviation_total'],
            'lipid_deviation_total': work['lipid_deviation_total'],
            'age_group': work['age_group'],
        }
    )
    latent_features = pd.DataFrame(
        {
            'intercept': 1.0,
            'activity_total': work['activity_total'],
            'activity_latent_interaction': work['activity_total'] * work['latent_ratio'],
            'constitution_tanshi': work['constitution_tanshi'],
            'tanshi_latent_interaction': work['constitution_tanshi'] * work['latent_ratio'],
            'metabolic_deviation_total': work['metabolic_deviation_total'],
            'age_group': work['age_group'],
        }
    )

    return {
        'source': 'fitted',
        'tanshi_model': _solve_least_squares(work['constitution_tanshi'], tanshi_features),
        'latent_model': _solve_least_squares(work['latent_state_h'], latent_features),
        'config': cfg,
    }


def build_patient_response_profile(row: pd.Series, calibration: dict[str, Any] | None) -> dict[str, float]:
    calibration = calibration or {'source': 'default', 'tanshi_model': {}, 'latent_model': {}, 'config': dict(DEFAULT_TRANSITION_CALIBRATION)}
    cfg = {**DEFAULT_TRANSITION_CALIBRATION, **dict(calibration.get('config', {}))}
    age_risk = max(0.0, (float(row.get('age_group', 1)) - 1.0) / 4.0)
    latent_ratio = max(0.0, float(row.get('latent_state_h', 0.0)) / 100.0)
    tanshi_ratio = max(0.0, float(row.get('constitution_tanshi', 0.0)) / 100.0)
    tanshi_model = calibration.get('tanshi_model', {})
    latent_model = calibration.get('latent_model', {})

    activity_to_tanshi = -(
        float(tanshi_model.get('activity_total', 0.0))
        + float(tanshi_model.get('activity_age_interaction', 0.0)) * age_risk
        + float(tanshi_model.get('activity_tanshi_interaction', 0.0)) * tanshi_ratio
    )
    activity_to_latent = -(
        float(latent_model.get('activity_total', 0.0))
        + float(latent_model.get('activity_latent_interaction', 0.0)) * latent_ratio
    )
    tanshi_to_latent = (
        float(latent_model.get('constitution_tanshi', 0.0))
        + float(latent_model.get('tanshi_latent_interaction', 0.0)) * latent_ratio
    )

    return {
        'activity_to_tanshi': max(float(cfg['min_activity_to_tanshi']), activity_to_tanshi),
        'activity_to_latent': max(float(cfg['min_activity_to_latent']), activity_to_latent),
        'tanshi_to_latent': max(float(cfg['min_tanshi_to_latent']), tanshi_to_latent),
    }


def stage_effect(
    tcm_level: int,
    intensity: int,
    frequency: int,
    months: int,
    scenario_multiplier: float,
    clinical_rules: dict,
    synergy_config: dict,
    response_config: dict | None = None,
) -> tuple[float, float]:
    exercise = clinical_rules['exercise']
    tcm = clinical_rules['tcm']
    response_cfg = {**DEFAULT_TRANSITION_CALIBRATION, **(response_config or {})}
    stable_frequency = max(float(exercise.get('stable_if_below_frequency', 5)), 1.0)
    intensity_gain_per_level = float(exercise.get('monthly_intensity_gain_per_level', 0.03))
    frequency_gain_per_extra_session = float(exercise.get('monthly_frequency_gain_per_extra_session', 0.01))
    intensity_levels_above_baseline = max(0, int(intensity) - 1)
    frequency_gate = min(1.0, float(frequency) / stable_frequency)
    frequency_extras = max(0.0, float(frequency) - stable_frequency)
    intensity_response = float(months) * intensity_levels_above_baseline * intensity_gain_per_level * frequency_gate
    frequency_response = float(months) * frequency_extras * frequency_gain_per_extra_session
    exercise_response = intensity_response + frequency_response
    synergy = 0.0
    if synergy_config.get('enabled', False):
        synergy = (
            float(synergy_config['coefficient'])
            * max(0, tcm_level - 1)
            * max(exercise_response, 0.0)
            * math.exp(-float(synergy_config['diminishing_scale']) * max(0, frequency - stable_frequency))
        )
    tcm_absolute = float(months) * float(tcm['monthly_absolute_gain'][tcm_level])
    activity_response = scenario_multiplier * max(0.0, exercise_response + synergy)
    tcm_response = scenario_multiplier * max(0.0, tcm_absolute)
    return activity_response, tcm_response


def estimate_state_gains(
    row: pd.Series,
    tcm_level: int,
    intensity: int,
    frequency: int,
    months: int,
    scenario_multiplier: float,
    clinical_rules: dict,
    intervention_config: dict,
    calibration: dict[str, Any] | None,
) -> tuple[float, float]:
    profile = build_patient_response_profile(row, calibration)
    response_cfg = _get_transition_config(intervention_config)
    activity_response, tcm_response = stage_effect(
        tcm_level,
        intensity,
        frequency,
        months,
        scenario_multiplier,
        clinical_rules,
        intervention_config.get('synergy', {}),
        response_cfg,
    )
    tanshi_gain = max(0.0, profile['activity_to_tanshi'] * activity_response + tcm_response)
    latent_gain = max(0.0, profile['activity_to_latent'] * activity_response + profile['tanshi_to_latent'] * tanshi_gain)
    mult_cfg = intervention_config.get('metabolic_gain_multiplier', {}) if intervention_config else {}
    bmi_unit = float(mult_cfg.get('bmi_per_unit', 0.0))
    if bmi_unit > 0.0 and 'dev_bmi' in row.index:
        bmi_adj = 1.0 + bmi_unit * max(0.0, float(row.get('dev_bmi', 0.0)))
        latent_gain *= bmi_adj
        tanshi_gain *= bmi_adj
    return latent_gain, tanshi_gain
