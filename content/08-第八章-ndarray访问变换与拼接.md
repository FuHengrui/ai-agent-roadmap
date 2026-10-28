@@h1 第八章　ndarray 访问、变换与拼接
@@sub 阶段 17 · 数据科学与智能分析基础　|　数值计算　|　难度 ★★☆

@@why 这一章在解决什么问题
**数组建好了，接下来全是数据科学日常操作：取某行某列、切片、重排形状、拼接、切分、转置。** 这些动作 Pandas 里天天见，但底子是 numpy 这一套。更关键的是**"视图 vs 副本"这个坑**：改了切片，原数组神秘跟着变——不懂这个，你会 debug 到怀疑人生。

这一章把 ndarray 的**取数、变形状、拼与拆、转置**四大类操作一次讲清。学完你能回答：一维/二维切片怎么写、视图和副本什么区别、reshape 和 transpose 谁改变内存、concatenate 和 hstack 什么关系、split 怎么切出指定块。

@@prep 开始之前
上一章的数组会建就能开始，这章不用装新东西，切片和 reshape 要动手敲。

@@goal 学到这儿就够了
能取出行列切片、分清视图和副本，能 reshape、拼接、转置并说清 axis 指哪个方向，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：NumPy 数组创建——arrays 出生
**本章** ← 你在这里：数组的存取与整形——取行取列、重排拼接
**下一章**：NumPy 计算、统计与进阶——算术/统计/矩阵乘/广播/掩码
**再往后**：Pandas（存取逻辑直接迁移到 Series/DataFrame）→ MySQL
**阶段终点**：完成"读数据 → 清洗 → 计算 → 可视化 → 入库"链路

@@note info 学习提示
本章操作密集，**建议每段代码都在 Jupyter 里跑完再看答案**。重点盯三类"形状变化"操作：reshape（改形状不改逻辑序）、transpose（换轴）、concatenate（拼接）——它们对应数据科学里最常见的三种"整形"诉求。

@@point ① 一维索引与切片
@@need 要解决什么
一维数组怎么取单个元素、怎么取连续一段、怎么跳着取？

@@idea 核心思路

```python
import numpy as np

a = np.arange(10)          # [0 1 2 3 4 5 6 7 8 9]

a[0]         # 0：第 1 个
a[-1]        # 9：倒数第 1 个
a[2:5]       # [2 3 4]：含 2 不含 5
a[::2]       # [0 2 4 6 8]：每隔 1 个取（步长 2）
a[::-1]      # [9 ... 0]：反转
```

记忆口诀：**切片 a[起:止:步长]，"含头不含尾"**，负索引从末尾数，步长可为负（反转）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| a[2:5] 只有 3 个元素 | 含头不含尾；想要 5 就切到 6 |
| 下标越界 IndexError | 单元素索引越界报错；切片越界不报错（自动截断到边界） |

@@point ② 二维索引与切片
@@need 要解决什么
**取某一行、某一列、某块区域**——二维数组的索引规则和 Excel 表格思维一致。

@@idea 核心思路

```python
import numpy as np

a = np.arange(12).reshape(3, 4)
# [[ 0  1  2  3]
#  [ 4  5  6  7]
#  [ 8  9 10 11]]

a[0]            # 第 0 行：[0 1 2 3]
a[1, 2]         # 第 1 行第 2 列：6
a[:, 1]         # 所有行的第 1 列：[1 5 9]
a[1:, :2]       # 第 1-2 行、前 2 列：[ [4 5], [8 9] ]
```

规则：**a[行, 列]**，逗号前管行、逗号后管列；`:` 表示"这一维全要"。列切片 `a[:, 1]` 是数据科学出现率最高的操作（取一列特征）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| a[1,2] 和 a[1][2] 结果一样但建议用哪种 | 前者标准。a[1][2] 两步取也能用但要连续索引 |
| 取一列出来是 1 维还是 2 维 | a[:, 1] 是 1 维；要保留列维度写 a[:, 1:2] |

@@point ③ 视图与副本：切片是视图
@@need 要解决什么
**改了切片，原数组居然跟着变了！** 这不是 bug，是 numpy 的"视图（view）"机制——本章最重要的坑。

@@idea 核心思路

```python
import numpy as np

a = np.arange(5)
b = a[1:4]          # 切片 → 视图（不是复制）

b[0] = 99
print(a)            # [0 99 2 3 4]：原数组跟着变了！
```

规则：

- **切片（基本切片）= 视图**：共享底层内存，改视图影响原数组；
- **c = a.copy()**：真副本，改副本不影响原数组；
- 方括号里用整数数组/布尔掩码（高级索引）= **副本**（不共享）。

记忆：**"切片省内存、复制保安全"**。要修改原数组就放心用视图；要保留原数组历史就 copy。

```python
c = a[:].copy()     # 显式复制后随便改
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 修改切片后原数组"灵异变化" | 正常机制！切片=视图共享内存；不需要联动就 .copy() |
| 高级索引（掩码）改了一样的现象 | 掩码/花式索引是副本，不联动；两类行为不一样，别混记 |

@@point ④ reshape：重排形状
@@need 要解决什么
**数据个数不变，只是换个"形状"排布**（一维拉成二维、二维展成三维批次……）——reshape 全搞定。

@@idea 核心思路

```python
import numpy as np

a = np.arange(12)
b = a.reshape(3, 4)       # 12 个元素排成 3x4（行优先填充）
c = a.reshape(2, 2, 3)    # 三维：2x2x3
d = a.reshape(-1, 4)      # -1 自动算：行数 = 12/4 = 3
```

要点：

- **元素总数必须整除**：12 → 3x4 可以，3x5 报错；
- **`-1` 表示"这一维自动推导"**：reshape(-1, 4) 是"不管几行，每行 4 列"；
- reshape 返回**视图**（条件允许时）或新数组，**不改原数组**（除非 reshape 到不连续内存）。

记忆：reshape 只"改包装不改内容"，一行变多行是重排布局，不是排序。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| reshape(3, 5) 报错 total size | 12 个元素凑不出 3x5=15；总个数必须相等 |
| 改 reshape 结果原数组变了 | reshape 通常返回视图共享内存；要独立就 copy |
| -1 写两处报错 | -1 只能出现一次，其余维要定死 |

@@point ⑤ ravel 与 flatten：展平
@@need 要解决什么
**多维数组"拉直"成一维**——ravel 和 flatten 都能做，区别一个讲究内存、一个不问来路。

@@idea 核心思路

```python
import numpy as np

a = np.arange(6).reshape(2, 3)
# [[0 1 2]
#  [3 4 5]]

r = a.ravel()          # [0 1 2 3 4 5]：尽量返回视图（共享内存）
f = a.flatten()        # [0 1 2 3 4 5]：总是返回副本（独立）
```

选择：**flatten 更安全（改它不影响原数组），ravel 更省内存（可能共享）**。开发调试个人代码用 flatten 不用纠结联动问题；追求极致性能的大数组用 ravel。

都按"行优先"展平（第一行拼完拼第二行），`order='F'` 可改列优先（少用）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ravel 后改坏原数组 | ravel 是视图时会联动；不想联动用 flatten |
| 展平顺序和预期不同 | 默认行优先（C 顺序）；记忆：C 语言的二维数组就是这个排法 |

@@point ⑥ concatenate：通用拼接
@@need 要解决什么
**两块数组要并起来**——concatenate 是通用拼接器，按 axis 指定沿哪根轴拼。

@@idea 核心思路

```python
import numpy as np

a = np.array([[1, 2], [3, 4]])
b = np.array([[5, 6], [7, 8]])

np.concatenate([a, b], axis=0)   # 沿第 0 轴（行）拼 → 4x2 上下叠加
np.concatenate([a, b], axis=1)   # 沿第 1 轴（列）拼 → 2x4 左右拼接
```

注意：**concatenate 要求被拼数组除拼接轴外维度一致**——axis=0 拼接时列数必须相同，axis=1 拼接时行数必须相同，否则 ValueError。

配 .shape 验证：拼接前先打印两边 shape，是排查拼接报错最快的方法。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| concat 报"axis dimension mismatch" | 除拼接轴外形状不一致；先打印 shape 对齐 |
| 传参写成 concatenate(a, b) | 正确的是列表 concatenate([a, b])，括号一层别省 |

@@point ⑦ hstack / vstack：水平与垂直堆叠
@@need 要解决什么
concatenate 还要写 axis，**"左右拼/上下拼"有没有更直白的方法？** hstack/vstack（与 column_stack/row_stack 同族）。

@@idea 核心思路

```python
import numpy as np

a = np.array([1, 2, 3])
b = np.array([4, 5, 6])

np.hstack([a, b])      # [1 2 3 4 5 6]：横向（沿列）拼
np.vstack([a, b])      # [[1 2 3] [4 5 6]]：纵向（沿行）拼
```

辅助工具：`column_stack` 把一维数组按列拼成二维（a、b 各占一列）；`row_stack` 等价 vstack。

与 concatenate 的对应：**hstack(一维=拼接, 二维=axis=1)；vstack(二维=axis=0)**——记"h 横、v 竖"就好。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| hstack 出来的形状和想的不一样 | hstack 一维是"接成一条长 1 维"，二维才是"左右拼" |
| 形状不一致报错 | 与 concatenate 同理，先查 shape |

@@point ⑧ transpose 与 T：转置
@@need 要解决什么
**行列互换**（3x2 → 2x3）——transpose() 或 .T 属性一步到位。

@@idea 核心思路

```python
import numpy as np

a = np.arange(6).reshape(2, 3)
# [[0 1 2]
#  [3 4 5]]

a.T               # [[0 3] [1 4] [2 5]]：2x3 → 3x2
a.transpose()     # 等价
a3 = np.arange(24).reshape(2, 3, 4)   # 轴序交换要三维以上才用得上
b = a3.transpose(2, 0, 1)   # 按 2/0/1 重排，形状变 (4,2,3)
```

注意：

- **转置返回视图**（共享内存）——和 reshape 一样要留意修改联动；
- 一维数组转置**不变**（没有列可换）；
- 数值计算中"矩阵乘法配型"常需要 trans 对齐维度。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 1 维数组 .T 没变化 | 正常：一维没有行列之分，原地不动 |
| 矩阵乘法维度不对 | 先转置对齐（如 (3,2)@(2,4) 中间维要相等）；见下一章 dot |

@@point ⑨ split：按份切分
@@need 要解决什么
**拼的反操作：把数组切成长度相等的几段**或按指定位置切开——split 家族。

@@idea 核心思路

```python
import numpy as np

a = np.arange(9)

np.split(a, 3)            # 均分 3 段：[0 1 2] [3 4 5] [6 7 8]
np.split(a, [2, 5])       # 按位置切：[:2] [2:5] [5:] 三段
```

等价便捷款：

- `hsplit(a, n)`：水平切分（列方向均分）；
- `vsplit(a, n)`：垂直切分（行方向均分）。

报错提醒：**均分必须能整除**——split(a, 4) 对 9 元素会报"array split does not result in an equal division"；不能整除时用 `array_split`（自动调节末尾段大小）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| split(a, 4) 报错切不均匀 | 用 np.array_split；或先取整除段再处理余数 |
| 切完的段怎么拼接回去 | 结果可直接喂 concatenate/stack 还原 |

@@point ⑩ axis 轴：所有"沿哪个方向"的钥匙
@@need 要解决什么
concat 有 axis、split 有 axis、后面 sum/mean 也有 axis——**axis 到底是什么？** 这是最后一个必须击穿的抽象。

@@idea 核心思路
**axis = 沿哪个轴去操作**。用一句话记：**axis=0 是"跨行"（沿第一维滑动）、axis=1 是"跨列"（沿第二维滑动）**。

```python
import numpy as np

a = np.arange(12).reshape(3, 4)
# [[ 0  1  2  3]
#  [ 4  5  6  7]
#  [ 8  9 10 11]]

np.sum(a, axis=0)        # [12 15 18 21]：每一列求和（跨行，结果=每列一个数）
np.sum(a, axis=1)        # [6 22 38]：每一行求和（跨列，结果=每行一个数）
a.sum()                  # 不带 axis：全部元素求和 = 66
```

理解路径：**axis 指定后，"那一维的长度"会被吃掉**——sum(a, axis=0) 后 shape (3,4)→(4,)；axis=1 后 (3,4)→(3,)。降维收缩的方向就是 axis。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| axis=0 求和却"竖着没动" | axis 是"被消掉的那一维"；axis=0 消的是行号，剩下列 |
| 三维 axis 分不清 | 从 0 数到 n-1；"消哪维看哪维"原则一以贯之 |

@@summary
这一章，数组的"存取整形"全链路打通：

| 操作 | 核心函数/语法 | 一句话 |
|---|---|---|
| 取数 | a[行, 列]、切片 [起:止:步] | 含头不含尾，负索引倒着数 |
| 视图 vs 副本 | 切片=视图、copy()=副本、高级索引=副本 | 改切片会动原数组 |
| 重排 | reshape(-1, x)/ravel/flatten | 改形状不改数据；flatten 更安全 |
| 拼接 | concatenate([a,b], axis=) / hstack / vstack | 拼前先查 shape |
| 转置 | .T / transpose() | 行列互换，返回视图 |
| 切分 | split / array_split / hsplit / vsplit | 均分要整除，不整用 array_split |
| 轴概念 | axis=0 跨行、axis=1 跨列 | 消哪维看哪维 |

一句话记住本章：**切片是视图会联动（要安全就 copy），reshape 只管包装、transpose 换轴、concat 拼接先对 shape，一切"沿哪个方向"全看 axis——数组整形从此不再迷路。**

@@quiz
1. a[2:5] 取到的是哪些元素？切片为什么不用像单元素索引那样担心越界？
2. 二维数组 a 中，取"所有行的第 2 列"的写法是什么？
3. 修改切片得到的子数组后，原数组会跟着变吗？为什么？怎么避免？
4. reshape(-1, 4) 中的 -1 是什么意思？reshape 出的结果与原数组共享内存吗？
5. ravel 和 flatten 分别返回视图还是副本？练习时建议用哪个？
6. concatenate([a, b], axis=1) 要求 a、b 的哪个维度必须一致？报错时第一步该做什么？
7. hstack 对一维数组和对二维数组的行为分别是什么？
@@links
参考|numpy （68 页）|#
工具|NumPy 官网|https://numpy.org/
文档|NumPy 索引教程|https://numpy.org/doc/stable/user/basics.indexing.html