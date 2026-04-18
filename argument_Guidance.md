# argument_Guidance

## 1. 文档定位

本文档用于统一整个项目在论文、答辩、说明文档中的叙述口径。目标不是“写得宏大”，而是做到：

1. 贴合当前代码真实实现；
2. 贴合题面三问；
3. 公式、变量、模型与输出目录一一对应；
4. 能直接指导正文写作、图表说明、答辩口径和附录说明。

本文档对应当前有效代码与结果目录：

- 代码入口：`scripts/run_full_pipeline.py`
- 调度核心：`src/pipeline/runner.py`
- 当前有效结果：`outputs/run_20260417_211020/`

---

## 2. 项目总口径

### 2.1 题目对象

题面为 `2026年第十六届MathorCup数学应用挑战赛题目—C题.pdf`，主题是：

> 面向中老年人群高血脂症的风险预警及干预方案优化。

题面共有 **3 个问题**：

1. 问题 1：从血常规和活动量表中筛选关键指标，研究九种体质对发病风险的贡献差异；
2. 问题 2：构建低/中/高三级风险预警模型，给出阈值依据，并识别痰湿高风险人群核心特征组合；
3. 问题 3：针对确诊痰湿体质患者，设计 6 个月个体化干预方案，并总结“患者特征-最优方案”规律。

### 2.2 总体方法路线

当前项目采用的真实路线是：

1. **数据治理与派生特征构造**  
   将原始 1000 例样本标准化，并构造偏离特征、活动能力特征、体质结构特征、背景风险特征、交互特征。

2. **三视角潜状态建模**  
   分别从体质、活动、代谢三组变量提取一阶潜因子，再对三类因子做二阶综合，形成 `latent_state_h`。

3. **前置特征风险预警模型**  
   使用不含血脂诊断变量泄露的前置特征构造风险模型，通过阈值搜索输出低/中/高三级风险，并对概率做后验校准。

4. **痰湿高风险规则挖掘**  
   在痰湿子群内识别覆盖率、纯度、提升度均满足要求的核心规则组合。

5. **6 个月干预优化**  
   针对痰湿患者，在年龄、活动能力、调理分级、频次、成本、耐受度、平滑度等约束下求解离散最优方案，并输出预算前沿与特征-方案映射。

### 2.3 关键总原则

正文和答辩中建议明确以下三条总原则：

1. **不使用深度学习**  
   当前方案完全基于经典统计建模、优化建模与规则挖掘，符合数模竞赛语境。

2. **风险预警不直接复写诊断**  
   当前风险模型的输入显式剔除了 `TC/TG/LDL-C/HDL-C` 及其派生泄露变量，避免把诊断变量直接再预测一遍。

3. **问题三采用离散决策优化，而非经验拍脑袋给方案**  
   干预方案是在题面约束下通过组合优化得到，而不是手工规定的固定模板。

---

## 3. 数据与符号口径

### 3.1 原始变量组

来自 `data/raw/附件1：样例数据.xlsx` 的标准化字段主要包括：

1. 九种体质积分与体质标签；
2. `ADL`、`IADL`、`activity_total`；
3. 血脂指标：`tc`、`tg`、`ldl_c`、`hdl_c`；
4. 代谢指标：`fasting_glucose`、`uric_acid`、`bmi`；
5. 诊断标签：`hyperlipidemia_label`、`lipid_abnormality_type`；
6. 背景变量：`age_group`、`sex`、`smoking_history`、`drinking_history`。

### 3.2 统一符号建议

建议正文统一采用以下符号：

- 第 \(i\) 个样本：\(i=1,\dots,n\)
- 体质九分量向量：\(\mathbf{c}_i\)
- 活动能力向量：\(\mathbf{a}_i\)
- 代谢偏离向量：\(\mathbf{m}_i\)
- 一阶潜因子：\(F_i^{(c)},F_i^{(a)},F_i^{(m)}\)
- 二阶综合潜状态：\(H_i\)
- 连续风险概率：\(\hat p_i\)
- 连续风险分数：\(R_i=100\hat p_i\)
- 三级风险阈值：\(t_1,t_2\)
- 第 \(k\) 阶段干预方案：\(u_{ik}=(z_{ik},q_{ik},f_{ik})\)  
  其中 `z` 为中医调理等级，`q` 为活动强度，`f` 为周频次。

---

## 4. 阶段 01：数据治理与派生特征

对应代码：

- `src/pipeline/stage_01_data.py`
- `src/features/*.py`
- `src/domain/clinical_thresholds.py`

### 4.1 偏离特征

当前代码不是直接用原始值，而是构造“偏离正常区间”的连续偏离量。  
核心公式来自 `src/domain/clinical_thresholds.py`：

\[
d(x;[L,U])=\left(\frac{\max(L-x,0)+\max(x-U,0)}{U-L}\right)^{1.5}
\]

据此构造：

- `dev_tc`
- `dev_tg`
- `dev_ldl_c`
- `dev_hdl_c`
- `dev_fasting_glucose`
- `dev_bmi`
- `dev_uric_acid`

然后进一步聚合为：

\[
\text{lipid\_deviation\_total}
=
dev\_{tc}+dev\_{tg}+dev\_{ldl\_c}+dev\_{hdl\_c}
\]

\[
\text{metabolic\_deviation\_total}
=
dev\_{fasting\_glucose}+dev\_{bmi}+dev\_{uric\_acid}
\]

### 4.2 活动能力特征

对应 `src/features/activity_features.py`：

\[
\text{activity\_risk}=\frac{100-\text{activity\_total}}{100}
\]

并构造：

- `low_activity_flag`: `activity_total < 40`
- `mid_activity_flag`: `40 <= activity_total < 60`
- `high_activity_flag`: `activity_total >= 60`

### 4.3 体质结构特征

对应 `src/features/constitution_features.py`：

\[
\text{constitution\_tanshi\_dominance}

=
\frac{\text{constitution\_tanshi}}{\sum_{j=1}^{9}\text{constitution\_score}_j}
\]

\[
\text{constitution\_pinghe\_protective}
=
\frac{\text{constitution\_pinghe}}{\sum_{j=1}^{9}\text{constitution\_score}_j}
\]

并构造：

- `constitution_label_argmax_mismatch`
- `phlegm_dampness_label_flag = 1(constitution_label == 5)`

### 4.4 背景风险特征

对应 `src/features/metabolic_features.py`：

\[
\text{age\_risk}=\frac{\text{age\_group}-1}{4}
\]

\[
\text{background\_risk}
=
\frac{\text{age\_risk}+0.3\cdot \text{smoking\_flag}+0.3\cdot \text{drinking\_flag}}{1.6}
\]

### 4.5 交互特征

对应 `src/features/interactions.py`：

\[
\text{tanshi\_x\_low\_activity}
=
\text{constitution\_tanshi\_dominance}\cdot \text{low\_activity\_flag}
\]

\[
\text{tanshi\_x\_bmi\_deviation}
=
\text{constitution\_tanshi\_dominance}\cdot dev\_{bmi}
\]

\[
\text{metabolic\_x\_low\_activity}
=
\text{metabolic\_deviation\_total}\cdot \text{low\_activity\_flag}
\]

### 4.6 写作口径建议

建议正文写法：

> 我们首先依据题面附表中的临床正常范围，将血脂、血糖、尿酸、BMI 等连续检测值转化为“相对于正常区间的偏离量”，再与活动能力、体质偏颇程度、背景行为风险共同构成统一特征空间，从而保证后续潜状态建模、风险分层和干预优化均建立在同一张规范化特征底表之上。

---

## 5. 问题 1：潜状态与体质贡献差异

对应代码：

- `src/models/latent_state.py`
- `src/pipeline/stage_02_latent.py`

### 5.1 一阶潜因子

三组视角定义为：

1. 体质视角：九种体质积分；
2. 活动视角：`adl_total`、`iadl_total`、`activity_total`、`activity_risk`；
3. 代谢视角：`lipid_deviation_total`、`metabolic_deviation_total`、`dev_bmi`、`dev_fasting_glucose`、`dev_uric_acid`。

每一视角先做标准化，再提取单因子：

\[
\mathbf{x}^{(v)}_i \xrightarrow{\text{standardize}} \tilde{\mathbf{x}}^{(v)}_i
\]

\[
F_i^{(v)} = \text{FA}_1(\tilde{\mathbf{x}}^{(v)}_i)
\]

其中当前代码默认使用：

- `FactorAnalysis(n_components=1)`
- 若失败则退化到 `PCA(n_components=1)`。

### 5.2 二阶综合隐状态

把三个一阶因子：

\[
\mathbf{F}_i = \left(F_i^{(c)},F_i^{(a)},F_i^{(m)}\right)
\]

再做一维 `PCA`：

\[
H_i^{raw}=\text{PCA}_1(\mathbf{F}_i)
\]

然后使用最小-最大规范化到 0-100：

\[
H_i = 100\cdot \frac{H_i^{raw}-\min(H^{raw})}{\max(H^{raw})-\min(H^{raw})+\varepsilon}
\]

项目中的最终综合隐状态即：

- `latent_state_h`

### 5.3 九种体质贡献差异

当前代码采用的是“体质因子载荷的绝对值占比”来度量九种体质贡献差异：

\[
w_j = \frac{|\lambda_j|}{\sum_{k=1}^{9}|\lambda_k|}
\]

其中 \(\lambda_j\) 为第 \(j\) 个体质指标在 `constitution_factor` 上的载荷。

这对应输出文件：

- `latent/constitution_contributions_to_latent.csv`
- `latent/constitution_contribution_stability.csv`

### 5.4 稳健性口径

当前项目对问题一不是只做一次拟合，而是做了：

1. 载荷 bootstrap；
2. 体质贡献 bootstrap；
3. 潜状态得分稳定性 bootstrap。

因此可以在正文中写：

> 问题一的潜状态提取不是一次性拟合结果，而是经过 bootstrap 反复重抽样验证后得到的稳定结构。

### 5.5 当前应如何谨慎表述

虽然问题一的统计实现已经完整，但当前结果中“痰湿体质一定是贡献最大项”并没有被直接验证出来。  
因此建议口径写成：

> 九种体质对潜在体质风险结构的贡献存在显著差异，其中部分体质维度的贡献更高；痰湿积分并非唯一主导项，但在综合风险结构中占有稳定位置。

不要写成：

> 痰湿体质是贡献最大的唯一核心因子。

因为这与当前代码输出不完全一致。

---

## 6. 问题 2：风险预警、阈值分层与规则组合

对应代码：

- `src/models/risk_score.py`
- `src/models/thresholding.py`
- `src/models/rule_mining.py`
- `src/pipeline/stage_03_risk.py`
- `src/pipeline/stage_04_rules.py`

### 6.1 风险模型总口径

当前主模型不是传统“直接用血脂异常标签再拟合血脂指标”，而是：

1. 使用血脂/确诊信息只定义训练锚点；
2. 风险模型输入只保留前置特征；
3. 主模型为 `anchor_front_logistic`；
4. 概率输出经后验校准。

### 6.2 风险特征矩阵

当前主模型的基础特征包括：

- `constitution_factor`
- `activity_factor`
- `metabolic_deviation_total`
- `activity_total`
- `activity_risk`
- `constitution_tanshi`
- `dev_bmi`
- `dev_fasting_glucose`
- `dev_uric_acid`
- `age_group`
- `background_risk`

交互项包括：

- `tanshi_x_low_activity`
- `tanshi_x_bmi_deviation`
- `metabolic_x_low_activity`
- `age_x_activity_risk`

### 6.3 防泄露原则

当前代码显式排除以下诊断泄露特征：

- `tc`
- `tg`
- `ldl_c`
- `hdl_c`
- `dev_tc`
- `dev_tg`
- `dev_ldl_c`
- `dev_hdl_c`
- `lipid_deviation_total`
- `hyperlipidemia_label`
- `latent_state_h`
- `metabolic_factor`

因此推荐在论文中明确写：

> 为避免把确诊依据直接重复编码进风险模型，我们在问题二主模型中显式剔除了核心血脂诊断变量及其派生偏离量，仅将其用于锚点定义和后验解释，而不作为风险预测输入。

### 6.4 锚点训练逻辑

代码中使用：

- `high_anchor`: 由确诊标签/血脂异常确定；
- `low_anchor`: 由血脂偏离为零且未确诊确定。

设训练标签为：

\[
y_i=
\begin{cases}
1, & i \in \text{high anchor}\\
0, & i \in \text{low anchor}
\end{cases}
\]

### 6.5 Logistic 风险模型

对标准化后的前置特征 \(z_{ij}\)，拟合：

\[
\eta_i = \beta_0 + \sum_{j=1}^{p}\beta_j z_{ij}
\]

\[
\hat p_i^{raw}=\sigma(\eta_i)=\frac{1}{1+e^{-\eta_i}}
\]

### 6.6 概率校准

当前主模型已加入自动后验校准，配置位于：

- `configs/risk_model.yaml`

本轮使用：

- `probability_calibration: auto`
- `calibration_selection_metric: brier_score`

代码会在 `none / sigmoid / isotonic` 三者中选出最优校准器。  
当前有效结果显示最终选择：

- `isotonic`

因此最终概率记为：

\[
\hat p_i = g(\hat p_i^{raw})
\]

其中 \(g(\cdot)\) 为自动选择的单调校准映射。

最终连续风险分数定义为：

\[
R_i=100\hat p_i
\]

### 6.7 三级风险阈值搜索

当前阈值并不是人工指定，而是通过网格搜索得到。  
在每组候选 \((t_1,t_2)\) 下，定义：

- 低风险：\(R_i<t_1\)
- 中风险：\(t_1 \le R_i < t_2\)
- 高风险：\(R_i \ge t_2\)

然后用以下综合目标函数打分：

\[
\text{Obj}(t_1,t_2)=
0.20\cdot low\_ok
+0.20\cdot high\_ok
+0.20\cdot severity\_gap
+0.15\cdot between
+0.10\cdot compactness
+0.05\cdot margin
+0.05\cdot balance
+0.05\cdot monotonic
- penalty
\]

其中：

- `low_ok`：低锚点落入低风险组的比例；
- `high_ok`：高锚点落入高风险组的比例；
- `severity_gap`：高低组严重度差；
- `between`：组间离散度；
- `compactness`：组内紧致度；
- `margin`：阈值间隔；
- `balance`：三组样本比例平衡度；
- `monotonic`：严重度是否满足低 < 中 < 高。

### 6.8 问题二规则挖掘

规则挖掘仅在痰湿子群内进行，目标是识别：

\[
\text{Target}=1(\text{risk\_tier}=\text{high})
\]

候选规则从以下条件池组合得到：

- `痰湿积分>=60`
- `痰湿积分>=80`
- `活动总分<40`
- `活动总分<60`
- `BMI偏离>0`
- `TG偏离>0`
- `LDL偏离>0`
- `综合隐状态高`
- `血脂偏离总量高`
- `代谢偏离总量高`
- `血糖偏离>0`
- `尿酸偏离>0`
- `吸烟史=1`
- `饮酒史=1`

每条规则计算：

\[
\text{coverage}=\frac{\text{规则覆盖的高风险样本数}}{\text{高风险样本总数}}
\]

\[
\text{purity}=\frac{\text{规则覆盖的高风险样本数}}{\text{规则覆盖样本总数}}
\]

\[
\text{lift}=\frac{\text{purity}}{\text{高风险总体基线占比}}
\]

然后通过“增量覆盖 + 冗余约束”选出最小规则集。

### 6.9 问题二建议写作口径

可以强写的内容：

1. 模型具有较强排序能力；
2. 经校准后，风险概率解释力显著增强；
3. 三级风险与确诊率、潜状态呈单调关系；
4. 痰湿高风险人群存在可解释的核心组合特征。

### 6.10 问题二的基线对照、消融与显著性

为了避免“只报一个最好模型”的嫌疑，当前验证层已额外输出：

- `validation/risk_model_benchmark.csv`
- `validation/risk_model_ablation.csv`
- `validation/risk_model_significance.csv`

其中基线对照包含：

1. `anchor_front_logistic` 主模型；
2. `legacy_weighted` 旧版手工加权口径；
3. `severity_ridge` 连续严重度 Ridge 基线。

本轮关键结果可以直接写为：

1. 主模型 `AUC=0.9219`、`PR-AUC=0.9774`；
2. 旧版手工加权仅 `AUC=0.7915`；
3. Ridge 基线仅 `AUC=0.5674`；
4. 主模型对两类基线在 `AUC / PR-AUC / Brier / LogLoss` 上均为显著改进。

显著性文件中的 `p_value_two_sided` 基于配对 bootstrap 改进分布给出。  
因此这里更合适的表述是：

> 主模型相对旧版手工加权和连续严重度 Ridge 基线均表现出稳定且统计显著的优势，说明当前结果并非某一次样本划分下的偶然波动。

消融实验则对应“模型到底靠什么在起作用”。  
当前逐项删除：

1. 体质信息；
2. 活动信息；
3. 代谢信息；
4. 背景信息；
5. 交互项。

本轮最关键发现是：

1. 去代谢信息后，`AUC` 从 `0.9219` 降至 `0.5997`；
2. `anchor_gap` 从 `32.68` 降至 `2.52`；
3. 对应显著性检验几乎全部为极强显著。

这说明：

> 代谢偏离信息是问题二风险识别的核心支撑模块；体质信息也有稳定增益；活动与背景信息更多起到边际修正和分层细化作用。

需要谨慎的内容：

1. 不宜宣称规则集已经穷尽所有临床模式；
2. 不宜把某一条规则写成“唯一病因”；
3. 更适合写“高风险表型组合”而不是“病理因果律”；
4. 即便显著性很强，也应写成“当前样本内规律稳定”，而不是“已证明普适规律”。

---

## 7. 问题 3：干预优化、预算前沿与匹配规律

对应代码：

- `src/models/intervention_optimizer.py`
- `src/domain/intervention_rules.py`
- `src/domain/activity_rules.py`
- `src/domain/tcm_rules.py`
- `src/pipeline/stage_05_optimize.py`

### 7.1 决策变量

对每个患者，每个阶段决策为：

\[
u_{ik}=(z_{ik},q_{ik},f_{ik})
\]

其中：

- \(z_{ik}\)：中医调理等级（1/2/3）
- \(q_{ik}\)：活动强度等级（1/2/3）
- \(f_{ik}\)：训练频次（1-10 次/周）

项目中当前采用三阶段：

1. 激活期 2 个月
2. 巩固期 2 个月
3. 维持期 2 个月

### 7.2 可行域约束

#### 7.2.1 调理等级约束

根据题面附表 2：

- 痰湿积分 \( \le 58 \) 只允许 1 级；
- \(59\sim61\) 允许 1/2 级；
- \( \ge 62 \) 允许 1/2/3 级。

#### 7.2.2 活动强度约束

由年龄约束和活动总分约束共同决定：

\[
\mathcal{Q}_i = \mathcal{Q}_i^{age}\cap \mathcal{Q}_i^{activity}
\]

#### 7.2.3 频次约束

\[
f_{ik}\in\{1,2,\dots,10\}
\]

#### 7.2.4 成本约束

单阶段成本：

\[
Cost_{ik}=4\cdot months_k \cdot f_{ik}\cdot c(q_{ik}) + months_k \cdot c(z_{ik})
\]

总成本满足：

\[
\sum_k Cost_{ik}\le B
\]

其中 \(B\) 为预算上限，当前主要扫描：

- 500
- 800
- 1200
- 1500
- 2000

#### 7.2.5 耐受度约束

当前定义：

\[
Tol_i = base + \alpha \cdot activity\_total_i - \beta \cdot age\_group_i
\]

阶段负担分数：

\[
Burden_{ik}=w_1 q_{ik}+w_2 f_{ik}
\]

并要求：

- 每阶段负担不超过个人耐受度；
- 总负担不超过阶段数乘耐受上限。

#### 7.2.6 平滑度约束

当前代码使用的是**硬约束**而非软惩罚：

\[
|q_{i,k+1}-q_{ik}|\le 1
\]

这点非常重要，正文应明确写出：

> 活动强度跳变超过 1 个等级的方案直接判为不可行，而不是仅在目标函数中做轻微惩罚。

### 7.3 状态转移与干预收益

题面给出：

- 每提升一级强度，每月痰湿积分预期下降 3%
- 每周增加 1 次训练，每月痰湿积分预期下降 1%

当前代码实现为：

\[
\text{exercise\_response}
=
months \cdot (q-1)\cdot 0.03 \cdot gate(f)
+
months \cdot \max(f-5,0)\cdot 0.01
\]

再叠加中医调理固定收益和协同项，得到活动响应与中医响应，最终映射到：

- `tanshi_gain`
- `latent_gain`

### 7.4 优化目标

当前主输出使用的是：

- `optimize_for='pareto_tanshi'`

即在预算扫描中，优先最小化多情景下的最终痰湿积分。  
对于三阶段问题，当前代码采用的是：

- 与 MILP 等价的**三阶段路径枚举**求解器；
- 目标先比较最坏情景最终痰湿，再比较成本，再比较总负担。

因此，正文推荐表述为：

> 问题三主结果采用基于题面规则的离散路径优化方法，在预算约束下优先压低最坏情景痰湿结局，并在相同结局水平下优先选择成本更低、负担更小的方案。

### 7.5 匹配规律提取

优化不是只给单个患者方案，还进一步对主预算方案表做分组聚合，提取：

1. `risk_tier + age_group` 对应的方案众数；
2. `activity_bin + age_group` 对应的方案众数。

这就是题面所要求的：

> “患者特征-最优方案”的匹配规律。

### 7.6 当前问题三的限制口径

本轮结果中存在一部分无可行解样本，尤其集中在高年龄组。  
因此建议正文写作时明确：

1. 高龄且活动能力受限患者在题面硬约束下可行域显著缩小；
2. 无可行解并不代表模型失败，而代表当前约束下不存在满足预算、耐受度和平滑度的可实施方案；
3. 若需要工程落地，可额外给出“保守替代方案”作为管理建议，但当前代码输出的是严格可行解。

### 7.7 问题三的基线对照与显著性

为防止“优化器总能比随便方案更好”的质疑，当前验证层还加入了：

- `validation/optimization_baseline_patient_level.csv`
- `validation/optimization_baseline_summary.csv`
- `validation/optimization_significance.csv`

其中基线并不是完全随机方案，而是题面可行域内的两类启发式方案：

1. `min_cost_feasible`：优先选择成本最低的可行路径；
2. `min_burden_feasible`：优先选择负担最低的可行路径。

本轮总体结果显示：

1. 主优化方案平均 `final_tanshi_score=42.47`；
2. 两类启发式基线平均约为 `50.74`；
3. 主优化方案平均 `final_latent_state=18.46`，基线约为 `20.22`；
4. 但主优化方案平均成本约 `1266.32`，明显高于基线的 `252.00`。

对应的配对显著性检验采用 Wilcoxon：

1. 基线减主方案的平均末期痰湿积分差约为 `8.27`；
2. 基线减主方案的平均末期潜状态差约为 `1.76`；
3. 两者 `p` 值均约为 `10^-27` 量级；
4. 成本与负担差异也显著，说明效果提升是以更积极投入换来的。

这组结果在论文中的最佳口径不是“我们方案无条件最好”，而是：

> 与低成本、低负担的可行启发式基线相比，优化方案能够显著改善末期痰湿结局与潜状态结局，但与此同时需要承担更高的成本和干预负担，因此其优势体现为可解释的效果-成本权衡优化，而非无代价提升。

还需要补一句解释：

> 当前两类启发式基线在本轮结果中数值重合，说明在现有规则与预算约束下，最低成本路径同时也是最低负担路径；这不是结果异常，而是可行域结构本身导致的退化重合。

---

## 8. 三个问题之间的逻辑关联

### 8.1 问题 1 到问题 2

问题 1 生成：

- `constitution_factor`
- `activity_factor`
- `metabolic_factor`
- `latent_state_h`

这些变量进入问题 2，用于风险建模、阈值分层和解释风险结构。

### 8.2 问题 2 到问题 3

问题 2 生成：

- `risk_tier`
- `continuous_risk_score`

这些变量进入问题 3，用于：

1. 描述患者风险层级；
2. 形成“患者特征-最优方案”的映射表；
3. 辅助解释为什么某些患者应采用更保守或更积极的方案。

### 8.3 总体闭环

因此全文建议按如下闭环叙述：

1. 先用问题 1 构建潜状态，识别风险结构；
2. 再用问题 2 把风险结构转化为可预警、可分层、可解释的风险等级；
3. 最后在问题 3 中对高关注子群给出受约束的最优干预路径。

---

## 9. 正文写作中哪些话能说，哪些话不要说

### 9.1 可以说

1. 当前模型已实现三级风险预警；
2. 当前模型已显式避免使用血脂诊断变量作为风险输入；
3. 风险概率经校准后已有较好的可信度；
4. 干预优化满足题面年龄、活动能力、频次、成本、调理等级等约束；
5. 预算扫描结果显示明显边际收益递减；
6. 主模型相对基线与若干消融版本具有稳定优势；
7. 优化方案相对低成本/低负担基线存在显著效果提升，但伴随更高成本与负担。

### 9.2 不建议说

1. “我们精确发现痰湿体质是唯一决定因素”；
2. “我们证明了严格的临床因果关系”；
3. “所有患者都能得到可行方案”；
4. “风险概率就是未来真实发病概率的严格估计值”。

### 9.3 推荐说法

更推荐写：

> 本文模型给出的风险值应理解为“多维前置特征下的相对风险概率/风险强度”，其主要用途是排序、分层与干预优先级识别，而非替代临床确诊。

---

## 10. 与当前输出目录的对应关系

如果正文每章都要挂钩到结果文件，建议如下：

- 问题一：优先引用 `latent/` 目录结果；
- 问题二：优先引用 `risk/`、`rules/`、`validation/risk_evidence_summary.json`、`validation/risk_model_ablation.csv`、`validation/risk_model_significance.csv`；
- 问题三：优先引用 `optimization/`、`validation/optimization_robustness.csv`、`validation/optimization_baseline_summary.csv`、`validation/optimization_significance.csv`；
- 总结与答辩：优先引用 `validation/diagnostics.json`、`validation/risk_model_benchmark.csv` 与 `validation/optimization_baseline_summary.csv`。

---

## 11. 一句话总口径

当前项目的最稳妥总口径是：

> 我们基于题面给定的体质、活动、代谢和诊断信息，先构建三视角潜状态以刻画中老年人群的隐含健康结构，再利用不含诊断泄露的前置特征建立经后验校准的三级风险预警模型，并在痰湿确诊患者子群上构建满足成本、耐受度和平滑性约束的 6 个月离散干预优化模型，从而形成“风险识别—规则解释—个体干预”的完整闭环。

