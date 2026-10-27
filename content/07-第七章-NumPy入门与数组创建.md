@@h1 第七章　NumPy 入门与数组创建
@@sub 阶段 17 · 数据科学与智能分析基础　|　数值计算　|　难度 ★★☆

@@why 这一章在解决什么问题
**Pandas、matplotlib 都在背后依赖同一个底座——NumPy 的数组（ndarray）。** 不懂数组的创建和属性，后面你看到的 Series/DataFrame、图形数据，全是一团"会跑但不懂"的黑盒。而且处理大数据时 Python 原生列表慢得离谱，NumPy 数组快几十倍。

这一章先把数组的"**创建 12 式**"练熟：array/arange/random/zeros 全家/empty/full/eye/linspace/logspace，顺带把 dtype 和属性（ndim/shape/dtype/size）钉死。学完你能回答：ndarray 比 list 快在哪、13 种创建方式怎么选、dtype 为什么重要、随机数四兄弟各什么用。

@@map 这一章在整个知识库里的位置
**上一章**：Seaborn 统计图表——数据的"可视出口"
**本章** ← 你在这里：NumPy 章节开篇——数组创建与基本认知，数据科学"计算底座"的第一块砖
**下一章**：ndarray 访问、变换与拼接——索引切片、视图副本、reshape/concatenate
**再往后**：NumPy 计算统计进阶 → Pandas（它的数据内核就是 numpy）→ MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路；NumPy 这 3 章把"计算"两个字做实

@@note info 学习提示
创建方式多，但**底层只有两条主线：手动构造（array/arange/linspace/random）与预置模板（zeros/ones/eye…）**。建议在 Jupyter 里每个函数都跑一遍并看 `.shape`——"创建出来是什么形状"比"函数名"更重要。本章全部用 Jupyter/交互式终端练习。

@@point ① 认识 ndarray：为什么数组比列表快
@@need 要解决什么
**为什么不直接用 Python 列表做数据分析？** 这是第一个必须想通的问题，否则 NumPy 学起来像"多此一举"。

@@idea 核心思路
NumPy（Numerical Python）的核心对象是 **ndarray（N 维数组对象）**，它对比 Python 列表有两个关键差异：

| 维度 | 列表 list | ndarray |
|---|---|---|
| 元素类型 | 可混装任意类型 | 单一 dtype，内存连续 |
| 计算方式 | 逐元素 Python 循环（慢） | 底层 C 语言向量化（快） |
| 数学运算 | 需手写循环 | 整个数组直接参与运算 |

```python
import numpy as np

arr = np.array([1, 2, 3, 4])
print(arr + 10)        # 整个数组 +10，无循环
print(arr ** 2)        # 逐元素平方
```

数组运算 vs 列表 `[1,2,3] + [4,5,6]`（结果是拼接）——**ndarray 的 + 是逐元素相加**，这就是向量化的意义。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用列表去重/运算又慢又绕 | 那是没上 NumPy；数组运算一行解决 |
| `np.array` 和 `list` 混着算 | 数组 + 列表会自动转数组；但类型不清时先统一转数组 |

@@point ② array()：从列表/元组手动创建
@@need 要解决什么
**已经有一份数据（列表、嵌套列表），怎么变成数组？**

@@idea 核心思路

```python
import numpy as np

a1 = np.array([1, 2, 3])                    # 一维
a2 = np.array([[1, 2], [3, 4]])             # 二维（嵌套列表）
a3 = np.array([(1, 2), (3, 4)])             # 元组转数组一样
a4 = np.array(5)                            # 标量也能转（0 维数组）
```

自动推断 dtype：整型列表 → int64，含小数 → float64，字符串 → 不能参与数值计算。**"array" 是通用转换入口，其余创建方式都是它的特化**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 层数不齐的嵌套列表报错 | 如 [[1,2],[3]]：行列不齐无法成矩形数组（报 ValueError），先补齐数据 |
| 用 np.array 替代 arange/zeros 等 | 功能重叠但语义不清；固定套路用专门函数，手动数据才用 array |

@@point ③ arange：等距整数序列
@@need 要解决什么
**需要 0 到 N 的连续整数下标/坐标**——arange 是"range 的数组版"。

@@idea 核心思路

```python
import numpy as np

np.arange(5)          # 0,1,2,3,4（不含 5）
np.arange(1, 10)      # 1...9
np.arange(1, 10, 2)   # 1,3,5,7,9（步长 2）
np.arange(0, 1, 0.1)  # 浮点步长可用：0, 0.1, ..., 0.9（但浮点累计误差）
```

对比记忆：**arange(终点) / arange(起点, 终点) / arange(起点, 终点, 步长)**，与 Python range 完全同构；区别是 range 返回迭代器、arange 直接出数组。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| arange 浮点结果 0.30000000000000004 | 浮点累计误差，正常；精确等分用 linspace |
| 忘了"含头不含尾" | arange(0,5) 只有 0-4，5 不包含 |

@@point ④ random 四兄弟：random / randint / randn / normal
@@need 要解决什么
**随机数在测试、初始化、模拟里无处不在**——NumPy 随机四兄弟各管一摊，别用混。

@@idea 核心思路

```python
import numpy as np

np.random.random(5)                # [0,1) 均匀分布 5 个
np.random.random((2, 3))           # 传形状元组（2 行 3 列）
np.random.randint(1, 100, 10)      # [1,100) 整数 10 个
np.random.randn(5)                 # 标准正态(均值0方差1)
np.random.normal(0, 1, (2, 3))     # 指定均值/方差的正态，可指定形状
```

对应关系记法：

| 函数 | 分布 | 常用来 |
|---|---|---|
| random / rand | 均匀 [0,1) | 概率测试 |
| randint | 均匀整数 [a,b) | 模拟骰子、随机样本下标 |
| randn | 标准正态 | 噪声、初始权重 |
| normal(均值, 标准差, 形状) | 任意正态 | 指定量级的模拟数据 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| random((2,3)) 报错 | random 传形状元组；randint 第 3 个参数是数量不是形状 |
| 随机结果每次不同 | 想要可复现：`np.random.seed(42)` 固定种子（同一种子跑出同一串数） |

@@point ⑤ 数组四属性：ndim / shape / dtype / size
@@need 要解决什么
拿到一个数组第一件事就是"**看它几维、多长、什么类型**"——四个属性是三观。

@@idea 核心思路

```python
import numpy as np

a = np.array([[1, 2, 3], [4, 5, 6]])

a.ndim          # 2：维度数（轴数）
a.shape         # (2, 3)：每维长度（2 行 3 列）
a.dtype         # int64：元素类型
a.size          # 6：元素总数（= 2*3）
```

三个容易混的点：

- **shape 是元组**，一维也是 (n,) 带逗号：`np.array([1,2,3]).shape → (3,)`；
- **size = shape 各维乘积**，不等于 shape；
- **dtype 描述元素类型**：int64/float64/uint8/str/bool 等，决定内存与运算精度。

```python
print(a.shape[0], a.shape[1])   # 行数 2、列数 3（shape 元组按下标取）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| a.shape 打出来 (3,) 而不是 (3) | 元组单个元素必须带逗号，正常 |
| 以为 size 是"第几维的大小" | size 是总元素数；某维大小用 shape[轴号] |

@@point ⑥ zeros / ones：零阵与全一阵
@@need 要解决什么
**初始化"全 0 / 全 1"的数组**是最常见的预置操作（累加器、占位、掩码）。

@@idea 核心思路

```python
import numpy as np

np.zeros(5)              # 一维 5 个 0
np.zeros((2, 3))         # 2x3 全 0
np.ones((3, 4))          # 3x4 全 1
np.zeros((2, 2), dtype=int)   # 可指定整数类型
np.ones_like(arr)        # 与 arr 同形状的全 1（形状自动继承）
```

注意形状传参的两种写法：**传整数给一维，传元组给多维**——`np.zeros(2,3)` 是错误写法。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| np.zeros(2,3) 报错 | 形状要元组 zeros((2,3))；一维才直接给整数 |
| zeros 出来是 float 0.0 | 默认 float64；要整数加 dtype=int |

@@point ⑦ empty / full：空数组与填充数组
@@need 要解决什么
**zeros/ones 不够用：想开一块"没初始化"的阵（empty）或"全填同一个值"（full）**。

@@idea 核心思路

```python
import numpy as np

np.empty((3, 3))           # 分配内存但不初始化（内容是垃圾值！）
np.full((2, 3), 7)         # 2x3 全填 7
np.full((2, 2), 3.14)      # 填充浮点也行
```

关键认知：

- **empty 不初始化**：里面是内存里的旧数据（垃圾值），只是"快"。**读取未写入的位置结果不可预测，练习别用**；
- **full 才是"指定值填充"的正式入口**，别用 `np.ones*5` 变通。

使用模式：**预分配大数组再逐段写入**时 empty 省初始化时间；数值模拟/掩码常用 full。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| empty 出来的数字巨大且无规律 | 那是未初始化的垃圾值，正常；需要确定内容用 zeros/full |
| 以为 full 只能填整数 | 任意数值都可以，还能配合 dtype |

@@point ⑧ eye：单位矩阵
@@need 要解决什么
**需要"主对角线为 1"的单位矩阵**——数学计算（如矩阵求逆的前置）常用。

@@idea 核心思路

```python
import numpy as np

np.eye(3)          # 3x3 单位阵：对角线 1，其余 0
np.eye(2, 3)       # 2 行 3 列，对角线还是 1
```

注意：**eye 是"对角线为 1 的方阵/矩形"，不是全 1 阵**——全 1 用 ones，这两个名字极易搞混。

```python
np.eye(3, dtype=int)   # 整数型单位阵
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| eye(3) 出来对角 1 其余 0，以为该全是 1 | eye=单位阵；全 1 请用 ones |
| eye 与 identity 混淆 | identity(n) 只做方阵，eye 支持矩形，一般用 eye |

@@point ⑨ linspace：等距浮点序列
@@need 要解决什么
**在 [a, b] 之间均匀取 N 个点**（画图 x 轴、采样）——linspace 精确等分，不含浮点累计误差。

@@idea 核心思路

```python
import numpy as np

np.linspace(0, 1, 5)     # [0, 0.25, 0.5, 0.75, 1.0] —— 端点默认都包含
np.linspace(0, 10, 4)    # [0, 3.333, 6.667, 10.0]
np.linspace(0, 1, 5, endpoint=False)   # 不含终点：0,0.2,0.4,0.6,0.8
```

对比 arange：**linspace(起, 止, 个数) 按个数等分；arange(起, 止, 步长) 按步长推进**。画图选 x 轴、需要"正好 N 个点"——用 linspace。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| linspace 元素数和预期对不上 | 默认含端点；算点数是 endpoint 默认 True 的结果 |
| 与 arange 混淆 | arange 数的是步长、linspace 数的是个数；需求"恰好 N 个"用 linspace |

@@point ⑩ logspace：等比浮点序列
@@need 要解决什么
**数据跨越几个数量级（10^-2 到 10^3），等距取点浪费**——logspace 在指数上等距，画对数坐标必备。

@@idea 核心思路

```python
import numpy as np

np.logspace(0, 3, 4)     # 10^0, 10^1, 10^2, 10^3 → [1, 10, 100, 1000]
np.logspace(-2, 2, 5)    # 0.01, 0.1, 1, 10, 100
```

理解：**参数是 10 的指数起点和终点**——`logspace(0,3,4)` = `10**linspace(0,3,4)`。默认底数是 10，`base=2` 可换底。

用途：频率轴（10Hz~10kHz）、网页收入差距、参数搜索（数量级扫描）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| logspace(0,3,4) 出来的数像"很大" | 它就是 1,10,100,1000——因为参数是"指数"不是"数值" |
| 忘记 base 参数 | 默认 10；换底用 base=2/np.e 等 |

@@point ⑪ dtype 与 astype：数据类型控制
@@need 要解决什么
**内存大小、计算精度都取决于 dtype**；两数组类型不一致时运算还会出"诡异"结果。怎么查、怎么转？

@@idea 核心思路

```python
import numpy as np

a = np.array([1, 2, 3])
a.dtype                     # int64
b = a.astype(float)         # 转为 float64（返回新数组，原数组不变）
b.dtype                     # float64

c = np.array([1.5, 2.7])
c.astype(int)               # [1, 2]：直接截断小数，不是四舍五入！
```

三类高频转换：

- `astype(float)` / `astype(int)`：数值类型切换（int 转换是**截断**）；
- `astype(bool)`：0 → False，非 0 → True（掩码基础）；
- `astype('str')`：数值转字符串（拼接展示时）。

注意：**astype 返回新数组，不修改原数组**；忘记赋值 = 没转。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| astype(int) 把 2.7 变成 3？ | 不会，是截断为 2；四舍五入要用 np.round 再转 |
| 转了类型原数组没变 | astype 不改原数组，必须 `arr = arr.astype(...)` 接收 |

@@point ⑫ 创建方式速查：什么时候用哪个
@@need 要解决什么
13 种创建方式记不住，**面对具体需求选哪一个？** 一张决策表收尾。

@@idea 核心思路

| 需求 | 函数 | 例 |
|---|---|---|
| 已有数据转数组 | array() | np.array([[1,2],[3,4]]) |
| 连续整数序列 | arange() | np.arange(0, 20, 2) |
| [a,b] 间均匀 N 点 | linspace() | np.linspace(0,1,5) |
| 数量级跨度采样 | logspace() | np.logspace(-2,2,5) |
| 随机均匀 [0,1) | random() / rand() | np.random.random((3,3)) |
| 随机整数 | randint() | np.random.randint(1,7,10) |
| 正态随机 | randn()/normal() | np.random.normal(0,1,100) |
| 全 0 / 全 1 | zeros / ones | np.zeros((2,3)) |
| 指定值阵 | full | np.full((3,2), 7) |
| 单位阵 | eye | np.eye(4) |
| 快分配不初始化 | empty | np.empty((100,100)) |

实战串一遍：

```python
import numpy as np

x = np.linspace(0, 10, 100)                    # x 轴
y = 2 * x + np.random.normal(0, 1, x.shape)    # 带噪声的直线
mask = y > np.median(y)                        # 高于中位数的掩码
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 看教程每个函数都学但用不起来 | 记"需求 → 函数"对应（上表），用的时候查表 |
| 一次想造"阶梯数据" | 先 arange/linspace 造线，再 tile/repeat（第 9 章变换） |

@@summary
这一章你拿下了数组创建的"全招式"：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **ndarray 认知**：同质 dtype + 向量化计算 | 懂它比列表快的根本原因 |
| **手动构造**：array / arange / linspace / logspace | 从数据、序列、等分采样三条路造数组 |
| **随机数四件套**：random / randint / randn / normal | 测试与模拟数据随手造 |
| **预置模板**：zeros / ones / full / empty / eye | 初始化、占位、掩码、单位阵各有其主 |
| **四属性**：ndim / shape / dtype / size | 拿到数组先"验明正身" |
| **类型控制**：dtype 检查 + astype 转换 | 精度与内存可控；截断 vs 四舍五入心里有数 |

一句话记住本章：**手动数据用 array、序列用 arange、等分用 linspace、随机用 random 系列、预置用 zeros/ones/full/eye——先验 shape 与 dtype，数组的"出生方式"就全在你手里了。**

@@quiz
1. ndarray 比 Python 列表快的两个根本原因是什么？
2. arange(1, 10, 2) 的结果是什么？它的第三个参数是什么含义？
3. randint(1, 7, 10) 与 random((2, 3)) 的参数含义有何不同？
4. ndim、shape、dtype、size 四个属性各是什么？shape(3,) 里的逗号是怎么回事？
5. zeros((2,3)) 与 zeros(2,3) 有什么区别？
6. empty 数组里的值为什么"诡异"？为什么练习时不用它？
7. eye(3) 和 ones((3,3)) 的区别是什么？
@@links
参考|numpy （68 页）|#
工具|NumPy 官网|https://numpy.org/
文档|NumPy 数组创建教程|https://numpy.org/doc/stable/user/absolute_beginners.html