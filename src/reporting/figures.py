from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from reporting.plot_style import (
    ANCHOR_HIGH,
    ANCHOR_LOW,
    BLUE_DEEP,
    BLUE_LIGHT,
    BLUE_MID,
    CMAP_DIVERGING,
    CMAP_SEQUENTIAL,
    ROSE,
    ROSE_LIGHT,
    TIER_PALETTE,
    apply_journal_rcparams,
    save_figure,
)

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
apply_journal_rcparams()
sns.set_theme(style='whitegrid', palette=[BLUE_MID, ROSE, ROSE_LIGHT])


def _prepare_path(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def plot_risk_distribution(df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    sns.histplot(
        x=df['continuous_risk_score'],
        bins=32,
        kde=True,
        ax=ax,
        color=BLUE_MID,
        edgecolor='white',
        linewidth=0.35,
        kde_kws={'bw_adjust': 1.0},
    )
    ax.set_title('Continuous risk score distribution', fontsize=12, pad=10)
    ax.set_xlabel('Continuous risk score (0–100)')
    ax.set_ylabel('Count')
    for line in ax.lines:
        line.set_color(ROSE)
        line.set_linewidth(2.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    save_figure(path, fig)
    plt.close(fig)


def plot_latent_loading_heatmap(loadings: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    fig_h = max(5.2, 0.36 * len(loadings))
    fig, ax = plt.subplots(figsize=(8.4, fig_h))
    sns.heatmap(
        loadings,
        annot=False,
        cmap=CMAP_DIVERGING,
        center=0,
        linewidths=0.45,
        linecolor='white',
        cbar_kws={'label': 'Loading', 'shrink': 0.75},
        ax=ax,
    )
    ax.set_title('Latent factor loadings', fontsize=12, pad=10)
    ax.set_xlabel('Factor')
    ax.set_ylabel('Feature')
    save_figure(path, fig)
    plt.close(fig)


def plot_latent_loading_stability_forest(summary: pd.DataFrame, path: str | Path, top_n: int = 18) -> None:
    path = _prepare_path(path)
    if summary.empty:
        return
    plot_df = summary.sort_values(['factor_name', 'mean_abs_loading'], ascending=[True, False]).groupby('factor_name', group_keys=False).head(top_n)
    nrows = plot_df['factor_name'].nunique()
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10.2, max(4.2, 0.34 * len(plot_df))), squeeze=False)
    for ax, (factor_name, group) in zip(axes.ravel(), plot_df.groupby('factor_name')):
        group = group.sort_values('mean_abs_loading', ascending=True)
        xerr = np.vstack(
            [
                group['mean_abs_loading'] - group['abs_ci_lower'],
                group['abs_ci_upper'] - group['mean_abs_loading'],
            ]
        )
        ax.errorbar(
            x=group['mean_abs_loading'],
            y=group['feature'],
            xerr=xerr,
            fmt='o',
            color=BLUE_MID,
            ecolor=ROSE_LIGHT,
            elinewidth=1.0,
            capsize=3,
            markersize=5,
        )
        ax.set_title(f'{factor_name} — loading stability', fontsize=11)
        ax.set_xlabel('Mean |loading| (95% CI)')
        ax.set_ylabel('')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    fig.suptitle('Bootstrap stability of factor loadings', fontsize=12, y=1.01)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_latent_score_stability_boxplot(score_stability: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if score_stability.empty:
        return
    plot_df = score_stability.copy()
    metric_df = plot_df.melt(
        id_vars=['bootstrap_id', 'factor_name'],
        value_vars=['pearson_corr', 'spearman_corr'],
        var_name='metric',
        value_name='value',
    )
    fig, ax = plt.subplots(figsize=(10.2, 5.0))
    sns.boxplot(
        data=metric_df,
        x='factor_name',
        y='value',
        hue='metric',
        ax=ax,
        palette={'pearson_corr': BLUE_MID, 'spearman_corr': ROSE},
        linewidth=0.9,
        fliersize=3,
    )
    ax.set_title('Latent score stability across bootstraps', fontsize=12, pad=10)
    ax.set_xlabel('Factor')
    ax.set_ylabel('Correlation / overlap')
    ax.tick_params(axis='x', rotation=22)
    ax.legend(title='Metric', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_risk_score_by_tier(df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    order = ['low', 'medium', 'high']
    palette = [TIER_PALETTE[o] for o in order]
    sns.boxplot(
        data=df,
        x='risk_tier',
        y='continuous_risk_score',
        order=order,
        hue='risk_tier',
        hue_order=order,
        dodge=False,
        legend=False,
        ax=ax,
        palette=palette,
        linewidth=1.0,
    )
    ax.set_title('Continuous risk score by risk tier', fontsize=12, pad=10)
    ax.set_xlabel('Risk tier')
    ax.set_ylabel('Continuous risk score')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_risk_threshold_heatmap(grid: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if grid.empty:
        return
    pivot = grid.pivot_table(index='t2', columns='t1', values='objective', aggfunc='max')
    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    sns.heatmap(
        pivot.sort_index(ascending=False),
        cmap=CMAP_SEQUENTIAL,
        linewidths=0.25,
        linecolor='white',
        cbar_kws={'label': 'Objective', 'shrink': 0.82},
        ax=ax,
    )
    ax.set_title('Threshold search objective surface', fontsize=12, pad=10)
    ax.set_xlabel(r'$t_1$ (low $\to$ medium)')
    ax.set_ylabel(r'$t_2$ (medium $\to$ high)')
    save_figure(path, fig)
    plt.close(fig)


def plot_risk_anchor_overlay(df: pd.DataFrame, thresholds: dict, path: str | Path) -> None:
    path = _prepare_path(path)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    sns.histplot(
        x=df['continuous_risk_score'],
        bins=32,
        stat='density',
        color=BLUE_LIGHT,
        alpha=0.55,
        edgecolor='white',
        linewidth=0.35,
        ax=ax,
        label='All patients',
    )
    low_scores = df.loc[df['low_anchor'] == 1, 'continuous_risk_score']
    high_scores = df.loc[df['high_anchor'] == 1, 'continuous_risk_score']
    if not low_scores.empty:
        sns.kdeplot(x=low_scores, color=ANCHOR_LOW, linewidth=2.2, label='Low-profile anchors', ax=ax)
    if not high_scores.empty:
        sns.kdeplot(x=high_scores, color=ANCHOR_HIGH, linewidth=2.2, label='High-profile anchors', ax=ax)
    t1 = float(thresholds['low_to_medium_threshold'])
    t2 = float(thresholds['medium_to_high_threshold'])
    ax.axvline(t1, color=BLUE_MID, linestyle='--', lw=1.8, label=r'$t_1$')
    ax.axvline(t2, color=ROSE, linestyle='-.', lw=1.8, label=r'$t_2$')
    ax.set_title('Risk score density with anchors and thresholds', fontsize=12, pad=10)
    ax.set_xlabel('Continuous risk score')
    ax.set_ylabel('Density')
    ax.legend(loc='upper right', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_risk_component_mean_bar(component_df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    component_cols = [c for c in component_df.columns if c.startswith('score_')]
    if not component_cols:
        return
    plot_df = component_df.groupby('risk_tier')[component_cols].mean().reset_index().melt(id_vars='risk_tier', var_name='component', value_name='mean_value')
    fig, ax = plt.subplots(figsize=(10.2, 5.0))
    sns.barplot(
        data=plot_df,
        x='component',
        y='mean_value',
        hue='risk_tier',
        hue_order=['low', 'medium', 'high'],
        ax=ax,
        palette=[TIER_PALETTE['low'], TIER_PALETTE['medium'], TIER_PALETTE['high']],
        edgecolor='white',
        linewidth=0.5,
    )
    ax.set_title('Mean risk score components by tier', fontsize=12, pad=10)
    ax.set_xlabel('Component')
    ax.set_ylabel('Mean contribution (standardized scale)')
    ax.tick_params(axis='x', rotation=35)
    for lab in ax.get_xticklabels():
        lab.set_ha('right')
    ax.legend(title='Tier', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_rule_selection_frequency(rule_stability: pd.DataFrame, path: str | Path, top_n: int = 12) -> None:
    path = _prepare_path(path)
    if rule_stability.empty:
        return
    plot_df = rule_stability.head(top_n).sort_values('selection_frequency', ascending=True)
    fig, ax = plt.subplots(figsize=(10.2, max(4.2, 0.36 * len(plot_df))))
    vals = plot_df['selection_frequency'].to_numpy()
    n = max(len(vals), 1)
    colors = CMAP_SEQUENTIAL(np.linspace(0.22, 0.96, n))
    ax.barh(plot_df['rule'], vals, color=colors, edgecolor='white', linewidth=0.4)
    ax.set_title('Rule selection frequency (bootstrap)', fontsize=12, pad=10)
    ax.set_xlabel('Selection frequency')
    ax.set_ylabel('Rule')
    ax.set_xlim(0, min(1.05, float(vals.max()) * 1.12 + 0.02))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_rule_coverage_waterfall(rules: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if rules.empty or 'incremental_coverage' not in rules.columns:
        return
    plot_df = rules.sort_values('selected_order')
    cumulative = plot_df['incremental_coverage'].cumsum()
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    x = np.arange(len(plot_df))
    ax.bar(x, plot_df['incremental_coverage'], color=BLUE_LIGHT, edgecolor='white', linewidth=0.5, label='Incremental coverage')
    ax.plot(x, cumulative, color=ROSE, marker='o', lw=2.0, markersize=7, label='Cumulative coverage')
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in plot_df['selected_order'].tolist()])
    ax.set_title('Core rule incremental coverage', fontsize=12, pad=10)
    ax.set_xlabel('Selection order')
    ax.set_ylabel('Coverage')
    ax.legend(loc='lower right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_rule_purity_vs_coverage(rules: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if rules.empty:
        return
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    scatter = ax.scatter(
        rules['coverage'],
        rules['purity'],
        c=rules['lift'],
        s=60 + 160 * (rules['size'] / max(rules['size'].max(), 1)),
        cmap=CMAP_SEQUENTIAL,
        alpha=0.88,
        edgecolors=BLUE_DEEP,
        linewidths=0.45,
    )
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label('Lift')
    ax.set_title('Rule purity vs coverage', fontsize=12, pad=10)
    ax.set_xlabel('Coverage')
    ax.set_ylabel('Purity')
    ax.set_xlim(-0.02, min(1.02, float(rules['coverage'].max()) + 0.05))
    ax.set_ylim(-0.02, min(1.02, float(rules['purity'].max()) + 0.05))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)
