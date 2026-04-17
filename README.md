# MathorCup C题代码框架

本项目实现 **2026 年 MathorCup C 题：中老年人群高血脂症的风险预警及干预方案优化** 的可复现流水线（**不使用深度学习**）。

## 核心方法（与论文/附录对齐）

- **问题一**：三视角（体质九积分 / 活动 ADL+IADL / 代谢偏离）各 **因子分析（FactorAnalysis）** 提取一阶因子；二阶综合隐状态为对三因子得分的 **一维 PCA**（或配置为固定权重）；输出九体质在一阶因子上的载荷占比及与确诊标签的**单变量对照表**（仅作解释，不作问题二主监督）。
- **问题二**：以**血脂/确诊仅作锚点**，风险模型默认使用 **前置特征锚定 Logistic**（体质、活动、BMI/血糖/尿酸、年龄等），显式剥离 `TC/TG/LDL-C/HDL-C` 及其派生定义变量；阈值网格 + bootstrap；痰湿高危 **组合规则挖掘**（规则池不含「痰湿标签=1」平凡项）。
- **问题三**：**三阶段整数规划（SciPy MILP）**，对 `(调理, 强度, 频次)` 合法组合做离散展开；收益按题面 **强度 3% / 频次 1%** 规则写成组合常数；含**强度跳变硬约束**、预算上限、年龄/活动强度、**痰湿积分—调理档位（附表2）**、训练频次 **1–10 次/周**；输出 **预算扫描 + 帕累托前沿** 与 **患者特征—方案众数映射表**。

## 快速开始

```bash
python scripts/run_full_pipeline.py
```

分阶段：

```bash
python scripts/run_q1.py
python scripts/run_q2.py
python scripts/run_q3.py
```

## 默认输出目录（`outputs/run_*/`）

| 阶段 | 目录 | 与题目对应 | 关键文件 |
|------|------|------------|----------|
| 0 | `governance/` | 数据治理 | `canonical_dataset.csv`、`governance_report.json` |
| 1 | `latent/` | 问题一 | `latent_state_scores.csv`、`latent_second_order.csv`、`constitution_contributions_to_latent.csv`、`constitution_univariate_risk_association.csv` |
| 2 | `risk/` | 问题二 | `risk_scores.csv`、`risk_thresholds.json`、`risk_model_coefficients.csv`、`minimal_rules.csv`（由 `rules/` 阶段产出） |
| 3 | `rules/` | 问题二规则 | `minimal_rules.csv`、`core_rules.csv` |
| 4 | `optimization/` | 问题三 | `phlegm_patient_plans.csv`、`phlegm_patient_plans_budget_grid.csv`、`pareto_frontier_summary.csv`、`sample_1_2_3_plans.csv`、`strategy_mapping_by_risk_tier_age.csv` |
| 5 | `validation/` | 稳健性摘要 | `diagnostics.json`、`optimization_robustness.csv` |

## 主要配置

- `configs/risk_model.yaml`：潜状态提取、风险模型类型（默认 `anchor_front_logistic`）、锚点与阈值、规则阈值。
- `configs/clinical_rules.yaml`：血脂/代谢区间、活动强度规则、**中医调理档位与痰湿积分区间**、频次上下界，以及题面 **强度 3% / 频次 1%** 参数。
- `configs/intervention.yaml`：三阶段月数、预算扫描列表、`frequency_from_clinical_rules`、情景系数、强度跳变上限等。
- `configs/performance.yaml`：并行 worker（`n_jobs`）、快速阈值网格（`fast_threshold_grid`）、可选 GPU 线性代数开关（见下）。

## 性能与并行

- **Bootstrap / MILP**：潜状态、风险阈值、规则稳定性及逐患者 MILP 默认通过 **joblib** 并行（`performance.n_jobs`，`-1` 为占满 CPU）。
- **阈值搜索**：`thresholding.search_risk_thresholds_with_grid` 已改为向量化实现，显著降低 Python 双重循环开销。
- **潜状态稳定性**：`latent_stability.csv` 与载荷 bootstrap **复用同一次** `bootstrap_latent_loadings` 结果，避免重复拟合因子模型。
- **可选 GPU**：安装 **CuPy** 且环境变量/配置 `use_gpu_linear_algebra: true` 时，`utils/gpu_optional.py` 可对大规模矩阵做行标准化等（小样本自动走 NumPy）。**SciPy MILP、sklearn 因子分析仍以 CPU 为主**，这与数模场景下的真实瓶颈一致。

## 风险与优化口径

- **风险模型防泄露**：`src/models/risk_score.py` 默认走 `anchor_front_logistic`，训练特征中显式剥离 `TC/TG/LDL-C/HDL-C`、`dev_*` 血脂偏离、`lipid_deviation_total`、`hyperlipidemia_label` 及含血脂的一体化隐状态。
- **预算扫描**：`stage_05_optimize.py` 会按 `intervention.budget_levels` 逐个预算求解，导出 `pareto_frontier_summary.csv`。
- **平滑度**：相邻阶段活动强度最大跳变为 `max_intensity_jump: 1`，不是单纯软惩罚。

## 绘图与论文资产

- 期刊向主题与 **玫瑰红—深蓝** 渐变/发散色盘见 `src/reporting/plot_style.py`；各阶段在 `runtime.plots: true` 时导出 **PNG + 同 stem 的 PDF**（便于 LaTeX 排版）。
- 主流程仅在 `runtime.plots: true` 时额外写 `risk/continuous_risk_score.png`，与阶段 03 行为一致。

## 代码审查摘要

- 痰湿优化子群与规则阶段对齐：`utils/cohort.phlegm_intervention_cohort()`（优先 `phlegm_dampness_label_flag`，否则 `constitution_label == 5`）。详见 `docs/CODE_REVIEW.md`。

## 说明

- 全文设计文档见根目录与 `docs/` 下的 `整体技术路线框架.md`；其中 **§0.1 已实现边界** 与代码一致，后文理想化扩展写作时请与 §0.1 对齐。
