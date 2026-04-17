from __future__ import annotations

import math


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


def stage_effect(tcm_level: int, intensity: int, frequency: int, months: int, scenario_multiplier: float, clinical_rules: dict, synergy_config: dict) -> tuple[float, float]:
    exercise = clinical_rules['exercise']
    tcm = clinical_rules['tcm']
    if frequency < exercise['stable_if_below_frequency']:
        exercise_gain_rate = 0.0
    else:
        exercise_gain_rate = max(0.0, (intensity - 1) * exercise['monthly_intensity_gain_per_level']) + max(0.0, (frequency - 5) * exercise['monthly_frequency_gain_per_extra_session'])
    tcm_absolute = float(tcm['monthly_absolute_gain'][tcm_level])
    synergy = 0.0
    if synergy_config.get('enabled', False):
        synergy = float(synergy_config['coefficient']) * max(0, tcm_level - 1) * max(0, intensity - 1) * math.exp(-float(synergy_config['diminishing_scale']) * max(0, frequency - 5))
    exercise_gain_rate *= scenario_multiplier
    tcm_absolute *= scenario_multiplier
    synergy *= scenario_multiplier
    total_relative_gain = months * max(0.0, exercise_gain_rate + synergy)
    total_absolute_gain = months * tcm_absolute
    return total_relative_gain, total_absolute_gain
