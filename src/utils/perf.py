"""从项目配置解析并行度等运行参数。"""

from __future__ import annotations

from typing import Any

from joblib import effective_n_jobs


def resolve_n_jobs(config: dict[str, Any] | None) -> int:
    if not config:
        return effective_n_jobs(-1)
    perf = config.get('performance') or {}
    raw = perf.get('n_jobs', -1)
    try:
        return int(effective_n_jobs(int(raw)))
    except (TypeError, ValueError):
        return effective_n_jobs(-1)


def fast_threshold_grid(config: dict[str, Any] | None) -> bool:
    if not config:
        return False
    return bool((config.get('performance') or {}).get('fast_threshold_grid', False))


def use_gpu_linear_algebra(config: dict[str, Any] | None) -> bool:
    if not config:
        return False
    return bool((config.get('performance') or {}).get('use_gpu_linear_algebra', False))
