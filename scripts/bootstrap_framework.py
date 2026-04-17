from __future__ import annotations

from pathlib import Path
from textwrap import dedent
import shutil

ROOT = Path(__file__).resolve().parents[1]


def write(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")


def maybe_copy(src_name: str, dst_rel: str) -> None:
    src = ROOT / src_name
    dst = ROOT / dst_rel
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build() -> None:
    for rel in [
        'data/raw', 'data/interim', 'data/processed', 'configs', 'src/data', 'src/domain',
        'src/features', 'src/models', 'src/pipeline', 'src/evaluation', 'src/reporting',
        'src/utils', 'scripts', 'tests', 'outputs', 'docs', 'notebooks'
    ]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    maybe_copy('附件1：样例数据.xlsx', 'data/raw/附件1：样例数据.xlsx')
    maybe_copy('sample_preview.tsv', 'data/raw/sample_preview.tsv')
    maybe_copy('c_topic_extracted.txt', 'data/raw/c_topic_extracted.txt')
    maybe_copy('2026年第十六届MathorCup数学应用挑战赛题目—C题.pdf', 'data/raw/2026年第十六届MathorCup数学应用挑战赛题目—C题.pdf')
    maybe_copy('整体技术路线框架.md', 'docs/整体技术路线框架.md')

    write('pyproject.toml', '''
        [build-system]
        requires = ["setuptools>=68", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "mathorcup-c"
        version = "0.1.0"
        description = "MathorCup C题研究型代码框架"
        readme = "README.md"
        requires-python = ">=3.11"
        dependencies = [
          "pandas>=2.2",
          "numpy>=2.0",
          "scipy>=1.13",
          "scikit-learn>=1.5",
          "statsmodels>=0.14",
          "pyyaml>=6.0",
          "openpyxl>=3.1",
          "matplotlib>=3.8",
          "seaborn>=0.13"
        ]

        [tool.setuptools]
        package-dir = {"" = "src"}

        [tool.setuptools.packages.find]
        where = ["src"]

        [tool.pytest.ini_options]
        pythonpath = ["src"]
        testpaths = ["tests"]
    ''')

    write('README.md', '''
        # MathorCup C题代码框架

        本项目实现 2026 年 MathorCup C题：中老年人群高血脂症的风险预警及干预方案优化 的研究型代码框架。

        ## 核心能力

        - 数据治理与规则校验
        - 临床偏离度与主题特征工程
        - 三视角潜结构与综合隐状态识别
        - 锚定式连续风险分层
        - 痰湿高危核心规则提取
        - 三阶段鲁棒干预优化
        - 稳健性分析与论文资产导出

        ## 快速开始

        ```bash
        python scripts/run_full_pipeline.py
        ```

        单独运行：

        ```bash
        python scripts/run_q1.py
        python scripts/run_q2.py
        python scripts/run_q3.py
        ```
    ''')

    write('.gitignore', '''
        __pycache__/
        *.pyc
        .pytest_cache/
        .venv/
        outputs/
        data/interim/
        data/processed/
        *.png
        *.pdf
        *.svg
    ''')

    write('configs/base.yaml', '''
        seed: 20260417
        paths:
          raw_excel: "data/raw/附件1：样例数据.xlsx"
          sample_preview: "data/raw/sample_preview.tsv"
          topic_text: "data/raw/c_topic_extracted.txt"
          tech_route: "docs/整体技术路线框架.md"
          outputs_dir: "outputs"
        runtime:
          save_intermediate: true
          bootstrap_samples: 50
          plots: true
    ''')

    write('configs/data_schema.yaml', '''
        row_count_expected: 1000
        column_count_expected: 37
        column_mapping:
          样本ID: sample_id
          体质标签: constitution_label
          平和质: constitution_pinghe
          气虚质: constitution_qixu
          阳虚质: constitution_yangxu
          阴虚质: constitution_yinxu
          痰湿质: constitution_tanshi
          湿热质: constitution_shire
          血瘀质: constitution_xueyu
          气郁质: constitution_qiyu
          特禀质: constitution_tebing
          ADL用厕: adl_toilet
          ADL吃饭: adl_eating
          ADL步行: adl_walking
          ADL穿衣: adl_dressing
          ADL洗澡: adl_bathing
          ADL总分: adl_total
          IADL购物: iadl_shopping
          IADL做饭: iadl_cooking
          IADL理财: iadl_finance
          IADL交通: iadl_transport
          IADL服药: iadl_medication
          IADL总分: iadl_total
          活动量表总分（ADL总分+IADL总分）: activity_total
          HDL-C（高密度脂蛋白）: hdl_c
          LDL-C（低密度脂蛋白）: ldl_c
          TG（甘油三酯）: tg
          TC（总胆固醇）: tc
          空腹血糖: fasting_glucose
          血尿酸: uric_acid
          BMI: bmi
          高血脂症二分类标签: hyperlipidemia_label
          血脂异常分型标签（确诊病例）: lipid_abnormality_type
          年龄组: age_group
          性别: sex
          吸烟史: smoking_history
          饮酒史: drinking_history
        groups:
          constitution_scores:
            - constitution_pinghe
            - constitution_qixu
            - constitution_yangxu
            - constitution_yinxu
            - constitution_tanshi
            - constitution_shire
            - constitution_xueyu
            - constitution_qiyu
            - constitution_tebing
          adl_items:
            - adl_toilet
            - adl_eating
            - adl_walking
            - adl_dressing
            - adl_bathing
          iadl_items:
            - iadl_shopping
            - iadl_cooking
            - iadl_finance
            - iadl_transport
            - iadl_medication
          lipid_core:
            - hdl_c
            - ldl_c
            - tg
            - tc
          metabolic_related:
            - fasting_glucose
            - uric_acid
            - bmi
          background:
            - age_group
            - sex
            - smoking_history
            - drinking_history
    ''')

    write('configs/clinical_rules.yaml', '''
        lipid_ranges:
          tc: [3.1, 6.2]
          tg: [0.56, 1.7]
          ldl_c: [2.07, 3.1]
          hdl_c: [1.04, 1.55]
        metabolic_ranges:
          fasting_glucose: [3.9, 6.1]
          bmi: [18.5, 23.9]
        uric_acid_ranges:
          male: [208, 428]
          female: [155, 357]
        activity_rules:
          age_to_intensity:
            1: [1, 2, 3]
            2: [1, 2, 3]
            3: [1, 2]
            4: [1, 2]
            5: [1]
          score_to_intensity:
            low:
              max_score: 39.999
              allowed: [1]
            mid:
              min_score: 40
              max_score: 59.999
              allowed: [1, 2]
            high:
              min_score: 60
              allowed: [1, 2, 3]
        exercise:
          duration_minutes:
            1: 10
            2: 20
            3: 30
          single_cost:
            1: 3
            2: 5
            3: 8
          frequency_range: [1, 10]
          stable_if_below_frequency: 5
          monthly_intensity_gain_per_level: 0.03
          monthly_frequency_gain_per_extra_session: 0.01
        tcm:
          monthly_cost:
            1: 30
            2: 80
            3: 130
          monthly_absolute_gain:
            1: 1.5
            2: 3.0
            3: 4.5
        budget:
          six_month_total_max: 2000
    ''')

    write('configs/risk_model.yaml', '''
        latent_state:
          view_weights:
            constitution: 0.35
            activity: 0.25
            metabolic: 0.40
          bootstrap_samples: 50
        risk_score:
          weights:
            latent_state: 0.30
            lipid_deviation_total: 0.35
            metabolic_deviation_total: 0.15
            activity_risk: 0.10
            constitution_tanshi: 0.05
            background_risk: 0.05
          interaction_weights:
            tanshi_x_low_activity: 0.08
            tanshi_x_bmi_deviation: 0.06
            metabolic_x_low_activity: 0.05
        anchors:
          low_latent_quantile: 0.35
          high_latent_quantile: 0.65
          low_activity_cutoff: 40
          adequate_activity_cutoff: 60
        thresholds:
          search_grid_points: 60
          bootstrap_samples: 50
        rules:
          max_rule_size: 3
          min_coverage: 0.20
          min_purity: 0.60
    ''')

    write('configs/intervention.yaml', '''
        stages:
          - name: activation
            months: 2
          - name: consolidation
            months: 2
          - name: maintenance
            months: 2
        frequency_candidates: [1, 3, 5, 7, 10]
        beam_width: 64
        scenarios:
          optimistic: 1.15
          nominal: 1.00
          conservative: 0.80
        objective_weights:
          final_latent_state: 0.35
          final_tanshi_score: 0.35
          total_cost: 0.10
          total_burden: 0.10
          smoothness: 0.10
        burden:
          intensity_weight: 1.0
          frequency_weight: 0.4
          change_intensity_weight: 0.8
          change_frequency_weight: 0.15
        synergy:
          enabled: true
          coefficient: 0.015
          diminishing_scale: 0.12
        tolerance:
          activity_weight: 0.15
          age_weight: 3.0
          base_capacity: 4.0
    ''')

    write('src/__init__.py', '')
    write('src/data/__init__.py', '')
    write('src/domain/__init__.py', '')
    write('src/features/__init__.py', '')
    write('src/models/__init__.py', '')
    write('src/pipeline/__init__.py', '')
    write('src/evaluation/__init__.py', '')
    write('src/reporting/__init__.py', '')
    write('src/utils/__init__.py', '')

    write('src/main.py', '''
        from pipeline.runner import run_full_pipeline

        if __name__ == '__main__':
            run_full_pipeline()
    ''')

    write('src/utils/config.py', '''
        from __future__ import annotations

        from pathlib import Path
        from typing import Any, Dict
        import yaml


        def load_yaml(path: str | Path) -> Dict[str, Any]:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}


        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            merged = dict(base)
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged


        def load_project_config(root: str | Path) -> Dict[str, Any]:
            root = Path(root)
            base = load_yaml(root / 'configs' / 'base.yaml')
            schema = load_yaml(root / 'configs' / 'data_schema.yaml')
            clinical = load_yaml(root / 'configs' / 'clinical_rules.yaml')
            risk = load_yaml(root / 'configs' / 'risk_model.yaml')
            intervention = load_yaml(root / 'configs' / 'intervention.yaml')
            merged = deep_merge(base, {'schema': schema})
            merged = deep_merge(merged, {'clinical_rules': clinical})
            merged = deep_merge(merged, {'risk_model': risk})
            merged = deep_merge(merged, {'intervention': intervention})
            merged['project_root'] = str(root)
            return merged
    ''')

    write('src/utils/io.py', '''
        from __future__ import annotations

        from pathlib import Path
        from datetime import datetime
        from typing import Any
        import json


        def ensure_dir(path: str | Path) -> Path:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            return path


        def make_run_dir(root: str | Path, outputs_dir: str = 'outputs') -> Path:
            run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return ensure_dir(Path(root) / outputs_dir / run_name)


        def write_json(path: str | Path, obj: Any) -> None:
            path = Path(path)
            ensure_dir(path.parent)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
    ''')

    write('src/utils/logging_utils.py', '''
        import logging


        def get_logger(name: str) -> logging.Logger:
            logger = logging.getLogger(name)
            if not logger.handlers:
                logger.setLevel(logging.INFO)
                handler = logging.StreamHandler()
                formatter = logging.Formatter('[%(levelname)s] %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            return logger
    ''')

    write('src/utils/seed.py', '''
        import random
        import numpy as np


        def set_seed(seed: int) -> None:
            random.seed(seed)
            np.random.seed(seed)
    ''')

    write('src/data/schema.py', '''
        from __future__ import annotations

        from dataclasses import dataclass
        from typing import Dict, List


        @dataclass(frozen=True)
        class DataSchema:
            row_count_expected: int
            column_count_expected: int
            column_mapping: Dict[str, str]
            groups: Dict[str, List[str]]


        def build_schema(schema_config: dict) -> DataSchema:
            return DataSchema(
                row_count_expected=schema_config['row_count_expected'],
                column_count_expected=schema_config['column_count_expected'],
                column_mapping=schema_config['column_mapping'],
                groups=schema_config['groups'],
            )
    ''')

    write('src/data/loader.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from data.schema import DataSchema


        def load_raw_excel(project_root: str | Path, relative_path: str) -> pd.DataFrame:
            return pd.read_excel(Path(project_root) / relative_path)


        def standardize_columns(df: pd.DataFrame, schema: DataSchema) -> pd.DataFrame:
            missing = [c for c in schema.column_mapping if c not in df.columns]
            if missing:
                raise ValueError(f'Missing expected columns: {missing}')
            standardized = df.rename(columns=schema.column_mapping).copy()
            standardized = standardized[list(schema.column_mapping.values())]
            return standardized
    ''')

    write('src/data/cleaning.py', '''
        from __future__ import annotations

        import pandas as pd

        INTEGER_COLUMNS = [
            'sample_id', 'constitution_label', 'hyperlipidemia_label', 'lipid_abnormality_type',
            'age_group', 'sex', 'smoking_history', 'drinking_history'
        ]


        def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
            out = df.copy()
            for col in out.columns:
                out[col] = pd.to_numeric(out[col], errors='raise')
            for col in INTEGER_COLUMNS:
                out[col] = out[col].astype(int)
            return out


        def validate_shape(df: pd.DataFrame, expected_rows: int, expected_cols: int) -> None:
            if len(df) != expected_rows:
                raise ValueError(f'Expected {expected_rows} rows, got {len(df)}')
            if df.shape[1] != expected_cols:
                raise ValueError(f'Expected {expected_cols} columns, got {df.shape[1]}')


        def validate_no_missing(df: pd.DataFrame) -> None:
            if df.isna().any().any():
                raise ValueError('Dataset contains missing values')


        def clean_dataset(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
            out = coerce_types(df)
            validate_shape(out, schema['row_count_expected'], schema['column_count_expected'])
            validate_no_missing(out)
            return out
    ''')

    write('src/domain/constitution_logic.py', '''
        from __future__ import annotations

        import pandas as pd

        CONSTITUTION_SCORE_COLUMNS = [
            'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
            'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
        ]


        def constitution_argmax_label(df: pd.DataFrame) -> pd.Series:
            max_idx = df[CONSTITUTION_SCORE_COLUMNS].idxmax(axis=1)
            label_map = {name: idx + 1 for idx, name in enumerate(CONSTITUTION_SCORE_COLUMNS)}
            return max_idx.map(label_map).astype(int)


        def constitution_argmax_mismatch_count(df: pd.DataFrame) -> int:
            return int((constitution_argmax_label(df) != df['constitution_label']).sum())
    ''')

    write('src/domain/clinical_thresholds.py', '''
        from __future__ import annotations

        import numpy as np
        import pandas as pd


        def deviation_from_interval(series: pd.Series, low: float, high: float, power: float = 1.5) -> pd.Series:
            below = np.maximum(low - series, 0)
            above = np.maximum(series - high, 0)
            scale = max(high - low, 1e-6)
            return ((below + above) / scale) ** power


        def uric_acid_deviation(df: pd.DataFrame, male_range: tuple[float, float], female_range: tuple[float, float], power: float = 1.5) -> pd.Series:
            male = df['sex'] == 1
            out = pd.Series(0.0, index=df.index)
            out.loc[male] = deviation_from_interval(df.loc[male, 'uric_acid'], male_range[0], male_range[1], power)
            out.loc[~male] = deviation_from_interval(df.loc[~male, 'uric_acid'], female_range[0], female_range[1], power)
            return out


        def derive_hyperlipidemia_label_by_rules(df: pd.DataFrame) -> pd.Series:
            condition = (df['tc'] > 6.2) | (df['tg'] > 1.7) | (df['ldl_c'] > 3.1) | (df['hdl_c'] < 1.04)
            return condition.astype(int)


        def derive_lipid_type_by_rules(df: pd.DataFrame) -> pd.Series:
            tc_high = df['tc'] > 6.2
            tg_high = df['tg'] > 1.7
            label = np.zeros(len(df), dtype=int)
            label[(tc_high) & (~tg_high)] = 1
            label[(~tc_high) & (tg_high)] = 2
            label[(tc_high) & (tg_high)] = 3
            return pd.Series(label, index=df.index)
    ''')

    write('src/domain/activity_rules.py', '''
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
    ''')

    write('src/domain/intervention_rules.py', '''
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
    ''')

    write('src/data/governance_report.py', '''
        from __future__ import annotations

        from typing import Dict, Any
        import pandas as pd
        from domain.clinical_thresholds import derive_hyperlipidemia_label_by_rules
        from domain.constitution_logic import constitution_argmax_mismatch_count


        def build_governance_report(df: pd.DataFrame) -> Dict[str, Any]:
            derived = derive_hyperlipidemia_label_by_rules(df)
            label_rule_match = int((derived == df['hyperlipidemia_label']).all())
            activity_identity_match = int(((df['adl_total'] + df['iadl_total']) == df['activity_total']).all())
            return {
                'row_count': int(len(df)),
                'column_count': int(df.shape[1]),
                'missing_values_total': int(df.isna().sum().sum()),
                'activity_identity_match': label_rule_match if False else activity_identity_match,
                'label_rule_match': label_rule_match,
                'constitution_label_argmax_mismatch_count': constitution_argmax_mismatch_count(df),
                'hyperlipidemia_distribution': {str(k): int(v) for k, v in df['hyperlipidemia_label'].value_counts().sort_index().items()},
                'constitution_distribution': {str(k): int(v) for k, v in df['constitution_label'].value_counts().sort_index().items()},
            }
    ''')

    write('src/data/feature_registry.py', '''
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
    ''')

    write('src/features/deviation_features.py', '''
        from __future__ import annotations

        import pandas as pd
        from domain.clinical_thresholds import deviation_from_interval, uric_acid_deviation


        def build_deviation_features(df: pd.DataFrame, clinical_rules: dict) -> pd.DataFrame:
            out = pd.DataFrame(index=df.index)
            lipid_ranges = clinical_rules['lipid_ranges']
            metabolic_ranges = clinical_rules['metabolic_ranges']
            uric_ranges = clinical_rules['uric_acid_ranges']
            out['dev_tc'] = deviation_from_interval(df['tc'], *lipid_ranges['tc'])
            out['dev_tg'] = deviation_from_interval(df['tg'], *lipid_ranges['tg'])
            out['dev_ldl_c'] = deviation_from_interval(df['ldl_c'], *lipid_ranges['ldl_c'])
            out['dev_hdl_c'] = deviation_from_interval(df['hdl_c'], *lipid_ranges['hdl_c'])
            out['dev_fasting_glucose'] = deviation_from_interval(df['fasting_glucose'], *metabolic_ranges['fasting_glucose'])
            out['dev_bmi'] = deviation_from_interval(df['bmi'], *metabolic_ranges['bmi'])
            out['dev_uric_acid'] = uric_acid_deviation(df, tuple(uric_ranges['male']), tuple(uric_ranges['female']))
            out['lipid_deviation_total'] = out[['dev_tc', 'dev_tg', 'dev_ldl_c', 'dev_hdl_c']].sum(axis=1)
            out['metabolic_deviation_total'] = out[['dev_fasting_glucose', 'dev_bmi', 'dev_uric_acid']].sum(axis=1)
            return out
    ''')

    write('src/features/activity_features.py', '''
        from __future__ import annotations

        import pandas as pd


        def build_activity_features(df: pd.DataFrame) -> pd.DataFrame:
            out = pd.DataFrame(index=df.index)
            out['adl_share'] = df['adl_total'] / df['activity_total'].replace(0, 1)
            out['iadl_share'] = df['iadl_total'] / df['activity_total'].replace(0, 1)
            out['activity_risk'] = (100 - df['activity_total']) / 100.0
            out['low_activity_flag'] = (df['activity_total'] < 40).astype(int)
            out['mid_activity_flag'] = ((df['activity_total'] >= 40) & (df['activity_total'] < 60)).astype(int)
            out['high_activity_flag'] = (df['activity_total'] >= 60).astype(int)
            return out
    ''')

    write('src/features/constitution_features.py', '''
        from __future__ import annotations

        import pandas as pd
        from domain.constitution_logic import constitution_argmax_label

        CONSTITUTION_SCORE_COLUMNS = [
            'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
            'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
        ]


        def build_constitution_features(df: pd.DataFrame) -> pd.DataFrame:
            out = pd.DataFrame(index=df.index)
            row_sum = df[CONSTITUTION_SCORE_COLUMNS].sum(axis=1).replace(0, 1)
            out['constitution_tanshi_dominance'] = df['constitution_tanshi'] / row_sum
            out['constitution_pinghe_protective'] = df['constitution_pinghe'] / row_sum
            out['constitution_label_argmax_mismatch'] = (constitution_argmax_label(df) != df['constitution_label']).astype(int)
            out['phlegm_dampness_label_flag'] = (df['constitution_label'] == 5).astype(int)
            return out
    ''')

    write('src/features/metabolic_features.py', '''
        from __future__ import annotations

        import pandas as pd


        def build_metabolic_features(df: pd.DataFrame) -> pd.DataFrame:
            out = pd.DataFrame(index=df.index)
            out['age_risk'] = (df['age_group'] - 1) / 4.0
            out['male_flag'] = (df['sex'] == 1).astype(int)
            out['smoking_flag'] = df['smoking_history'].astype(int)
            out['drinking_flag'] = df['drinking_history'].astype(int)
            out['background_risk'] = (out['age_risk'] + 0.3 * out['smoking_flag'] + 0.3 * out['drinking_flag']) / 1.6
            return out
    ''')

    write('src/features/interactions.py', '''
        from __future__ import annotations

        import pandas as pd


        def build_interaction_features(feature_df: pd.DataFrame) -> pd.DataFrame:
            out = pd.DataFrame(index=feature_df.index)
            out['tanshi_x_low_activity'] = feature_df['constitution_tanshi_dominance'] * feature_df['low_activity_flag']
            out['tanshi_x_bmi_deviation'] = feature_df['constitution_tanshi_dominance'] * feature_df['dev_bmi']
            out['metabolic_x_low_activity'] = feature_df['metabolic_deviation_total'] * feature_df['low_activity_flag']
            return out
    ''')

    write('src/models/latent_state.py', '''
        from __future__ import annotations

        from dataclasses import dataclass
        import numpy as np
        import pandas as pd
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        CONSTITUTION_VIEW = [
            'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
            'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing'
        ]
        ACTIVITY_VIEW = ['adl_total', 'iadl_total', 'activity_total', 'activity_risk']
        METABOLIC_VIEW = ['lipid_deviation_total', 'metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid']


        @dataclass
        class LatentStateResult:
            frame: pd.DataFrame
            loadings: pd.DataFrame


        def _first_component(df: pd.DataFrame, columns: list[str], invert: bool = False) -> tuple[pd.Series, pd.Series]:
            x = df[columns].copy()
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x)
            pca = PCA(n_components=1, random_state=0)
            comp = pca.fit_transform(x_scaled).ravel()
            loadings = pd.Series(pca.components_[0], index=columns)
            if invert:
                comp = -comp
                loadings = -loadings
            if loadings.abs().max() > 0:
                if loadings.loc[loadings.abs().idxmax()] < 0:
                    comp = -comp
                    loadings = -loadings
            return pd.Series(comp, index=df.index), loadings


        def fit_latent_state(df: pd.DataFrame, risk_config: dict) -> LatentStateResult:
            constitution_score, constitution_loadings = _first_component(df, CONSTITUTION_VIEW)
            activity_score, activity_loadings = _first_component(df, ACTIVITY_VIEW, invert=True)
            metabolic_score, metabolic_loadings = _first_component(df, METABOLIC_VIEW)
            weights = risk_config['latent_state']['view_weights']
            latent = weights['constitution'] * constitution_score + weights['activity'] * activity_score + weights['metabolic'] * metabolic_score
            latent_scaled = (latent - latent.min()) / (latent.max() - latent.min() + 1e-9) * 100
            out = pd.DataFrame({
                'constitution_factor': constitution_score,
                'activity_factor': activity_score,
                'metabolic_factor': metabolic_score,
                'latent_state_h': latent_scaled,
            }, index=df.index)
            loadings = pd.concat([
                constitution_loadings.rename('constitution_factor'),
                activity_loadings.rename('activity_factor'),
                metabolic_loadings.rename('metabolic_factor'),
            ], axis=1).fillna(0)
            return LatentStateResult(frame=out, loadings=loadings)
    ''')

    write('src/models/risk_score.py', '''
        from __future__ import annotations

        import numpy as np
        import pandas as pd


        def normalize_series(series: pd.Series) -> pd.Series:
            return (series - series.min()) / (series.max() - series.min() + 1e-9)


        def build_continuous_risk_score(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
            weights = risk_config['risk_score']['weights']
            iweights = risk_config['risk_score']['interaction_weights']
            parts = {
                'latent_state': normalize_series(df['latent_state_h']),
                'lipid_deviation_total': normalize_series(df['lipid_deviation_total']),
                'metabolic_deviation_total': normalize_series(df['metabolic_deviation_total']),
                'activity_risk': normalize_series(df['activity_risk']),
                'constitution_tanshi': normalize_series(df['constitution_tanshi']),
                'background_risk': normalize_series(df['background_risk']),
            }
            score = (
                weights['latent_state'] * parts['latent_state']
                + weights['lipid_deviation_total'] * parts['lipid_deviation_total']
                + weights['metabolic_deviation_total'] * parts['metabolic_deviation_total']
                + weights['activity_risk'] * parts['activity_risk']
                + weights['constitution_tanshi'] * parts['constitution_tanshi']
                + weights['background_risk'] * parts['background_risk']
                + iweights['tanshi_x_low_activity'] * normalize_series(df['tanshi_x_low_activity'])
                + iweights['tanshi_x_bmi_deviation'] * normalize_series(df['tanshi_x_bmi_deviation'])
                + iweights['metabolic_x_low_activity'] * normalize_series(df['metabolic_x_low_activity'])
            )
            score = normalize_series(score) * 100
            return pd.DataFrame({'continuous_risk_score': score}, index=df.index)


        def build_anchor_flags(df: pd.DataFrame, risk_config: dict) -> pd.DataFrame:
            anchors = risk_config['anchors']
            low_latent_cut = df['latent_state_h'].quantile(anchors['low_latent_quantile'])
            high_latent_cut = df['latent_state_h'].quantile(anchors['high_latent_quantile'])
            low_anchor = (
                (df['hyperlipidemia_label'] == 0)
                & (df['latent_state_h'] <= low_latent_cut)
                & (df['activity_total'] >= anchors['adequate_activity_cutoff'])
            )
            high_anchor = (
                (df['hyperlipidemia_label'] == 1)
                & (df['latent_state_h'] >= high_latent_cut)
                & (df['lipid_deviation_total'] > df['lipid_deviation_total'].median())
            )
            return pd.DataFrame({'low_anchor': low_anchor.astype(int), 'high_anchor': high_anchor.astype(int)})
    ''')

    write('src/models/thresholding.py', '''
        from __future__ import annotations

        import numpy as np
        import pandas as pd


        def search_risk_thresholds(score: pd.Series, low_anchor: pd.Series, high_anchor: pd.Series, grid_points: int = 60) -> tuple[float, float]:
            low_grid = np.linspace(score.quantile(0.05), score.quantile(0.70), grid_points)
            high_grid = np.linspace(score.quantile(0.30), score.quantile(0.95), grid_points)
            best = None
            best_obj = -1e18
            for t1 in low_grid:
                for t2 in high_grid:
                    if t2 <= t1:
                        continue
                    low_ok = ((score[low_anchor == 1] < t1).mean() if (low_anchor == 1).any() else 0.0)
                    high_ok = ((score[high_anchor == 1] >= t2).mean() if (high_anchor == 1).any() else 0.0)
                    margin = t2 - t1
                    obj = 0.45 * low_ok + 0.45 * high_ok + 0.10 * margin / 100.0
                    if obj > best_obj:
                        best_obj = obj
                        best = (float(t1), float(t2))
            return best or (float(score.quantile(0.33)), float(score.quantile(0.67)))


        def assign_risk_tier(score: pd.Series, t1: float, t2: float) -> pd.Series:
            tiers = pd.Series('medium', index=score.index)
            tiers.loc[score < t1] = 'low'
            tiers.loc[score >= t2] = 'high'
            return tiers
    ''')

    write('src/models/rule_mining.py', '''
        from __future__ import annotations

        from itertools import combinations
        from typing import Dict, List
        import pandas as pd


        def build_candidate_conditions(df: pd.DataFrame) -> Dict[str, pd.Series]:
            q_latent = df['latent_state_h'].quantile(0.7)
            q_lipid = df['lipid_deviation_total'].quantile(0.7)
            q_meta = df['metabolic_deviation_total'].quantile(0.7)
            conditions = {
                '痰湿标签=1': df['phlegm_dampness_label_flag'] == 1,
                '痰湿积分>=60': df['constitution_tanshi'] >= 60,
                '活动总分<40': df['activity_total'] < 40,
                '活动总分<60': df['activity_total'] < 60,
                'BMI偏离>0': df['dev_bmi'] > 0,
                'TG偏离>0': df['dev_tg'] > 0,
                'LDL偏离>0': df['dev_ldl_c'] > 0,
                '综合隐状态高': df['latent_state_h'] >= q_latent,
                '血脂偏离总量高': df['lipid_deviation_total'] >= q_lipid,
                '代谢偏离总量高': df['metabolic_deviation_total'] >= q_meta,
            }
            return conditions


        def extract_minimal_rules(df: pd.DataFrame, max_rule_size: int = 3, min_coverage: float = 0.20, min_purity: float = 0.60) -> pd.DataFrame:
            target = (df['phlegm_dampness_label_flag'] == 1) & (df['risk_tier'] == 'high')
            if target.sum() == 0:
                return pd.DataFrame(columns=['rule', 'coverage', 'purity', 'lift', 'size'])
            conditions = build_candidate_conditions(df)
            base_rate = target.mean()
            rows: List[dict] = []
            names = list(conditions)
            for size in range(1, max_rule_size + 1):
                for combo in combinations(names, size):
                    mask = pd.Series(True, index=df.index)
                    for name in combo:
                        mask &= conditions[name]
                    covered = mask.sum()
                    if covered == 0:
                        continue
                    true_positive = (mask & target).sum()
                    coverage = true_positive / max(int(target.sum()), 1)
                    purity = true_positive / covered
                    lift = purity / max(base_rate, 1e-9)
                    if coverage >= min_coverage and purity >= min_purity:
                        rows.append({
                            'rule': ' + '.join(combo),
                            'coverage': float(coverage),
                            'purity': float(purity),
                            'lift': float(lift),
                            'size': size,
                        })
            out = pd.DataFrame(rows)
            if out.empty:
                return out
            out = out.sort_values(['size', 'coverage', 'purity', 'lift'], ascending=[True, False, False, False]).drop_duplicates('rule')
            return out.head(12).reset_index(drop=True)
    ''')

    write('src/models/patient_state.py', '''
        from __future__ import annotations

        import pandas as pd


        def build_patient_state_table(df: pd.DataFrame) -> pd.DataFrame:
            cols = [
                'sample_id', 'constitution_label', 'constitution_tanshi', 'activity_total', 'age_group',
                'bmi', 'uric_acid', 'fasting_glucose', 'smoking_history', 'drinking_history',
                'latent_state_h', 'continuous_risk_score', 'risk_tier'
            ]
            out = df[cols].copy()
            out['is_phlegm_patient'] = (out['constitution_label'] == 5).astype(int)
            return out
    ''')

    write('src/models/intervention_optimizer.py', '''
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
    ''')

    write('src/evaluation/stability.py', '''
        from __future__ import annotations

        import numpy as np
        import pandas as pd
        from models.latent_state import fit_latent_state
        from models.thresholding import search_risk_thresholds


        def bootstrap_latent_state_stability(df: pd.DataFrame, risk_config: dict, n_boot: int = 20, seed: int = 20260417) -> pd.DataFrame:
            rng = np.random.default_rng(seed)
            records = []
            for i in range(n_boot):
                sample_idx = rng.choice(df.index.to_numpy(), size=len(df), replace=True)
                sampled = df.loc[sample_idx].reset_index(drop=True)
                result = fit_latent_state(sampled, risk_config)
                loads = result.loadings.abs().mean(axis=1)
                for name, value in loads.items():
                    records.append({'bootstrap_id': i, 'feature': name, 'mean_abs_loading': float(value)})
            out = pd.DataFrame(records)
            return out.groupby('feature', as_index=False)['mean_abs_loading'].agg(['mean', 'std']).reset_index()


        def bootstrap_threshold_stability(score: pd.Series, low_anchor: pd.Series, high_anchor: pd.Series, n_boot: int = 20, seed: int = 20260417) -> pd.DataFrame:
            rng = np.random.default_rng(seed)
            records = []
            idx = np.arange(len(score))
            for i in range(n_boot):
                sample = rng.choice(idx, size=len(idx), replace=True)
                t1, t2 = search_risk_thresholds(score.iloc[sample].reset_index(drop=True), low_anchor.iloc[sample].reset_index(drop=True), high_anchor.iloc[sample].reset_index(drop=True))
                records.append({'bootstrap_id': i, 't1': t1, 't2': t2})
            return pd.DataFrame(records)
    ''')

    write('src/evaluation/calibration.py', '''
        from __future__ import annotations

        import pandas as pd


        def summarize_risk_tiers(df: pd.DataFrame) -> pd.DataFrame:
            summary = df.groupby('risk_tier').agg(
                sample_count=('sample_id', 'count'),
                avg_latent_state=('latent_state_h', 'mean'),
                avg_activity_total=('activity_total', 'mean'),
                avg_tanshi=('constitution_tanshi', 'mean'),
                confirmed_rate=('hyperlipidemia_label', 'mean'),
            )
            return summary.reset_index()
    ''')

    write('src/evaluation/robustness.py', '''
        from __future__ import annotations

        import pandas as pd


        def summarize_optimization_robustness(plan_df: pd.DataFrame) -> pd.DataFrame:
            if plan_df.empty:
                return pd.DataFrame()
            cols = [c for c in ['final_latent_state', 'final_tanshi_score', 'total_cost', 'total_burden'] if c in plan_df.columns]
            return plan_df[cols].agg(['mean', 'std', 'min', 'max']).T.reset_index().rename(columns={'index': 'metric'})
    ''')

    write('src/evaluation/diagnostics.py', '''
        from __future__ import annotations

        import pandas as pd


        def build_basic_diagnostics(df: pd.DataFrame) -> dict:
            return {
                'n_samples': int(len(df)),
                'risk_tier_distribution': {str(k): int(v) for k, v in df['risk_tier'].value_counts().items()} if 'risk_tier' in df else {},
                'phlegm_patient_count': int((df['constitution_label'] == 5).sum()) if 'constitution_label' in df else 0,
            }
    ''')

    write('src/evaluation/report_metrics.py', '''
        from __future__ import annotations

        import pandas as pd


        def compact_metric_table(metrics: dict) -> pd.DataFrame:
            return pd.DataFrame({'metric': list(metrics.keys()), 'value': list(metrics.values())})
    ''')

    write('src/reporting/tables.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd


        def save_table(df: pd.DataFrame, path: str | Path) -> None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(path, index=False, encoding='utf-8-sig')
    ''')

    write('src/reporting/figures.py', '''
        from __future__ import annotations

        from pathlib import Path
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd


        def plot_risk_distribution(df: pd.DataFrame, path: str | Path) -> None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            plt.figure(figsize=(8, 4))
            sns.histplot(df['continuous_risk_score'], bins=30, kde=True)
            plt.title('Continuous Risk Score Distribution')
            plt.tight_layout()
            plt.savefig(path)
            plt.close()
    ''')

    write('src/reporting/export_results.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from utils.io import write_json


        def save_frame(df: pd.DataFrame, path: str | Path) -> None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(path, index=False, encoding='utf-8-sig')


        def save_payload(payload: dict, path: str | Path) -> None:
            write_json(path, payload)
    ''')

    write('src/reporting/narrative_helpers.py', '''
        from __future__ import annotations

        import pandas as pd


        def summarize_top_rules(rule_df: pd.DataFrame) -> list[str]:
            if rule_df.empty:
                return ['未识别出满足约束的高风险核心组合。']
            lines = []
            for _, row in rule_df.head(5).iterrows():
                lines.append(f"规则：{row['rule']}；覆盖率={row['coverage']:.2f}，纯度={row['purity']:.2f}，提升度={row['lift']:.2f}")
            return lines
    ''')

    write('src/pipeline/stage_01_data.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from data.loader import load_raw_excel, standardize_columns
        from data.schema import build_schema
        from data.cleaning import clean_dataset
        from data.governance_report import build_governance_report
        from data.feature_registry import registry_to_frame
        from features.deviation_features import build_deviation_features
        from features.activity_features import build_activity_features
        from features.constitution_features import build_constitution_features
        from features.metabolic_features import build_metabolic_features
        from features.interactions import build_interaction_features
        from reporting.export_results import save_frame, save_payload


        def run_stage_01_data(config: dict, run_dir: Path) -> pd.DataFrame:
            schema = build_schema(config['schema'])
            raw = load_raw_excel(config['project_root'], config['paths']['raw_excel'])
            std = standardize_columns(raw, schema)
            df = clean_dataset(std, config['schema'])
            deviations = build_deviation_features(df, config['clinical_rules'])
            activity = build_activity_features(df)
            constitution = build_constitution_features(df)
            metabolic = build_metabolic_features(df)
            base = pd.concat([df, deviations, activity, constitution, metabolic], axis=1)
            interactions = build_interaction_features(base)
            enriched = pd.concat([base, interactions], axis=1)
            governance = build_governance_report(enriched)
            stage_dir = run_dir / 'governance'
            save_frame(enriched, stage_dir / 'canonical_dataset.csv')
            save_frame(registry_to_frame(), stage_dir / 'feature_registry.csv')
            save_payload(governance, stage_dir / 'governance_report.json')
            return enriched
    ''')

    write('src/pipeline/stage_02_latent.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from models.latent_state import fit_latent_state
        from evaluation.stability import bootstrap_latent_state_stability
        from reporting.export_results import save_frame


        def run_stage_02_latent(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
            result = fit_latent_state(df, config['risk_model'])
            out = pd.concat([df, result.frame], axis=1)
            stability = bootstrap_latent_state_stability(out, config['risk_model'], n_boot=min(20, config['runtime']['bootstrap_samples']))
            stage_dir = run_dir / 'latent'
            save_frame(result.loadings.reset_index().rename(columns={'index': 'feature'}), stage_dir / 'latent_loadings.csv')
            save_frame(result.frame.reset_index(drop=True), stage_dir / 'latent_state_scores.csv')
            save_frame(stability, stage_dir / 'latent_stability.csv')
            return out
    ''')

    write('src/pipeline/stage_03_risk.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from models.risk_score import build_continuous_risk_score, build_anchor_flags
        from models.thresholding import search_risk_thresholds, assign_risk_tier
        from evaluation.calibration import summarize_risk_tiers
        from evaluation.stability import bootstrap_threshold_stability
        from reporting.export_results import save_frame, save_payload


        def run_stage_03_risk(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
            risk_df = build_continuous_risk_score(df, config['risk_model'])
            anchors = build_anchor_flags(pd.concat([df, risk_df], axis=1), config['risk_model'])
            score = risk_df['continuous_risk_score']
            t1, t2 = search_risk_thresholds(score, anchors['low_anchor'], anchors['high_anchor'], grid_points=config['risk_model']['thresholds']['search_grid_points'])
            tiers = assign_risk_tier(score, t1, t2)
            out = pd.concat([df, risk_df, anchors], axis=1)
            out['risk_tier'] = tiers
            summary = summarize_risk_tiers(out)
            threshold_boot = bootstrap_threshold_stability(score, anchors['low_anchor'], anchors['high_anchor'], n_boot=min(20, config['runtime']['bootstrap_samples']))
            stage_dir = run_dir / 'risk'
            save_frame(out[['sample_id', 'continuous_risk_score', 'risk_tier', 'low_anchor', 'high_anchor']], stage_dir / 'risk_scores.csv')
            save_frame(summary, stage_dir / 'risk_tier_summary.csv')
            save_frame(threshold_boot, stage_dir / 'risk_threshold_bootstrap.csv')
            save_payload({'low_to_medium_threshold': t1, 'medium_to_high_threshold': t2}, stage_dir / 'risk_thresholds.json')
            return out
    ''')

    write('src/pipeline/stage_04_rules.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from models.rule_mining import extract_minimal_rules
        from reporting.export_results import save_frame


        def run_stage_04_rules(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
            rules = extract_minimal_rules(
                df,
                max_rule_size=config['risk_model']['rules']['max_rule_size'],
                min_coverage=config['risk_model']['rules']['min_coverage'],
                min_purity=config['risk_model']['rules']['min_purity'],
            )
            stage_dir = run_dir / 'rules'
            save_frame(rules, stage_dir / 'minimal_rules.csv')
            return rules
    ''')

    write('src/pipeline/stage_05_optimize.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from models.patient_state import build_patient_state_table
        from models.intervention_optimizer import optimize_population
        from reporting.export_results import save_frame


        def run_stage_05_optimize(df: pd.DataFrame, config: dict, run_dir: Path) -> pd.DataFrame:
            patient_state = build_patient_state_table(df)
            phlegm = df[df['constitution_label'] == 5].copy()
            plans = optimize_population(phlegm, config['clinical_rules'], config['intervention'])
            if not plans.empty:
                plans = plans.merge(patient_state[['sample_id', 'risk_tier', 'activity_total', 'age_group', 'constitution_tanshi']], on='sample_id', how='left')
            stage_dir = run_dir / 'optimization'
            save_frame(patient_state, stage_dir / 'patient_state_table.csv')
            save_frame(plans, stage_dir / 'phlegm_patient_plans.csv')
            sample_cases = plans[plans['sample_id'].isin([1, 2, 3])].copy() if not plans.empty else plans
            save_frame(sample_cases, stage_dir / 'sample_1_2_3_plans.csv')
            return plans
    ''')

    write('src/pipeline/stage_06_validate.py', '''
        from __future__ import annotations

        from pathlib import Path
        import pandas as pd
        from evaluation.diagnostics import build_basic_diagnostics
        from evaluation.robustness import summarize_optimization_robustness
        from evaluation.report_metrics import compact_metric_table
        from reporting.export_results import save_frame, save_payload


        def run_stage_06_validate(df: pd.DataFrame, plans: pd.DataFrame, run_dir: Path) -> None:
            diagnostics = build_basic_diagnostics(df)
            robustness = summarize_optimization_robustness(plans)
            stage_dir = run_dir / 'validation'
            save_payload(diagnostics, stage_dir / 'diagnostics.json')
            save_frame(compact_metric_table(diagnostics), stage_dir / 'diagnostics_table.csv')
            if not robustness.empty:
                save_frame(robustness, stage_dir / 'optimization_robustness.csv')
    ''')

    write('src/pipeline/runner.py', '''
        from __future__ import annotations

        from pathlib import Path
        from utils.config import load_project_config
        from utils.io import make_run_dir
        from utils.logging_utils import get_logger
        from utils.seed import set_seed
        from pipeline.stage_01_data import run_stage_01_data
        from pipeline.stage_02_latent import run_stage_02_latent
        from pipeline.stage_03_risk import run_stage_03_risk
        from pipeline.stage_04_rules import run_stage_04_rules
        from pipeline.stage_05_optimize import run_stage_05_optimize
        from pipeline.stage_06_validate import run_stage_06_validate
        from reporting.figures import plot_risk_distribution

        logger = get_logger(__name__)


        def run_full_pipeline(project_root: str | Path | None = None):
            project_root = Path(project_root or Path(__file__).resolve().parents[2])
            config = load_project_config(project_root)
            set_seed(config['seed'])
            run_dir = make_run_dir(project_root, config['paths']['outputs_dir'])
            logger.info('Running stage 01: data governance and features')
            df = run_stage_01_data(config, run_dir)
            logger.info('Running stage 02: latent state')
            df = run_stage_02_latent(df, config, run_dir)
            logger.info('Running stage 03: risk stratification')
            df = run_stage_03_risk(df, config, run_dir)
            logger.info('Running stage 04: rule extraction')
            run_stage_04_rules(df, config, run_dir)
            logger.info('Running stage 05: intervention optimization')
            plans = run_stage_05_optimize(df, config, run_dir)
            logger.info('Running stage 06: validation')
            run_stage_06_validate(df, plans, run_dir)
            plot_risk_distribution(df, run_dir / 'risk' / 'continuous_risk_score.png')
            logger.info('Pipeline finished: %s', run_dir)
            return run_dir
    ''')

    write('scripts/run_full_pipeline.py', '''
        from __future__ import annotations

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from pipeline.runner import run_full_pipeline

        if __name__ == '__main__':
            run_full_pipeline(Path(__file__).resolve().parents[1])
    ''')

    write('scripts/run_q1.py', '''
        from __future__ import annotations

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from utils.config import load_project_config
        from utils.io import make_run_dir
        from utils.seed import set_seed
        from pipeline.stage_01_data import run_stage_01_data
        from pipeline.stage_02_latent import run_stage_02_latent

        root = Path(__file__).resolve().parents[1]
        config = load_project_config(root)
        set_seed(config['seed'])
        run_dir = make_run_dir(root, config['paths']['outputs_dir'])
        df = run_stage_01_data(config, run_dir)
        run_stage_02_latent(df, config, run_dir)
    ''')

    write('scripts/run_q2.py', '''
        from __future__ import annotations

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from utils.config import load_project_config
        from utils.io import make_run_dir
        from utils.seed import set_seed
        from pipeline.stage_01_data import run_stage_01_data
        from pipeline.stage_02_latent import run_stage_02_latent
        from pipeline.stage_03_risk import run_stage_03_risk
        from pipeline.stage_04_rules import run_stage_04_rules

        root = Path(__file__).resolve().parents[1]
        config = load_project_config(root)
        set_seed(config['seed'])
        run_dir = make_run_dir(root, config['paths']['outputs_dir'])
        df = run_stage_01_data(config, run_dir)
        df = run_stage_02_latent(df, config, run_dir)
        df = run_stage_03_risk(df, config, run_dir)
        run_stage_04_rules(df, config, run_dir)
    ''')

    write('scripts/run_q3.py', '''
        from __future__ import annotations

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from utils.config import load_project_config
        from utils.io import make_run_dir
        from utils.seed import set_seed
        from pipeline.stage_01_data import run_stage_01_data
        from pipeline.stage_02_latent import run_stage_02_latent
        from pipeline.stage_03_risk import run_stage_03_risk
        from pipeline.stage_05_optimize import run_stage_05_optimize

        root = Path(__file__).resolve().parents[1]
        config = load_project_config(root)
        set_seed(config['seed'])
        run_dir = make_run_dir(root, config['paths']['outputs_dir'])
        df = run_stage_01_data(config, run_dir)
        df = run_stage_02_latent(df, config, run_dir)
        df = run_stage_03_risk(df, config, run_dir)
        run_stage_05_optimize(df, config, run_dir)
    ''')

    write('scripts/make_report_assets.py', '''
        from __future__ import annotations

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
        from pipeline.runner import run_full_pipeline

        if __name__ == '__main__':
            run_full_pipeline(Path(__file__).resolve().parents[1])
    ''')

    write('tests/test_data_rules.py', '''
        import pandas as pd
        from domain.clinical_thresholds import derive_hyperlipidemia_label_by_rules, derive_lipid_type_by_rules


        def test_label_rule_derivation():
            df = pd.DataFrame({
                'tc': [5.0, 6.5, 5.0],
                'tg': [1.0, 1.0, 2.0],
                'ldl_c': [2.5, 2.5, 2.5],
                'hdl_c': [1.2, 1.2, 1.2],
            })
            labels = derive_hyperlipidemia_label_by_rules(df)
            assert labels.tolist() == [0, 1, 1]
            lipid_type = derive_lipid_type_by_rules(df)
            assert lipid_type.tolist() == [0, 1, 2]
    ''')

    write('tests/test_feature_logic.py', '''
        import pandas as pd
        from features.activity_features import build_activity_features


        def test_activity_risk_monotonicity():
            df = pd.DataFrame({'adl_total': [10, 20], 'iadl_total': [10, 20], 'activity_total': [20, 40]})
            feats = build_activity_features(df)
            assert feats.loc[0, 'activity_risk'] > feats.loc[1, 'activity_risk']
    ''')

    write('tests/test_latent_state.py', '''
        import numpy as np
        import pandas as pd
        from models.latent_state import fit_latent_state


        def test_latent_state_output_shape():
            rng = np.random.default_rng(0)
            df = pd.DataFrame(rng.normal(size=(20, 18)), columns=[
                'constitution_pinghe', 'constitution_qixu', 'constitution_yangxu', 'constitution_yinxu',
                'constitution_tanshi', 'constitution_shire', 'constitution_xueyu', 'constitution_qiyu', 'constitution_tebing',
                'adl_total', 'iadl_total', 'activity_total', 'activity_risk',
                'lipid_deviation_total', 'metabolic_deviation_total', 'dev_bmi', 'dev_fasting_glucose', 'dev_uric_acid'
            ])
            result = fit_latent_state(df, {'latent_state': {'view_weights': {'constitution': 0.35, 'activity': 0.25, 'metabolic': 0.40}}})
            assert 'latent_state_h' in result.frame.columns
            assert len(result.frame) == len(df)
    ''')

    write('tests/test_risk_thresholds.py', '''
        import pandas as pd
        from models.thresholding import search_risk_thresholds, assign_risk_tier


        def test_threshold_search_orders_thresholds():
            score = pd.Series([10, 20, 30, 70, 80, 90])
            low_anchor = pd.Series([1, 1, 0, 0, 0, 0])
            high_anchor = pd.Series([0, 0, 0, 1, 1, 1])
            t1, t2 = search_risk_thresholds(score, low_anchor, high_anchor, grid_points=10)
            tiers = assign_risk_tier(score, t1, t2)
            assert t1 < t2
            assert set(tiers.unique()) <= {'low', 'medium', 'high'}
    ''')

    write('tests/test_rule_extraction.py', '''
        import pandas as pd
        from models.rule_mining import extract_minimal_rules


        def test_rule_extraction_runs():
            df = pd.DataFrame({
                'phlegm_dampness_label_flag': [1, 1, 1, 0, 0],
                'constitution_tanshi': [70, 65, 30, 20, 10],
                'activity_total': [30, 35, 70, 60, 50],
                'dev_bmi': [1, 1, 0, 0, 0],
                'dev_tg': [1, 1, 0, 0, 0],
                'dev_ldl_c': [1, 0, 0, 0, 0],
                'latent_state_h': [90, 80, 20, 10, 5],
                'lipid_deviation_total': [4, 3, 0, 0, 0],
                'metabolic_deviation_total': [2, 2, 0, 0, 0],
                'risk_tier': ['high', 'high', 'low', 'low', 'medium'],
            })
            out = extract_minimal_rules(df)
            assert isinstance(out, pd.DataFrame)
    ''')

    write('tests/test_intervention_optimizer.py', '''
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
                'tcm': {'monthly_cost': {1: 30, 2: 80, 3: 130}, 'monthly_absolute_gain': {1: 1.5, 2: 3.0, 3: 4.5}},
                'budget': {'six_month_total_max': 2000},
            }
            intervention = {
                'stages': [{'name': 'a', 'months': 2}, {'name': 'b', 'months': 2}, {'name': 'c', 'months': 2}],
                'frequency_candidates': [1, 3, 5],
                'beam_width': 10,
                'scenarios': {'optimistic': 1.1, 'nominal': 1.0, 'conservative': 0.8},
                'objective_weights': {'final_latent_state': 0.35, 'final_tanshi_score': 0.35, 'total_cost': 0.1, 'total_burden': 0.1, 'smoothness': 0.1},
                'burden': {'intensity_weight': 1.0, 'frequency_weight': 0.4, 'change_intensity_weight': 0.8, 'change_frequency_weight': 0.15},
                'synergy': {'enabled': True, 'coefficient': 0.015, 'diminishing_scale': 0.12},
                'tolerance': {'activity_weight': 0.15, 'age_weight': 3.0, 'base_capacity': 4.0},
            }
            result = optimize_patient_plan(row, clinical_rules, intervention)
            assert result['status'] in {'ok', 'infeasible'}
    ''')

    print('Framework files generated successfully.')


if __name__ == '__main__':
    build()
