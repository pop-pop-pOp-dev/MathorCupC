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
