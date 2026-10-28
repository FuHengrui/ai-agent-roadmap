@@h1 第九章　NumPy 计算、统计与进阶
@@sub 阶段 17 · 数据科学与智能分析基础　|　数值计算　|　难度 ★★☆

@@why 这一章在解决什么问题
**数组能建、能取、能拼了，但数值分析的主角是"算"：求均值中位数、矩阵乘法、排序、去重、按条件挑数。** 这些操作要么列表手写到怀疑人生，要么 Pandas 里"知其然不知其所以然"。NumPy 把它们全部向量化——一行顶十行，速度还快几十倍。

这一章把计算能力一次讲透：**通用函数（ufunc）、算术统计全家桶、矩阵乘积、排序、广播机制、布尔掩码**。学完你能回答：求和/均值等统计怎么按 axis 算、dot 和 * 的区别、广播的"形状对齐"规则、掩码筛选为什么这么常用。

@@prep 开始之前
上一章的索引切片熟了就能开始，这章不用装新东西，广播和掩码要自己在数组上试。

@@goal 学到这儿就够了
能用 ufunc 和统计函数算结果、分清 dot 与 *，能写出广播和布尔掩码取数，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：ndarray 访问变换——存取与整形
**本章** ← 你在这里：数组的"算力"——计算、统计、广播、掩码，NumPy 章节收官
**下一章**：Pandas 系列开始（Series/DataFrame 的数值操作 90% 来自本章）
**再往后**：Pandas → MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路；数字统计的计算底座本章交付

@@note info 学习提示
前三章里 axis 是"取哪个方向"，本章它再次出现（统计按轴算）——**建议把上一章第 ⑩ 点再看一遍再往下**。广播（第 ⑧ 点）是本章唯一的"抽象难点"，先记结论：形状对齐、后对齐、能补 1 就补 1；掩码（第 ⑨ 点）则是数据科学使用率最高的筛选手段，务必练熟。

@@point ① 通用函数 ufunc：逐元素计算的灵魂
@@need 要解决什么
**数组 + 数组、sin、exp 这些"逐元素"运算为什么能一行完成？** 先搞懂 ufunc 概念，后面所有计算都有底。

@@idea 核心思路
通用函数（ufunc）对数组**逐元素**运算，返回同形状新数组：

```python
import numpy as np

a = np.array([1, 2, 3])
b = np.array([10, 20, 30])

a + b          # [11 22 33]（+ 是 add 的运算符形式）
np.add(a, b)   # 等价
np.exp(a)      # e^1, e^2, e^3
np.sqrt(a)     # 平方根
np.sin(a)      # 三角
```

规律：**几乎每个数学运算都有"运算符版"和"函数版"**；numpy 运算对**整块数组**一次性完成，无需循环——这就是向量化。

运算符优先级注意：`a + 1` 也是 ufunc 广播（见第 ⑨ 点），标量与数组自动对齐。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 两个长度不同的数组直接 + 报错 | 形状不兼容；要么补维度（广播）要么先对齐 |
| 忘记 numpy 函数返回新数组 | 除了 inplace 操作（如 a *= 2），其余都不改原数组 |

@@point ② 取整与三角函数
@@need 要解决什么
**round/ceil/floor 怎么取整？三角函数有没有？** 常用数学函数速查。

@@idea 核心思路

```python
import numpy as np

a = np.array([1.2, 1.7, -1.5])

np.round(a)      # [1 2 -2]：四舍五入（银行家舍入注意：-1.5 → -2）
np.ceil(a)       # [2 2 -1]：向上取整
np.floor(a)      # [1 1 -2]：向下取整
np.trunc(a)      # [1 1 -1]：向零截断

np.sin([0, np.pi/2])      # [0 1]；cos/tan/tanh/arcsin 同族
np.deg2rad(180)           # π：角度转弧度
```

注意：**np.round 默认"银行家舍入"（.5 舍向偶数）**，与 astype(int) 的截断又不同——三种舍入行为（截断/四舍五入/银行家）别混。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| round(1.5) 出来是 2 还是 1？ | np.round(1.5)=2、np.round(2.5)=2（银行家舍入）；要常规四舍五入自己加 0.5 再 floor |
| 三角函数参数用度数报错 | numpy 三角默认弧度，用 np.deg2rad 转 |

@@point ③ 算术函数：加减乘除幂模
@@need 要解决什么
add/subtract/multiply/divide/power/mod——**函数版数学运算**，是 ufunc 的官方命名。

@@idea 核心思路

```python
import numpy as np

a = np.array([10, 8, 6])
b = np.array([2, 4, 3])

np.add(a, b)          # [12 12 9]
np.subtract(a, b)     # [8 4 3]
np.multiply(a, b)     # [20 32 18]
np.divide(a, b)       # [5 2 2]
np.power(a, 2)        # [100 64 36]：幂（平方）
np.mod(a, 3)          # [1 2 0]：取余
```

除零注意：**numpy 的 0 除不抛异常，出 inf/nan**（`np.inf` 无穷、`np.nan` 非数）——这是数据分析里"脏数据"的一大来源，后面 Pandas 章节专门处理。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 除 0 没报错但结果有 inf/warning | numpy 设计如此；计算前先过滤 0 或事后清理 inf/nan |
| power 与 ** 混用 | np.power(a, 2) 等价 a**2，无区别；注意 2 是幂次不是倍数 |

@@point ④ 统计函数：mean / median / std 全家
@@need 要解决什么
**求均值、中位数、标准差**——统计分析的三大件，注意它们各自对 NaN 的态度。

@@idea 核心思路

```python
import numpy as np

a = np.array([[1, 2, 3], [4, 5, 6]])

np.mean(a)          # 3.5：均值
np.median(a)        # 3.5：中位数（更抗离群值）
np.std(a)           # 1.7078：标准差（默认总体，ddof=1 样本）
np.var(a)           # 2.9167：方差
np.sum(a)           # 21：总和
np.min(a) / np.max(a)   # 1 / 6

np.mean(a, axis=0)  # [2.5 3.5 4.5]：按列均值（消行维）
```

**面对 NaN 的坑**：mean/median 遇到 NaN 直接返回 NaN；要跳过要用 `np.nanmean/np.nanmedian`——数据清洗前统计全是 NaN，你会在 Pandas 章节再次撞见。

均值和中间数的选择：**有离群值、要稳健 → 中位数；正态分布常规统计 → 均值**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 数据里有 NaN 统计出来全 NaN | 用 nanmean/nanmedian/nanstd 跳过 NaN |
| std 公式好像不对 | numpy 默认总体标准差（除 n）；样本标准差用 ddof=1 |

@@point ⑤ 极值与去重：argmax / argmin / unique
@@need 要解决什么
**最大值在哪、最小值在哪、有哪些不同的值**——三个高频"找点"操作。

@@idea 核心思路

```python
import numpy as np

a = np.array([3, 1, 4, 1, 5, 9, 2, 6])

np.max(a)          # 9：最大值
np.argmax(a)       # 5：最大值所在下标
np.argmin(a)       # 1：最小值所在下标
np.sort(a)         # [1 1 2 3 4 5 6 9]：排序（返回新数组）
np.unique(a)       # [1 2 3 4 5 6 9]：去重 + 排序
```

数据科学常用组合：**先 argmax 找"哪个样本最大"，再 unique 看"一共几种取值"**。

排序认知：

- `np.sort(a)` 不改原数组；
- 多维 `np.sort(a, axis=1)` 每行排序；
- **argsort** 返回排序后的下标（重排附件数据时用）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| sort 后原数组没变 | sort 默认返回新数组；原地用 a.sort() |
| argmax 和 max 混 | max 是值、argmax 是下标；"位置"问题一律 arg 开头 |

@@point ⑥ dot：矩阵乘法（与 * 不同！）
@@need 要解决什么
**矩阵乘法**（线性回归、神经网络的本质运算）——`*` 是逐元素乘，`dot` 是真正的矩阵乘，**两者天差地别**。

@@idea 核心思路

```python
import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

A * B                # 逐元素乘：[[5 12] [21 32]]（Hadamard 积）
A.dot(B)             # 矩阵乘：[[19 22] [43 50]]
np.dot(A, B)         # 等价
A @ B                # 现代写法（Python 3.5+ 运算符）最推荐
```

矩阵乘的维度规则：**A(2x3) @ B(3x4) → (2x4)**，中间维 3 必须相等（内积），这是"配型"；

向量特例：

```python
v = np.array([1, 2, 3])
w = np.array([1, 1, 1])
v @ w        # 6：点积（结果标量）——相关性的基础
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 * 做矩阵乘，结果全乱 | * 是逐元素；矩阵乘用 @ 或 dot |
| 维度配不上报错 | 检查中间维：A(2,3)@B(3,4) 中间都是 3 才行 |

@@point ⑦ sort / argsort：排序与排序下标
@@need 要解决什么
排序不只要结果，**还常常要"取回排序后的位置"**（如按成绩排列学生名字）——argsort 给出下标。

@@idea 核心思路

```python
import numpy as np

scores = np.array([85, 92, 78, 90])
names = np.array(['张', '王', '李', '赵'])

order = np.argsort(scores)      # [2 0 3 1]：从低到高的位置
names[order]                    # ['李' '张' '赵' '王']：成绩对应姓名重排
```

用法精髓：**argsort 把"排序顺序"借给别的数组**——成绩排序学生名单、特征重要性排序特征名。

反序与多列：`np.argsort(-scores)` 从高到低；二维 `argsort(axis=1)` 每行排序。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| argsort 结果看着"没排序" | 返回的是下标不是值；用 names[order] 才看到结果 |
| 想要降序 | 对 scores 取负 argsort(-scores)，或 sort 后 [::-1] |

@@point ⑧ broadcast 广播：形状对齐机制
@@need 要解决什么
**一个 (3,1) 的数组和 (1,4) 的数组能直接相加？** 形状不同为什么能算？——广播规则就是 numpy 的"自动扩展"。

@@idea 核心思路
广播规则（从后往前逐维对齐）：

```text
1. 形状从最后一个维度开始比较；
2. 维度相等 或 其中一个是 1（或缺失）→ 可扩展对齐；
3. 都大于 1 且不等 → 广播失败报错。
```

```python
import numpy as np

a = np.array([[1], [2], [3]])        # (3,1)
b = np.array([10, 20, 30, 40])       # (4,) → 视为 (1,4)

a + b        # 成功：(3,1)+(1,4) → (3,4) 广播扩展为同形状
```

```python
# 报错例子：(3,2) 与 (4,) → 第 1 维 2 vs 4 都不为 1 且不等 → 失败
c = np.ones((3, 2))
# c + np.array([1, 2, 3, 4])   # ValueError
```

记忆口诀：**"从后对齐，能补 1 就补 1，全不匹配就报错"**。广播是 ufunc、掩码、后续 Pandas 运算的地基算法。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 广播莫名报错 | 打印两数组 .shape 从末尾对齐比一遍，找"双不为 1 且不等"的维 |
| 以为广播是"复制数据" | 它是逻辑扩展、不真占内存，所以快；理解成"虚拟对齐"即可 |

@@point ⑨ 掩码（布尔索引）：按条件挑数据
@@need 要解决什么
**"把 >5 的元素挑出来、把所有偶数过滤出来"**——条件筛选是数据科学第一高频操作，掩码就是它的 numpy 形态。

@@idea 核心思路

```python
import numpy as np

a = np.arange(10)

mask = a > 5          # [False False ... True True True True]
a[mask]               # [6 7 8 9]：掩码为 True 的位置
a[a > 5]              # 一步写法，等价
a[(a > 2) & (a < 8)]  # 与条件：& 表示且（不是 and！）
a[(a == 0) | (a == 1)]  # 或条件：| 表示或
```

关键规矩：

- **对数组做比较得布尔数组**（掩码）；
- 掩码可直接当索引 **a[mask]**；
- 多条件**必须用 & 和 |**（运算符），不能用 Python 的 and/or（会报"truth value ambiguous"）——这是新手第一高频报错。

统计配搭：`(a > 5).sum()` 数满足条件个数、`a[a > 5].mean()` 条件组均值。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| a > 5 and a < 8 报 ValueError | numpy 数组不支持 and/or，改用 `&`（且）/ `\|`（或），且外层加括号 |
| 掩码形状和数组不匹配 | 掩码必须与对应维度长度一致（广播规则见上一点） |
| 比较结果"看不到 True/False" | 打印掩码确认；条件写反改符号即可 |

@@summary
这一章，NumPy 的"算力"全交付：

| 能力 | 关键 API | 一句话 |
|---|---|---|
| 逐元素运算 | ufunc：add/exp/sin/sqrt | 向量化，无循环 |
| 数学函数 | round/ceil/floor、三角 | 注意三种"舍入"行为 |
| 算术 | add/subtract/multiply/divide/power/mod | 除 0 得 inf/nan 不报错 |
| 统计 | mean/median/std/var/sum | 有 NaN 用 nan 前缀版 |
| 极值与去重 | max/argmax/unique | arg 开头是下标 |
| 矩阵乘 | @ / dot（* 是逐元素！） | 中间维必须相等 |
| 排序 | sort / argsort | argsort 下标记姓名重排 |
| 广播 | 形状对齐规则 | 从后对齐、补 1 |
| 掩码 | a[a > 5] 布尔索引 | `&` / `\|`（别写成 and/or） |

一句话记住本章：**统计用 mean 族、矩阵乘用 @、筛选用掩码 a[条件]、排序下标用 argsort——再配合"广播从后对齐"的规则，NumPy 的计算能力就是你的了；下一章开始，Pandas 的所有列运算都站在这里。**

@@quiz
1. 为什么说 numpy 运算"向量化"？ufunc 的典型行为是什么？
2. np.round、np.floor、astype(int) 三种"取整"行为一样吗？各是什么？
3. 数组除以 0 会报错吗？结果是什么？写程序时该怎么办？
4. 数据里包含 NaN 时，mean 和 nanmean 的行为有什么不同？
5. np.argmax(a) 返回的是什么？和 max(a) 的区别是什么？
6. A * B 与 A @ B 分别是什么运算？维度配型规则是什么？
7. argsort 返回什么？举一个用它"按成绩重排姓名"的例子。
@@links
参考|numpy （68 页）|#
工具|NumPy 官网|https://numpy.org/
文档|NumPy 广播官方说明|https://numpy.org/doc/stable/user/basics.broadcasting.html