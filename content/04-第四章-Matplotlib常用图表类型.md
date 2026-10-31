@@h1 第四章　Matplotlib 常用图表类型
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据可视化　|　难度 ★★☆

@@why 这一章在解决什么问题
**上一章的图能画了，但"选对图"是另一门手艺：想展示变化趋势、想对比分类、想看分布、想看相关性——每种诉求都有对应的图。** 选错图，数据再准也白搭。

这一章把 8 类高频图按"**解决什么问题**"来讲，每类图配一段能直接跑的代码和"什么时候用、什么时候别用"。学完你能回答：折线/条形/直方/箱线/散点/饼图/热图/3D 图分别适合什么数据，以及它们最常见的使用误区。

@@prep 开始之前
上一章会画基础图就能开始，这章不用装新东西，跟着把八种图各画一张即可。

@@goal 学到这儿就够了
拿到一组数据能判断该用折线、条形、直方、散点还是饼图，并按场景画出来，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：Matplotlib 基础与图形定制——会画、会修饰一张图
**本章** ← 你在这里：按数据关系选图——把"数据"翻译成"图"
**下一章**：Seaborn 入门与全局定制——接手你的统计绘图库，一行出图、风格统一
**再往后**：Seaborn 统计图表 → NumPy → Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"的完整链路

@@note info 学习提示
本章不要求背参数——**重点记住"什么图解决什么问题"**。每类图开头的"解决什么"就是记忆锚点，代码段在 Jupyter 里跑一遍留个印象即可。下一阶段 Pandas 的 df.plot 底层全部调用本章的图，先讲图、后讲表格，顺序是有意的。

@@point ① 折线图 plot：看见趋势
@@need 要解决什么
**数据随时间/有序批次变化，想看清涨跌趋势**——用折线图，这是最直观的"趋势图"。

@@idea 核心思路
折线图适合**有序数据**（时间序列、样本序号），x 轴是顺序、y 轴是数值，线的斜率就是变化速度：

```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 50)
y = np.sin(x) + np.random.normal(0, 0.2, 50)   # 正弦 + 噪声

plt.plot(x, y, 'b-o', lw=1, label='数据')
plt.xlabel('时间')
plt.ylabel('数值')
plt.legend()          # 显示图例（必须有 label 才有图例项）
plt.grid(alpha=0.3)
```

**图例的坑**：不写 label 参数，legend() 画出来是空的——图例只收录带 label 的曲线。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| legend 有框但没内容 | plot 时没传 label 参数，补齐即可 |
| 折线乱成一团 | 数据不是有序的；先排序再画，或改用散点图 |

@@point ② 条形图 bar：分类对比
@@need 要解决什么
**几类东西比大小**（各区销量、各班人数）——条形图，高度即数量，一眼比出高低。

@@idea 核心思路
竖向 bar 与横向 barh 两种（横向适合类别名很长的情况）：

```python
import matplotlib.pyplot as plt

cats = ['华东', '华南', '华北', '西南']
sales = [120, 95, 88, 60]

plt.bar(cats, sales, color='skyblue')      # 竖向
# plt.barh(cats, sales)                    # 横向：类别名横向排列

plt.ylabel('销量(万元)')
for i, v in enumerate(sales):
    plt.text(i, v + 2, str(v), ha='center')   # 柱顶标数值
```

同类变体：**分组条形图**（多系列并列）用 `width` 微调位置；**堆叠条形图**用 `bottom` 参数逐层累加。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 类别顺序不是你想的排序 | bar 按传入顺序画，不自动排序；要"从高到低"先给数据排序 |
| 柱顶显示的数值不居中对齐 | 用 ha='center' 对齐；柱太高时把文字放柱内（v - 偏移量） |

@@point ③ 直方图 hist：看分布
@@need 要解决什么
**一堆数值想知道"大概集中在哪、怎么分布"**（成绩、身高、价格）——直方图把数值分成一个个区间，数每个区间有多少个。

@@idea 核心思路
直方图的两个关键参数：**bins（分多少桶）和 density（归一化）**：

```python
import matplotlib.pyplot as plt
import numpy as np

data = np.random.normal(170, 8, 500)     # 500 人身高，均值 170、标准差 8（第二个参数是标准差，不是方差）

plt.hist(data, bins=20,                  # 桶数：太密锯齿、太疏丢细节
         color='steelblue', alpha=0.7)
plt.xlabel('身高(cm)')
plt.ylabel('人数')

# 归一化为概率密度（占比而非计数）：
# plt.hist(data, bins=20, density=True)
```

桶数经验：**默认 bins=10，样本几百个时用 15-30 区间比较稳**。`density=True` 后纵轴变成"每单位区间的占比"，不同样本量之间可直接比较形状。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直方图很锯齿/很秃 | bins 调小/调大；多试试不同桶数感受差异 |
| 想比较两组分布却看不出 | 加 density=True + alpha=0.5 叠加对比，或直接用箱线图 |

@@point ④ 箱线图 boxplot：分布浓缩成五数
@@need 要解决什么
想一眼看出一组数据的**中位数、四分位、离群点**——箱线图把分布浓缩成一"箱一须"。

@@idea 核心思路
箱线图用 **5 个数字**概括一组数据：须延伸到 1.5×IQR 内的最远数据点（不是最大/最小值），超出者画成离群点；箱体是 Q1–Q3，中间那道线是中位数；"须"外的点是**异常值**：

```python
import matplotlib.pyplot as plt
import numpy as np

# 三组对比数据
data = [np.random.normal(60, 10, 100),
        np.random.normal(70, 15, 100),
        np.random.normal(65, 5, 100)]

plt.boxplot(data,
            tick_labels=['A 班', 'B 班', 'C 班'],   # matplotlib 3.9+ 把 labels 改名成 tick_labels

            patch_artist=True,          # 给箱子填色
            vert=True)                  # 竖向；False 就横向
plt.ylabel('成绩')
```

读取要点：**箱子越扁 = 数据越集中；须越长 = 分布越散；箱外的孤立点是离群值**，先查数据有没有问题再谈"是不是异常"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用错数据结构报错 | boxplot 接受"多个序列的列表"；单组数据也要包成列表 `[data]` |
| 离群点特别多 | 先检查是不是数据录入错误；正常分布下离群点应是少数 |

@@point ⑤ 散点图 scatter：两变量关系
@@need 要解决什么
**两个数值变量之间有没有关系**（广告费和销量、身高和体重）——散点图，每个点是一个样本，形状透露相关性。

@@idea 核心思路
散点图还能用第三维信息（颜色、大小）编码更多含义：

```python
import matplotlib.pyplot as plt
import numpy as np

n = 100
x = np.random.uniform(0, 10, n)
y = 2 * x + np.random.normal(0, 1, n)     # 明显正相关
sizes = np.random.uniform(20, 300, n)     # 点大小

plt.scatter(x, y,
            s=sizes,          # 点大小（第三维）
            c=x,              # 点颜色跟着 x 变（第三维）
            alpha=0.6, cmap='viridis')
plt.colorbar()                # 颜色映射色条
plt.xlabel('广告投入')
plt.ylabel('销量')
```

读图：**点云整体向右上爬升 = 正相关，向右下 = 负相关，一团乱 = 无相关**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 加上 c 参数后颜色没变 | 颜色映射要配 cmap，且 colorbar 才能看出色阶含义 |
| 点太多糊成一片 | 加 alpha=0.3~0.6 看密度；或改用六边形分箱 hexbin |

@@point ⑥ 饼图 pie：占比，且只用在"少量类别"
@@need 要解决什么
想知道**各部分占整体的比例**——饼图。但比例图先用"这图适合吗"做一次灵魂拷问。

@@idea 核心思路

```python
import matplotlib.pyplot as plt

labels = ['苹果', '香蕉', '橙子']
sizes = [50, 30, 20]

plt.pie(sizes,
        labels=labels,
        explode=(0, 0.1, 0),        # 第二块"飞"出来（突出显示）
        autopct='%.1f%%',           # 显示百分比（保留 1 位小数）
        shadow=False)
plt.axis('equal')                    # 保证正圆，不然会变椭圆
```

**什么时候别用饼图**：类别超过 5-6 个、或者百分比差异不明显时，饼图读不准，**改用条形图**——这也几乎是数据分析界的共识。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 饼是椭圆 | 忘了 plt.axis('equal')（版本差异：较新版本默认已修正） |
| 类别多到看不清 | 就是该换条形图的信号，别硬堆饼图 |
| 百分比自动算的和想的不一样 | autopct 显示的是占比；如果你的数据本来就是百分数，需确认是否想显示原值 |

@@point ⑦ 热力图 imshow：矩阵可视化
@@need 要解决什么
**数据本身是个矩阵/表格**（相关矩阵、混淆矩阵、网格数据）——热力图，颜色深浅映射数值大小，格子型数据结构的天生搭档。

@@idea 核心思路
imshow 按矩阵行列排格子，颜色深浅表示数值：

```python
import matplotlib.pyplot as plt
import numpy as np

mat = np.random.rand(6, 6)          # 6x6 随机矩阵
plt.imshow(mat, cmap='Blues')       # 配色：Blues/Reds/viridis 等
plt.colorbar()                      # 数值色条
plt.xticks(range(6), ['A', 'B', 'C', 'D', 'E', 'F'])
plt.yticks(range(6), ['r1', 'r2', 'r3', 'r4', 'r5', 'r6'])
```

进阶：`interpolation='none'` 避免格子间平滑过渡（数据型矩阵用，图片型不要）；在格子里写数字可以用 `plt.text` 逐格标注——但**若矩阵有行/列标签且要统计特性，后面 Seaborn 的 heatmap 更顺手**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 格子之间模糊过渡 | 给 imshow 加 interpolation='none' 关闭平滑 |
| 行列对不上 | imshow 是"行=从上到下"，和多数表格习惯一致；确认向量方向即可 |

@@point ⑧ 3D 图：投影第三维
@@need 要解决什么
**数据有 x、y、z 三个维度**（地形、函数曲面、三维散点）——2D 装不下，上 3D。

@@idea 核心思路
3D 图的关键是**画布要用 3D 投影（projection='3d'）**，然后普通散点/曲面函数照常用：

```python
from mpl_toolkits.mplot3d import Axes3D      # 提供 3D 能力（部分版本需导入）
import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')    # 关键：projection='3d'

n = 100
x = np.random.normal(0, 1, n)
y = np.random.normal(0, 1, n)
z = np.random.normal(0, 1, n)

ax.scatter(x, y, z, c=z, cmap='coolwarm')     # 3D 散点
ax.set_xlabel('x轴'); ax.set_ylabel('y轴'); ax.set_zlabel('z轴')
```

曲面图 `ax.plot_surface(X, Y, Z)` 需要网格式数据（np.meshgrid 生成）；3D 图易"视觉欺骗"（远近遮挡误读），**能用 2D 表达就别上 3D**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| add_subplot(111) 后是 2D 图 | 没写 projection='3d'；写错会报"no 3d projection" |
| 3D 图两个点前后遮挡看不清 | 正常现象；3D 只适合真三维结构，别为了炫酷硬上 |

@@summary
这一章你拿到了"选图字典"：

| 图表 | 解决什么问题 | 别用来干嘛 |
|---|---|---|
| 折线图 | 有序数据的趋势 | 无序分类对比 |
| 条形图 | 分类别比大小 | 连续趋势 |
| 直方图 | 数值分布形状 | 类别对比（那是条形图） |
| 箱线图 | 分布五数 + 离群点 | 细粒度趋势 |
| 散点图 | 两变量关系 | 单变量分布 |
| 饼图 | 少量类别占比 | 5-6 类以上、差异小的占比 |
| 热力图 | 矩阵/网格数值 | 含行标签的统计表（用 Seaborn heatmap） |
| 3D 图 | 真三维结构 | 能用 2D 表达的场景 |

一句话记住本章：**趋势用折线、对比用条形、分布看直方/箱线、关系看散点、占比用饼图、矩阵用热图——先定"要回答什么问题"，再选图，绝不反过来。**

@@quiz
1. 折线图适合什么样的数据？画出来没有图例，最可能的原因是什么？
2. 条形图如何实现"从高到低"的排序显示？
3. 直方图的 bins 和 density 参数分别控制什么？不同样本量的两组分布想比较形状，该怎么做？
4. 箱线图的"箱"和"须"分别代表什么？箱外的点是什么？
5. 散点图中 c 和 s 参数分别编码了什么信息？
6. 为什么说"类别超过 5-6 个时别用饼图"？
7. 画 3D 图的必要条件是什么？为什么建议"能用 2D 就别上 3D"？

@@links
参考|matplotlib （52 页）|#
工具|Matplotlib 官网|https://matplotlib.org/
文档|Matplotlib 图表指南|https://matplotlib.org/stable/plot_types/index.html