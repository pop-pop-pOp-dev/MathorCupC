from __future__ import annotations

from itertools import combinations
from typing import Dict, List

import pandas as pd


TARGET_FLAG = '__target__'
MASK_FLAG = '__mask__'


def build_rule_target(df: pd.DataFrame) -> pd.Series:
    if 'risk_tier' not in df.columns:
        return pd.Series(False, index=df.index)
    return (df['risk_tier'] == 'high').astype(bool)


def build_candidate_conditions(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """候选条件池：不出现「痰湿标签=1」等把目标写进条件式的项，避免平凡规则。"""
    q_latent = df['latent_state_h'].quantile(0.7)
    q_lipid = df['lipid_deviation_total'].quantile(0.7)
    q_meta = df['metabolic_deviation_total'].quantile(0.7)
    conditions: Dict[str, pd.Series] = {
        '痰湿积分>=60': df['constitution_tanshi'] >= 60,
        '痰湿积分>=80': df['constitution_tanshi'] >= 80,
        '活动总分<40': df['activity_total'] < 40,
        '活动总分<60': df['activity_total'] < 60,
        'BMI偏离>0': df['dev_bmi'] > 0,
        'TG偏离>0': df['dev_tg'] > 0,
        'LDL偏离>0': df['dev_ldl_c'] > 0,
        '综合隐状态高': df['latent_state_h'] >= q_latent,
        '血脂偏离总量高': df['lipid_deviation_total'] >= q_lipid,
        '代谢偏离总量高': df['metabolic_deviation_total'] >= q_meta,
    }
    if 'constitution_tanshi_dominance' in df.columns:
        conditions['痰湿偏颇占优'] = df['constitution_tanshi_dominance'] >= df['constitution_tanshi_dominance'].quantile(0.75)
    if 'dev_fasting_glucose' in df.columns:
        conditions['血糖偏离>0'] = df['dev_fasting_glucose'] > 0
    if 'dev_uric_acid' in df.columns:
        conditions['尿酸偏离>0'] = df['dev_uric_acid'] > 0
    if 'smoking_history' in df.columns:
        conditions['吸烟史=1'] = df['smoking_history'] == 1
    if 'drinking_history' in df.columns:
        conditions['饮酒史=1'] = df['drinking_history'] == 1
    return conditions


def enumerate_candidate_rules(
    df: pd.DataFrame,
    max_rule_size: int = 3,
    min_coverage: float = 0.20,
    min_purity: float = 0.60,
) -> pd.DataFrame:
    target = build_rule_target(df)
    if target.sum() == 0:
        return pd.DataFrame(columns=['rule', 'coverage', 'purity', 'lift', 'size', 'support_n', 'covered_n', 'target_hits', TARGET_FLAG, MASK_FLAG])
    conditions = build_candidate_conditions(df)
    base_rate = target.mean()
    rows: List[dict] = []
    names = list(conditions)
    for size in range(1, max_rule_size + 1):
        for combo in combinations(names, size):
            mask = pd.Series(True, index=df.index)
            for name in combo:
                mask &= conditions[name]
            covered = int(mask.sum())
            if covered == 0:
                continue
            true_positive = int((mask & target).sum())
            coverage = true_positive / max(int(target.sum()), 1)
            purity = true_positive / covered
            lift = purity / max(base_rate, 1e-9)
            if coverage >= min_coverage and purity >= min_purity:
                rows.append(
                    {
                        'rule': ' + '.join(combo),
                        'coverage': float(coverage),
                        'purity': float(purity),
                        'lift': float(lift),
                        'size': size,
                        'support_n': covered,
                        'covered_n': covered,
                        'target_hits': true_positive,
                        TARGET_FLAG: target.copy(),
                        MASK_FLAG: mask.copy(),
                    }
                )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(['size', 'coverage', 'purity', 'lift'], ascending=[True, False, False, False]).reset_index(drop=True)


def _is_redundant(candidate_mask: pd.Series, chosen_masks: list[pd.Series], overlap_threshold: float) -> bool:
    for chosen in chosen_masks:
        overlap = float((candidate_mask & chosen).sum() / max(int(candidate_mask.sum()), 1))
        if overlap >= overlap_threshold:
            return True
    return False


def select_minimal_rule_set(
    candidates: pd.DataFrame,
    target: pd.Series,
    max_rules_kept: int = 12,
    overlap_threshold: float = 0.85,
    min_incremental_coverage: float = 0.05,
) -> pd.DataFrame:
    if candidates.empty or target.sum() == 0:
        return pd.DataFrame(columns=['rule', 'coverage', 'purity', 'lift', 'size', 'support_n', 'covered_n', 'target_hits', 'incremental_coverage', 'selected_order', 'is_core_rule'])

    uncovered = target.copy()
    chosen_rows: list[dict] = []
    chosen_masks: list[pd.Series] = []
    rank = 1
    candidates = candidates.copy()

    while rank <= max_rules_kept and uncovered.any():
        best_idx = None
        best_pos = None
        best_key = None
        best_incremental = 0.0
        for pos, (idx, row) in enumerate(candidates.iterrows()):
            mask = row[MASK_FLAG]
            if _is_redundant(mask, chosen_masks, overlap_threshold):
                continue
            incremental_hits = int((mask & uncovered).sum())
            incremental_coverage = incremental_hits / max(int(target.sum()), 1)
            if incremental_coverage < min_incremental_coverage:
                continue
            key = (incremental_coverage, float(row['purity']), -int(row['size']), float(row['lift']))
            if best_key is None or key > best_key:
                best_key = key
                best_idx = idx
                best_pos = pos
                best_incremental = incremental_coverage
        if best_idx is None or best_pos is None:
            break
        selected_row = candidates.iloc[best_pos]
        selected = selected_row.to_dict()
        selected['incremental_coverage'] = float(best_incremental)
        selected['selected_order'] = rank
        selected['is_core_rule'] = 1
        chosen_rows.append(selected)
        selected_mask = selected_row[MASK_FLAG]
        chosen_masks.append(selected_mask)
        uncovered = uncovered & ~selected_mask
        candidates = candidates.drop(index=best_idx)
        rank += 1

    if not chosen_rows:
        return pd.DataFrame(columns=['rule', 'coverage', 'purity', 'lift', 'size', 'support_n', 'covered_n', 'target_hits', 'incremental_coverage', 'selected_order', 'is_core_rule'])

    out = pd.DataFrame(chosen_rows)
    return out.drop(columns=[TARGET_FLAG, MASK_FLAG], errors='ignore').reset_index(drop=True)


def build_rule_coverage_matrix(df: pd.DataFrame, selected_rules: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    if selected_rules.empty or candidates.empty:
        return pd.DataFrame(columns=['sample_id'])
    matrix = pd.DataFrame({'sample_id': df['sample_id'].values})
    candidate_lookup = candidates.set_index('rule')
    for rule in selected_rules['rule']:
        mask = candidate_lookup.loc[rule, MASK_FLAG]
        matrix[rule] = mask.astype(int).values
    return matrix


def extract_minimal_rules(df: pd.DataFrame, max_rule_size: int = 3, min_coverage: float = 0.20, min_purity: float = 0.60) -> pd.DataFrame:
    candidates = enumerate_candidate_rules(df, max_rule_size=max_rule_size, min_coverage=min_coverage, min_purity=min_purity)
    target = build_rule_target(df)
    selected = select_minimal_rule_set(candidates, target)
    if selected.empty:
        return selected
    return selected.head(12).reset_index(drop=True)
