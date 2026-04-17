from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math
import pandas as pd
from domain.activity_rules import feasible_intensities
from domain.intervention_rules import stage_exercise_cost, stage_tcm_cost, tolerance_capacity, burden_score, stage_effect


@dataclass
class PlanState:
    latent_state: float
    tanshi_score: float
    total_cost: float
    total_burden: float
    prev_intensity: int | None = None
    prev_frequency: int | None = None
    plan: tuple = ()


def _next_state(row: pd.Series, state: PlanState, tcm_level: int, intensity: int, frequency: int, months: int, clinical_rules: dict, intervention_config: dict) -> PlanState | None:
    tol = tolerance_capacity(row['activity_total'], int(row['age_group']), intervention_config['tolerance'])
    burden = burden_score(intensity, frequency, state.prev_intensity, state.prev_frequency, intervention_config['burden'])
    if burden > tol:
        return None
    cost = stage_exercise_cost(intensity, frequency, months, clinical_rules['exercise']['single_cost']) + stage_tcm_cost(tcm_level, months, clinical_rules['tcm']['monthly_cost'])
    new_total_cost = state.total_cost + cost
    if new_total_cost > clinical_rules['budget']['six_month_total_max']:
        return None
    scenarios = intervention_config['scenarios']
    latent_vals = []
    tanshi_vals = []
    for factor in scenarios.values():
        rel_gain, abs_gain = stage_effect(tcm_level, intensity, frequency, months, factor, clinical_rules, intervention_config['synergy'])
        next_tanshi = max(0.0, state.tanshi_score * max(0.0, 1.0 - rel_gain) - abs_gain)
        next_latent = max(0.0, state.latent_state * max(0.0, 1.0 - 0.8 * rel_gain) - 0.6 * abs_gain)
        latent_vals.append(next_latent)
        tanshi_vals.append(next_tanshi)
    next_latent = max(latent_vals)
    next_tanshi = max(tanshi_vals)
    return PlanState(
        latent_state=next_latent,
        tanshi_score=next_tanshi,
        total_cost=new_total_cost,
        total_burden=state.total_burden + burden,
        prev_intensity=intensity,
        prev_frequency=frequency,
        plan=state.plan + ((tcm_level, intensity, frequency),),
    )


def _objective(state: PlanState, intervention_config: dict) -> float:
    w = intervention_config['objective_weights']
    smoothness = 0.0
    if len(state.plan) >= 2:
        for a, b in zip(state.plan[:-1], state.plan[1:]):
            smoothness += abs(a[1] - b[1]) + 0.2 * abs(a[2] - b[2])
    return (
        w['final_latent_state'] * state.latent_state
        + w['final_tanshi_score'] * state.tanshi_score
        + w['total_cost'] * state.total_cost / 2000.0
        + w['total_burden'] * state.total_burden / 50.0
        + w['smoothness'] * smoothness / 10.0
    )


def optimize_patient_plan(row: pd.Series, clinical_rules: dict, intervention_config: dict) -> dict:
    stages = intervention_config['stages']
    freq_candidates = intervention_config['frequency_candidates']
    beam_width = intervention_config['beam_width']
    beam = [PlanState(latent_state=float(row['latent_state_h']), tanshi_score=float(row['constitution_tanshi']), total_cost=0.0, total_burden=0.0)]
    for stage in stages:
        next_beam = []
        allowed_intensities = feasible_intensities(int(row['age_group']), float(row['activity_total']), clinical_rules['activity_rules'])
        for state in beam:
            for tcm_level, intensity, frequency in product([1, 2, 3], allowed_intensities, freq_candidates):
                nxt = _next_state(row, state, tcm_level, intensity, frequency, int(stage['months']), clinical_rules, intervention_config)
                if nxt is not None:
                    next_beam.append(nxt)
        if not next_beam:
            break
        next_beam = sorted(next_beam, key=lambda s: _objective(s, intervention_config))[:beam_width]
        beam = next_beam
    if not beam:
        return {'sample_id': int(row['sample_id']), 'status': 'infeasible'}
    best = min(beam, key=lambda s: _objective(s, intervention_config))
    return {
        'sample_id': int(row['sample_id']),
        'status': 'ok',
        'final_latent_state': float(best.latent_state),
        'final_tanshi_score': float(best.tanshi_score),
        'total_cost': float(best.total_cost),
        'total_burden': float(best.total_burden),
        'plan': list(best.plan),
    }


def optimize_population(df: pd.DataFrame, clinical_rules: dict, intervention_config: dict) -> pd.DataFrame:
    rows = [optimize_patient_plan(row, clinical_rules, intervention_config) for _, row in df.iterrows()]
    out = pd.DataFrame(rows)
    if 'plan' in out.columns:
        out['first_stage_tcm'] = out['plan'].apply(lambda x: x[0][0] if isinstance(x, list) and x else None)
        out['first_stage_intensity'] = out['plan'].apply(lambda x: x[0][1] if isinstance(x, list) and x else None)
        out['first_stage_frequency'] = out['plan'].apply(lambda x: x[0][2] if isinstance(x, list) and x else None)
    return out
