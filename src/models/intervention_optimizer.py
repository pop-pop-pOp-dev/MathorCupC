from __future__ import annotations

from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed, effective_n_jobs
from scipy.optimize import Bounds, LinearConstraint, milp

from domain.activity_rules import feasible_intensities
from domain.tcm_rules import allowed_tcm_levels, exercise_frequency_candidates
from domain.intervention_rules import (
    burden_score,
    build_patient_response_profile,
    estimate_state_gains,
    fit_transition_calibration,
    stage_exercise_cost,
    stage_tcm_cost,
    tolerance_capacity,
)


def _build_action_space(row: pd.Series, clinical_rules: dict, intervention_config: dict) -> list[dict[str, Any]]:
    allowed_intensities = feasible_intensities(int(row['age_group']), float(row['activity_total']), clinical_rules['activity_rules'])
    stages = intervention_config['stages']
    freq_candidates = exercise_frequency_candidates(clinical_rules, intervention_config)
    tcm_levels = allowed_tcm_levels(float(row.get('constitution_tanshi', 0.0)), clinical_rules)
    actions: list[dict[str, Any]] = []
    for stage_idx, stage in enumerate(stages):
        months = int(stage['months'])
        stage_name = str(stage.get('name', f'stage_{stage_idx + 1}'))
        for tcm_level, intensity, frequency in product(tcm_levels, allowed_intensities, freq_candidates):
            stage_cost = stage_exercise_cost(intensity, frequency, months, clinical_rules['exercise']['single_cost'])
            stage_cost += stage_tcm_cost(tcm_level, months, clinical_rules['tcm']['monthly_cost'])
            stage_burden = burden_score(intensity, frequency, None, None, intervention_config['burden'])
            actions.append(
                {
                    'stage_idx': stage_idx,
                    'stage_name': stage_name,
                    'months': months,
                    'tcm_level': int(tcm_level),
                    'intensity': int(intensity),
                    'frequency': int(frequency),
                    'cost': float(stage_cost),
                    'burden': float(stage_burden),
                }
            )
    return actions


def _build_stage_action_map(actions: list[dict[str, Any]]) -> dict[int, list[int]]:
    mapping: dict[int, list[int]] = {}
    for idx, action in enumerate(actions):
        mapping.setdefault(int(action['stage_idx']), []).append(idx)
    return mapping


def _build_pair_data(
    actions: list[dict[str, Any]],
    stage_actions: dict[int, list[int]],
    max_intensity_jump: int = 1,
) -> tuple[list[dict[str, Any]], list[tuple[int, int]]]:
    pairs: list[dict[str, Any]] = []
    forbidden_pairs: list[tuple[int, int]] = []
    for stage_idx in sorted(stage_actions)[:-1]:
        current_actions = stage_actions.get(stage_idx, [])
        next_actions = stage_actions.get(stage_idx + 1, [])
        for i in current_actions:
            for j in next_actions:
                intensity_jump = abs(int(actions[i]['intensity']) - int(actions[j]['intensity']))
                if intensity_jump > max_intensity_jump:
                    forbidden_pairs.append((i, j))
                    continue
                penalty = intensity_jump + 0.2 * abs(int(actions[i]['frequency']) - int(actions[j]['frequency']))
                pairs.append({'from_idx': i, 'to_idx': j, 'penalty': float(penalty)})
    return pairs, forbidden_pairs


def _build_transition_tables(
    row: pd.Series,
    actions: list[dict[str, Any]],
    clinical_rules: dict,
    intervention_config: dict,
    calibration: dict[str, Any] | None,
) -> dict[str, dict[int, tuple[float, float]]]:
    tables: dict[str, dict[int, tuple[float, float]]] = {}
    for scenario_name, factor in intervention_config['scenarios'].items():
        scenario_table: dict[int, tuple[float, float]] = {}
        for action_idx, action in enumerate(actions):
            latent_gain, tanshi_gain = estimate_state_gains(
                row,
                int(action['tcm_level']),
                int(action['intensity']),
                int(action['frequency']),
                int(action['months']),
                float(factor),
                clinical_rules,
                intervention_config,
                calibration,
            )
            scenario_table[action_idx] = (float(latent_gain), float(tanshi_gain))
        tables[str(scenario_name)] = scenario_table
    return tables


def _solver_status(result: Any) -> str:
    status_map = {
        0: 'Optimal',
        1: 'IterationLimit',
        2: 'Infeasible',
        3: 'Unbounded',
        4: 'SolverError',
    }
    return status_map.get(int(getattr(result, 'status', 4)), 'SolverError')


def optimize_patient_plan(
    row: pd.Series,
    clinical_rules: dict,
    intervention_config: dict,
    calibration: dict[str, Any] | None = None,
    budget_override: float | None = None,
    optimize_for: str = 'weighted',
) -> dict:
    actions = _build_action_space(row, clinical_rules, intervention_config)
    if not actions:
        return {'sample_id': int(row['sample_id']), 'status': 'infeasible', 'solver_status': 'no_actions'}

    stage_actions = _build_stage_action_map(actions)
    pair_data, forbidden_pairs = _build_pair_data(
        actions,
        stage_actions,
        max_intensity_jump=int(intervention_config.get('max_intensity_jump', 1)),
    )
    response_profile = build_patient_response_profile(row, calibration)
    tolerance_limit = float(tolerance_capacity(row['activity_total'], int(row['age_group']), intervention_config['tolerance']))
    transition_tables = _build_transition_tables(row, actions, clinical_rules, intervention_config, calibration)
    scenarios = list(transition_tables.keys())
    objective_weights = intervention_config['objective_weights']
    max_budget = float(budget_override if budget_override is not None else clinical_rules['budget']['six_month_total_max'])
    n_actions = len(actions)
    n_pairs = len(pair_data)
    eta_idx = n_actions + n_pairs
    n_vars = eta_idx + 1

    cost_coeffs = np.asarray([float(action['cost']) for action in actions], dtype=float)
    burden_coeffs = np.asarray([float(action['burden']) for action in actions], dtype=float)
    pair_penalties = np.asarray([float(pair['penalty']) for pair in pair_data], dtype=float)
    max_total_burden = max(tolerance_limit * max(len(stage_actions), 1), 1.0)

    constraints: list[LinearConstraint] = []

    for stage_idx, indices in stage_actions.items():
        row_vec = np.zeros(n_vars, dtype=float)
        row_vec[indices] = 1.0
        constraints.append(LinearConstraint(row_vec, 1.0, 1.0))

        burden_row = np.zeros(n_vars, dtype=float)
        burden_row[indices] = burden_coeffs[indices]
        constraints.append(LinearConstraint(burden_row, -np.inf, tolerance_limit))

    budget_row = np.zeros(n_vars, dtype=float)
    budget_row[:n_actions] = cost_coeffs
    constraints.append(LinearConstraint(budget_row, -np.inf, max_budget))

    total_burden_row = np.zeros(n_vars, dtype=float)
    total_burden_row[:n_actions] = burden_coeffs
    constraints.append(LinearConstraint(total_burden_row, -np.inf, max_total_burden))

    for from_idx, to_idx in forbidden_pairs:
        forbidden_row = np.zeros(n_vars, dtype=float)
        forbidden_row[int(from_idx)] = 1.0
        forbidden_row[int(to_idx)] = 1.0
        constraints.append(LinearConstraint(forbidden_row, -np.inf, 1.0))

    for pair_idx, pair in enumerate(pair_data):
        y_idx = n_actions + pair_idx
        row1 = np.zeros(n_vars, dtype=float)
        row1[y_idx] = 1.0
        row1[int(pair['from_idx'])] = -1.0
        constraints.append(LinearConstraint(row1, -np.inf, 0.0))

        row2 = np.zeros(n_vars, dtype=float)
        row2[y_idx] = 1.0
        row2[int(pair['to_idx'])] = -1.0
        constraints.append(LinearConstraint(row2, -np.inf, 0.0))

        row3 = np.zeros(n_vars, dtype=float)
        row3[int(pair['from_idx'])] = 1.0
        row3[int(pair['to_idx'])] = 1.0
        row3[y_idx] = -1.0
        constraints.append(LinearConstraint(row3, -np.inf, 1.0))

    latent_start = float(row['latent_state_h'])
    tanshi_start = float(row['constitution_tanshi'])
    for scenario_name in scenarios:
        latent_gains = np.asarray([transition_tables[scenario_name][idx][0] for idx in range(n_actions)], dtype=float)
        tanshi_gains = np.asarray([transition_tables[scenario_name][idx][1] for idx in range(n_actions)], dtype=float)

        latent_nonneg = np.zeros(n_vars, dtype=float)
        latent_nonneg[:n_actions] = latent_gains
        constraints.append(LinearConstraint(latent_nonneg, -np.inf, latent_start))

        tanshi_nonneg = np.zeros(n_vars, dtype=float)
        tanshi_nonneg[:n_actions] = tanshi_gains
        constraints.append(LinearConstraint(tanshi_nonneg, -np.inf, tanshi_start))

        scenario_row = np.zeros(n_vars, dtype=float)
        if optimize_for == 'pareto_tanshi':
            scenario_row[:n_actions] = -tanshi_gains
            scenario_constant = -tanshi_start
        else:
            scenario_row[:n_actions] = (
                float(objective_weights['total_cost']) * cost_coeffs / max(max_budget, 1.0)
                + float(objective_weights['total_burden']) * burden_coeffs / max_total_burden
                - float(objective_weights['final_latent_state']) * latent_gains
                - float(objective_weights['final_tanshi_score']) * tanshi_gains
            )
            if n_pairs:
                scenario_row[n_actions:eta_idx] = float(objective_weights['smoothness']) * pair_penalties / 10.0
            scenario_constant = -(
                float(objective_weights['final_latent_state']) * latent_start
                + float(objective_weights['final_tanshi_score']) * tanshi_start
            )
        scenario_row[eta_idx] = -1.0
        constraints.append(LinearConstraint(scenario_row, -np.inf, scenario_constant))

    c = np.zeros(n_vars, dtype=float)
    c[eta_idx] = 1.0
    lower_bounds = np.zeros(n_vars, dtype=float)
    upper_bounds = np.ones(n_vars, dtype=float)
    upper_bounds[eta_idx] = np.inf
    integrality = np.ones(n_vars, dtype=int)
    integrality[eta_idx] = 0

    result = milp(
        c=c,
        constraints=constraints,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
    )
    solver_status = _solver_status(result)
    if not bool(getattr(result, 'success', False)) or getattr(result, 'x', None) is None:
        return {'sample_id': int(row['sample_id']), 'status': 'infeasible', 'solver_status': solver_status}

    solution = np.asarray(result.x, dtype=float)
    selected_indices = [idx for idx in range(n_actions) if solution[idx] > 0.5]
    selected = sorted(selected_indices, key=lambda idx: int(actions[idx]['stage_idx']))
    plan = [(int(actions[idx]['tcm_level']), int(actions[idx]['intensity']), int(actions[idx]['frequency'])) for idx in selected]

    nominal_key = 'nominal' if 'nominal' in transition_tables else scenarios[0]
    nominal_latent_gain = sum(transition_tables[nominal_key][idx][0] for idx in selected)
    nominal_tanshi_gain = sum(transition_tables[nominal_key][idx][1] for idx in selected)
    total_cost = float(cost_coeffs[selected].sum()) if selected else 0.0
    total_burden = float(burden_coeffs[selected].sum()) if selected else 0.0
    smoothness = float(sum(pair_penalties[pair_idx] * solution[n_actions + pair_idx] for pair_idx in range(n_pairs))) if n_pairs else 0.0
    nominal_objective = (
        float(objective_weights['final_latent_state']) * max(0.0, latent_start - nominal_latent_gain)
        + float(objective_weights['final_tanshi_score']) * max(0.0, tanshi_start - nominal_tanshi_gain)
        + float(objective_weights['total_cost']) * total_cost / max(max_budget, 1.0)
        + float(objective_weights['total_burden']) * total_burden / max_total_burden
        + float(objective_weights['smoothness']) * smoothness / 10.0
    )

    return {
        'sample_id': int(row['sample_id']),
        'status': 'ok',
        'solver_status': solver_status,
        'robust_type': 'scenario_minmax_milp',
        'budget_cap': max_budget,
        'objective_mode': optimize_for,
        'final_latent_state': float(max(0.0, latent_start - nominal_latent_gain)),
        'final_tanshi_score': float(max(0.0, tanshi_start - nominal_tanshi_gain)),
        'total_cost': total_cost,
        'total_burden': total_burden,
        'worst_case_objective': float(solution[eta_idx]),
        'nominal_objective': float(nominal_objective),
        'scenario_gap': float(solution[eta_idx] - nominal_objective),
        'profile_activity_to_tanshi': float(response_profile['activity_to_tanshi']),
        'profile_activity_to_latent': float(response_profile['activity_to_latent']),
        'profile_tanshi_to_latent': float(response_profile['tanshi_to_latent']),
        'plan': plan,
    }


def _optimize_patient_plan_row(
    row_dict: dict[str, Any],
    clinical_rules: dict,
    intervention_config: dict,
    calibration: dict[str, Any] | None,
    budget_override: float | None,
    optimize_for: str,
) -> dict:
    return optimize_patient_plan(
        pd.Series(row_dict),
        clinical_rules,
        intervention_config,
        calibration=calibration,
        budget_override=budget_override,
        optimize_for=optimize_for,
    )


def optimize_population(
    df: pd.DataFrame,
    clinical_rules: dict,
    intervention_config: dict,
    n_jobs: int | None = None,
    budget_override: float | None = None,
    optimize_for: str = 'weighted',
) -> pd.DataFrame:
    calibration = fit_transition_calibration(df, intervention_config)
    nj = int(effective_n_jobs(-1 if n_jobs is None else int(n_jobs)))
    row_dicts = [row.to_dict() for _, row in df.iterrows()]
    if nj == 1 or len(row_dicts) <= 1:
        rows = [
            _optimize_patient_plan_row(d, clinical_rules, intervention_config, calibration, budget_override, optimize_for)
            for d in row_dicts
        ]
    else:
        rows = Parallel(n_jobs=nj)(
            delayed(_optimize_patient_plan_row)(
                d,
                clinical_rules,
                intervention_config,
                calibration,
                budget_override,
                optimize_for,
            )
            for d in row_dicts
        )
    out = pd.DataFrame(rows)
    if 'plan' in out.columns:
        out['first_stage_tcm'] = out['plan'].apply(lambda x: x[0][0] if isinstance(x, list) and x else None)
        out['first_stage_intensity'] = out['plan'].apply(lambda x: x[0][1] if isinstance(x, list) and x else None)
        out['first_stage_frequency'] = out['plan'].apply(lambda x: x[0][2] if isinstance(x, list) and x else None)
    out['calibration_source'] = calibration.get('source', 'default')
    return out
