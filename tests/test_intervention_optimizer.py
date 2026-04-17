import pandas as pd
from models.intervention_optimizer import optimize_patient_plan


def test_optimizer_returns_feasible_or_infeasible():
    row = pd.Series({
        'sample_id': 1,
        'age_group': 2,
        'activity_total': 50,
        'latent_state_h': 60.0,
        'constitution_tanshi': 65.0,
    })
    clinical_rules = {
        'activity_rules': {
            'age_to_intensity': {1: [1, 2, 3], 2: [1, 2, 3], 3: [1, 2], 4: [1, 2], 5: [1]},
            'score_to_intensity': {'low': {'max_score': 39.999, 'allowed': [1]}, 'mid': {'min_score': 40, 'max_score': 59.999, 'allowed': [1, 2]}, 'high': {'min_score': 60, 'allowed': [1, 2, 3]}}
        },
        'exercise': {'single_cost': {1: 3, 2: 5, 3: 8}, 'stable_if_below_frequency': 5, 'monthly_intensity_gain_per_level': 0.03, 'monthly_frequency_gain_per_extra_session': 0.01},
        'tcm': {
            'monthly_cost': {1: 30, 2: 80, 3: 130},
            'monthly_absolute_gain': {1: 1.5, 2: 3.0, 3: 4.5},
            'tcm_allowed_levels_by_tanshi': [{'max_tanshi': 100.0, 'levels': [1, 2, 3]}],
        },
        'budget': {'six_month_total_max': 2000},
    }
    intervention = {
        'stages': [{'name': 'a', 'months': 2}, {'name': 'b', 'months': 2}, {'name': 'c', 'months': 2}],
        'frequency_candidates': [1, 3, 5],
        'max_intensity_jump': 1,
        'scenarios': {'optimistic': 1.1, 'nominal': 1.0, 'conservative': 0.8},
        'objective_weights': {'final_latent_state': 0.35, 'final_tanshi_score': 0.35, 'total_cost': 0.1, 'total_burden': 0.1, 'smoothness': 0.1},
        'burden': {'intensity_weight': 1.0, 'frequency_weight': 0.4, 'change_intensity_weight': 0.8, 'change_frequency_weight': 0.15},
        'synergy': {'enabled': True, 'coefficient': 0.015, 'diminishing_scale': 0.12},
        'tolerance': {'activity_weight': 0.15, 'age_weight': 3.0, 'base_capacity': 4.0},
    }
    result = optimize_patient_plan(row, clinical_rules, intervention, budget_override=800.0, optimize_for='pareto_tanshi')
    assert result['status'] in {'ok', 'infeasible'}
    if result['status'] == 'ok':
        assert result['total_cost'] <= 800.0 + 1e-9
        plan = result['plan']
        assert all(abs(plan[idx][1] - plan[idx - 1][1]) <= 1 for idx in range(1, len(plan)))
        assert result['objective_mode'] == 'pareto_tanshi'
