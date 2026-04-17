from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List
import pandas as pd


@dataclass
class FeatureSpec:
    name: str
    source: str
    direction: str
    stage: str
    description: str


def build_feature_registry() -> List[FeatureSpec]:
    return [
        FeatureSpec('lipid_deviation_total', 'clinical rules', 'higher_is_riskier', 'features', '核心血脂超阈值偏离总量'),
        FeatureSpec('metabolic_deviation_total', 'clinical rules', 'higher_is_riskier', 'features', '血糖、尿酸、BMI 超阈值偏离总量'),
        FeatureSpec('activity_risk', 'activity_total', 'higher_is_riskier', 'features', '活动能力不足风险量'),
        FeatureSpec('constitution_tanshi_dominance', 'constitution scores', 'higher_is_riskier', 'features', '痰湿偏颇主导度'),
        FeatureSpec('latent_state_h', 'latent model', 'higher_is_riskier', 'latent', '综合隐状态'),
        FeatureSpec('continuous_risk_score', 'risk model', 'higher_is_riskier', 'risk', '连续风险势函数输出'),
    ]


def registry_to_frame() -> pd.DataFrame:
    return pd.DataFrame(asdict(x) for x in build_feature_registry())
