from __future__ import annotations

from typing import Any


def allowed_tcm_levels(constitution_tanshi: float, clinical_rules: dict) -> list[int]:
    """按题面附表2，由当前痰湿积分确定可选中医调理档位。"""
    tcm = clinical_rules.get('tcm', {})
    rules = tcm.get('tcm_allowed_levels_by_tanshi')
    if not rules:
        return [1, 2, 3]
    t = float(constitution_tanshi)
    for r in sorted(rules, key=lambda x: float(x.get('max_tanshi', 100.0))):
        if t <= float(r.get('max_tanshi', 100.0)):
            return [int(x) for x in r.get('levels', [1, 2, 3])]
    return [1, 2, 3]


def exercise_frequency_candidates(clinical_rules: dict, intervention_config: dict) -> list[int]:
    if intervention_config.get('frequency_from_clinical_rules', False):
        rng = clinical_rules.get('exercise', {}).get('frequency_range', [1, 10])
        lo, hi = int(rng[0]), int(rng[1])
        return list(range(lo, hi + 1))
    raw = intervention_config.get('frequency_candidates', [5])
    return [int(x) for x in raw]
