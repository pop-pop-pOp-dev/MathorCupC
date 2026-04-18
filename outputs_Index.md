# outputs_Index

## 1. 文档目的

本文档对当前有效结果目录 `outputs/run_20260417_211020/` 下的全部结果文件进行索引说明，回答以下问题：

1. 该结果文件位于哪里；
2. 由哪个脚本、哪个阶段函数生成；
3. 文件的内容是什么；
4. 本轮结果大致表现如何；
5. 该结果能够支撑什么结论。

本文档严格贴合当前代码实际，不对未生成的文件做虚构说明。

## 2. 总入口与分阶段脚本

### 2.1 全链路总入口

- 总脚本：`scripts/run_full_pipeline.py`
- 调度函数：`src/pipeline/runner.py` 中的 `run_full_pipeline()`

该函数按如下顺序调度：

1. `run_stage_01_data()`
2. `run_stage_02_latent()`
3. `run_stage_03_risk()`
4. `run_stage_04_rules()`
5. `run_stage_05_optimize()`
6. `run_stage_06_validate()`

### 2.2 分问题脚本

- 问题一可单独由 `scripts/run_q1.py` 跑通；
- 问题二可单独由 `scripts/run_q2.py` 跑通；
- 问题三可单独由 `scripts/run_q3.py` 跑通；
- 当前目录 `outputs/run_20260417_211020/` 来自全链路脚本 `scripts/run_full_pipeline.py`。

## 3. 当前有效结果目录

- 当前唯一保留的有效结果目录：`outputs/run_20260417_211020/`

该目录下共有六个阶段子目录：

1. `governance/`
2. `latent/`
3. `risk/`
4. `rules/`
5. `optimization/`
6. `validation/`

---

## 4. 阶段 01：数据治理与派生特征

生成函数：

- `src/pipeline/stage_01_data.py` 中的 `run_stage_01_data()`

上游依赖：

- `data/raw/附件1：样例数据.xlsx`
- `src/data/loader.py`
- `src/data/cleaning.py`
- `src/features/*.py`

### 4.1 文件索引

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/governance/canonical_dataset.csv`](outputs/run_20260417_211020/governance/canonical_dataset.csv) | 表格 | `run_stage_01_data()` | 标准化后的总样本主表，包含原始字段、偏离特征、活动特征、体质特征、背景特征与交互项 | 成功生成，是后续全部阶段的统一输入底表 | 支撑“全项目数据口径统一、所有问题共享同一主表” |
| [`outputs/run_20260417_211020/governance/feature_registry.csv`](outputs/run_20260417_211020/governance/feature_registry.csv) | 表格 | `run_stage_01_data()` | 列出项目内登记的特征名与用途 | 成功生成，可用于论文附录或答辩时解释字段来源 | 支撑“特征工程透明可解释” |
| [`outputs/run_20260417_211020/governance/governance_report.json`](outputs/run_20260417_211020/governance/governance_report.json) | 文字/JSON | `run_stage_01_data()` | 数据治理摘要，包括样本、字段、清洗后状态等 | 成功生成，表明 `1000 x 37` 原始数据已被统一处理 | 支撑“输入数据满足题面样本规模要求” |

### 4.2 本阶段可支撑的结论

1. 原始 Excel 已被成功读入并标准化；
2. 所有下游问题共享同一张规范化数据表，而不是各阶段各写一套口径；
3. 体质、活动、代谢、交互项均已经被显式构造，满足多维建模前提。

---

## 5. 阶段 02：潜状态提取与问题一证据

生成函数：

- `src/pipeline/stage_02_latent.py` 中的 `run_stage_02_latent()`

核心模型：

- `src/models/latent_state.py`
- `src/models/constitution_effects.py`
- `evaluation/stability.py`

本阶段对应题面问题 1 的主要结果。

### 5.1 核心表格与文字结果

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/latent/latent_loadings.csv`](outputs/run_20260417_211020/latent/latent_loadings.csv) | 表格 | `run_stage_02_latent()` | 一阶因子载荷宽表 | 给出体质、活动、代谢三视角的因子载荷 | 支撑“关键指标筛选” |
| [`outputs/run_20260417_211020/latent/latent_loadings_detailed.csv`](outputs/run_20260417_211020/latent/latent_loadings_detailed.csv) | 表格 | `run_stage_02_latent()` | 载荷长表，便于绘图和排序 | 成功生成 | 支撑“载荷可视化与附录汇报” |
| [`outputs/run_20260417_211020/latent/latent_view_diagnostics.csv`](outputs/run_20260417_211020/latent/latent_view_diagnostics.csv) | 表格 | `run_stage_02_latent()` | 各视角解释率、特征数、提取方式 | 本轮使用 `factor_analysis` + 二阶 `pca_one_component` | 支撑“潜状态构造不是拍脑袋加权” |
| [`outputs/run_20260417_211020/latent/latent_second_order.csv`](outputs/run_20260417_211020/latent/latent_second_order.csv) | 表格 | `run_stage_02_latent()` | 二阶潜状态的组合系数 | 给出三类一阶因子进入二阶综合隐状态的系数 | 支撑“问题一最终潜状态是二阶综合结果” |
| [`outputs/run_20260417_211020/latent/latent_state_scores.csv`](outputs/run_20260417_211020/latent/latent_state_scores.csv) | 表格 | `run_stage_02_latent()` | 每个样本的一阶/二阶潜状态得分 | 成功生成，是后续风险建模与优化的重要输入 | 支撑“问题一结果进入问题二、问题三” |
| [`outputs/run_20260417_211020/latent/constitution_contributions_to_latent.csv`](outputs/run_20260417_211020/latent/constitution_contributions_to_latent.csv) | 表格 | `run_stage_02_latent()` | 九种体质对一阶体质因子的贡献占比 | 本轮显示 `constitution_pinghe` 绝对占比最高，`constitution_tanshi` 也有贡献但不是最大 | 支撑“九种体质贡献差异” |
| [`outputs/run_20260417_211020/latent/constitution_univariate_risk_association.csv`](outputs/run_20260417_211020/latent/constitution_univariate_risk_association.csv) | 表格 | `run_stage_02_latent()` | 九种体质单变量风险关联 | 成功生成，可用于问题一中“体质差异与风险关联”的解释 | 支撑“不同体质与发病风险的方向和强弱不同” |
| [`outputs/run_20260417_211020/latent/latent_stability.csv`](outputs/run_20260417_211020/latent/latent_stability.csv) | 表格 | `run_stage_02_latent()` | 旧口径稳定性结果 | 成功生成 | 支撑“潜状态重抽样后不是随机噪声” |
| [`outputs/run_20260417_211020/latent/latent_bootstrap_loadings.csv`](outputs/run_20260417_211020/latent/latent_bootstrap_loadings.csv) | 表格 | `run_stage_02_latent()` | 载荷 bootstrap 结果 | 成功生成 | 支撑“载荷稳定性” |
| [`outputs/run_20260417_211020/latent/latent_bootstrap_summary.csv`](outputs/run_20260417_211020/latent/latent_bootstrap_summary.csv) | 表格 | `run_stage_02_latent()` | 载荷稳定性汇总 | 成功生成 | 支撑“问题一统计稳健性” |
| [`outputs/run_20260417_211020/latent/latent_score_stability.csv`](outputs/run_20260417_211020/latent/latent_score_stability.csv) | 表格 | `run_stage_02_latent()` | 潜状态得分重抽样稳定性明细 | 成功生成 | 支撑“样本得分稳定性” |
| [`outputs/run_20260417_211020/latent/latent_score_stability_summary.csv`](outputs/run_20260417_211020/latent/latent_score_stability_summary.csv) | 表格 | `run_stage_02_latent()` | 潜状态得分稳定性汇总 | 本轮 `constitution_factor`、`metabolic_factor`、`latent_state_h` 稳定性较好 | 支撑“问题一结论可复现” |
| [`outputs/run_20260417_211020/latent/constitution_contribution_bootstrap.csv`](outputs/run_20260417_211020/latent/constitution_contribution_bootstrap.csv) | 表格 | `run_stage_02_latent()` | 九体质贡献 bootstrap 明细 | 成功生成 | 支撑“体质贡献差异不是偶然” |
| [`outputs/run_20260417_211020/latent/constitution_contribution_stability.csv`](outputs/run_20260417_211020/latent/constitution_contribution_stability.csv) | 表格 | `run_stage_02_latent()` | 九体质贡献稳定性汇总 | 成功生成 | 支撑“贡献排名有稳定性证据” |
| [`outputs/run_20260417_211020/latent/latent_stability_summary.json`](outputs/run_20260417_211020/latent/latent_stability_summary.json) | 文字/JSON | `run_stage_02_latent()` | 问题一稳健性摘要 | 本轮给出解释率、二阶方法、贡献稳定性、得分稳定性 | 支撑“问题一结论可写入正文” |

### 5.2 图结果

| 文件 | 生成函数/绘图函数 | 图意 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|
| [`outputs/run_20260417_211020/latent/latent_loading_heatmap.png`](outputs/run_20260417_211020/latent/latent_loading_heatmap.png) / [`pdf`](outputs/run_20260417_211020/latent/latent_loading_heatmap.pdf) | `run_stage_02_latent()` / `plot_latent_loading_heatmap()` | 展示不同特征在三类因子上的载荷结构 | 便于看出哪组指标主导哪类潜因子 | 支撑“关键指标筛选” |
| [`outputs/run_20260417_211020/latent/latent_loading_stability_forest.png`](outputs/run_20260417_211020/latent/latent_loading_stability_forest.png) / [`pdf`](outputs/run_20260417_211020/latent/latent_loading_stability_forest.pdf) | `run_stage_02_latent()` / `plot_latent_loading_stability_forest()` | 展示载荷均值与置信区间 | 森林图可直接支撑论文稳健性段落 | 支撑“问题一稳定性” |
| [`outputs/run_20260417_211020/latent/latent_score_stability_boxplot.png`](outputs/run_20260417_211020/latent/latent_score_stability_boxplot.png) / [`pdf`](outputs/run_20260417_211020/latent/latent_score_stability_boxplot.pdf) | `run_stage_02_latent()` / `plot_latent_score_stability_boxplot()` | 展示潜状态得分在 bootstrap 下的相关性分布 | 本轮整体稳定性较好 | 支撑“潜状态可复现” |

### 5.3 本阶段可以支撑的主要结论

1. 可以从体质、活动、代谢三视角构造出一阶潜因子；
2. 可以进一步组合出二阶综合隐状态 `latent_state_h`；
3. 九种体质对体质因子的贡献存在差异；
4. 问题一的统计结果并非一次拟合的偶然结果，而有 bootstrap 稳健性支撑。

---

## 6. 阶段 03：风险分层与问题二主模型

生成函数：

- `src/pipeline/stage_03_risk.py` 中的 `run_stage_03_risk()`

核心模型：

- `src/models/risk_score.py`
- `src/models/thresholding.py`

本阶段对应题面问题 2 的主结果。

### 6.1 表格与文字结果

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/risk/risk_scores.csv`](outputs/run_20260417_211020/risk/risk_scores.csv) | 表格 | `run_stage_03_risk()` | 每个样本的连续风险值、概率、分层标签、锚点标记 | 成功生成，是问题二主表 | 支撑“全体样本三级风险输出” |
| [`outputs/run_20260417_211020/risk/risk_tier_summary.csv`](outputs/run_20260417_211020/risk/risk_tier_summary.csv) | 表格 | `run_stage_03_risk()` | 低/中/高三组样本量、潜状态、活动、痰湿、确诊率汇总 | 本轮高风险组确诊率最高、低风险组最低 | 支撑“三级风险有实际区分度” |
| [`outputs/run_20260417_211020/risk/risk_thresholds.json`](outputs/run_20260417_211020/risk/risk_thresholds.json) | 文字/JSON | `run_stage_03_risk()` | 主阈值结果 | 本轮输出低中、高风险分界阈值 | 支撑“问题二阈值已明确给出” |
| [`outputs/run_20260417_211020/risk/risk_threshold_summary.json`](outputs/run_20260417_211020/risk/risk_threshold_summary.json) | 文字/JSON | `run_stage_03_risk()` | 阈值、模型元数据、bootstrap 区间 | 本轮包含 `probability_calibration=isotonic` 等关键信息 | 支撑“阈值不是拍脑袋，而是搜索+bootstrap 结果” |
| [`outputs/run_20260417_211020/risk/risk_threshold_bootstrap.csv`](outputs/run_20260417_211020/risk/risk_threshold_bootstrap.csv) | 表格 | `run_stage_03_risk()` | 阈值 bootstrap 明细 | 成功生成 | 支撑“阈值稳定性” |
| [`outputs/run_20260417_211020/risk/risk_threshold_grid.csv`](outputs/run_20260417_211020/risk/risk_threshold_grid.csv) | 表格 | `run_stage_03_risk()` | 阈值网格面 | 记录每个 `(t1,t2)` 候选的目标函数值 | 支撑“阈值来源可追溯” |
| [`outputs/run_20260417_211020/risk/risk_threshold_stability_summary.csv`](outputs/run_20260417_211020/risk/risk_threshold_stability_summary.csv) | 表格 | `run_stage_03_risk()` | 阈值稳定性汇总 | 成功生成 | 支撑“分层不是偶然切出来的” |
| [`outputs/run_20260417_211020/risk/risk_tier_bootstrap_summary.csv`](outputs/run_20260417_211020/risk/risk_tier_bootstrap_summary.csv) | 表格 | `run_stage_03_risk()` | 风险层比例稳定性 | 成功生成 | 支撑“分层规模具有稳健性” |
| [`outputs/run_20260417_211020/risk/risk_score_component_breakdown.csv`](outputs/run_20260417_211020/risk/risk_score_component_breakdown.csv) | 表格 | `run_stage_03_risk()` | 风险分数的分项贡献拆解 | 可以看到各 `score_*` 分量贡献 | 支撑“风险模型可解释” |
| [`outputs/run_20260417_211020/risk/risk_model_coefficients.csv`](outputs/run_20260417_211020/risk/risk_model_coefficients.csv) | 表格 | `run_stage_03_risk()` | 风险模型系数、方向和标准化权重 | 成功生成 | 支撑“关键特征方向与强度说明” |
| [`outputs/run_20260417_211020/risk/risk_model_cv_metrics.csv`](outputs/run_20260417_211020/risk/risk_model_cv_metrics.csv) | 表格 | `run_stage_03_risk()` | 交叉验证指标 | 本轮 AUC、PR-AUC、Brier、log loss 都较好 | 支撑“模型性能成立” |
| [`outputs/run_20260417_211020/risk/risk_model_calibration.csv`](outputs/run_20260417_211020/risk/risk_model_calibration.csv) | 表格 | `run_stage_03_risk()` | 概率校准分箱结果 | 本轮校准明显优于旧版结果 | 支撑“概率输出可以解释为较可信的风险概率” |
| [`outputs/run_20260417_211020/risk/risk_anchor_monotonicity.csv`](outputs/run_20260417_211020/risk/risk_anchor_monotonicity.csv) | 表格 | `run_stage_03_risk()` | 低锚点/高锚点均值比较 | 本轮高锚点风险均值明显高于低锚点 | 支撑“模型能拉开低高风险前沿” |
| [`outputs/run_20260417_211020/risk/risk_tier_severity_summary.csv`](outputs/run_20260417_211020/risk/risk_tier_severity_summary.csv) | 表格 | `run_stage_03_risk()` | 三层风险组与严重度、代谢、潜状态的汇总关系 | 成功生成 | 支撑“三级风险与临床/潜状态严重度一致” |
| [`outputs/run_20260417_211020/risk/risk_anchor_diagnostics.json`](outputs/run_20260417_211020/risk/risk_anchor_diagnostics.json) | 文字/JSON | `run_stage_03_risk()` | 锚点数量与占比 | 成功生成 | 支撑“训练前沿定义透明” |

### 6.2 图结果

| 文件 | 生成函数/绘图函数 | 图意 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|
| [`outputs/run_20260417_211020/risk/continuous_risk_score.png`](outputs/run_20260417_211020/risk/continuous_risk_score.png) / [`pdf`](outputs/run_20260417_211020/risk/continuous_risk_score.pdf) | `run_stage_03_risk()` / `plot_risk_distribution()` | 连续风险分布图 | 展示整体分数分布 | 支撑“风险输出连续化，而不是只做二分类” |
| [`outputs/run_20260417_211020/risk/risk_score_by_tier_boxplot.png`](outputs/run_20260417_211020/risk/risk_score_by_tier_boxplot.png) / [`pdf`](outputs/run_20260417_211020/risk/risk_score_by_tier_boxplot.pdf) | `run_stage_03_risk()` / `plot_risk_score_by_tier()` | 三级风险箱线图 | 可视化低/中/高三组明显分离 | 支撑“风险三级可视化可分” |
| [`outputs/run_20260417_211020/risk/risk_threshold_heatmap.png`](outputs/run_20260417_211020/risk/risk_threshold_heatmap.png) / [`pdf`](outputs/run_20260417_211020/risk/risk_threshold_heatmap.pdf) | `run_stage_03_risk()` / `plot_risk_threshold_heatmap()` | 阈值网格目标函数图 | 展示最优阈值区域 | 支撑“阈值有客观搜索依据” |
| [`outputs/run_20260417_211020/risk/risk_anchor_overlay.png`](outputs/run_20260417_211020/risk/risk_anchor_overlay.png) / [`pdf`](outputs/run_20260417_211020/risk/risk_anchor_overlay.pdf) | `run_stage_03_risk()` / `plot_risk_anchor_overlay()` | 风险分数与锚点叠加图 | 显示低锚点和高锚点在风险轴上的相对位置 | 支撑“锚点分离有效” |
| [`outputs/run_20260417_211020/risk/risk_component_mean_bar.png`](outputs/run_20260417_211020/risk/risk_component_mean_bar.png) / [`pdf`](outputs/run_20260417_211020/risk/risk_component_mean_bar.pdf) | `run_stage_03_risk()` / `plot_risk_component_mean_bar()` | 各风险层的分项均值柱图 | 可视化风险构成差异 | 支撑“问题二解释性” |

### 6.3 本阶段可以支撑的主要结论

1. 已建立低/中/高三级风险预警模型；
2. 已给出低中阈值与中高阈值的客观选取依据；
3. 模型排序能力、校准能力与锚点区分能力都可以量化汇报；
4. 风险结果已为问题二规则挖掘和问题三优化分层提供输入。

---

## 7. 阶段 04：痰湿高风险规则挖掘

生成函数：

- `src/pipeline/stage_04_rules.py` 中的 `run_stage_04_rules()`

核心模型：

- `src/models/rule_mining.py`

### 7.1 文件索引

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/rules/rule_candidates.csv`](outputs/run_20260417_211020/rules/rule_candidates.csv) | 表格 | `run_stage_04_rules()` | 全部候选规则池 | 成功生成 | 支撑“规则不是人工只挑一条” |
| [`outputs/run_20260417_211020/rules/minimal_rules.csv`](outputs/run_20260417_211020/rules/minimal_rules.csv) | 表格 | `run_stage_04_rules()` | 经过覆盖、纯度、增量覆盖筛选后的最小规则集 | 本轮核心规则包括 `尿酸偏离>0` 和 `活动总分<60` | 支撑“痰湿高风险核心特征组合” |
| [`outputs/run_20260417_211020/rules/rule_coverage_matrix.csv`](outputs/run_20260417_211020/rules/rule_coverage_matrix.csv) | 表格 | `run_stage_04_rules()` | 每条规则覆盖哪些样本 | 成功生成 | 支撑“规则可追溯到样本层” |
| [`outputs/run_20260417_211020/rules/rule_stability.csv`](outputs/run_20260417_211020/rules/rule_stability.csv) | 表格 | `run_stage_04_rules()` | bootstrap 规则稳定性明细 | 成功生成 | 支撑“规则具有重复出现性” |
| [`outputs/run_20260417_211020/rules/core_rules.csv`](outputs/run_20260417_211020/rules/core_rules.csv) | 表格 | `run_stage_04_rules()` | 选择频率超过阈值的稳定核心规则 | 成功生成 | 支撑“可写进正文的核心规则” |
| [`outputs/run_20260417_211020/rules/rule_summary.json`](outputs/run_20260417_211020/rules/rule_summary.json) | 文字/JSON | `run_stage_04_rules()` | 规则挖掘总体摘要 | 包含建模样本量、候选规则数、最终规则数、增量覆盖等 | 支撑“问题二规则过程可解释” |
| [`outputs/run_20260417_211020/rules/rule_stability_summary.json`](outputs/run_20260417_211020/rules/rule_stability_summary.json) | 文字/JSON | `run_stage_04_rules()` | 前几条规则的稳定性摘要 | 本轮 `尿酸偏离>0` 稳定性很强 | 支撑“问题二规则稳健性” |

### 7.2 图结果

| 文件 | 生成函数/绘图函数 | 图意 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|
| [`outputs/run_20260417_211020/rules/rule_selection_frequency.png`](outputs/run_20260417_211020/rules/rule_selection_frequency.png) / [`pdf`](outputs/run_20260417_211020/rules/rule_selection_frequency.pdf) | `run_stage_04_rules()` / `plot_rule_selection_frequency()` | 规则选择频率图 | 可视化规则稳定性 | 支撑“哪些规则值得纳入正文” |
| [`outputs/run_20260417_211020/rules/rule_coverage_waterfall.png`](outputs/run_20260417_211020/rules/rule_coverage_waterfall.png) / [`pdf`](outputs/run_20260417_211020/rules/rule_coverage_waterfall.pdf) | `run_stage_04_rules()` / `plot_rule_coverage_waterfall()` | 规则增量覆盖瀑布图 | 显示多条规则叠加后的覆盖结构 | 支撑“规则集是递进构造的” |
| [`outputs/run_20260417_211020/rules/rule_purity_vs_coverage.png`](outputs/run_20260417_211020/rules/rule_purity_vs_coverage.png) / [`pdf`](outputs/run_20260417_211020/rules/rule_purity_vs_coverage.pdf) | `run_stage_04_rules()` / `plot_rule_purity_vs_coverage()` | 候选规则纯度-覆盖散点图 | 用于说明为何选中某些规则 | 支撑“规则筛选标准客观” |

### 7.3 本阶段可以支撑的主要结论

1. 已识别痰湿体质高风险人群的核心特征组合；
2. 已输出最小规则集和稳定规则集；
3. 问题二不仅有一个“黑箱风险值”，还有可解释的规则证据。

---

## 8. 阶段 05：个体化干预优化与问题三结果

生成函数：

- `src/pipeline/stage_05_optimize.py` 中的 `run_stage_05_optimize()`

核心模型：

- `src/models/intervention_optimizer.py`
- `src/domain/intervention_rules.py`
- `src/models/strategy_mapping.py`

本阶段对应题面问题 3 的主结果。

### 8.1 文件索引

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/optimization/patient_state_table.csv`](outputs/run_20260417_211020/optimization/patient_state_table.csv) | 表格 | `run_stage_05_optimize()` | 参与优化的患者状态表 | 成功生成 | 支撑“问题三输入状态明确定义” |
| [`outputs/run_20260417_211020/optimization/phlegm_patient_plans.csv`](outputs/run_20260417_211020/optimization/phlegm_patient_plans.csv) | 表格 | `run_stage_05_optimize()` | 主预算下的个体化干预方案 | 含每位痰湿患者的方案、成本、负担、结局 | 支撑“6个月个体化方案已生成” |
| [`outputs/run_20260417_211020/optimization/phlegm_patient_plans_budget_grid.csv`](outputs/run_20260417_211020/optimization/phlegm_patient_plans_budget_grid.csv) | 表格 | `run_stage_05_optimize()` | 多预算扫描下的全体方案表 | 成功生成 | 支撑“帕累托与边际收益分析” |
| [`outputs/run_20260417_211020/optimization/pareto_frontier_summary.csv`](outputs/run_20260417_211020/optimization/pareto_frontier_summary.csv) | 表格 | `run_stage_05_optimize()` | 预算-疗效前沿摘要 | 本轮预算越高，平均痰湿/潜状态越优，且后期边际收益下降 | 支撑“问题三预算-效果权衡” |
| [`outputs/run_20260417_211020/optimization/pareto_budget_marginal_gains.csv`](outputs/run_20260417_211020/optimization/pareto_budget_marginal_gains.csv) | 表格 | `run_stage_05_optimize()` | 各预算档之间的边际收益 | 本轮 `500->800` 收益最大，之后收益明显递减 | 支撑“边际收益递减” |
| [`outputs/run_20260417_211020/optimization/pareto_budget_evidence.json`](outputs/run_20260417_211020/optimization/pareto_budget_evidence.json) | 文字/JSON | `run_stage_05_optimize()` | 帕累托证据摘要 | 包含收益递减与总改善量 | 支撑“问题三总结性论断” |
| [`outputs/run_20260417_211020/optimization/strategy_mapping_by_risk_tier_age.csv`](outputs/run_20260417_211020/optimization/strategy_mapping_by_risk_tier_age.csv) | 表格 | `run_stage_05_optimize()` | 风险层级+年龄组 -> 最优方案模式 | 已给出众数型匹配规律 | 支撑“患者特征-最优方案匹配规律” |
| [`outputs/run_20260417_211020/optimization/strategy_mapping_by_activity_bins.csv`](outputs/run_20260417_211020/optimization/strategy_mapping_by_activity_bins.csv) | 表格 | `run_stage_05_optimize()` | 活动能力+年龄组 -> 最优方案模式 | 成功生成 | 支撑“活动特征影响方案选择” |
| [`outputs/run_20260417_211020/optimization/strategy_mapping_summary.json`](outputs/run_20260417_211020/optimization/strategy_mapping_summary.json) | 文字/JSON | `run_stage_05_optimize()` | 匹配规律摘要 | 成功生成 | 支撑“问题三总览” |
| [`outputs/run_20260417_211020/optimization/primary_budget_feasibility_by_group.csv`](outputs/run_20260417_211020/optimization/primary_budget_feasibility_by_group.csv) | 表格 | `run_stage_05_optimize()` | 不同风险层和年龄组下的方案可行率 | 本轮高年龄组可行率明显下降 | 支撑“无可行解样本解释” |
| [`outputs/run_20260417_211020/optimization/sample_1_2_3_plans.csv`](outputs/run_20260417_211020/optimization/sample_1_2_3_plans.csv) | 表格 | `run_stage_05_optimize()` | 题面要求的样本 1、2、3 最优方案 | 已直接给出三位样本的最优方案 | 支撑“题面显式要求已满足” |

### 8.2 本阶段可以支撑的主要结论

1. 已对痰湿患者给出 6 个月分阶段个体化干预方案；
2. 已给出样本 1、2、3 的方案；
3. 已给出风险层级/年龄组/活动能力与最优方案的匹配规律；
4. 已给出成本-疗效前沿和边际收益分析。

---

## 9. 阶段 06：验证、对照与答辩摘要

生成函数：

- `src/pipeline/stage_06_validate.py` 中的 `run_stage_06_validate()`

本阶段用于把问题 1-3 的结果压缩成更适合写正文、答辩、附录的摘要证据。

### 9.1 文件索引

| 文件 | 类型 | 生成函数 | 作用 | 本轮结果说明 | 支撑结论 |
|---|---|---|---|---|---|
| [`outputs/run_20260417_211020/validation/diagnostics.json`](outputs/run_20260417_211020/validation/diagnostics.json) | 文字/JSON | `run_stage_06_validate()` | 全项目主诊断摘要 | 包含样本数、风险分布、痰湿人数、帕累托、预算证据、风险证据 | 支撑“整项目结果总览” |
| [`outputs/run_20260417_211020/validation/diagnostics_table.csv`](outputs/run_20260417_211020/validation/diagnostics_table.csv) | 表格 | `run_stage_06_validate()` | 将诊断摘要压平成表格 | 成功生成 | 支撑“正文/附录表格化展示” |
| [`outputs/run_20260417_211020/validation/stability_overview.json`](outputs/run_20260417_211020/validation/stability_overview.json) | 文字/JSON | `run_stage_06_validate()` | 问题一、二、规则稳健性总览 | 成功生成 | 支撑“方法稳健性总述” |
| [`outputs/run_20260417_211020/validation/stability_overview_table.csv`](outputs/run_20260417_211020/validation/stability_overview_table.csv) | 表格 | `run_stage_06_validate()` | 稳健性摘要表格化 | 成功生成 | 支撑“bootstrap 样本与阈值等汇总” |
| [`outputs/run_20260417_211020/validation/optimization_robustness.csv`](outputs/run_20260417_211020/validation/optimization_robustness.csv) | 表格 | `run_stage_06_validate()` | 优化结果的均值、方差、极值摘要 | 成功生成 | 支撑“问题三结果稳定性” |
| [`outputs/run_20260417_211020/validation/risk_evidence_summary.json`](outputs/run_20260417_211020/validation/risk_evidence_summary.json) | 文字/JSON | `run_stage_06_validate()` | 风险模型最核心证据摘要 | 本轮 AUC、ECE、校准误差、风险单调性都集中汇总 | 支撑“问题二结论写作” |
| [`outputs/run_20260417_211020/validation/risk_model_benchmark.csv`](outputs/run_20260417_211020/validation/risk_model_benchmark.csv) | 表格 | `run_stage_06_validate()` | 主模型、旧版手工加权、Ridge 基线对照 | 本轮主模型明显优于两类基线 | 支撑“我们的方法优于旧口径/弱基线” |
| [`outputs/run_20260417_211020/validation/risk_model_ablation.csv`](outputs/run_20260417_211020/validation/risk_model_ablation.csv) | 表格 | `run_stage_06_validate()` | 风险模型消融实验 | 完整主模型与“去体质/去活动/去代谢/去背景/去交互项”逐项对照；其中去代谢信息后 AUC 由 0.9219 大幅降至 0.5997 | 支撑“问题二不是拍脑袋拼特征，而是存在关键模块贡献差异” |
| [`outputs/run_20260417_211020/validation/risk_model_significance.csv`](outputs/run_20260417_211020/validation/risk_model_significance.csv) | 表格 | `run_stage_06_validate()` | 风险模型基线/消融的显著性检验 | 对旧版手工加权、Ridge 及各消融版本做配对 bootstrap；主模型相对两类基线在 AUC、PR-AUC、Brier、LogLoss 上均显著更优 | 支撑“问题二优势不是单次偶然” |
| [`outputs/run_20260417_211020/validation/optimization_baseline_patient_level.csv`](outputs/run_20260417_211020/validation/optimization_baseline_patient_level.csv) | 表格 | `run_stage_06_validate()` | 个体层级优化基线对照 | 将优化方案与 `min_cost_feasible`、`min_burden_feasible` 启发式基线放到同一患者层面逐一比较 | 支撑“问题三改进不是只看总体均值” |
| [`outputs/run_20260417_211020/validation/optimization_baseline_summary.csv`](outputs/run_20260417_211020/validation/optimization_baseline_summary.csv) | 表格 | `run_stage_06_validate()` | 优化方案与启发式基线总体对照 | 主方案平均末期痰湿积分约 42.47，显著低于两类基线的 50.74，但成本和负担更高 | 支撑“问题三存在明确效果-成本权衡” |
| [`outputs/run_20260417_211020/validation/optimization_significance.csv`](outputs/run_20260417_211020/validation/optimization_significance.csv) | 表格 | `run_stage_06_validate()` | 优化阶段显著性检验 | 对配对可行样本做 Wilcoxon 检验；主方案相对基线平均再降低痰湿积分约 8.27、降低末期潜状态约 1.76，显著性极强 | 支撑“问题三优势不是个别样本特例” |

### 9.2 本阶段可以支撑的主要结论

1. 当前结果不是“只给结果、不做验证”，而是有完整验证层；
2. 风险模型已有基线对照、模块消融与显著性证据；
3. 优化阶段已有预算边际收益、启发式基线对照与配对显著性解释；
4. 这批验证文件是答辩时最重要的摘要材料。

---

## 10. 按题面问题映射最重要结果

### 10.1 问题 1

重点文件：

- `latent/latent_loadings.csv`
- `latent/latent_second_order.csv`
- `latent/constitution_contributions_to_latent.csv`
- `latent/constitution_univariate_risk_association.csv`
- `latent/latent_stability_summary.json`

可支撑结论：

1. 三视角潜因子可构建；
2. 九种体质贡献存在差异；
3. 关键指标与潜状态具有稳定性证据。

### 10.2 问题 2

重点文件：

- `risk/risk_scores.csv`
- `risk/risk_tier_summary.csv`
- `risk/risk_threshold_summary.json`
- `rules/minimal_rules.csv`
- `validation/risk_evidence_summary.json`
- `validation/risk_model_benchmark.csv`
- `validation/risk_model_ablation.csv`
- `validation/risk_model_significance.csv`

可支撑结论：

1. 已输出三级风险；
2. 已明确阈值；
3. 已给出核心特征组合；
4. 主模型优于旧版手工加权与 Ridge 基线；
5. 消融实验表明代谢偏离信息与体质信息是问题二最关键的贡献模块；
6. 显著性检验说明上述优势不是单次抽样波动。

### 10.3 问题 3

重点文件：

- `optimization/phlegm_patient_plans.csv`
- `optimization/sample_1_2_3_plans.csv`
- `optimization/strategy_mapping_by_risk_tier_age.csv`
- `optimization/pareto_frontier_summary.csv`
- `optimization/pareto_budget_marginal_gains.csv`
- `optimization/primary_budget_feasibility_by_group.csv`
- `validation/optimization_baseline_summary.csv`
- `validation/optimization_significance.csv`

可支撑结论：

1. 已生成个体化方案；
2. 已满足样本 1、2、3 的题面要求；
3. 已总结“患者特征-最优方案”规律；
4. 已说明预算收益递减与部分高龄组无可行解现象；
5. 已证明优化方案相对低成本/低负担启发式基线确有显著改善；
6. 已给出效果提升伴随更高成本与负担的权衡关系。

---

## 11. 使用建议

如果要快速查结果，建议按下面顺序阅读：

1. 先看 `validation/diagnostics.json`
2. 再看 `validation/risk_evidence_summary.json`
3. 然后按问题分别看：
   - 问题一：`latent/`
   - 问题二：`risk/` + `rules/`
   - 问题三：`optimization/`

如果要写论文正文，建议优先调用：

1. `risk_model_benchmark.csv`
2. `risk_evidence_summary.json`
3. `risk_model_ablation.csv`
4. `risk_model_significance.csv`
5. `optimization_baseline_summary.csv`
6. `optimization_significance.csv`
7. `pareto_frontier_summary.csv`
8. `sample_1_2_3_plans.csv`
9. `strategy_mapping_by_risk_tier_age.csv`

