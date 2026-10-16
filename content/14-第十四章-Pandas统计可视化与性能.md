@@h1 第十四章　Pandas 统计、可视化与性能
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据分析　|　难度 ★★★

@@why 这一章在解决什么问题
**表处理能力齐了，但收尾三件事还没解决：①统计报告要的透视表/交叉表/频数表；②"表 → 图"一刻钟出图；③数据一大（几百万行）Pandas 卡死怎么办。** 这三点是 Pandas 从"会用"到"能交付"的分水岭。

学完你能回答：value_counts 和萧群、pivot_table 和 crosstab 的区别、df.plot 和 matplotlib 的关系、Pandas 三大主流图怎么出、大表读取怎么提速、向量化为什么比循环快。

@@map 这一章在整个知识库里的位置
**上一章**：数据合并与时间序列——跨表、跨时间
**本章** ← 你在这里：Pandas 收官——透视统计、直出图表、性能优化，Pandas 五章到此闭环
**下一章**：MySQL 入门——数据科学链路里的"存"，Pandas 的 to_sql 将在这里安家
**再往后**：MySQL 六章 → 阶段收官
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"全链路

@@note info 学习提示
本章前 3 点是"统计表"，中 4 点是"出图"，后 3 点是"提速"——三段各自独立、合起来是交付三部曲。性能段（⑧⑨⑩）先记结论："**先统计再循环、先减列再读取、能向量化就别 for**"，细节用到再翻。

@@point ① value_counts：频数统计
@@need 要解决什么
**某个类别列各有多少个**（男多少女多少、各省销量）——value_counts 一行出频数，还带归一化占比。

@@idea 核心思路

```python
import pandas as pd

df = pd.DataFrame({'性别': ['男', '女', '男', '男']})

df['性别'].value_counts()      # 男 3、女 1（默认降序）
df['性别'].value_counts(normalize=True)   # 占比：男 0.75
df['性别'].value_counts(dropna=False)     # NaN 也纳入统计
```

要点：

- **默认按频数降序**，结果带索引=类别值；
- **normalize=True 输出比例**（求和=1）；
- **dropna=False 才统计缺失值**（默认忽略 NaN）。

多列版本：`df.nunique()` 数每列不同值个数（分类"多样性"体检）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| value_counts 结果没到预期 | 默认忽略 NaN，统计前先想清楚要不要 dropna=False |
| 想按字母序不是频数序 | value_counts().sort_index() 排标签 |

@@point ② pivot_table：透视表
@@need 要解决什么
**"每个班 × 每个性别的平均成绩"这种二维交叉统计**——pivot_table 把"行、列、值、聚合"四个维度一次指定。

@@idea 核心思路

```python
import pandas as pd

df = pd.DataFrame({'班级': ['A', 'A', 'B', 'B'],
                   '性别': ['男', '女', '男', '女'],
                   '成绩': [88, 92, 76, 85]})

pd.pivot_table(df,
               index='班级',          # 行方向分组
               columns='性别',        # 列方向分组
               values='成绩',         # 要统计的值
               aggfunc='mean')        # 聚合方式（默认 mean）
# 性别   女   男
# 班级
# A     92   88
# B     85   76
```

关键参数：**index/columns/values/aggfunc** 四件套——aggfunc 支持 'sum'/'count'/'max' 等；`fill_value=0` 填空值；`margins=True` 加小计行。

与 groupby 的关系：**pivot_table = 行×列双维度分组**；groupby 做单维聚合，透视做二维交叉。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 出来的格子里 NaN | 该（行,列）组合无数据；fill_value=0 处理 |
| values 列有多个想分别看 | 传 values=['成绩','身高']，aggfunc 用字典 |
| aggfunc 想多个函数 | aggfunc=['mean','sum'] 多层结果 |

@@point ③ crosstab：交叉表
@@need 要解决什么
**两个（或多个）分类列的交叉"计数"**——crosstab 是"count 版透视表"，专门数组合出现的次数。

@@idea 核心思路

```python
import pandas as pd

df = pd.DataFrame({'性别': ['男', '女', '男', '男', '女'],
                   '是否购买': ['是', '否', '是', '否', '是']})

pd.crosstab(df['性别'], df['是否购买'])
# 是否购买  否  是
# 性别
# 女       1  1
# 男       1  2

pd.crosstab(df['性别'], df['是否购买'], normalize='index')  # 行内占比
```

与 pivot_table 的区别：

- **crosstab 专做"计数交叉"**，不需要 values（数行即可）；
- **pivot_table 需要指定 values + aggfunc**（均值/求和等）；
- 输入都是"列"，顺序是 crosstab(行变量, 列变量)。

用途：客户画像（性别×是否购买）、市场分析主力表。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| crosstab 想算均值 | 它不是干这个的；用 pivot_table(values=..., aggfunc='mean') |
| 行列传反 | crosstab(行, 列)：第一个参数变行索引 |

@@point ④ df.plot：Pandas 直出图 & 中文设置
@@need 要解决什么
**分析完想立刻看趋势**，不用每次回 matplotlib —— DataFrame 自带 plot 方法，内部就是 matplotlib。

@@idea 核心思路

```python
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams['font.sans-serif'] = 'SimHei'      # 中文先配好（必备！）
plt.rcParams['axes.unicode_minus'] = False

df = pd.DataFrame({'月份': [1, 2, 3, 4], '销售额': [10, 20, 15, 30]})
df.set_index('月份').plot()     # 折线图（默认）：索引做 x
```

理解：

- **df.plot(kind=...) 是 matplotlib 的封装**：kind 决定图型；
- **非数值/索引列自动当 x**：x 轴用索引，数值列各画一条；
- 中文乱码和 matplotlib 同样的 rcParams 配置（第 3 章内容复用）。

配置习惯：**一个脚本内把两行 rcParams 写在最前**，全脚本图都正确。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| df.plot 中文变方块 | 同一套 rcParams 配置没写；确认 SimHei 可用 |
| 想用某列做 x 轴 | df.plot(x='月份', y='销售额') 显式指定 |
| plot 和 plt 分不清 | df.plot 只是生成图，plt.show/savefig 仍归 matplotlib 管 |

@@point ⑤ 折线图与面积图
@@need 要解决什么
**多列趋势对比（两产品销量走势）**——Pandas 一行出多线；要"累积量感"用面积图。

@@idea 核心思路

```python
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

df = pd.DataFrame({'月份': [1, 2, 3, 4],
                   '产品A': [10, 20, 15, 30],
                   '产品B': [8, 12, 18, 22]})

df.set_index('月份').plot(kind='line', marker='o')   # 多列折线
df.set_index('月份').plot(kind='area', alpha=0.5)    # 面积图（alpha 半透明）
```

记忆法：**kind 参数切换图型**——'line' 折线、'area' 面积、'bar' 柱状、'hist' 直方、'pie' 饼图、'box' 箱线、'scatter' 散点。

面积图多列叠加可能相互遮挡，**alpha=0.3-0.5 半透明**是标配。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 面积图叠得太黑 | 加 alpha=0.3~0.5 半透明 |
| 图太挤没有刻度 | figsize 在 plot(figsize=(8,4)) 里控制 |

@@point ⑥ 柱状图与直方图
@@need 要解决什么
**分类对比用柱状（bar）、分布看直方（hist）**——Pandas 一行切换，分组柱状加参数。

@@idea 核心思路

```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

df = pd.DataFrame({'月份': [1, 2, 3, 4],
                   '产品A': [10, 20, 15, 30],
                   '产品B': [8, 12, 18, 22]})

df.set_index('月份').plot(kind='bar')               # 分组柱状（并列）
df.set_index('月份').plot(kind='bar', stacked=True) # 堆叠柱状
s = pd.Series(np.random.normal(60, 10, 100))
s.plot(kind='hist', bins=20)                        # 直方图
```

分工：**bar 是"类别标签"的对比（x 是分类），hist 是"数值"的分布（x 是区间）**——和 matplotlib 章节的口诀一致。

补充：柱状图常常配 rot=0 让 x 标签横排（月份文字太长不重叠）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| hist 画出来的像 bar | 传了分类值；hist 必须传连续数值 |
| 柱状标签挤成一团 | plot(kind='bar', rot=0) 横排标签 |

@@point ⑦ 饼图、箱线图与散点图
@@need 要解决什么
**占比（pie）、分布五数（box）、两变量关系（scatter）**——Pandas + NumPy 一套带走。

@@idea 核心思路

```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.rcParams['font.sans-serif'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

df = pd.DataFrame({'部门': ['研发', '销售', '行政'], '人数': [80, 50, 20]})
df.set_index('部门')['人数'].plot(kind='pie', autopct='%.1f%%')   # 饼图

data = pd.DataFrame({'成绩': np.random.normal(70, 10, 100),
                     '班级': np.random.choice(['A', 'B'], 100)})
data.boxplot(by='班级')      # 按班级分组箱线

data.plot(kind='scatter', x='成绩', y='班级')   # 散点（x,y 都传数值列）
```

提示：**scatter 要 x/y 两个数值列**；boxplot 是 DataFrame 方法（不是 plot(kind)）——一个月错一次没关系，记住"箱线是 df.boxplot"。

点 ⑦ 组合提示：**占比 pie → 分布 box → 关系 scatter**，一页分析报告的基本构成。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| scatter 报错 missing x/y | 传明确的两列：plot(kind='scatter', x='列1', y='列2') |
| boxplot 当 plot(kind) 传入不认 | 箱线用 df.boxplot() 独立方法 |

@@point ⑧ 性能认知：数据量级与计时
@@need 要解决什么
**"Pandas 怎么这么慢？"先诊断：数据多大、慢在哪一步。** 会用计时工具，才知道优化有没有效。

@@idea 核心思路

```python
import pandas as pd
import numpy as np

# 数据量认知参考：
#    1 万行   → 各种操作毫秒级
#    100 万行 → 单次操作亚秒~秒级（注意内存）
#    1000 万+ → 要考虑 chunk/列裁剪/换工具

df = pd.DataFrame({'a': np.random.randn(1_000_000),
                   'b': np.random.randn(1_000_000)})

# 计时手段：
%timeit df['a'].mean()          # Jupyter 魔法：多次计时取均值
%time df['a'].mean()            # 单次计时
```

两类计时魔法（Jupyter 专用）全流程可用：

- **%time 单次**、**%timeit 多次取稳定**；
- 脚本场景用 `import time; t=time.time(); ...; print(time.time()-t)`。

优化节奏：**先计时定位瓶颈 → 针对性优化 → 再计时对比**。别凭感觉优化。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| %timeit 在脚本文件里报错 | 它是 Jupyter 魔法；脚本用 time 模块 |
| 1 千万行操作卡死 | 先看内存（任务管理器）、降列数（usecols）再往下（第 ⑨ 点） |

@@point ⑨ 大文件读取提速：usecols / dtype / chunksize
@@need 要解决什么
**几个 G 的 CSV 一读就内存爆**——三招：只读需要的列、指定类型省内存、按块分批处理。

@@idea 核心思路

```python
import pandas as pd

# 第 1 招：只读需要的列
df = pd.read_csv('big.csv', usecols=['日期', '销售额'])

# 第 2 招：指定 dtype 省内存（字符串→category，整数→int32）
df = pd.read_csv('big.csv',
                 dtype={'性别': 'category'})

# 第 3 招：分块读，逐块处理
chunks = pd.read_csv('big.csv', chunksize=100000)   # 每 10 万行一块
total = 0
for chunk in chunks:              # 逐块累加
    total += chunk['销售额'].sum()
print(total)
```

memory 概念：

- **usecols 少读列**（最省）；**dtype 省内存**（int64→int32 省一半、object→category 效果显著）；
- **chunksize 分批**：内存恒定，处理完再丢弃，适合聚合类任务。

重复读取场景还可用 `pd.read_csv(..., parse_dates=['日期'])` 一步转时间。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只读一部分列但后续缺列报错 | usecols 想清楚下游需要哪些列再定 |
| 分块聚合结果不对 | 每块单独统计后手动合并（上面 total 累加示例） |
| dtype 指定后值被截断 | int32 不够大时数值溢出，用 int64 或 float32 评估 |

@@point ⑩ 代码优化：向量化 > apply > for
@@need 要解决什么
**同一个任务三种写法速度差百倍**——优化顺序：能向量化绝不循环。

@@idea 核心思路

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({'成绩': np.random.randint(0, 100, 100000)})

# ❌ 慢：显式 for 循环
# result = []
# for x in df['成绩']:
#     result.append(x * 2)

# 中：apply（逐行 Python）
df['成绩x2'] = df['成绩'].apply(lambda x: x * 2)

# ✅ 快：向量化（整个列一次运算）
df['成绩x2'] = df['成绩'] * 2

# ✅ 条件逻辑也向量化：np.where / 掩码
df['等级'] = np.where(df['成绩'] >= 60, '及格', '不及格')
```

速度对比经验：**向量化 ≈ 100 倍于 apply ≈ 1000 倍于 for 循环**。

三条铁律：

1. **加减乘除/比较/逻辑 → 直接列运算**（最淳朴最快）；
2. **条件分支 → np.where / 掩码赋值**（loc[条件] = 值）；
3. **apply 只留给"确无向量化写法"的自定义函数**（如复杂字符串处理）。

附加技巧：`df.eval('新列 = a + b')` 与 `pd.eval` 可进一步提速表达式。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 觉得循环"能看懂就先用" | 数据一大就卡；养成"先想向量化写法"的习惯 |
| np.where 只支持两分支 | 多分支用 np.select(条件列表, 值列表) |
| eval 语法报错 | 列名不能有空格等；较复杂表达式优先普通向量化 |

@@summary
这一章，Pandas 五章的收官三件套：

| 能力 | 关键 API | 一句话 |
|---|---|---|
| 频数 | value_counts(normalize=) | 类别计数/占比 |
| 透视 | pivot_table(index, columns, values, aggfunc) | 二维交叉聚合 |
| 交叉 | crosstab(行列, normalize=) | 两个分类的计数交叉 |
| 出图 | df.plot(kind=...) | line/area/bar/hist/pie/box/scatter |
| 中文 | rcParams SimHei + unicode_minus | 与 matplotlib 同一套 |
| 计时 | %time / %timeit | 先测再优 |
| 大文件 | usecols / dtype / chunksize | 少读、瘦身、分块 |
| 提速 | 向量化 > apply > for | np.where 管条件 |

一句话记住本章：**value_counts 数数、pivot_table 交叉聚合、df.plot 一行出图（先配好 rcParams 中文）；性能上"向量化优先、for 循环最后"，大文件 usecols+chunksize——Pandas 至此功成，数据科学链路中"清洗计算可视化"三段全部就绪。**

@@quiz
1. value_counts 默认的排序方式是什么？normalize=True 和 dropna=False 各起什么作用？
2. pivot_table 的 index、columns、values、aggfunc 四个参数分别是什么含义？
3. crosstab 和 pivot_table 的核心差异是什么？crosstab 需要 values 吗？
4. df.plot 内部的底层库是什么？Pandas 出中文图的先决配置是哪两行？
5. df.plot(kind='bar', stacked=True) 与分组柱状（不 stacked）的视觉差别是什么？
6. hist 与 bar 的本质区别（从数据类型上讲）是什么？
7. %time 与 %timeit 的区别是什么？脚本文件里没有这两个魔法该怎么办？
@@links
讲义|Pandas 讲义（145 页）|#
工具|Pandas 官网|https://pandas.pydata.org/
文档|Pandas 可视化|https://pandas.pydata.org/docs/user_guide/visualization.html