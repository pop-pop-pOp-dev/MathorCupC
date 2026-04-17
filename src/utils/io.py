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
