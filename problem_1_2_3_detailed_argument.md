# problem_1_2_3_detailed_argument

## 1. 文档说明

本文档面向题面三问，给出一份详细、自洽、贴合当前代码和结果的论述提纲。每一问都回答以下问题：

1. 题目要求是什么；
2. 我们最终给出的答案是什么；
3. 哪些结果文件支撑这个答案；
4. 我们是如何得到这个答案的；
5. 当前还应如何谨慎表述；
6. 该问与前后两问如何关联。

本文严格对应当前有效结果目录：

- `outputs/run_20260417_211020/`

---

## 2. 问题 1：关键指标筛选、痰湿严重度表征与九体质贡献差异

### 2.1 题目要求

题面问题 1 要求：

1. 从血常规体检指标和活动量表评分中筛选出能表征痰湿体质严重程度、且能预警高血脂发病风险的关键指标；
2. 研究九种体质对发病风险的贡献度差异。

因此，问题 1 的本质任务是：

- 找到多维指标中的关键结构；
- 用一个统一的潜在表征刻画痰湿严重程度与总体风险结构；
- 比较九体质在该结构中的相对贡献。

### 2.2 我们给出的答案

我们当前对问题 1 的回答是：

1. 按“体质-活动-代谢”三视角分别提取一阶潜因子；
2. 再将三类一阶因子综合成二阶潜状态 `latent_state_h`；
3. 通过载荷绝对值占比衡量九种体质对体质因子的贡献差异；
4. 用 bootstrap 稳健性分析证明潜状态结构具有较好的重复性。

可直接写入正文的答案表达为：

> 本文将体质积分、活动能力和代谢偏离三类指标分别压缩为一阶潜因子，并进一步综合得到个体总体潜状态 `latent_state_h`。结果表明，不同体质指标在体质因子上的贡献存在显著差异；同时，该潜状态结构在重抽样条件下保持较好的稳定性，因此可以作为问题二风险预警与问题三干预优化的中间表征。

### 2.3 支撑问题 1 的关键结果文件

#### 结构建模结果

- [`outputs/run_20260417_211020/latent/latent_loadings.csv`](outputs/run_20260417_211020/latent/latent_loadings.csv)
- [`outputs/run_20260417_211020/latent/latent_second_order.csv`](outputs/run_20260417_211020/latent/latent_second_order.csv)
- [`outputs/run_20260417_211020/latent/latent_state_scores.csv`](outputs/run_20260417_211020/latent/latent_state_scores.csv)

#### 九体质贡献差异

- [`outputs/run_20260417_211020/latent/constitution_contributions_to_latent.csv`](outputs/run_20260417_211020/latent/constitution_contributions_to_latent.csv)
- [`outputs/run_20260417_211020/latent/constitution_univariate_risk_association.csv`](outputs/run_20260417_211020/latent/constitution_univariate_risk_association.csv)

#### 稳健性结果

- [`outputs/run_20260417_211020/latent/latent_bootstrap_summary.csv`](outputs/run_20260417_211020/latent/latent_bootstrap_summary.csv)
- [`outputs/run_20260417_211020/latent/latent_score_stability_summary.csv`](outputs/run_20260417_211020/latent/latent_score_stability_summary.csv)
- [`outputs/run_20260417_211020/latent/latent_stability_summary.json`](outputs/run_20260417_211020/latent/latent_stability_summary.json)

#### 图形结果

- [`outputs/run_20260417_211020/latent/latent_loading_heatmap.png`](outputs/run_20260417_211020/latent/latent_loading_heatmap.png)
- [`outputs/run_20260417_211020/latent/latent_loading_stability_forest.png`](outputs/run_20260417_211020/latent/latent_loading_stability_forest.png)
- [`outputs/run_20260417_211020/latent/latent_score_stability_boxplot.png`](outputs/run_20260417_211020/latent/latent_score_stability_boxplot.png)

### 2.4 我们是如何得到这个答案的

#### 第一步：按机制分三组，而不是把全部变量混成一个分数

我们把原始变量分为三类：

1. 九种体质积分；
2. 活动能力与活动风险；
3. 血脂、血糖、尿酸、BMI 的偏离特征。

这样做的逻辑是：

- 体质描述的是内在偏颇；
- 活动描述的是外在功能状态；
- 代谢偏离描述的是生理异常程度。

三者本身属于不同层面，先分组提取潜因子更符合题面结构。

#### 第二步：构造一阶潜因子

对每一组变量做标准化，并提取单因子：

- 体质因子 `constitution_factor`
- 活动因子 `activity_factor`
- 代谢因子 `metabolic_factor`

这一步对应 `latent_loadings.csv` 和 `latent_view_diagnostics.csv`。

#### 第三步：构造二阶综合潜状态

得到三个一阶因子之后，再做二阶综合，形成 `latent_state_h`。  
它的含义不是替代某个单一指标，而是：

> 在体质偏颇、活动不足和代谢异常共同作用下，个体总体风险结构的位置。

这一步对应 `latent_second_order.csv` 和 `latent_state_scores.csv`。

#### 第四步：比较九体质贡献

我们不是简单比较九体质的均值，而是看九体质指标在体质因子中的载荷及其绝对贡献占比。

因此，“贡献差异”的含义在本文中应理解为：

> 不同体质指标对潜在体质风险结构的解释份额不同。

#### 第五步：稳健性验证

为避免问题 1 变成“一次性因子分析结果”，项目又做了：

1. 载荷 bootstrap；
2. 体质贡献 bootstrap；
3. 样本得分稳定性 bootstrap。

因此可以合理说：

> 问题 1 的潜状态结构不是偶然拟合结果，而具备较好的可重复性。

### 2.5 当前问题 1 能支撑到什么程度

能强支撑的结论：

1. 可从多维变量中提取体质、活动、代谢三类潜在结构；
2. 九体质贡献存在差异；
3. 潜状态具有 bootstrap 稳健性；
4. 问题 1 结果可以自然流入问题 2 和问题 3。

需要谨慎表述的地方：

1. 当前结果并没有直接证明“痰湿体质一定是所有体质中贡献最大的唯一主导项”；
2. 更适合写“贡献存在差异并具有稳定性”，不宜写成“严格因果排序”。

### 2.6 与问题 2 的关联

问题 1 的产物不是独立摆设，而是进入问题 2 的输入层。  
`constitution_factor`、`activity_factor`、`metabolic_factor`、`latent_state_h` 都参与了后续风险建模与解释。

因此，问题 1 到问题 2 的自然过渡可以写成：

> 在完成多维潜状态表征后，下一步将这些结构性变量输入风险预警模型，以实现从“关键结构识别”到“三级风险分层”的递进建模。

---

## 3. 问题 2：三级风险预警、阈值依据与痰湿高风险核心组合

### 3.1 题目要求

题面问题 2 要求：

1. 构建融合多维特征的风险预警模型；
2. 输出低、中、高三级风险；
3. 给出三级风险阈值依据；
4. 识别痰湿体质高风险人群的核心特征组合，并进行解释。

### 3.2 我们给出的答案

我们当前对问题 2 的回答是：

1. 使用不含血脂泄露变量的前置特征构建 `anchor_front_logistic` 风险模型；
2. 对模型输出概率做后验校准，形成连续风险概率和连续风险分数；
3. 通过网格搜索与 bootstrap 稳健性分析确定三级风险阈值；
4. 在痰湿子群内进行规则挖掘，提取高风险核心特征组合。

可直接写入正文的答案表达为：

> 本文构建了一个融合体质潜因子、活动能力、代谢偏离、痰湿积分及背景风险的三级风险预警模型。该模型显式剔除了血脂诊断泄露变量，先在锚点样本上训练，再对输出概率做后验校准，从而同时保证风险排序能力与概率解释能力。在此基础上，我们通过阈值搜索获得低/中/高三级风险分层，并在痰湿体质子群内进一步提炼出高风险核心特征组合。

### 3.3 支撑问题 2 的关键结果文件

#### 主模型结果

- [`outputs/run_20260417_211020/risk/risk_scores.csv`](outputs/run_20260417_211020/risk/risk_scores.csv)
- [`outputs/run_20260417_211020/risk/risk_tier_summary.csv`](outputs/run_20260417_211020/risk/risk_tier_summary.csv)
- [`outputs/run_20260417_211020/risk/risk_model_coefficients.csv`](outputs/run_20260417_211020/risk/risk_model_coefficients.csv)

#### 阈值与分层依据

- [`outputs/run_20260417_211020/risk/risk_thresholds.json`](outputs/run_20260417_211020/risk/risk_thresholds.json)
- [`outputs/run_20260417_211020/risk/risk_threshold_summary.json`](outputs/run_20260417_211020/risk/risk_threshold_summary.json)
- [`outputs/run_20260417_211020/risk/risk_threshold_grid.csv`](outputs/run_20260417_211020/risk/risk_threshold_grid.csv)
- [`outputs/run_20260417_211020/risk/risk_anchor_monotonicity.csv`](outputs/run_20260417_211020/risk/risk_anchor_monotonicity.csv)

#### 性能和校准证据

- [`outputs/run_20260417_211020/risk/risk_model_cv_metrics.csv`](outputs/run_20260417_211020/risk/risk_model_cv_metrics.csv)
- [`outputs/run_20260417_211020/risk/risk_model_calibration.csv`](outputs/run_20260417_211020/risk/risk_model_calibration.csv)
- [`outputs/run_20260417_211020/validation/risk_evidence_summary.json`](outputs/run_20260417_211020/validation/risk_evidence_summary.json)
- [`outputs/run_20260417_211020/validation/risk_model_benchmark.csv`](outputs/run_20260417_211020/validation/risk_model_benchmark.csv)

#### 规则挖掘结果

- [`outputs/run_20260417_211020/rules/minimal_rules.csv`](outputs/run_20260417_211020/rules/minimal_rules.csv)
- [`outputs/run_20260417_211020/rules/core_rules.csv`](outputs/run_20260417_211020/rules/core_rules.csv)
- [`outputs/run_20260417_211020/rules/rule_summary.json`](outputs/run_20260417_211020/rules/rule_summary.json)
- [`outputs/run_20260417_211020/rules/rule_stability_summary.json`](outputs/run_20260417_211020/rules/rule_stability_summary.json)

### 3.4 我们是如何得到这个答案的

#### 第一步：风险预警只使用前置特征

问题 2 最关键的建模原则是：

> 风险预警不直接把血脂诊断标准重新作为输入特征。

当前代码显式剔除了血脂核心指标及其偏离量，只把它们用于锚点定义与后验解释。  
因此，问题 2 的主模型可以解释为：

> 基于体质、活动、背景和非诊断性代谢异常，识别高血脂风险。

#### 第二步：得到连续风险概率与分数

模型先输出连续风险概率，再将其乘以 100 得到连续风险分数。  
这样做的好处是：

1. 可以做全体样本排序；
2. 可以做阈值搜索；
3. 可以为问题 3 提供更细粒度的患者状态描述。

#### 第三步：对概率做后验校准

本轮结果中，主模型经过自动概率校准后，表现明显优于未校准状态。  
当前 `risk_threshold_summary.json` 说明最终自动选择：

- `probability_calibration = isotonic`

同时 `validation/risk_evidence_summary.json` 中：

- `roc_auc` 保持较高；
- `brier_score` 较低；
- `expected_calibration_error` 已很低。

因此可以明确写：

> 模型不仅能够区分高低风险，还能够给出较为可信的相对风险概率。

#### 第四步：搜索三级风险阈值

当前三级风险不是人工按 33%、67% 切分，而是：

1. 在候选阈值网格上遍历；
2. 同时考虑锚点识别正确率、严重度单调性、组间分离度、分组平衡度；
3. 再用 bootstrap 验证阈值稳定性。

这一步对应：

- `risk_threshold_grid.csv`
- `risk_threshold_summary.json`
- `risk_threshold_bootstrap.csv`

因此可以在论文中有力回应“阈值依据是什么”这一题面要求。

#### 第五步：提取痰湿高风险核心特征组合

题面不满足于只给一个模型分数，还要求明确“高风险组合”。  
因此在痰湿子群内部进一步构造候选规则池，并依据覆盖率、纯度、提升度及增量覆盖筛出最小规则集。

当前 `minimal_rules.csv` 给出的规则就是问题 2 的解释层答案。

#### 第六步：补做基线对照、消融与显著性检验

为了回答“我们的模型为什么可信、是否只是偶然跑得好”，当前验证层又增加了三类结果：

- `validation/risk_model_benchmark.csv`
- `validation/risk_model_ablation.csv`
- `validation/risk_model_significance.csv`

其中：

1. `risk_model_benchmark.csv` 用来比较主模型、旧版手工加权和连续严重度 Ridge 基线；
2. `risk_model_ablation.csv` 用来比较完整主模型与去体质、去活动、去代谢、去背景、去交互项后的版本；
3. `risk_model_significance.csv` 用配对 bootstrap 给出这些差异的显著性区间和 `p` 值。

本轮结果显示：

1. 主模型 `AUC=0.9219`，高于旧版手工加权的 `0.7915` 和 Ridge 基线的 `0.5674`；
2. 去代谢信息后，`AUC` 下降到 `0.5997`，是所有消融中退化最明显的一项；
3. 去体质信息后也有稳定退化，说明体质模块并非可有可无。

因此问题 2 不应只写成“我们拟合了一个模型”，而应写成：

> 与旧版手工加权和连续严重度 Ridge 基线相比，当前主模型在区分能力、概率质量和锚点分离上均表现出稳定优势；消融实验进一步说明，代谢偏离模块是风险识别的核心支撑，体质模块提供了稳定增益，说明当前风险模型确实捕捉到了具有结构意义的风险规律，而不是单纯依赖某次抽样偶然得到的结果。

### 3.5 当前问题 2 的正式答案可如何表述

推荐正文表述：

> 结果显示，经校准后的主模型具有较强的风险区分能力，高风险组的确诊率显著高于低风险组，且风险分层与潜状态严重度保持单调一致。三级阈值由锚点分离与严重度结构共同搜索得到，说明分层标准具有客观依据。进一步的基线对照与消融实验表明，当前主模型显著优于旧版手工加权与连续严重度 Ridge 基线，且代谢偏离与体质信息是其中最关键的贡献模块。此外，在痰湿子群内，尿酸偏离异常与活动能力不足等因素共同构成了高风险表型的重要特征组合，使问题二的答案既具预测性，又具可解释性。

### 3.6 当前问题 2 还能补强的点

尽管问题 2 已经比较完整，但仍有两点可以继续加强：

1. 规则层面还可以进一步增强中医叙事一致性；
2. 对“高风险但尚未完全确诊”的边缘人群，可以增加更细的讨论。

### 3.7 与问题 3 的关联

问题 2 产生的 `risk_tier` 会进入问题 3，用于总结“患者特征-最优方案”的映射规律。  
因此，问题 2 到问题 3 的自然过渡句可以写成：

> 在得到三级风险分层后，下一步针对痰湿确诊患者，在风险等级、年龄和活动能力等特征约束下进一步设计 6 个月个体化干预方案。

---

## 4. 问题 3：痰湿确诊患者的 6 个月个体化干预优化

### 4.1 题目要求

题面问题 3 要求：

1. 针对体质标签为 5 的确诊痰湿患者；
2. 结合中医调理原则与身体耐受度；
3. 在考虑经济成本与降低痰湿积分目标的前提下；
4. 构建优化模型，给出不同患者的 6 个月干预方案；
5. 总结“患者特征-最优方案”匹配规律；
6. 单独给出样本 `ID=1,2,3` 的最优方案。

### 4.2 我们给出的答案

我们当前对问题 3 的回答是：

1. 在痰湿患者子群上构造离散动作空间；
2. 对每位患者给出 3 个阶段、总计 6 个月的方案；
3. 每阶段方案由“中医调理等级 + 活动强度 + 周频次”三元组组成；
4. 在预算、耐受度、年龄/活动约束、调理等级约束和平滑约束下求解最优路径；
5. 在总体层面输出预算前沿和“风险层级/年龄组 -> 最优方案模式”映射；
6. 题面指定的样本 1、2、3 的最优方案已经显式给出。

可直接写入正文的答案表达为：

> 本文将题面干预决策离散化为“调理等级-活动强度-周频次”的三元组合，在年龄、活动能力、经济成本、耐受度及阶段平滑性等现实约束下，对痰湿确诊患者求解 6 个月最优干预路径。结果不仅给出了个体级最优方案，还总结了不同风险层级和年龄组的方案匹配规律，并显式输出了样本 1、2、3 的个体最优干预方案。

### 4.3 支撑问题 3 的关键结果文件

#### 个体方案结果

- [`outputs/run_20260417_211020/optimization/phlegm_patient_plans.csv`](outputs/run_20260417_211020/optimization/phlegm_patient_plans.csv)
- [`outputs/run_20260417_211020/optimization/sample_1_2_3_plans.csv`](outputs/run_20260417_211020/optimization/sample_1_2_3_plans.csv)

#### 匹配规律结果

- [`outputs/run_20260417_211020/optimization/strategy_mapping_by_risk_tier_age.csv`](outputs/run_20260417_211020/optimization/strategy_mapping_by_risk_tier_age.csv)
- [`outputs/run_20260417_211020/optimization/strategy_mapping_by_activity_bins.csv`](outputs/run_20260417_211020/optimization/strategy_mapping_by_activity_bins.csv)
- [`outputs/run_20260417_211020/optimization/strategy_mapping_summary.json`](outputs/run_20260417_211020/optimization/strategy_mapping_summary.json)

#### 预算与帕累托证据

- [`outputs/run_20260417_211020/optimization/pareto_frontier_summary.csv`](outputs/run_20260417_211020/optimization/pareto_frontier_summary.csv)
- [`outputs/run_20260417_211020/optimization/pareto_budget_marginal_gains.csv`](outputs/run_20260417_211020/optimization/pareto_budget_marginal_gains.csv)
- [`outputs/run_20260417_211020/optimization/pareto_budget_evidence.json`](outputs/run_20260417_211020/optimization/pareto_budget_evidence.json)

#### 可行性与稳健性结果

- [`outputs/run_20260417_211020/optimization/primary_budget_feasibility_by_group.csv`](outputs/run_20260417_211020/optimization/primary_budget_feasibility_by_group.csv)
- [`outputs/run_20260417_211020/validation/optimization_robustness.csv`](outputs/run_20260417_211020/validation/optimization_robustness.csv)

#### 基线与显著性结果

- [`outputs/run_20260417_211020/validation/optimization_baseline_patient_level.csv`](outputs/run_20260417_211020/validation/optimization_baseline_patient_level.csv)
- [`outputs/run_20260417_211020/validation/optimization_baseline_summary.csv`](outputs/run_20260417_211020/validation/optimization_baseline_summary.csv)
- [`outputs/run_20260417_211020/validation/optimization_significance.csv`](outputs/run_20260417_211020/validation/optimization_significance.csv)

### 4.4 我们是如何得到这个答案的

#### 第一步：只对痰湿患者子群建模

题面明确指出：

> 问题 3 针对的是确诊为痰湿体质的患者。

当前代码通过 `phlegm_intervention_cohort()` 统一筛选痰湿干预子群，因此问题 3 的样本对象与题面是一致的，而不是对全体 1000 人都一视同仁地做优化。

#### 第二步：构造离散动作空间

每个阶段的决策由三部分构成：

1. 中医调理等级；
2. 活动干预强度；
3. 每周训练频次。

每个患者可行的动作空间并不相同，而是受以下约束共同决定：

1. 年龄组；
2. 活动总分；
3. 当前痰湿积分；
4. 预算；
5. 耐受度。

因此，问题 3 当前不是“给固定模板”，而是真正的个体化可行域优化。

#### 第三步：把题面规则直接写进模型

当前优化模型显式写入了题面约束：

1. 调理等级与痰湿积分区间匹配；
2. 活动强度与年龄组、活动总分匹配；
3. 训练频次在 `1-10 次/周`；
4. 6 个月总成本受预算约束；
5. 每提升一级强度、每增加一次训练的收益按题面规则计算；
6. 活动强度跨阶段跳变超过 1 个等级会被直接判为不可行。

因此可以在正文中理直气壮地写：

> 我们不是先拍一个主观方案，再去解释为什么合理；而是先把题面规则写成约束，再让求解器在可行域内找最优路径。

#### 第四步：输出个体最优方案

`phlegm_patient_plans.csv` 中给出了每位痰湿患者在主预算下的最优方案，包括：

- 最终潜状态；
- 最终痰湿积分；
- 总成本；
- 总负担；
- 三阶段方案路径。

题面特别要求的样本 1、2、3，则由：

- `sample_1_2_3_plans.csv`

直接给出。

#### 第五步：总结“患者特征-最优方案”规律

题面不满足于给出若干单例方案，还要求总结规律。  
因此项目把个体方案进一步聚合成：

1. `risk_tier + age_group` 映射表；
2. `activity_bin + age_group` 映射表。

这样问题 3 就形成了：

1. 个体级答案；
2. 群体级模式总结。

#### 第六步：做预算前沿分析

如果只给单一预算下的方案，问题 3 的结论会偏单薄。  
当前项目额外加入预算扫描，得到：

- `pareto_frontier_summary.csv`
- `pareto_budget_marginal_gains.csv`

因此问题 3 还能回答一个更有价值的问题：

> 在增加预算时，收益是否持续增长，还是存在边际递减？

#### 第七步：把优化方案与可行启发式基线比较

如果只给最优解而没有对照，答辩时很容易被追问：

> “你的优化方案究竟比简单规则好多少？”

因此当前又构造了两类启发式基线：

1. `min_cost_feasible`：在题面可行域内优先选择最低成本路径；
2. `min_burden_feasible`：在题面可行域内优先选择最低负担路径。

再将它们与 `optimized` 主方案做患者级配对比较。  
本轮结果表明：

1. 主方案平均末期痰湿积分约为 `42.47`，两类基线约为 `50.74`；
2. 主方案平均末期潜状态约为 `18.46`，基线约为 `20.22`；
3. 主方案相对基线平均再降低痰湿积分约 `8.27`，降低末期潜状态约 `1.76`；
4. Wilcoxon 检验的 `p` 值达到 `10^-27` 量级。

与此同时：

1. 主方案平均成本约 `1266.32`，基线约 `252.00`；
2. 主方案平均负担约 `13.83`，基线约 `4.20`。

因此问题 3 的正确叙事不是“优化总能免费变好”，而是：

> 在相同题面规则下，优化方案确实能显著改善结局，但需要更高成本和更高干预负担，因此它解决的是效果-成本-负担之间的权衡最优问题。

### 4.5 当前问题 3 的正式答案可如何表述

推荐正文表述：

> 针对痰湿确诊患者，我们构建了一个离散路径优化模型，在满足年龄、活动能力、调理等级、训练频次、预算和耐受度等约束的前提下，输出了 6 个月个体化最优干预方案。结果显示，低龄组和活动能力较好的患者可获得更积极的中高频、中高强度方案，而高龄组在平滑约束和耐受度约束下更倾向于保守方案。预算扫描进一步表明，随着预算提升，平均痰湿结局持续改善，但在中高预算区间边际收益显著递减。进一步的基线对照与显著性检验说明，当前优化方案相对低成本、低负担启发式基线能够显著改善末期痰湿积分和潜状态结局，但其代价是更高的经济成本与执行负担。

### 4.6 当前问题 3 需要谨慎说明的地方

问题 3 当前最需要主动解释的是：

1. 并非所有痰湿患者都存在严格可行解；
2. 高年龄组、低活动能力组的可行率明显下降；
3. 这不是模型错误，而是题面硬约束与耐受度约束共同收缩了可行域。

因此建议在正文中主动增加一小段说明：

> 对部分高龄或活动能力较低的患者，题面规定的强度、频次、成本及耐受度约束叠加后，可能不存在同时满足全部条件的严格可行方案。该结果反映的是现实约束的强烈作用，而不是优化模型的失效。

### 4.7 与前两问的关联

问题 3 并不是脱离前两问独立展开的。  
它继承了前两问的两个关键输出：

1. 问题 1 的潜状态 `latent_state_h`，用于表征患者当前整体风险结构；
2. 问题 2 的 `risk_tier`，用于总结不同风险层级对应的最优方案模式。

因此三问在结构上是连贯的：

1. 问题 1 负责“结构表征”；
2. 问题 2 负责“风险分层”；
3. 问题 3 负责“干预决策”。

---

## 5. 三个问题之间的整体闭环

### 5.1 闭环逻辑

当前项目的三问不是三个孤立模型，而是一个递进闭环：

1. **问题 1：识别结构**  
   从多维指标中提取潜在风险结构，得到个体潜状态表征；
2. **问题 2：识别层级**  
   基于潜状态及其他前置特征，识别个体属于低、中、高哪一层风险；
3. **问题 3：实施干预**  
   对高关注子群进一步给出满足现实约束的 6 个月个体化方案。

### 5.2 最适合在正文中的总表述

推荐把三问整体总结为：

> 本文以“结构识别—风险分层—干预优化”为主线，首先从体质、活动和代谢三个维度提取潜在健康结构，其次构建经校准的三级风险预警模型并给出痰湿高风险表型组合，最后在题面现实约束下对痰湿确诊患者进行 6 个月离散干预优化，从而形成从风险识别到策略制定的完整闭环。

### 5.3 三问目前的满足程度

结合当前代码和结果，可做如下判断：

1. 问题 1：结构上已经完整，结论表达需稍谨慎；
2. 问题 2：当前是最成熟的一问，预测、校准、基线对照与消融证据都较强；
3. 问题 3：方案、预算前沿和基线显著性都已补齐，但需主动解释无可行解样本及效果-成本权衡。

---

## 6. 结论性建议

如果这份文档用于指导论文正文，我建议：

1. 把问题 2 作为全文最强的实证核心；
2. 把问题 3 作为应用落地亮点；
3. 把问题 1 写成“结构识别与表征”而不是“唯一病因发现”。

这样最符合当前代码和结果，也最能避免答辩时被追问“你的结论是不是写得比结果更强”。


