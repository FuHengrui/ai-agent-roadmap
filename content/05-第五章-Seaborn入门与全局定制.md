@@h1 第五章　Seaborn 入门与全局定制
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据可视化　|　难度 ★★☆

@@why 这一章在解决什么问题
**Matplotlib 什么都能画，但"什么都要自己配"：配色靠自己、样式靠自己、统计图（箱线、密度、回归）要一堆代码拼。** 一个统计图，Matplotlib 要 20 行，Seaborn 一行出图还自带置信区间——你缺的就是这个"高效层"。

这一章解决 Seaborrn 的"**选型与全局定制**"：为什么数据分析用它、怎么装、自带数据集哪来的、四套全局风格怎么设、调色板体系怎么玩。学完你能回答：Seaborn 和 Matplotlib 的关系、set_style/set_context/set_palette 各自管什么、调色板的"离散/连续"两类怎么选。

@@map 这一章在整个知识库里的位置
**上一章**：Matplotlib 常用图表类型——底层绘图库"全都能画"
**本章** ← 你在这里：Seaborn 入门——建立在 Matplotlib 之上的统计绘图库，默认就好看、默认带统计量
**下一章**：Seaborn 统计图表一族——bar/hist/box/heatmap 等十几个"一行出图"
**再往后**：NumPy → Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路；可视化主刀手从这章开始换 Seaborn

@@note info 学习提示
Seaborn 的设计哲学是"**风格与数据解耦**"：风格全局统一调一次，图表函数只管数据和统计。所以本章表面在讲"样式"，实则是在搭"后面所有图的地基"。调色板建议边跑边看（Jupyter 里直接出图），比背色名快。

@@point ① 为什么数据分析默认用 Seaborn
@@need 要解决什么
上一章 Matplotlib 已能画图，**为什么还要学第二个库？** 学之前先弄懂它的价值，才不会学了又忘。

@@idea 核心思路
Seaborn 是**基于 Matplotlib 的高层统计绘图库**，定位有三：

- **自动带统计量**：`sns.boxplot`、`sns.histplot` 默认就计算分布统计，不用你手动算；
- **一行出图**：绘图函数按"dataframe 列名 = 参数"设计，`sns.barplot(x='类别', y='数值', data=df)` 即可；
- **默认审美在线**：内置配色、网格、坐标轴样式，开箱即用比我手动调 Matplotlib 好看。

它与 Matplotlib 的关系：**Seaborn 是上层封装，Matplotlib 是底层引擎**。Seaborn 的图本质是 Matplotlib 图，`plt.title()`、`plt.savefig()` 等底层函数照常用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Seaborn 是独立画图引擎 | 它是 Matplotlib 的封装，Seaborn 图也是 Matplotlib 图，底层 API 依然生效 |
| 想要"自由度高"的复杂定制 | 高频需求 Seaborn 都有但深定制不如直接 Matplotlib；两者常混合用 |

@@point ② 安装与导入
@@need 要解决什么
**装哪个版本、怎么导入才不和现有环境打架？**

@@idea 核心思路
安装（在目标虚拟环境下）：

```bash
pip install seaborn
# 或 conda install seaborn
```

依赖：Seaborn 需要 numpy、pandas、matplotlib 支撑（安装时自动带上）。导入规范：

```python
import seaborn as sns
import matplotlib.pyplot as plt

# 老提醒：新版 seaborn 默认样式过渡自旧版
sns.set_theme()        # 应用默认主题（可选）
```

`import seaborn as sns` 是官方默认别名，社区代码几乎都这么写，别改成别的。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 导入 seaborn 报缺 pandas/matplotlib | 先装齐依赖：pip install pandas matplotlib seaborn |
| 图风格很"旧" | 新版换了默认主题；显式调用 sns.set_theme() 应用新样式 |

@@point ③ 自带数据集 load_dataset：练手数据从哪来
@@need 要解决什么
教程图里的花、企鹅、航班数据看着专业，**这些数据哪来的？我自己怎么搞一份来练？**

@@idea 核心思路
Seaborn 内置 `load_dataset()` 直接从在线仓库拉取示例数据集：

```python
import seaborn as sns

df = sns.load_dataset('iris')      # 鸢尾花：三种花 150 行样本
# 常见还有：titanic 泰坦尼克、tips 小费、penguins 企鹅、flights 航班
```

注意行为：**首次使用需联网下载**；返回的是 Pandas DataFrame，可直接被所有 sns 绘图函数消费。

离线/自备方案：自己构造 DataFrame，或用 Pandas 读本地 csv（阶段 Pandas 章节会讲）——`load_dataset` 只是"快速练手"的入口。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| load_dataset 报网络错误 | 该函数需联网；断网/被墙时用本地数据替代 |
| 拿到的是 DataFrame 不知道怎么用 | 先 `df.head()` 看列名，绘图的 x/y/hue 参数就填列名 |

@@point ④ 全局定制四件套：style / context / palette / font
@@need 要解决什么
一站式的"换肤"入口，**四类参数分别管什么？**

@@idea 核心思路
Seaborn 的全局外观由四个维度控制：

```python
import seaborn as sns

sns.set_style('whitegrid')      # 背景风格：white/dark/whitegrid/darkgrid/ticks
sns.set_context('notebook')     # 上下文（字号/线宽）：paper/notebook/talk/poster
sns.set_palette('deep')         # 调色板：deep/muted/bright/dark/colorblind 等
sns.set(font='SimHei')          # 全局字体（中文字体名）
```

记忆锚点：**style 管背景、context 管字号线宽、palette 管配色、font 管字体**。set() 是"一次性全设"的快捷方式（可传任意上述参数）。

字号场景选择：**paper** 适合打印发表（小）、**notebook** 默认（屏幕笔记）、**talk** 演讲（大）、**poster** 海报（最大）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 中文还是方框 | seaborn.set(font='SimHei') 只对标题/标签生效一部分，仍需要在 plt.rcParams 层面配字体（见第 3 章） |
| 风格改了但个别图没变 | 绘图时显式传了 style/palette 参数的图，会覆盖全局设置——局部优先 |

@@point ⑤ set_theme 与 set：全局与局部的关系
@@need 要解决什么
`set_theme()` 和 `set()` 长得像，**到底有什么区别、什么时候用哪个？**

@@idea 核心思路
`set_theme()` 是 **Seaborn 0.11+ 的统一入口**：一次调用同时设置所有主题维度（style/context/palette/font/rcParams），并应用默认配色与 Matplotlib 集成：

```python
import seaborn as sns

sns.set_theme(style='darkgrid', context='talk', palette='muted')
```

`set()` 则更"轻"——只是 `set_theme()` 的别名/兼容接口，接受同一组参数。**新代码统一用 set_theme()**。

关键概念：Seaborn 的主题设置走 `sns.set_theme()`；**图内拿到单个 Axes 后的样式修正**（如改刻度）仍用 Matplotlib 的 rcParams 或 ax 方法——两层是打通的。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 老教程用 set()，新教程用 set_theme() | 都行，set_theme 是新推荐写法；参数用法完全一致 |
| 设置后字体大小"忽大忽小" | context 每档字号不同；以及注意是否在绘图后又被 set 覆盖 |

@@point ⑥ 调色板基础：color_palette 与分类色板
@@need 要解决什么
图的配色来自调色板，**它有哪些分类？怎么查看、怎么取用？**

@@idea 核心思路
调色板分两大类：**分类（discrete）** 和 **连续（sequential/diverging）**。分类色板用在 x 轴分类/分组上，一套 6-10 个互不混淆的颜色：

```python
import seaborn as sns

sns.color_palette('deep', 6)            # 查看默认分类色板（前 6 色）
sns.color_palette('Set2', 8)            # 另一组内置色板
```

```python
# 绘图时直接指定调色板
sns.set_palette('deep')
sns.barplot(x=['A', 'B', 'C'], y=[30, 50, 20])
```

内置常用分类色板名：**deep、muted、bright、pastel、dark、colorblind**（都基于色块差异设计），以及 **Set1/Set2/Set3**、**tab10/tab20** 这类知名系列。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 颜色太少看不出区别 | 分类超过 10 个时，要么换 tab20，要么用下一个知识点（连续色板）按数值着色 |
| 色板名拼写错误（如 pastel 写成 pastle） | 报 KeyError；从 sns.color_palette() 无参调用先看全列表再抄名 |

@@point ⑦ 连续调色板：数值映射颜色
@@need 要解决什么
数据本身是**连续数值**（温度、密度、相关系数），想用颜色深浅表达大小——这需要"连续色板"。

@@idea 核心思路
两类连续色板：

```python
import seaborn as sns

# 顺序型（sequential）：单色从浅到深，适合"越高越大"
sns.color_palette('Blues', 12)             # 蓝从浅到深
sns.color_palette('viridis', 12)           # matplotlib 经典连续色

# 发散型（diverging）：中间色 + 两端相反色，适合"有正负/偏离中心"
sns.diverging_palette(250, 30, s=80, l=55, as_cmap=True)   # 蓝到红
```

作用对象：heatmap 的 cmap、scatter 的 palette/hue、lineplot 的 hue——连续数值 → 颜色映射。

应用示例（热图 + 连续色板）：

```python
import numpy as np

mat = np.random.rand(8, 8)
sns.heatmap(mat, cmap='viridis')           # 数值大 = 颜色浅亮
```

选色提示：发散类延续顺序用 **'RdBu_r'/'coolwarm'**（红蓝），自定义时手动设置 diverge_range。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 热图颜色和数值方向相反 | 用 '_r' 后缀翻转色板（如 Blues_r）；理解色板方向再上色 |
| 顺序型色板用在有正负的数据 | 用发散型(RdBu/coolwarm)，顺序型表达不出"中心点" |

@@point ⑧ 色板应用与指定绘制坐标轴 (ax)
@@need 要解决什么
练习到一定阶段，**你觉得默认图都一个样，想"换色、把图画到指定子图里"**——两个高频进阶需求。

@@idea 核心思路
**指定调色板画图**（绘图函数大多有 palette 参数）：

```python
import seaborn as sns

sns.barplot(x=['A', 'B', 'C'], y=[30, 50, 20], palette='Set2')
# 连续数值映射：sns.scatterplot(..., hue=data, palette='viridis')
```

**画到指定 Axes（子图编排的核心技巧）**：

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(10, 4))   # 一行两个 Axes

sns.barplot(x=['A', 'B'], y=[30, 50], ax=axes[0])       # 图一
sns.scatterplot(x=[1, 2, 3], y=[1, 4, 9], ax=axes[1])   # 图二
```

规律：**几乎所有 sns 绘图函数都接受 `ax=` 参数**；不给就画到"当前 Axes"（plt.gca()）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 图没画进指定的子图里 | 漏了 ax 参数，或把 axes[0] 写成了 axes（整个数组） |
| palette 参数不生效 | 个别函数参数名不同（如 histplot 用 palette，lineplot 用 palette 但需配合 hue）——查对应函数签名 |

@@summary
这一章你掌握了 Seaborn 的地基：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **选型认知**：Seaborn 是 Matplotlib 高层封装，一行出图 + 自动统计 | 知道"为什么雪它"，才知道什么时候切回 Matplotlib |
| **安装导入**：pip/conda 安装，`import seaborn as sns` | 标准姿势 |
| **练手数据**：load_dataset 内置数据 | 所有教程案例都基于它们，可复现 |
| **四件套定制**：style 背景 / context 字号 / palette 配色 / font 字体 | 一次设置全局生效 |
| **主题入口**：set_theme 新写法 vs set 兼容写法 | 写新代码不用老眼界 |
| **调色板体系**：分类（set 系列）vs 连续（顺序/发散） | 按数据性质选色，不靠感觉 |
| **色板应用 + ax 参数**：palette= 与 ax= | 换色、排子图两个最实用技巧 |

一句话记住本章：**Seaborn 是 Matplotlib 的统计绘图上层封装；style/context/palette/font 四件套管全局，palette 分分类与连续两类，绘图函数统一认 ax= 参数——地基建好，下一章所有图都站在这上面。**

@@quiz
1. Seaborn 与 Matplotlib 是什么关系？给出一个"Seaborn 图里用 Matplotlib 功能"的例子。
2. load_dataset 返回什么类型的数据？首次调用需要什么条件？
3. set_style、set_context、set_palette、set(font=) 分别控制图的什么维度？
4. set_theme 与 set 的关系是什么？新代码推荐用哪个？
5. 分类色板与连续色板的适用场景分别是什么？发散型色板适合什么数据？
6. 想让 Seaborn 图画进 plt.subplots 创建的第二个子图，关键参数是什么？
7. 顺序型色板（如 Blues）用在有正负符号的数据上有什么问题？应该换什么？

@@links
参考|Seaborn （index.md，39 页）|#
工具|Seaborn 官网|https://seaborn.pydata.org/
文档|Seaborn 调色板教程|https://seaborn.pydata.org/tutorial/color_palettes.html