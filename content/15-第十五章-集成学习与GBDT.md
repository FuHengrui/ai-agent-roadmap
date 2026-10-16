@@h1 第十五章　集成学习：森林、Boosting 与梯度提升
@@sub 阶段 20 · 机器学习算法与工程实战　|　集成学习　|　难度 ★★★

@@why 这一章在解决什么问题
上一章结尾抛了句狠话：单棵决策树"精度一般"。那怎么救？——**"三个臭皮匠，顶个诸葛亮"**：把一堆弱模型组合成一个强模型，这就是**集成学习（Ensemble Learning）**。这一章学两大门派 + 一个王牌：

- **Bagging 门派**：并行训练一堆"各自为战"的树，投票/平均——代表作**随机森林（Random Forest）**。
- **Boosting 门派**：串行训练，后一棵树"专治前一棵树的错"——代表作**Adaboost** 和 **GBDT（梯度提升决策树）**。

GBDT 尤其值得高度重视：它是 XGBoost、LightGBM、CatBoost 这些"Kaggle 霸主"的祖师爷，也是当前表格数据领域最强的模型家族。**学完本章，你手里就有了对抗绝大多数结构化数据的"终极大招"。**

@@map 上一章→本章→下一章
上一章学完单棵决策树（分裂、剪枝）并记下"单树精度一般"。**本章（讲义7 章节5-8）补齐三个算法：随机森林（Bagging）→ Adaboost（样本加权）→ GBDT（负梯度拟合残差）→ 应用 GBDT 分类实战**。下一章起进入阶段 20 收尾实战专题，把回归、分类、聚类、树模型组成"武器库"应对综合场景。

@@point ① 集成学习总览：越乱越好 vs 越错越补
@@need 要解决什么
"集成"具体怎么把弱模型变强？两大门派的核心机制分别是什么？

@@idea 核心思路
集成学习 = 训练**多个基学习器（弱模型）**，再按规则组合（投票/平均/加权）。两大门派：

| 门派 | 训练方式 | 代表作 | 关键直觉 |
|---|---|---|---|
| Bagging（并行式） | 各模型**独立并行**训练 | 随机森林 | 人人有票：让模型各不相同，平均掉彼此的错误 |
| Boosting（串行式） | 模型**逐个串行**，后一个学前一个的错 | Adaboost、GBDT | 循序渐进：每人专治前人的病，最后合力 |

- 共同前提：**基学习器要"好而不同"**——都得比瞎猜强一点（好），又不能一模一样（不同，否则集成=单模型）。
- 为什么有效：若每个模型错误是"随机独立"的，误差会互相抵消；Bagging 靠"随机性制造差异"，Boosting 靠"关注错样本制造差异"。

**至此，解决单树"精度一般"的方案正式登场。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 集成 100 个完全一样的决策树 | 一模一样=啥也没集成，投票结果与单树无异；**必须注入随机性**（Bagging）或序列纠错（Boosting） |
| 基学习器太弱（比瞎猜还差） | 集成救不动；基学习器至少比随机的略好是前提 |

@@point ② Bagging：随机抽样的并行投票
@@need 要解决什么
"一群树并行投票"具体怎么实现？为什么不直接重复训练同样的树？

@@idea 核心思路
**Bagging（Bootstrap Aggregating，自助采样聚合）**：
1. 从训练集**有放回地随机抽样**（bootstrap）造出 n 个不同的"自助样本集"（每个和原数据等大，有的样本重复出现、有的缺席）。
2. 在每个自助集上训练一棵独立决策树。
3. 预测时：分类**投票**（多数票），回归**平均**。

- 为什么要"有放回"：让每棵树的训练数据**各不相同**（差异 → 错误独立 → 可抵消），还不浪费样本。
- Bagging 的效果：方差显著下降（单棵树"跳得厉害"，一群树"平均下来稳"），偏差基本不变。
- 额外福利：未被抽中的样本（约 1/3，**OOB 袋外样本**）天然可当验证集评估——**不需要额外切验证集**让 Bagging 比"单树+手工验证"更省事。

**Bagging 本质**：用"并行 + 平均/投票"换稳定性。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 有放回抽样的结果和原数据"差不多"就不加随机 | 差异正是关键；把"不放回"理解成普通切分=没有 Bagging 效果 |
| 忘了 OOB 可以免切验证集 | 随机森林自带 oob_score_，避免"反复看测试集"的泄漏（联合上一章教训） |

@@point ③ 随机森林：Bagging + 特征随机
@@need 要解决什么
Bagging 只随机了"行"（样本）；如果所有树都用同一策略挑特征，还不是一模一样？——随机森林再抽"列"（特征）。

@@idea 核心思路
**随机森林（Random Forest）** = Bagging 决策树 + **特征子采样**：
- 除了每棵树用不同自助样本，**每次分裂只在随机抽出的"特征子集"里挑最优切分**（分类默认 √n 个特征，回归默认 n/3）。
- 双随机（行随机 + 列随机）让树之间的差异被拉满，从而大幅压低方差、抗过拟合。

```python
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(n_estimators=100, max_depth=10,
                            random_state=42, oob_score=True)
rf.fit(X_train, y_train)
print(rf.score(X_test, y_test))
print(rf.oob_score_)        # 袋外验证分数（免切验证集）
print(rf.feature_importances_)   # 特征重要性（集成后更稳）
```
- `n_estimators`：树的数量（默认 100），越多越稳但有收益递减。
- **重要福利**：特征重要性（多棵树平均）比单树更可靠，直接做特征筛选。

调参三板斧：`n_estimators`（越多越稳）、`max_depth`/`min_samples_leaf`（剪枝防过拟合，同单树）、`max_features`（控制列随机强度）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| n_estimators 拉到 1 万 | 收益递减且慢；100~500 常见，用 OOB 曲线确认"够用"即可 |
| 忘了设置 max_depth | 深树+随机森林仍有泄漏风险；规范设置两个剪枝参数 |
| 把 oob_score 当万能 | OOB 是"袋内验证"，与真正的留出测试集都要看（口径不同） |

@@point ④ Adaboost：给"错题"加权的串行提升
@@need 要解决什么
Boosting 门派的思路：串行纠错。Adaboost 具体怎么"记住前树的错误"？——**给样本加权**。

@@idea 核心思路
**Adaboost（Adaptive Boosting，自适应提升）**流程：
1. 第一棵弱树在原始数据上训练，所有样本权重相等。
2. 算这棵树的**加权错误率**，并给树一个**话语权 α**（错误率越低、α 越大）。
3. **提高被分错样本的权重**、降低分对样本的权重（"错题加粗标记"）。
4. 下一棵弱树在**重新加权的数据**上训练（被迫更关注错题）。
5. 反复 N 轮，最终预测 = N 棵树的**加权投票**（α 越大话语权越大）。

- 关键数学：样本权重更新公式 w_i ← w_i · exp(α·[y_i≠ŷ_i])——错题权重乘大、对题权重乘小，归一化后继续。
- 思想一句话：**"这轮谁错了，下轮就多练谁"**——像错题本学习法。

```python
from sklearn.ensemble import AdaBoostClassifier
ada = AdaBoostClassifier(n_estimators=50, random_state=42)
ada.fit(X_train, y_train)
```
- 优势：偏差快速下降（比 Bagging 更能"啃硬骨头"）。
- 风险：**对噪声很敏感**（离群点被强行加倍关注 → 模型被脏数据带偏）；数据噪声大时优先 Bagging。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Adaboost 每棵树都在"重新采样"数据 | 数据不变，变的是**样本权重**（模型训练时要支持 sample_weight，决策树支持） |
| 数据噪声大还硬上 Adaboost | 错题里混着噪声，越练越偏；噪声场景优先随机森林（鲁棒） |

@@point ⑤ GBDT：让树去拟合"残差"的梯度提升
@@need 要解决什么
Adaboost 用"加权错题"难再接大模型；换个更普适的框架：**每一轮新树去拟合"上一轮整体预测的残差（错误）"**。这就是 GBDT 的核心——梯度提升（Gradient Boosting）。

@@idea 核心思路
**GBDT（Gradient Boosting Decision Tree）**流程（以回归为例）：
1. 初始预测：常数（如均值）。
2. 计算**残差** r_i = y_i - ŷ_i（"还差多少没预测对"）。
3. 训练一棵小树，**专门拟合残差**（输入 x，输出逼近 r_i）。
4. 更新预测：ŷ = ŷ + 学习率 × 新树输出。
5. 重复 2~4 若干轮：每一轮都在"补前一轮的缺口"。

为什么叫"梯度提升"：**残差其实就是 MSE 损失关于预测值的负梯度**（对 ŷ_i 求导 J=(1/2)(y-ŷ)² → 负梯度 = y-ŷ = 残差）。所以整套路子就是**用树去拟合损失函数的负梯度**——框架与第 4~6 章"梯度下降"同构，只是"下降的单位"从参数更新变成"加一棵树"。
（对分类任务：把树拟合目标换成"分类损失（log loss）的负梯度"，公式不同但框架一致。）

三个必须知道的概念：
- **shrinkage（学习率）**：每轮新树贡献缩水（0.01~0.1），换取更多轮次、更稳收敛。
- **n_estimators**：树的数量（轮数）。
- **subsample**：每轮随机抽一部分样本训练（行随机），缓解过拟合（随机梯度提升）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把"拟合残差"理解成"拟合 y" | 第 3 轮以后树拟合的是残差（y-当前预测），不是原始 y；这是 GBDT 和 Adaboost 的分水岭 |
| 学习率设 1 还想多轮叠加 | 学习率大 → 前期全押注首棵树 → 过拟合；**学习率设小（0.1 或 0.05）+ 树多加** |

@@point ⑥ 随机森林 vs GBDT：两派正面交锋
@@need 要解决什么
两大门派都强，工程里到底选谁？给一张"打架"的决策表。

@@idea 核心思路
| 维度 | 随机森林（Bagging） | GBDT（Boosting） |
|---|---|---|
| 训练方式 | 并行，互不影响 | 串行，链式依赖 |
| 降低什么 | 方差（稳定） | 偏差（精准） |
| 对噪声 | 鲁棒 | 敏感 |
| 调参 | 少（early 就很好） | 多（学习率、树数要配合） |
| 表格数据精度 | 强 | **更强**（普遍实战结论） |
| 训练速度 | 可并行，快 | 串行，慢 |
| 高维稀疏（文本） | 一般 | 表现弱（树不适合稀疏） |
| 代表实现 | sklearn RF | sklearn GBDT / XGBoost / LightGBM |

选型一句话：**追求上限、数据干净 → GBDT 系（XGBoost/LightGBM）；求稳、不想调参、有噪声 → 随机森林；稀疏高维（文本/ID 类）→ 线性模型或 LR，别硬用树。** 树家族在"纯表格、中高维稠密"数据上是王者。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 表格数据一上来就神经网络 | 表格数据的王是树系（RF/GBDT），深度学习赢在图像/文本；**先跑树系基线再谈别的** |
| 稀疏高维还硬堆 GBDT | 树按"阈值切分"，稀疏特征信息被稀释；LR/线性+正则更合适 |

@@point ⑦ GBDT 工程实战：从分类到回归一鱼两吃
@@need 要解决什么
GBDT 代码怎么用？sklearn 接口把分类/回归分成两个类，各自字段要记清。

@@idea 核心思路
```python
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split

# 分类任务
gbc = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1,
                                 max_depth=3, random_state=42)
gbc.fit(X_train, y_train)
print(gbc.score(X_test, y_test))
print(gbc.feature_importances_)       # 特征重要性

# 回归任务（如保险花销，第九章的进阶候选）
gbr = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1,
                                max_depth=3, random_state=42)
gbr.fit(X_train, y_train)
```
三件事：
1. **max_depth=3 是经典配置**：GBDT 的树要"浅而多"（弱学习器接力），深树反而过拟合。
2. **learning_rate（shrinkage）+ n_estimators 是搭配调**：学习率小 → 树要多；一般 grid 一起搜。
3. 评价照旧：分类 accuracy/混淆矩阵、回归 RMSE。

**性能预告**：sklearn GBDT 只是"教学级实现"；工业实战请用 **XGBoost / LightGBM / CatBoost**（更快、更强、可 GPU），原理同 GBDT 框架——学通本章后再换库几乎零成本。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| GBDT 树的深度拉到 10+ | 深树+串行 = 狂过拟合；**默认 3 起步**，浅树多位接力才显功力 |
| 分类/回归类搞混 | GradientBoosting**Classifier** vs **Regressor** 字段独立；别把回归评估(accuracy)用到回归上 |
| 学了 GBDT 就忘 sklearn 的相对慢 | 大数据换 XGBoost/LightGBM；概念已在手，换库是 API 迁移不是重学 |

@@point ⑧ 实战综合：用集成模型客场挑战保险数据
@@need 要解决什么
集成模型到底比基线强多少？回到第九章的保险花销数据，用随机森林/GBDT 客场打一场"换武器"对照。

@@idea 核心思路
沿用第九章的流程（标准化、切分），只换模型部分：
```python
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import numpy as np

models = {
    "Ridge(基线)": Ridge(alpha=10),
    "RandomForest": RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42),
    "GBDT": GradientBoostingRegressor(n_estimators=200, learning_rate=0.1,
                                      max_depth=4, random_state=42),
}
for name, model in models.items():
    model.fit(x_train_s, np.log1p(y_train))
    rmse = np.sqrt(mean_squared_error(np.log1p(y_test),
                                      model.predict(x_test_s)))
    print(f"{name}: 测试 RMSE={rmse:.4f}")
```
预期：随机森林/GBDT 的测试 RMSE **明显低于 Ridge 基线**——因为特征交互（如"吸烟×肥胖"）呈非线性，树系能自动发现。
更进阶的对比口径：学习率配 0.05 + 树数 500 再试，探索"deep 基线 vs 树系"的差距。

**注意**：树系不用归一化也行，但这里沿用同一管线保持公平对比；实践上建议"树系不动 scaler、线性模型带 scaler"各自最佳化后再比。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 对比时只换模型不统一口径 | 公平对比 = 同一套切分(同 random_state)、同一目标(log1p)、同一评估(RMSE on 测试集) |
| 树多了就把 max_depth 也拉大 | RF/GBDT 同样要剪枝（max_depth/min_samples_leaf），深树在集成里也过拟合 |

@@point ⑨ 特征重要性：树家族白送的"筛选器"
@@need 要解决什么
"哪些特征最重要"是每个项目的灵魂问题。树系模型怎样免费回答？

@@idea 核心思路
- 特征重要性 ≈ 该特征在树分裂中被选中的**频次 × 带来的不纯度下降**（按树/森林平均）。
- sklearn 一行出：`model.feature_importances_`，值归一化成和为 1。
- 用法一：直接写报告（"吸烟、BMI 是花销最强预测因子"——与第九章 EDA 结论互证）。
- 用法二：**递归消除/阈值筛选**——把重要性低的列删掉重训，精简模型。

```python
import matplotlib.pyplot as plt
imp = gbr.feature_importances_
plt.barh(range(len(imp)), imp)
plt.yticks(range(len(imp)), feature_names)
plt.show()
```
**工程纪律**：重要性与数据分布绑定，特征一换、数据一变就作废，不得跨数据集套用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只看重要性不看方向 | 重要性只有"量级"没有正负（树不输出方向）；要"正负影响"请回看线性模型的 coef_ |
| 把重要性当全局真理 | 单次划分的噪声也会进重要性；多跑几次/用足球证据交叉验证才稳 |

@@point ⑩ 阶段 20 集成收官：从"一树"到"森林与机器"
@@need 要解决什么
最后把"树"的全部家族关系串成一张图，作为本章乃至整个阶段的收尾锚点。

@@idea 核心思路
决策树家族关系图（背这一条链）：
```
决策树（单树：可解释、易过拟合）
 ├── Bagging（行随机 + 投票/平均）→ 随机森林（+列随机）
 └── Boosting（串行纠错）
      ├── Adaboost（样本权重：错题加练）
      └── GBDT（拟合残差=负梯度 → XGBoost/LightGBM 工业版）
```
**阶段 20 武器库总览**（至此全部集齐）：
| 场景 | 武器 |
|---|---|
| 连续预测·线性 | 线性回归/Ridge/Lasso + 多项式 |
| 连续预测·非线性 | 决策树回归、RF、GBDT |
| 分类·线性 | 逻辑回归/Softmax |
| 分类·非线性 | 决策树、RF、GBDT |
| 无标签分堆·球形 | KMeans 家族 |
| 无标签分堆·任意形状 | DBSCAN/OPTICS/MeanShift |
| 特征重要度/可解释 | 树系 feature_importances_、线性 coef_ |

到这儿，你手里的武器已经覆盖监督回归、监督分类、无监督聚类三大任务，足够应对绝大多数结构化数据实战了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 学完武器库就"一把打天下" | 模型选择靠"问题类型+数据形状+规模+噪声"四要素，按场景挑武器 |
| 忽略"集成的前提" | 基学习器要"好而不同"，没有差异的集成没有价值 |

@@summary
集成学习三巨头收工：

| 算法 | 机制 | 一句话特征 | 适用 |
|---|---|---|---|
| 随机森林 | Bagging：行随机+列随机，并行投票/平均 | 稳、抗噪、少调参 | 默认基线、有噪声 |
| Adaboost | Boosting：错题加权，串行训练 | 偏差降得快、怕噪声 | 数据干净、分类 |
| GBDT | Boosting：逐轮拟合残差（负梯度） | 精度上限高、参数配对调 | 表格数据追求上限 |
| 关键参数 | n_estimators / learning_rate / max_depth | 学习率小+树多+浅树 | 按数据规模调 |
| 免费福利 | oob_score / feature_importances_ | 免验证集、特征筛选 | 所有树系项目 |

一句话记住本章：**集成学习 = 一群"好而不同"的树团战——Bagging 并行各练各的再投票（随机森林加一重列随机，稳而抗噪），Boosting 串行"专治前树的错"（Adaboost 给错题加权、GBDT 让新树直接拟合残差即负梯度，浅树多棵+小学习率精度封顶）；表格数据处理不了的就用树系（RF 求稳、GBDT 追上限、XGBoost/LightGBM 上工业）。**

@@quiz
1. Bagging 和 Boosting 的机制差异是什么？分别用什么方式"制造差异"？
2. Bagging 为什么用"有放回"抽样？OOB 样本有什么用途？
3. 随机森林的"双随机"指什么？各自解决什么问题？
4. Adaboost 提高样本权重的规则是什么？它对噪声为什么敏感？
5. 为什么 GBDT 拟合的是"残差"而不是原始 y？这个残差和梯度有什么关系？
6. 随机森林和 GBDT 在降低"方差/偏差"上的分工是什么？
7. 浅树+多棵+小学习率为什么是 GBDT 的经典配置？
8. 写一段代码：用同一训练/测试切分，对比 Ridge、RandomForest、GBDT 三个模型的测试 RMSE。

@@links
讲义|决策树讲义（章节5-8，27 页）|#
文档|sklearn ensemble 总览|https://scikit-learn.org/stable/modules/ensemble.html
文档|XGBoost 官方文档|https://xgboost.readthedocs.io/
文档|LightGBM 官方文档|https://lightgbm.readthedocs.io/