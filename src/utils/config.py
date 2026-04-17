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
    performance = load_yaml(root / 'configs' / 'performance.yaml')
    merged = deep_merge(base, {'schema': schema})
    merged = deep_merge(merged, {'clinical_rules': clinical})
    merged = deep_merge(merged, {'risk_model': risk})
    merged = deep_merge(merged, {'intervention': intervention})
    merged = deep_merge(merged, {'performance': performance})
    merged['project_root'] = str(root)
    return merged
