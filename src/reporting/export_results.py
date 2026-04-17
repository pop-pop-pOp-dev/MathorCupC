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
