"""期刊向统一视觉：玫瑰红—深蓝渐变与导出参数。"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# 品牌色（玫瑰红系 + 深蓝系）
ROSE_DEEP = '#8b1538'
ROSE = '#c43b5c'
ROSE_LIGHT = '#f5c8d4'
ROSE_PALE = '#fdf2f5'
BLUE_DEEP = '#0a1f44'
BLUE = '#1a3a6e'
BLUE_MID = '#3d6ba8'
BLUE_LIGHT = '#a8c4e8'
NEUTRAL = '#f0f2f5'

CMAP_SEQUENTIAL: LinearSegmentedColormap = LinearSegmentedColormap.from_list(
    'mathorcup_rose_blue_seq',
    [ROSE_PALE, ROSE_LIGHT, ROSE, BLUE_MID, BLUE, BLUE_DEEP],
    N=256,
)

CMAP_DIVERGING: LinearSegmentedColormap = LinearSegmentedColormap.from_list(
    'mathorcup_rose_blue_div',
    [BLUE_DEEP, BLUE_MID, NEUTRAL, ROSE_LIGHT, ROSE_DEEP],
    N=256,
)

TIER_PALETTE = {'low': BLUE_MID, 'medium': ROSE, 'high': ROSE_DEEP}
ANCHOR_LOW = BLUE
ANCHOR_HIGH = ROSE_DEEP


def apply_journal_rcparams() -> None:
    """设置全局 rcParams；中文字体链在 figures 模块首次加载时配置。"""
    mpl.rcParams.update(
        {
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.edgecolor': BLUE_DEEP,
            'axes.labelcolor': BLUE_DEEP,
            'axes.titleweight': 'semibold',
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.color': BLUE_DEEP,
            'ytick.color': BLUE_DEEP,
            'text.color': BLUE_DEEP,
            'grid.color': '#d0d8e8',
            'grid.linestyle': '-',
            'grid.linewidth': 0.6,
            'grid.alpha': 0.85,
            'legend.frameon': True,
            'legend.framealpha': 0.92,
            'legend.edgecolor': '#c8d0e0',
            'figure.dpi': 120,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.04,
            'savefig.facecolor': 'white',
            'savefig.edgecolor': 'none',
            'lines.linewidth': 1.6,
            'patch.linewidth': 0.8,
        }
    )


def save_figure(path: str | Path, fig: mpl.figure.Figure | None = None, export_pdf: bool = True) -> None:
    """高分辨率 PNG；可选同 stem 的 PDF 便于排版。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target_fig = fig or plt.gcf()
    target_fig.savefig(path, format='png')
    if export_pdf:
        pdf_path = path.with_suffix('.pdf')
        target_fig.savefig(pdf_path, format='pdf')
