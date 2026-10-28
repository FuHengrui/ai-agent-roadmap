@@h1 第三章　Matplotlib 基础与图形定制
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据可视化　|　难度 ★★☆

@@why 这一章在解决什么问题
**数据算出来了，但"看得懂"是另一回事：一行数字看不出趋势，一张图全明白了。** 可刚上手 Matplotlib 的你大概率会撞上这些墙：标题写中文变方框；想画多张子图不会排；两条量纲不同的线画不到一张图；想标出最小值不会加箭头……

这一章就是 Matplotlib 的"打地基"：**先看懂一张图由哪些部件组成，再学会从画出来到修饰完整的每一步**。学完你能回答：Figure/Axes/Axis 是什么关系、怎么解决中文乱码、怎么排多子图、怎么画双轴、怎么定制线条刻度网格、怎么标注释、怎么高清保存。

@@prep 开始之前
上一章的 Jupyter 能跑就行，先 pip install matplotlib；中文乱码这章带着修。

@@goal 学到这儿就够了
能画出带标题、图例、中文的折线图，能说清 Figure/Axes/Axis 各是什么并存成图片，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：Jupyter Notebook 与开发工具链——你的默认工作台
**本章** ← 你在这里：第一个绘图库 Matplotlib 的基础与定制——"画出一张能看的图"
**下一章**：Matplotlib 常用图表类型——折线、条形、直方、饼图等按场景选图
**再往后**：Seaborn（Matplotlib 的高层封装）→ NumPy → Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"的完整链路，可视化这一步从这里起步

@@note info 学习提示
本章 13 个知识点按"**组成 → 画 → 修**"推进：第 ①② 点建立概念，第 ③-⑤ 点画出第一张图并解决中文，第 ⑥-⑧ 点布局（子图/嵌套/双轴），第 ⑨-12 点修饰（线条/刻度/网格/标注），第 13 点保存。**所有示例建议在 Jupyter 里逐段跑**，改了参数立刻看效果，比背参数快十倍。

@@point ① Matplotlib 是什么与安装
@@need 要解决什么
数据分析要出图，第一个问题永远是：**用什么库、怎么装？**

@@idea 核心思路
Matplotlib 是 Python 数据可视化的事实标准库：接口风格类似 MATLAB，能画折线、散点、直方图、饼图、3D 图等几乎所有常见图表，是数据分析、科学计算的标配。

安装（在目标虚拟环境中）：

```bash
pip install matplotlib==3.8.2
```

两个认知校准：

- Matplotlib **不止能画 2D**，通过 `projection='3d'` 也支持 3D 图（第 4 章细讲）；
- 它是"底层绘图库"——后面学的 Seaborn 就是**建立在 Matplotlib 之上**的高层封装。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 装了后 `import matplotlib` 报错 | 检查是否装进了当前激活的环境；用 `conda install matplotlib` 也可 |
| 认为 Matplotlib 只能画 2D | 3D 也能画，只是需要显式指定 projection='3d'（见下章） |

@@point ② 图表的组成：Figure / Axes / Axis / Artist
@@need 要解决什么
教程里一会儿 figure、一会儿 axes、一会儿 axis，**三个词长得像，分不清就没法精准控制绘图对象。**

@@idea 核心思路
一张 Matplotlib 图的部件层级，从大到小：

| 术语 | 是什么 | 一句话记忆 |
|---|---|---|
| Figure | 最顶层的"画布/画板" | 装下所有内容的大容器 |
| Axes | 一个独立的"坐标系"，也就是一个子图 | 画布上的每一块独立绘图区 |
| Axis | 坐标轴本身（X 轴 / Y 轴） | 管刻度、标签；**注意拼写与 Axes 极像** |
| Artist | 图内所有可见元素（线、文字、图例…）的基类 | 图上你看到的一切都是 Artist |

拿"一张两行两列的子图"举例：整块窗口是 **Figure**，4 个小图各是一个 **Axes**，每个 Axes 上各有两条 **Axis**（x/y 轴）。

```python
import matplotlib.pyplot as plt

fig = plt.figure()                # 建画布（Figure）
ax = fig.add_subplot(1, 1, 1)     # 画布上建 1 个坐标系（Axes）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Axes 和 Axis 混着说 | Axes=坐标系（子图），Axis=坐标轴；教材里也常混，你自己分清就够了 |
| 想改 x 轴刻度却找不到对象 | 刻度挂在 Axis 上，用 `ax.set_xticks()`；坐标系用 `ax` 表示 |

@@point ③ pyplot 基础绘图流程：第一张图
@@need 要解决什么
一张最简单的折线图，**最少需要哪几行代码？** 先把主干跑通，再谈修饰。

@@idea 核心思路
pyplot 是 Matplotlib 的面向过程接口，核心流程三步：**构造数据 → plot 绘图 → show 显示**：

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [1, 4, 9, 16, 25]

plt.plot(x, y)          # 画折线
plt.show()              # 显示（Jupyter 里可省略，自动内嵌）
```

配套的基础方法（先混脸熟）：

```python
plt.title("图表标题")          # 标题
plt.xlabel("x 轴名称")        # x 轴标签
plt.ylabel("y 轴名称")        # y 轴标签
plt.figure(figsize=(8, 5))   # 设定画布宽高（英寸）、dpi 可选
```

注意 `plt.xticks`/`plt.yticks` 是**设置刻度**，`plt.xlabel`/`ylabel` 是**设置轴名**，别混。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 脚本里 plot 后没 show，图不显示 | 显示依赖 show()；Jupyter 里会自动内嵌则无需显式调用 |
| xlabel 和 xticks 分不清 | xlabel 是坐标轴的"名字"，xticks 是坐标轴的"刻度"（数值/标签） |

@@point ④ 中文乱码：每个新手的第一个坎
@@need 要解决什么
标题一写中文就变方框（□□□）或乱码，**因为 Matplotlib 默认字体不含中文字形。** 两行配置解决。

@@idea 核心思路
全局解决（写一次，全程生效）：

```python
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = 'SimHei'   # 指定中文字体（黑体）
plt.rcParams['axes.unicode_minus'] = False   # 解决负号显示为方块
```

**第二行 `unicode_minus` 特别容易漏**：只设字体不设它，负号照样显示成方块。

字体管理进阶（针对"系统没装 SimHei"的场景）：

```python
from matplotlib import font_manager

for f in font_manager.fontManager.ttflist:      # 查看系统可用中文字体
    print(f.name)
font_manager.fontManager.addfont('./你的字体.ttf')  # 临时加载额外字体文件
```

局部指定字体：`plt.title("标题", fontdict={'fontname': 'SimHei'})`，或对单个文本对象用 `FontProperties`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 设了 SimHei 还是乱码 | 系统没装该字体；用 ttflist 查实际可用的中文字体名，或下载字体文件 addfont |
| 数轴负号是方块 | 只设了 font.sans-serif、漏了 `axes.unicode_minus=False` |

@@point ⑤ 绘图风格：一键换肤
@@need 要解决什么
默认白底样式太素，**想要专业配色又不愿意手动调几十个参数**——Matplotlib 内置风格表一键切换。

@@idea 核心思路

```python
from matplotlib import style

print(style.available)          # 查看全部可用风格
style.use('ggplot')             # 应用 ggplot 风格（其他如 'seaborn-v0_8' 等）
```

```python
import matplotlib.pyplot as plt

plt.style.use('ggplot')
plt.plot([1, 2, 3], [4, 5, 6])
```

注意：**切换风格会改变默认参数**，某些之前手动设置的细节（如字体）可能被覆盖，需在换风格之后再设置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 换风格后之前设的中文字体失效 | 风格会重置 rcParams；把字体设置写在 style.use 之后 |
| 以为风格是"原样可用" | 风格只调默认样式，你的图仍需自己控制数据与含义 |

@@point ⑥ 多子图布局：subplot / subplots
@@need 要解决什么
想在一张画布里放 4 张小图对比，**怎么精确控制每个小图的位置？**

@@idea 核心思路
两种写法，都掌握：

```python
import matplotlib.pyplot as plt

# 写法一：序号定位法（1 起，从左到右、从上到下）
plt.figure(figsize=(12, 6))
plt.subplot(2, 2, 1)          # 2 行 2 列，第 1 个
plt.plot([1, 2, 3], [4, 5, 6])
plt.subplot(222)              # 简写：2 行 2 列第 2 个，等价 (2,2,2)
plt.scatter([1, 2, 3], [4, 5, 6])
```

```python
# 写法二：subplots 批量返回坐标系数组（推荐）
fig, axs = plt.subplots(2, 2, figsize=(12, 6))
axs[0, 0].plot([1, 2, 3], [4, 5, 6])     # 第 1 行第 1 列
axs[0, 1].bar([1, 2, 3], [4, 5, 6])      # 第 1 行第 2 列
axs[1, 0].scatter([1, 2, 3], [4, 5, 6])  # 第 2 行第 1 列
```

用 `fig.subplots()` 或 `plt.subplots()` 均可，返回值是 **Axes 数组**，按 `axs[行, 列]` 索引。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用了 `fig.subplot`（单数）报没有该方法 | 批量创建是 `subplots`（复数）；`fig.subplot` 方法不存在 |
| 子图位置排错 | 序号 1 起，从左上到右下（第 1 行 1、2；第 2 行 3、4） |

@@point ⑦ 嵌套图形：在主图里叠小图
@@need 要解决什么
想在大图上叠加一个小图（画中画，比如放个放大的局部），**怎么在任意位置放一个坐标轴？**

@@idea 核心思路
两种做法，核心都是用 **0~1 的比例坐标**（[left, bottom, width, height]）指定位置：

```python
import matplotlib.pyplot as plt

fig = plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])                     # 主图

# 方式一：plt.axes 在画布上新增坐标轴
plt.axes([0.2, 0.6, 0.2, 0.2])                     # left=0.2 bottom=0.6 宽高各 0.2
plt.plot([1, 2], [3, 4])

# 方式二：fig.add_axes 同样位置叠加
fig.add_axes([0.6, 0.2, 0.2, 0.2])
plt.scatter([1, 2], [3, 4])
```

同一张画布上，plt.axes 和 fig.add_axes 都能"抠"出一块新坐标系放在指定位置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 小图位置不对/跑出画布 | add_axes 参数是 0~1 的归一化坐标，不是像素；left+width 别超过 1 |
| 以为 add_subplot 只能用于嵌套 | add_subplot 是按网格加子图，add_axes 才能自由放置 |

@@point ⑧ 双轴显示：twinx 一图两量纲
@@need 要解决什么
温度（30℃ 左右）和湿度（70% 左右）量纲差一大截，**画一张图，一条线贴着底、一条线顶到天。** 需要左右两条 y 轴。

@@idea 核心思路
`ax.twinx()` 创建**共享 x 轴的右侧副 y 轴**：

```python
import matplotlib.pyplot as plt

fig, ax1 = plt.subplots()
times = [1, 2, 3, 4]
temp = [28, 30, 32, 31]        # 左侧量纲：温度

ax1.plot(times, temp, color='red')
ax1.set_ylabel('温度(℃)')

ax2 = ax1.twinx()              # 右边新 y 轴，共享 x 轴
humidity = [65, 70, 72, 68]
ax2.plot(times, humidity, color='blue')
ax2.set_ylabel('湿度(%)')

# 两条 plot 各自先设 label='温度' / label='湿度'，图例才有名字
fig.legend()    # 图例挂在 fig 上（两轴合一）
fig.tight_layout()             # 防止标签重叠
```

关键：**图例要挂在 fig 而不是单一 ax 上**，否则只显示一根轴的曲线。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 图例只出现一条线的名字 | legend 要挂在 fig 上（`fig.legend`），单轴 legend 只收录该轴曲线 |
| 右轴没有名字 | 记得给 ax2 单独 set_ylabel |

@@point ⑨ 线条与标记样式：颜色、线型、点形
@@need 要解决什么
多条线都是同一种蓝实线，**分不清谁是谁**——给每条线配不同的颜色、线型、点形。

@@idea 核心思路
`plt.plot` 的一串样式参数：

```python
import matplotlib.pyplot as plt

plt.plot(x, y,
         color='red',            # 线条颜色（color 或 c）
         linewidth=2,            # 线宽（linewidth 或 lw）
         linestyle='--',         # 线型：'-'实线 '--'虚线 ':'点线 '-.'点划线
         marker='o',             # 点形：'o'圆点 '*'星号 's'方块 '^'三角
         mfc='blue',             # 点的填充色（marker face color）
         markersize=10,          # 点的大小
         alpha=0.3)              # 整条线透明度 0~1
```

注意 **linewidth 是标准拼写**（不是 linewith）；linestyle 简写 ls、linewidth 简写 lw 都可用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| marker 加了没效果 | marker 只对点生效；线用 linestyle，点用 marker，两者配合才是"带点的线" |
| 拼写 linewith 不报错但线宽没变 | 参数名拼错会被忽略；正确是 linewidth |

@@point ⑩ 坐标轴刻度定制：xticks / yticks
@@need 要解决什么
刻度要么太密，要么显示的是 0、1、2……而你想要"第1天、第2天"这种业务标签。**刻度内容由你说了算。**

@@idea 核心思路

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5, 6, 7]
data = [29, 30, 31, 32, 28, 27, 30]

plt.xticks(x, ['第{}天'.format(i) for i in range(1, 8)])   # 位置 + 标签一一对应
plt.yticks(range(0, 35, 5))                               # 0 到 35，步长 5
```

坐标系对象的写法（子图场景更常用）：

```python
ax.set_xticks(x)                    # 设置位置
ax.set_xticklabels(['周一', '周二', '周三'])  # 设置标签
```

双轴场景下，左轴右轴各自 set_yticks 互不影响。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 标签个数和刻度数对不上 | 位置列表和标签列表**长度必须一致**，否则错位或报错 |
| `ax.xticks()` 报错 | Axes 对象没有 xticks 方法，用 `ax.set_xticks()` |

@@point ⑪ 网格与标题：grid / title / suptitle
@@need 要解决什么
图太素，读数值靠肉眼比划。**加网格辅助线 + 分大小的标题。**

@@idea 核心思路

```python
import matplotlib.pyplot as plt

plt.title('一天温度变化', fontsize=14)      # 图内标题
plt.suptitle('2030年10月1日', fontsize=18)  # 整图大标题（可盖住子图们）

plt.grid(axis='y',            # 只显示 y 向网格；'x' 或 'both'
         linestyle='--',      # 虚线网格，可 c= 颜色、lw= 线宽
         alpha=0.5)
```

`title` 管单个坐标系的小标题，`suptitle` 管整张画布的大标题——多子图时两个都常用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| grid 拼成 gird | 单词拼错参数不生效且不报错，检查拼写 |
| 网格太黑盖住数据 | 用 alpha=0.3~0.5 调淡 |

@@point ⑫ 数据标注与注释：text / annotate
@@need 要解决什么
图看完了，但**每个点的具体数值、最高/最低点在哪**？加文字标注单靠肉眼读坐标太累。

@@idea 核心思路
**text：给每个点标数值**（循环 + zip）：

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [3, 1, 4, 1, 5]

plt.plot(x, y, marker='o')
for i, j in zip(x, y):
    plt.text(i + 0.1, j, str(j), ha='center', va='bottom')  # 点旁标数值
```

**annotate：箭头指向关键点**（如最小值）：

```python
import numpy as np

m = min(y)                               # 最值
idx = y.index(m)
plt.annotate('最小值',                    # 注释文字
             xy=(x[idx], m),             # 箭头指向的数据点
             xytext=(x[idx] + 0.5, m + 1),  # 文字放置位置
             arrowprops=dict(facecolor='black',    # 箭头样式
                             width=1, headwidth=6, headlength=8))
```

参数速记：**xy 指哪里，xytext 文字放哪，arrowprops 画箭头**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| text 的偏移量用 0.1 没看出效果 | text 坐标是数据坐标，偏移量要按数据量级取（数据成千上万就偏移几十） |
| 箭头细到看不见 | arrowprops 缺 headwidth/headlength，箭头就几乎隐形；补上即可 |
| 中文标注乱码 | 标注也是文本，同样依赖第 ④ 点的字体配置 |

@@point ⑬ 保存图表：savefig
@@need 要解决什么
图画好了，**要存成文件插进报告/发出去**——存高清、存对格式、别存成空白。

@@idea 核心思路

```python
import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [4, 5, 6])

plt.savefig('./img/line1.png',     # 路径 + 文件名（支持 png/svg/jpeg/pdf）
            dpi=300,               # 清晰度（报告用 300，屏幕用 100-150）
            facecolor='white',     # 背景色（保存时默认透明背景可改）
            pad_inches=0.2)        # 四周留白
```

注意点：

- **png/jpeg 是位图**，dpi 决定清晰度；**svg/pdf 是矢量图**，放大不糊，适合论文插图；
- **先 savefig 再 show**：先 show 后保存可能存出空白图（画布被重置）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 保存出来是空白 | show() 之后才 savefig 常见；把 savefig 挪到 show 之前 |
| 报错没有文件夹 | 目录不存在会报错；先 `import os; os.makedirs('./img', exist_ok=True)` |
| 网页用 png 发糊 | 用 dpi=150 以上，或直接存 svg |

@@summary
这一章你掌握了 Matplotlib 的"画图 → 修饰 → 保存"全链路：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **部件认知**：Figure 画布 / Axes 坐标系 / Axis 坐标轴 / Artist 元素 | 看懂报错、精准控制对象的起点 |
| **基础流程**：plot → show，配 title/xlabel/ylabel | 第一张图 3 行代码跑通 |
| **中文方案**：rcParams 字体 + unicode_minus，ttflist/addfont 兜底 | 再无方框乱码 |
| **布局三件套**：subplot(s) 多子图、add_axes 画中画、twinx 双轴 | 复杂版式全部拿下 |
| **细节定制**：颜色/线宽/线型/点形、刻度标签、网格、标题层级 | 图从"能看"到"专业" |
| **标注与保存**：text 逐点标值、annotate 箭头注释、savefig 高清出图 | 图表可交付、可插文档 |

一句话记住本章：**先认 Figure/Axes/Axis，再 plot 画出来、rcParams 治中文、subplots 排布局、twinx 走双轴，最后 savefig 存高清——Matplotlib 的地基就稳了。**

@@quiz
1. Matplotlib 中 Figure、Axes、Axis、Artist 分别是什么？举一个"一张两行两列子图"对应关系的例子。
2. 解决中文乱码的两行 rcParams 配置是什么？为什么第二行不能省？
3. `plt.subplot(2,2,1)` 和 `plt.subplots(2,2)` 的区别是什么？
4. 在一张图上叠加两个任意位置的小图，用哪个方法？它的四个参数分别代表什么？
5. 想要温度、湿度两条量纲不同的线画在一张图上，核心方法是哪个？图例为什么最好挂在 fig 上？
6. annotate 的 xy、xytext、arrowprops 三个参数分别控制什么？
7. 为什么先 show 再 savefig 可能存出空白图？位图（png）和矢量图（svg/pdf）的清晰度机制有什么不同？

@@links
参考|matplotlib （52 页）|#
工具|Matplotlib 官网|https://matplotlib.org/
文档|Matplotlib 风格参考|https://matplotlib.org/stable/gallery/style_sheets/