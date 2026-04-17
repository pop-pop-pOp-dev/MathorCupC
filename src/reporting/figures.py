from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style='whitegrid')


def _prepare_path(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def plot_risk_distribution(df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    plt.figure(figsize=(8, 4))
    sns.histplot(x=df['continuous_risk_score'], bins=30, kde=True)
    plt.title('Continuous Risk Score Distribution')
    plt.xlabel('Continuous risk score')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def plot_latent_loading_heatmap(loadings: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    plt.figure(figsize=(8, max(5, 0.35 * len(loadings))))
    sns.heatmap(loadings, annot=False, cmap='RdBu_r', center=0, linewidths=0.4)
    plt.title('Latent Factor Loadings')
    plt.xlabel('Factor')
    plt.ylabel('Feature')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_latent_loading_stability_forest(summary: pd.DataFrame, path: str | Path, top_n: int = 18) -> None:
    path = _prepare_path(path)
    if summary.empty:
        return
    plot_df = summary.sort_values(['factor_name', 'mean_abs_loading'], ascending=[True, False]).groupby('factor_name', group_keys=False).head(top_n)
    nrows = plot_df['factor_name'].nunique()
    _, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(10, max(4, 0.32 * len(plot_df))), squeeze=False)
    for ax, (factor_name, group) in zip(axes.ravel(), plot_df.groupby('factor_name')):
        group = group.sort_values('mean_abs_loading', ascending=True)
        ax.errorbar(
            x=group['mean_abs_loading'],
            y=group['feature'],
            xerr=[group['mean_abs_loading'] - group['abs_ci_lower'], group['abs_ci_upper'] - group['mean_abs_loading']],
            fmt='o',
            color='#1f77b4',
            ecolor='#7f7f7f',
            capsize=3,
        )
        ax.set_title(f'{factor_name} loading stability')
        ax.set_xlabel('Mean absolute loading')
        ax.set_ylabel('Feature')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_latent_score_stability_boxplot(score_stability: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if score_stability.empty:
        return
    plot_df = score_stability.copy()
    metric_df = plot_df.melt(id_vars=['bootstrap_id', 'factor_name'], value_vars=['pearson_corr', 'spearman_corr'], var_name='metric', value_name='value')
    plt.figure(figsize=(10, 5))
    sns.boxplot(data=metric_df, x='factor_name', y='value', hue='metric')
    plt.title('Latent Score Stability Across Bootstraps')
    plt.xlabel('Factor')
    plt.ylabel('Correlation / overlap metric')
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_risk_score_by_tier(df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    plt.figure(figsize=(8, 4.5))
    sns.boxplot(data=df, x='risk_tier', y='continuous_risk_score', order=['low', 'medium', 'high'])
    plt.title('Continuous Risk Score by Risk Tier')
    plt.xlabel('Risk tier')
    plt.ylabel('Continuous risk score')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_risk_threshold_heatmap(grid: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if grid.empty:
        return
    pivot = grid.pivot_table(index='t2', columns='t1', values='objective', aggfunc='max')
    plt.figure(figsize=(8, 6))
    sns.heatmap(pivot.sort_index(ascending=False), cmap='viridis')
    plt.title('Threshold Search Objective Heatmap')
    plt.xlabel('t1')
    plt.ylabel('t2')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_risk_anchor_overlay(df: pd.DataFrame, thresholds: dict, path: str | Path) -> None:
    path = _prepare_path(path)
    plt.figure(figsize=(8, 4.5))
    sns.histplot(x=df['continuous_risk_score'], bins=30, stat='density', color='#9ecae1', alpha=0.6)
    low_scores = df.loc[df['low_anchor'] == 1, 'continuous_risk_score']
    high_scores = df.loc[df['high_anchor'] == 1, 'continuous_risk_score']
    if not low_scores.empty:
        sns.kdeplot(x=low_scores, color='#2ca25f', linewidth=2, label='Low anchors')
    if not high_scores.empty:
        sns.kdeplot(x=high_scores, color='#de2d26', linewidth=2, label='High anchors')
    plt.axvline(float(thresholds['low_to_medium_threshold']), color='#3182bd', linestyle='--', label='t1')
    plt.axvline(float(thresholds['medium_to_high_threshold']), color='#08519c', linestyle='-.', label='t2')
    plt.title('Risk Score Distribution with Anchors and Thresholds')
    plt.xlabel('Continuous risk score')
    plt.ylabel('Density')
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_risk_component_mean_bar(component_df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    component_cols = [c for c in component_df.columns if c.startswith('score_')]
    if not component_cols:
        return
    plot_df = component_df.groupby('risk_tier')[component_cols].mean().reset_index().melt(id_vars='risk_tier', var_name='component', value_name='mean_value')
    plt.figure(figsize=(10, 5))
    sns.barplot(data=plot_df, x='component', y='mean_value', hue='risk_tier', hue_order=['low', 'medium', 'high'])
    plt.title('Mean Risk Score Components by Risk Tier')
    plt.xlabel('Score component')
    plt.ylabel('Mean normalized contribution')
    plt.xticks(rotation=35, ha='right')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_rule_selection_frequency(rule_stability: pd.DataFrame, path: str | Path, top_n: int = 12) -> None:
    path = _prepare_path(path)
    if rule_stability.empty:
        return
    plot_df = rule_stability.head(top_n).sort_values('selection_frequency', ascending=True)
    plt.figure(figsize=(10, max(4, 0.35 * len(plot_df))))
    plt.barh(plot_df['rule'], plot_df['selection_frequency'], color='#3182bd')
    plt.title('Rule Selection Frequency')
    plt.xlabel('Selection frequency')
    plt.ylabel('Rule')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_rule_coverage_waterfall(rules: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if rules.empty or 'incremental_coverage' not in rules.columns:
        return
    plot_df = rules.sort_values('selected_order')
    cumulative = plot_df['incremental_coverage'].cumsum()
    plt.figure(figsize=(9, 4.5))
    plt.bar(range(len(plot_df)), plot_df['incremental_coverage'], color='#9ecae1', label='Incremental coverage')
    plt.plot(range(len(plot_df)), cumulative, color='#08519c', marker='o', label='Cumulative coverage')
    plt.xticks(range(len(plot_df)), [str(v) for v in plot_df['selected_order'].tolist()])
    plt.title('Core Rule Coverage Waterfall')
    plt.xlabel('Selected order')
    plt.ylabel('Coverage')
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def plot_rule_purity_vs_coverage(rules: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if rules.empty:
        return
    plt.figure(figsize=(7.5, 5))
    sns.scatterplot(data=rules, x='coverage', y='purity', size='lift', hue='size', sizes=(60, 220))
    plt.title('Rule Purity vs Coverage')
    plt.xlabel('Coverage')
    plt.ylabel('Purity')
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()
