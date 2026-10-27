@@h1 第六章　Seaborn 统计图表
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据可视化　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章的 Seaborn 能"换肤"了，**但图本身还没上场：柱状、直方、箱线、热图、回归图……每一类图到底一行代码怎么写？带什么统计量？** 数据从 DataFrame 到图，最快的路径就在这 14 个函数里。

这一章按"**分类对比 → 分布 → 关系 → 多图编排**"四条线把 Seaborn 统计图表一网打尽。学完你能回答：barplot 和 countplot 的区别、boxplot 和 violinplot 的区别、heatmap 的两个参数、jointplot/pairplot/FacetGrid 各自适合什么。

@@map 这一章在整个知识库里的位置
**上一章**：Seaborn 入门与全局定制——风格、调色板、ax 参数
**本章** ← 你在这里：Seaborn 的全部核心绘图函数——"数据 → 一行出图"
**下一章**：NumPy 入门——数组是 Pandas/绘图的数据底座，学会它，Pandas 的 Series/DataFrame 才不玄乎
**再往后**：NumPy 进阶 → Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路，可视化三章到这里收官

@@note info 学习提示
14 个函数长得像（都是 sns.xxxplot），记忆法：**记住"解决什么问题"这一列，函数名反而不难**。每个点的代码都基于 `sns.load_dataset` 的 iris/tips，你可以直接跑。不用背参数，用的时候回翻本章即可。

@@point ① barplot：分类均值柱状图
@@need 要解决什么
**每个类别多个样本，想看类别的"平均表现"及误差** — barplot 自动算均值、画误差线。

@@idea 核心思路
barplot 对 x 的每个类别，**聚合 y 的均值并画出置信区间/误差线**：

```python
import seaborn as sns

tips = sns.load_dataset('tips')          # 小费数据
sns.barplot(x='day', y='total_bill', data=tips, hue='sex')
```

要点：**它画的是"聚合统计量"，不是原始值**——如果你传的每个类别只有一个样本，图就是一个点加一条误差线。`hue` 参数用第二维度再拆分（如男女分组），柱子变并列。

置信区间计算：默认用自助抽样（bootstrap）估算 95% 置信区间，`errorbar=None` 可关掉。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 看到的"高度"和自己算的平均对不上 | 它画的就是均值 + 误差线；误差线不是数据范围 |
| 每一类只有一个值时柱子很矮 | 正常，单样本均值就是它本身；这种场景用 pointplot/scatter 更合适 |

@@point ② countplot：分类计数柱状图
@@need 要解决什么
**不看数值，只想数一数每个类别各有多少条记录**（男多少、女多少）——countplot 数数专用。

@@idea 核心思路
countplot 只统计**记录条数**，x 不给 y（y 是计数）：

```python
import seaborn as sns

tips = sns.load_dataset('tips')
sns.countplot(x='day', data=tips, hue='sex')
```

对比记忆：**barplot 需要一个 y 数值列（或估算法）求均值；countplot 不需要 y，直接数行数**。分类场景"有多少人/多少单/多少评论"第一反应就是 countplot。

一个坑位提醒：若 y 轴显示的不是整数计数而是比例，可能用了 `stat='percent'` 等变体参数（显式指定才生效）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 y 传了数值列给 countplot | 它不认；countplot 只要 x（或 y）一个分类列，另一轴是计数 |
| 计数上万时 y 轴太挤 | 改对数值：记不清参数名就查文档的 stat 参数 |

@@point ③ histplot：直方图与密度并取
@@need 要解决什么
**一组数值的分布长什么样**——histplot（新版本直方图函数），还能叠加核密度曲线与 KDE 分布图。

@@idea 核心思路

```python
import seaborn as sns
from matplotlib import pyplot as plt

sns.histplot(tips['total_bill'],           # 一列数值
             bins=20,                      # 分桶数（和 Matplotlib 一致）
             kde=True,                     # 叠加密度曲线
             stat='count')                 # 纵轴：count 计数 / density 归一化
plt.xlabel('账单金额')
```

额外形态：`sns.kdeplot` 单独画核密度曲线（更平滑的分布观感）；直方 + KDE 通常一图搞定（kde=True）。

对比 Matplotlib：**histplot 是 seaborn 版本（新版）**，老教程的 `sns.distplot` 已废弃，看到 distplot 代码请更新。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 sns.distplot 报 DeprecationWarning | 已废弃，改用 histplot 或 kdeplot |
| kde=True 后纵轴看不懂 | 计数和密度不同尺度；统一看 shape（形状）即可 | 

@@point ④ lineplot：趋势线 + 自动置信区间
@@need 要解决什么
**x 有序变化、y 有噪声**，想看清"真实趋势"而不被噪声带偏——lineplot 自动聚合 + 画置信区间。

@@idea 核心思路
当 x 上多个点共享同一值时，lineplot 自动求均值并画置信带：

```python
import seaborn as sns

fmri = sns.load_dataset('fmri')        # 脑部扫描实验数据：多被试、多时间点
sns.lineplot(x='timepoint', y='signal', data=fmri, hue='event')
```

带误差的理由：fmri 数据同一时间点有多名被试的多个值，lineplot 把它们聚合成"均值 ± 置信区间"的平滑带。

**无分组地还原原始噪音**：`err_style=None` 或设置 `ci=None`/`errorbar=None` 可关掉置信带，画纯折线。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 折线周围有"色带" | 那是置信区间，不是描边；不想看就传 errorbar=None |
| x 未排序时线条乱飞 | lineplot 默认排序聚合；数据本身噪声大时先平滑或换回归图 |

@@point ⑤ scatterplot：两数值变量的关系
@@need 要解决什么
**两个连续变量之间有没有相关趋势**——Scatterplot 与 Matplotlib 的 scatter 等价，但 API 面向 DataFrame 列名。

@@idea 核心思路

```python
import seaborn as sns

iris = sns.load_dataset('iris')
sns.scatterplot(x='sepal_length', y='petal_length',
                data=iris, hue='species', s=80)
```

`hue='species'` 自动按类别着色并生成图例——**这一步在 Matplotlib 里要手动循环写十几行**，Seaborn 一行。

进阶扩展：`size=` 参数把第三个数值映射成点大小；大数据量时加 alpha。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| hue 分类很多点时颜色糊 | 超过 6 个类别换色板（第 5 章），或降维再做散点 |
| 点太大遮挡 | s 调小 + alpha=0.5~0.7 |

@@point ⑥ stripplot：分类散点（抖动）
@@need 要解决什么
**想直接看到每个类别的原始数据点，而不是只看均值**——stripplot 把每个数据点撒在类别轴上（横向抖动避免重叠）。

@@idea 核心思路

```python
import seaborn as sns

tips = sns.load_dataset('tips')
sns.stripplot(x='day', y='total_bill', data=tips,
              jitter=True,          # 横向抖动（默认开），否则点全叠一条线
              dodge=True)           # hue 分组时错开位置
```

配合"均值/分布"类图叠加使用是数据分析常用组合：

```python
sns.boxplot(x='day', y='total_bill', data=tips, color='lightgray')
sns.stripplot(x='day', y='total_bill', data=tips, color='black')
```

箱线图给"分布骨架"，stripplot 给"原始真相"——这张组合图信息量极大。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 点全叠成一条竖线 | jitter 关了或抖动幅度 0；保持 jitter=True |
| hue 分组两边点贴在一起 | dodge=True 错开 |

@@point ⑦ swarmplot：蜂群散点（不重叠）
@@need 要解决什么
stripplot 抖动的点还是可能重叠，**想要"每一点都看得清"的完美不重叠布局**——swarmplot 按密度自动排布（蜂群图）。

@@idea 核心思路

```python
import seaborn as sns

sns.swarmplot(x='day', y='total_bill', data=tips, hue='sex')
```

- 每个点**不重叠**：算法把点沿分类轴排成"蜂群"形状，点密处自动铺开；
- 代价：**数据量大（几百上千点）时布局计算慢、图会很大**。

与 stripplot 的选择：**小样本（<100）用 swarm，大样本用 strip + alpha**。

搭配箱线/小提琴图也常用（先骨架后真点）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 数据一大，swarmplot 非常慢 | 换 stripplot；swarm 是为小样本设计的 |
| 点把箱线图遮完了 | 先画箱线后画 swarm，并给 swarm 的点设小 size、低 alpha |

@@point ⑧ boxplot：箱线图（Seaborn 版）
@@need 要解决什么
**五数概括 + 离群点标记**，Matplotlib 能做但配置繁琐；Seaborn 的 boxplot 一行出图，还能按 hue 拆分。

@@idea 核心思路

```python
import seaborn as sns

sns.boxplot(x='day', y='total_bill', data=tips, hue='sex')
```

- **箱**：Q1–Q3（四分位距 IQR）；**中位线**在箱内；
- **须**：上下 1.5×IQR 范围；**须外的点**是离群值；
- hue 分组时四组并排对比。

读图小抄：**看中位数（箱中线）比高低，看箱高（IQR）比稳定性，看须/离群点查异常**。

调色：`palette='Set2'`（分类）保持 hue 组风格一致，`color=` 单色时给整图一色。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 中位数不在箱子中间 | 正常——偏态分布时中位数偏到箱的一侧，正是箱线图在"说"分布偏斜 |
| 离群点太多 | 先回到数据检查是否"脏数据"；1.5×IQR 规则就是这么定的 |

@@point ⑨ violinplot：小提琴图（分布+箱体）
@@need 要解决什么
箱线图只给五数，**不给你看分布形状**（双峰还是单峰？）——小提琴图 = 箱线图 + 核密度曲线侧身。

@@idea 核心思路

```python
import seaborn as sns

sns.violinplot(x='day', y='total_bill', data=tips, hue='sex', split=False)
```

- **宽度** = 该数值处的密度（越宽数据越多）——"小提琴"的腰身就是分布形状；
- **中间的箱** = 经典的箱线图五数信息；
- **split=True**：同一分类内 hue 两组合并成"左右各一半"（半边图，省空间）。

选择逻辑：**看形状用 violin，快速比较数量关系用 box**；sample 少时 violin 会失真。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 小提琴"肚子"不对称/形状怪异 | 小样本 + KDE 平滑导致的假象；换 boxplot 更可靠 |
| split=True 只适用于 hue 为 2 组 | 多于两组时 split 无意义，保持并排 |

@@point ⑩ pointplot：类别均值点线图
@@need 要解决什么
**多个类别的均值变化趋势**（周一→周日销量均值）——pointplot：点 = 均值，线 = 顺序连接，误差线 = 置信区间。

@@idea 核心思路

```python
import seaborn as sns

sns.pointplot(x='time', y='total_bill', data=tips, hue='sex',
              markers=['o', 's'],        # 两组不同点形
              linestyles=['-', '--'])    # 两组不同线型
```

- 与 barplot 一样聚合均值画误差线，但**用点线而非柱**：适合类别多、空间紧的场景；
- hue 拆多组时用不同 linestyle 可读性更好。

适用例子：一周内每天订单均值变化、各月份用户活跃均值。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 看不到误差线 | 每类别只有一个样本时无 CI 可画；或 errorbar 被显式关闭 |
| 点线顺序乱 | x 传数值/有序类别才有序；无序字符串按出现顺序排 |

@@point ⑪ heatmap：矩阵数值热图
@@need 要解决什么
**矩阵型数据（相关矩阵、透视表、混淆矩阵）看数值分布**——heatmap 是 Seaborn 最出名的图之一。

@@idea 核心思路

```python
import seaborn as sns

iris = sns.load_dataset('iris')
corr = iris.corr(numeric_only=True)       # 数值列的相关系数矩阵
sns.heatmap(corr,
            annot=True,          # 格子里显示数值
            cmap='coolwarm',     # 发散色板（有正负）
            fmt='.2f')           # 数值格式（保留 2 位小数）
```

防坑三个高频点：**annot 不开就没有数字；fmt 不配会越界重叠；数值有正负要用发散色板（RdYlBu/coolwarm）**。

配套：`mask=` 参数可遮掉上三角（对称矩阵画一半），`cbar_kws` 调色条。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 格子里数字挤成一团 | 需要 fmt='.1f'/.2f 限制格式；或 figsize 调大 |
| 颜色看不出大小关系 | 换发散色板（有正负时）；相关矩阵常规用 coolwarm 或 RdBu_r |
| 列名太长看不到 | df 列改名，或用 xticklabels/yticklabels 精简 |

@@point ⑫ kdeplot：核密度曲线
@@need 要解决什么
直方图受"桶数"影响大，**想要不依赖分桶的平滑分布曲线**——kdeplot（核密度估计）。

@@idea 核心思路

```python
import seaborn as sns

sns.kdeplot(x='total_bill', data=tips, shade=True)      # 填充
sns.kdeplot(x='total_bill', data=tips, hue='sex', multiple='stack')  # 按组堆叠
```

- **shade**：曲线下方填充（老参数 fill=True 新写法）；
- **multiple**：多组 draw 方式——'layer' 叠加、'stack' 堆叠（面积不重叠）、'fill' 镜像填充（两两对比）。

对比 histplot：**kde 平滑、无桶数选择问题，但小样本失真**；直方忠实原始分桶但依赖 bins。常用 combo：histplot(kde=True)。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 曲线超出数据范围很长 | KDE 的带宽参数（bw_adjust）默认偏宽；调小 bw_adjust=0.5 收紧 |
| 小样本曲线怪 | n 太小时 KDE 不可靠，改直方图 |

@@point ⑬ regplot / lmplot：回归图（趋势+置信）
@@need 要解决什么
**想给散点加上回归直线，量化"x 增大 y 怎么变"**——regplot 散点 + 线性拟合 + 置信区间。

@@idea 核心思路

```python
import seaborn as sns

sns.regplot(x='total_bill', y='tip', data=tips)    # 自动线性回归线
```

- **lmplot**：regplot 的"多图版"，支持 hue/col 分组和 FacetGrid（整列整行多子图）：

```python
sns.lmplot(x='total_bill', y='tip', data=tips, hue='sex', col='day')
```

每列一个 day，每组一条回归线——**同时对比 4 天、2 个性别的趋势**。

参数速记：`order=` 多项式阶数（order=2 二次拟合）、`robust=True` 抗离群点、`scatter_kws={'alpha':0.5}` 透传散点样式。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 回归线看不出趋势 | 数据本身弱相关；先看 R²（数据科学在后面阶段会用 statsmodels）再决定要不要读这条线 |
| 离群点把回归线拉歪 | robust=True 用稳健估计；或剔除明显异常点 |

@@point ⑭ 多维探索：jointplot / pairplot / FacetGrid
@@need 要解决什么
单图看单点，**一次想同时看"两两关系矩阵"或"按条件分面"**——三个多图函数各管一段。

@@idea 核心思路
**jointplot：二变量联合分布**（散点/直方/kde 结合）：

```python
sns.jointplot(x='sepal_length', y='petal_width', data=iris,
              kind='scatter')        # kind: scatter/hist/kde/hex
```

**pairplot：数值列两两配对**（对角线看单变量分布，其余看关系）：

```python
sns.pairplot(iris, hue='species', corner=True)   # corner 只画下三角，省一半图
```

**FacetGrid：按条件分面（画布先行）**：

```python
g = sns.FacetGrid(tips, col='time', row='day', hue='sex')  # 分面定义
g.map(sns.scatterplot, 'total_bill', 'tip')                # 每个格子画散点再传两列
```

三者选择：**两变量联合 → jointplot；多数值列总览 → pairplot；按分类条件分多格同图 → FacetGrid/lmplot 的 col 参数**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| pairplot 一图几十个格子看不清 | corner=True、调小 figsize；数据列越多越要"砍列"再画 |
| FacetGrid 每个格子缺图例/标签 | g.map 后要用 g.add_legend() 补图例，ax 属性统一控制 |
| lmplot 的 col 和 FacetGrid 混着用迷糊 | lmplot 是"回归 + 分面"封装；需要自由组合其他图时用 FacetGrid |

@@summary
这一章，Seaborn 的统计图表全家桶过了一遍：

| 分类 | 图 | 一句话用途 |
|---|---|---|
| 分类对比 | barplot / countplot / pointplot | 均值对比 / 数数 / 均值趋势 |
| 分布 | histplot / kdeplot / boxplot / violinplot | 频数分布 / 平滑密度 / 五数 / 形状+五数 |
| 原始点 | stripplot / swarmplot | 抖动散点 / 不重叠蜂群 |
| 关系 | scatterplot / lineplot / regplot | 散点关系 / 趋势置信带 / 回归线 |
| 矩阵 | heatmap | 相关矩阵、透视表 |
| 多图 | jointplot / pairplot / FacetGrid | 联合 / 两两 / 分面 |

一句话记住本章：**对比用 bar/count，分布看 hist/kde/box/violin，关系用 scatter/line/reg，矩阵上 heatmap，多维交给 joint/pair/FacetGrid——十四图在手，数据任你"整活"。**

@@quiz
1. barplot 与 countplot 的核心区别是什么？各自需要什么数据形态？
2. 直方图函数 distplot 已被废弃，替代方案是什么？
3. lineplot 里折线周围的"色带"是什么？怎么关掉？
4. stripplot 与 swarmplot 的取舍依据是什么？
5. boxplot 与 violinplot 各自擅长回答什么问题？什么时候 violin 会失真？
6. heatmap 显示数值需要哪两个参数配合？数值含正负时该用什么色板？
7. jointplot、pairplot、FacetGrid 三个多图函数分别适合什么场景？

@@links
参考|Seaborn （index.md，39 页）|#
工具|Seaborn 官网|https://seaborn.pydata.org/
文档|Seaborn 示例画廊|https://seaborn.pydata.org/examples/index.html