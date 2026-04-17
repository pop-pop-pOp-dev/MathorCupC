# 代码审查与一致性（与计划对齐）

## 已修复 / 已对齐

| 问题 | 处理 |
|------|------|
| `runner.py` 在 `runtime.plots: false` 时仍写风险分布图 | 已与 `runtime.plots` 对齐，避免与 stage 03 重复产图逻辑混乱 |
| 问题三优化子群用 `constitution_label == 5`，与规则阶段 `phlegm_dampness_label_flag` 口径不一致 | 统一为 [`utils/cohort.py`](../src/utils/cohort.py) 的 `phlegm_intervention_cohort()`：优先痰湿标签，否则回退体质主标签 |
| Stage 02 中 `latent_stability` 与 `latent_bootstrap_loadings` 重复整套载荷 bootstrap | 由 `latent_state_stability_from_loadings_boot()` 复用同一份 `latent_boot` |

## 保留假设（需数据/题面确认）

- `phlegm_dampness_label_flag` 与官方“痰湿体质”定义一致；若赛方定义不同，只需调整 `phlegm_intervention_cohort` 一处。
- 样本量较小时 bootstrap 方差较大，属统计性质而非实现错误。

## 仍建议人工复核

- 全量 Excel 路径与 `configs/base.yaml` 中 `paths.raw_excel` 一致；缺失时回退 `sample_preview.tsv`（见 `data/loader.py`）。
- 论文叙述与 `整体技术路线框架.md` §0.1 已实现边界一致。
