from __future__ import annotations

import pandas as pd


def summarize_top_rules(rule_df: pd.DataFrame) -> list[str]:
    if rule_df.empty:
        return ['未识别出满足约束的高风险核心组合。']
    lines = []
    for _, row in rule_df.head(5).iterrows():
        lines.append(f"规则：{row['rule']}；覆盖率={row['coverage']:.2f}，纯度={row['purity']:.2f}，提升度={row['lift']:.2f}")
    return lines
