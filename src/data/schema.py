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
