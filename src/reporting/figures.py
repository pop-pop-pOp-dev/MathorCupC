from __future__ import annotations

import ast
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


def plot_constitution_contribution_bar(contrib: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if contrib.empty:
        return
    plot_df = contrib.sort_values('abs_share', ascending=True)
    fig, ax = plt.subplots(figsize=(9.4, max(4.6, 0.42 * len(plot_df))))
    colors = CMAP_SEQUENTIAL(np.linspace(0.25, 0.95, len(plot_df)))
    ax.barh(plot_df['constitution_feature'], plot_df['abs_share'], color=colors, edgecolor='white', linewidth=0.5)
    ax.set_title('Constitution contribution to first-order latent view', fontsize=12, pad=10)
    ax.set_xlabel('Absolute loading share')
    ax.set_ylabel('Constitution feature')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_problem_bridge_heatmap(bridge_df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if bridge_df.empty:
        return
    pivot = bridge_df.pivot_table(index='source_feature', columns='target_metric', values='pearson_corr', aggfunc='mean')
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    sns.heatmap(
        pivot,
        annot=True,
        fmt='.2f',
        cmap=CMAP_DIVERGING,
        center=0,
        linewidths=0.4,
        linecolor='white',
        cbar_kws={'label': 'Pearson correlation', 'shrink': 0.82},
        ax=ax,
    )
    ax.set_title('Bridge from latent structure to risk outputs', fontsize=12, pad=10)
    ax.set_xlabel('Problem 2 target')
    ax.set_ylabel('Problem 1 factor')
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_threshold_bootstrap_distributions(threshold_boot: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if threshold_boot.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 3.8))
    for ax, metric, color in zip(axes, ['t1', 't2', 'threshold_gap'], [BLUE_MID, ROSE, BLUE_DEEP]):
        sns.histplot(threshold_boot[metric], bins=14, kde=True, color=color, ax=ax, edgecolor='white', linewidth=0.4)
        ax.set_title(metric)
        ax.set_xlabel(metric)
        ax.set_ylabel('Count')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    fig.suptitle('Bootstrap distributions of selected thresholds', fontsize=12, y=1.03)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_tier_feature_gradient(gradient_long: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if gradient_long.empty:
        return
    plot_df = gradient_long.copy()
    fig, ax = plt.subplots(figsize=(10.4, 5.2))
    sns.lineplot(
        data=plot_df,
        x='risk_tier',
        y='normalized_mean',
        hue='feature',
        style='feature',
        markers=True,
        dashes=False,
        linewidth=2.0,
        ax=ax,
        palette=list(CMAP_SEQUENTIAL(np.linspace(0.18, 0.96, plot_df['feature'].nunique()))),
    )
    ax.set_title('Feature gradients across low / medium / high risk tiers', fontsize=12, pad=10)
    ax.set_xlabel('Risk tier')
    ax.set_ylabel('Normalized mean')
    ax.set_ylim(-0.02, 1.02)
    ax.legend(title='Feature', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_strategy_mapping_heatmap(driver_summary: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if driver_summary.empty:
        return
    plot_df = driver_summary.copy()
    pivot = plot_df.pivot_table(index='age_group', columns='risk_tier', values='first_stage_intensity_mode', aggfunc='mean')
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    sns.heatmap(
        pivot.sort_index(),
        annot=True,
        fmt='.1f',
        cmap=CMAP_SEQUENTIAL,
        linewidths=0.35,
        linecolor='white',
        cbar_kws={'label': 'Recommended first-stage intensity', 'shrink': 0.82},
        ax=ax,
    )
    ax.set_title('Patient feature to first-stage intensity mapping', fontsize=12, pad=10)
    ax.set_xlabel('Risk tier')
    ax.set_ylabel('Age group')
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_optimization_budget_shift(budget_shift: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if budget_shift.empty:
        return
    fig, ax1 = plt.subplots(figsize=(8.4, 4.8))
    ax1.plot(budget_shift['budget_cap'], budget_shift['mean_final_tanshi'], color=ROSE, marker='o', lw=2.0, label='Mean final tanshi')
    ax1.set_xlabel('Budget cap')
    ax1.set_ylabel('Mean final tanshi', color=ROSE)
    ax1.tick_params(axis='y', labelcolor=ROSE)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax2 = ax1.twinx()
    ax2.plot(
        budget_shift['budget_cap'],
        budget_shift['first_stage_frequency_mean'],
        color=BLUE_MID,
        marker='s',
        lw=1.8,
        label='Mean first-stage frequency',
    )
    ax2.set_ylabel('Mean first-stage frequency', color=BLUE_MID)
    ax2.tick_params(axis='y', labelcolor=BLUE_MID)
    fig.suptitle('Budget shift in effect and intervention intensity', fontsize=12, y=1.02)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_sample_plan_paths(sample_df: pd.DataFrame, path: str | Path) -> None:
    path = _prepare_path(path)
    if sample_df.empty:
        return
    records: list[dict[str, float | int | str]] = []
    for _, row in sample_df.iterrows():
        sample_id = int(row['sample_id'])
        plan_value = row.get('plan')
        if isinstance(plan_value, list):
            plan = plan_value
        else:
            try:
                plan = ast.literal_eval(str(plan_value)) if pd.notna(plan_value) else []
            except Exception:
                plan = []
        if isinstance(plan, list) and plan:
            for stage_idx, triple in enumerate(plan, start=1):
                tcm, intensity, frequency = triple
                records.append({'sample_id': sample_id, 'stage_idx': stage_idx, 'metric': 'tcm_level', 'value': float(tcm)})
                records.append({'sample_id': sample_id, 'stage_idx': stage_idx, 'metric': 'intensity', 'value': float(intensity)})
                records.append({'sample_id': sample_id, 'stage_idx': stage_idx, 'metric': 'frequency', 'value': float(frequency)})
        else:
            records.append({'sample_id': sample_id, 'stage_idx': 1, 'metric': 'tcm_level', 'value': float(row.get('first_stage_tcm', np.nan))})
            records.append({'sample_id': sample_id, 'stage_idx': 1, 'metric': 'intensity', 'value': float(row.get('first_stage_intensity', np.nan))})
            records.append({'sample_id': sample_id, 'stage_idx': 1, 'metric': 'frequency', 'value': float(row.get('first_stage_frequency', np.nan))})
    plot_df = pd.DataFrame(records)
    if plot_df.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.0), sharex=True)
    for ax, metric, title in zip(axes, ['tcm_level', 'intensity', 'frequency'], ['TCM level', 'Intensity', 'Frequency']):
        sub = plot_df[plot_df['metric'] == metric]
        sns.lineplot(data=sub, x='stage_idx', y='value', hue='sample_id', marker='o', linewidth=2.0, ax=ax)
        ax.set_title(title)
        ax.set_xlabel('Stage')
        ax.set_ylabel(title)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    fig.suptitle('Sample 1 / 2 / 3 intervention paths', fontsize=12, y=1.03)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)


def plot_workflow_overview(path: str | Path) -> None:
    path = _prepare_path(path)
    fig, ax = plt.subplots(figsize=(10.4, 3.8))
    ax.axis('off')
    boxes = [
        (0.05, 0.35, 0.18, 0.30, BLUE_LIGHT, 'Data\ngovernance'),
        (0.28, 0.35, 0.18, 0.30, BLUE_MID, 'Problem 1\nlatent structure'),
        (0.51, 0.35, 0.18, 0.30, ROSE_LIGHT, 'Problem 2\nrisk stratification'),
        (0.74, 0.35, 0.18, 0.30, ROSE, 'Problem 3\nintervention optimization'),
    ]
    for x, y, w, h, color, label in boxes:
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor='white', linewidth=1.5, alpha=0.95)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=11, color='white', weight='bold')
    for start_x in [0.23, 0.46, 0.69]:
        ax.annotate('', xy=(start_x + 0.05, 0.5), xytext=(start_x, 0.5), arrowprops=dict(arrowstyle='->', color=BLUE_DEEP, lw=2.0))
    ax.text(0.5, 0.86, 'MathorCup C closed-loop workflow', ha='center', va='center', fontsize=13, weight='bold')
    ax.text(0.5, 0.16, 'latent structure -> calibrated warning -> constrained personalized intervention', ha='center', va='center', fontsize=10, color=BLUE_DEEP)
    plt.tight_layout()
    save_figure(path, fig)
    plt.close(fig)
