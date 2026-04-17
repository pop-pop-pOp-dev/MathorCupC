from __future__ import annotations

from typing import List


def allowed_intensities_by_age(age_group: int, age_rule_map: dict) -> List[int]:
    return list(age_rule_map[int(age_group)])


def allowed_intensities_by_activity(activity_total: float, score_rules: dict) -> List[int]:
    if activity_total < score_rules['low']['max_score']:
        return list(score_rules['low']['allowed'])
    if score_rules['mid']['min_score'] <= activity_total < score_rules['mid']['max_score']:
        return list(score_rules['mid']['allowed'])
    return list(score_rules['high']['allowed'])


def feasible_intensities(age_group: int, activity_total: float, activity_rules: dict) -> List[int]:
    age_allowed = set(allowed_intensities_by_age(age_group, activity_rules['age_to_intensity']))
    score_allowed = set(allowed_intensities_by_activity(activity_total, activity_rules['score_to_intensity']))
    return sorted(age_allowed.intersection(score_allowed))
