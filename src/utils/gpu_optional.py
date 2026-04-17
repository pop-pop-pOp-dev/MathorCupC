"""可选 CuPy/CUDA：小矩阵或未安装时一律回退 NumPy，不改变数值语义。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


def cupy_cuda_available() -> bool:
    try:
        import cupy as cp  # type: ignore[import-not-found]

        try:
            n = int(cp.cuda.runtime.getDeviceCount())
        except Exception:
            return False
        return n > 0
    except Exception:
        return False


def standardize_rows_f64(X: np.ndarray, *, use_gpu: bool) -> np.ndarray:
    """行方向 z-score（用于可选 GPU 路径）；默认 NumPy。"""
    X = np.asarray(X, dtype=np.float64)
    if X.size == 0:
        return X
    if use_gpu and cupy_cuda_available():
        import cupy as cp  # type: ignore[import-not-found]

        g = cp.asarray(X)
        mu = g.mean(axis=1, keepdims=True)
        sigma = g.std(axis=1, keepdims=True) + 1e-12
        out = (g - mu) / sigma
        return cp.asnumpy(out)
    mu = X.mean(axis=1, keepdims=True)
    sigma = X.std(axis=1, keepdims=True) + 1e-12
    return (X - mu) / sigma
