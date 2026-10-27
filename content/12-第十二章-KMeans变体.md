@@h1 第十二章　KMeans 变体：五把手术刀修一个算法
@@sub 阶段 20 · 机器学习算法与工程实战　|　聚类算法　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章结尾列了 KMeans 的五个软肋：初始中心敏感、局部最优、怕离群点、算得慢、内存压力大。这一章逐个上"手术刀"——**五个变体，一病一刀**：

| 病 | 药 |
|---|---|
| 初始中心太差 | KMeans++ |
| 只找到局部最优 | 二分 KMeans |
| 均值被离群点拉偏 | KMedoids |
| 距离算太慢 | elkan |
| 数据太大内存爆 | Mini-Batch KMeans |

学完这一章，你对"算法发展史"会有深刻体会：**没有完美的算法，每个变体都是在时间、空间、稳定性、精度之间做一选择**。这也是机器学习工程化的常态——不是"哪个最好"，而是"现在卡在哪，选哪个解"。

@@map 上一章→本章→下一章
上一章学完 KMeans 主体（流程/距离/SSE/肘部法）并列出五条软肋。**本章逐个解决：KMedoids → 二分 KMeans → KMeans++ → elkan → Mini-Batch**。下一章接最后一块拼图：KMeans 家族搞不定的"任意形状"数据，交给密度聚类（DBSCAN/OPTICS/MeanShift）。

@@point ① KMeans 家族的技术谱系：先看全局
@@need 要解决什么
五个变体名字各异，怎么快速建立"谁治谁的病"的全局地图？

@@idea 核心思路
把 KMeans 看成一个"工厂流水线"，变体是给不同工位换零件：

| 变体 | 换掉的零件 | 治的病 |
|---|---|---|
| KMeans++ | 初始化步骤 | 初始中心差→收敛差 |
| 二分 KMeans | 整体流程（贪心分层） | 局部最优、初始敏感 |
| KMedoids | 质心定义（均值→中位数） | 离群点、非数值特征 |
| elkan | 距离计算（暴力→三角不等式） | 计算太慢 |
| Mini-Batch | 迭代方式（全量→分批） | 数据大内存爆 |

记忆口诀：**"初始不好++救，怕局部最优二分求，怕离群点上中位数，算得慢用三角不等式，内存大户走小批量。"** 每个变体的动机 = 上一章所列软肋编号，一一对应。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 五个变体名都认识，用的时候全忘 | 用"病→药"映射记忆：遇到具体痛点才出手，别五个都上 |
| 以为变体越多越好 | 每个变体引入新开销/参数；匹配场景才用 |

@@point ② KMeans++：把"随机初始"改成"概率远点"
@@need 要解决什么
原始 KMeans 随机选初始中心，运气差时几个中心挤在一团，收敛又慢又差。怎么保证初始中心"铺得开"？

@@idea 核心思路
**KMeans++** 的初始化策略（sklearn 默认开启）：
1. 第一个中心：随机选一个样本。
2. 之后每个新中心：以**正比于"到最近已有中心的距离"**的概率，从剩余样本中选——**离已有中心越远的点越容易被选中**。
3. 重复 K 次，得到"互相离得很远"的 K 个初始中心，再走标准 KMeans 迭代。

效果：初始中心天然分散，收敛更快、更稳，**大幅降低落到局部最优的概率**。实现成本极低（几乎免费），所以 sklearn 的 `KMeans(n_init='auto')` 默认就用 KMeans++。

```python
from sklearn.cluster import KMeans
km = KMeans(n_clusters=3, init='k-means++', n_init=10, random_state=42)
```
`init` 参数：`'k-means++'`（默认）或 `'random'`（完全随机，用于对照实验）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 KMeans++ 会改变迭代算法本身 | 只改**初始化**；迭代仍是"分配-更新"，别搞混 |
| 用 init='random' 生产 | 除非做对照实验，一律默认 k-means++（免费午餐） |

@@point ③ 二分 KMeans：贪心拆分的局部最优"解药"
@@need 要解决什么
KMeans 迭代只保证"局部最优"。有没有办法逼近全局最优？——把"一次分 K 簇"变成"逐个分裂"。

@@idea 核心思路
**二分 KMeans（Bisecting KMeans）**流程：
1. 先把全部数据当**一个簇**。
2. 循环 K-1 次：选当前 SSE 最大的一个簇，对它做**2-Means（K=2）**分裂成两个。
3. 重复直到簇数达到 K。

为什么有效：
- "贪心 + 从最差簇下手"：每次分裂都精确处理当前最"不内聚"的部分，很少浪费分裂机会。
- 天然对初始值不敏感：每次只做二分，2-Means 的局部最优风险比直接 K-Means 小得多。
- 结果稳定性显著高于普通 KMeans。

实现：sklearn 里对应 `KMeans` 的 `init` 可配合，或直接用聚类包里暴露的相似器；教学重点在"思想"：**复杂聚类的"分而治之"路线**。注意它仍是"球形偏好"家族，不解决形状问题。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为二分 KMeans 能聚任意形状 | 它只是更稳的 KMeans，球形偏好依旧；形状问题交给密度聚类 |
| 把"二分"理解成初始化技巧 | 它是**整体流程改写**（逐层分裂），目标函数同 SSE 但路径不同 |

@@point ④ KMedoids：用中位数治"离群点与均值"
@@need 要解决什么
均值对离群点极度敏感（一个超大值就把中心拉飞）。而且字符串/类别数据没法算均值。怎么办？——换"代表点"。

@@idea 核心思路
**KMedoids（K 中心点）**：不用"簇内均值"当中心，而是**选簇内离其他成员最近的那个真实样本**（medoid）当中心。
- 优势 1：medoid 是**真实数据点**，抗离群点（不像均值会被极端值拉走）。
- 优势 2：只要定义好"距离"，就能处理**非数值特征**（文本、类别）——均值做不到，中位数式的代表点可以。
- 代价：找 medoid 比算均值贵（要比较簇内两两距离）。

流程差异只有一步：第 3 步"更新中心"从"取平均"改为"在簇内选距离和最小的样本"。
```python
from sklearn_extra.cluster import KMedoids   # 需要 sklearn-extra 包
kmd = KMedoids(n_clusters=3, metric='euclidean', random_state=42)
kmd.fit(X)
```
（sklearn 主库暂无 KMedoids，可用 `sklearn-extra` 或 `cluster` 三方实现；教学重点是"为什么换"。）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 KMedoids 中心是"平均值点" | 是**真实样本**（原始数据中的一员），所以它抗噪也可解释（"以谁为代表"） |
| 装了 sklearn 就 import KMedoids 报错 | 在 sklearn-extra；或改用其他实现包；不要臆造 API |

@@point ⑤ elkan：用三角不等式给距离计算"减负"
@@need 要解决什么
KMeans 每轮迭代要算"每个样本到每个质心"的 m×K 次距离。数据百万级时，这是最大开销。怎么少算？（记忆点：elkan 来自提出者名字，不是"XX 算法"的缩写）

@@idea 核心思路
**elkan 优化**：基于一个初中数学事实——**三角不等式 |a-b| ≤ |a-c| + |c-b|**，为每个样本维护"到最近质心的距离上界"，直接**跳过**不可能更近的质心：
- 若"样本到当前质心的距离上界"已经小于"样本到候选质心的下界"，就不用再算这个候选质心了。
- 用 O(1) 的比较替代昂贵的距离计算，样本多、维数高时提速明显。

- 适用：样本量很大、特征稠密（欧氏距离）。
- 不适用：特征太稀疏（好处被 overhead 吃掉）、距离非欧氏（三角不等式前提不成立）。

```python
km = KMeans(n_clusters=3, algorithm='elkan')   # sklearn 默认 'lloyd'（经典版）
```
sklearn 中 `algorithm='elkan'` 或 `'lloyd'` 可选。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 elkan 当"新聚类算法" | 它是**同一算法的加速器**（优化实现），结果与经典 KMeans 等价 |
| 稀疏文本数据也开 elkan | 三角不等式剪枝在稀疏矩阵上收益小甚至变慢；稠密大数据才划算 |

@@point ⑥ Mini-Batch KMeans：把"全量迭代"改成"分批走"
@@need 要解决什么
样本达到千万级，每轮全量迭代内存和时间都爆。怎么让 KMeans 也能"大数据"？

@@idea 核心思路
**Mini-Batch KMeans**：每步只取**一小批样本**更新质心（思路与第 5 章 Mini-Batch 梯度下降同源）：
1. 随机抽一批样本（如 batch_size=100）。
2. 把这批样本分配到最近质心。
3. 用批内样本按一定学习率**部分更新**质心（新质心 = 旧质心×(1-σ) + 批均值×σ）。
4. 重复直到收敛（通常比全量少几个数量级的计算）。

```python
from sklearn.cluster import MiniBatchKMeans
mbk = MiniBatchKMeans(n_clusters=3, batch_size=100, random_state=42)
mbk.fit(X)
```
- 优点：速度快、内存友好，**支持流式/在线聚类**（数据不断来）。
- 代价：结果比全量 KMeans 略"糙"一点（每步信息不全），聚完可再用全量 KMeans 精修一轮对比。
- 参考经验：数据几十万级以下全量 KMeans 够用；百万级+ 或流式场景用 Mini-Batch。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Mini-Batch 聚得比全量更准 | 是**快**不是**准**；要求高精度先跑全量，Mini-Batch 用于规模/速度瓶颈 |
| 忽略 batch_size 参数 | 太小→质心抖动；太大→趋近全量（失去优势）；100~1000 常见区间 |

@@point ⑦ 变体对照总表：什么时候用谁
@@need 要解决什么
五个变体都学了，决策表收尾——工作里遇到具体场景到底开哪副药？

@@idea 核心思路
| 场景 | 推荐 | 理由 |
|---|---|---|
| 默认通用 | KMeans + KMeans++ | 免费改进，sklearn 默认 |
| 结果不稳定/卡局部最优 | 二分 KMeans | 贪心分裂更稳 |
| 有离群点/非数值特征 | KMedoids | 中位数式真实代表点 |
| 百万级稠密数据 | KMeans(algorithm='elkan') | 三角不等式剪枝提速 |
| 千万级/流式 | Mini-Batch KMeans | 分批在线、内存友好 |
| 球形偏好、怕离群点、初始敏感全治 | 上述自由组合 | 本质还是"球形家族"的取舍 |

一句话选型：**数据小求稳→二分；有离群/非数字→KMedoids；数据大→elkan 或 Mini-Batch；默认永远是 KMeans++。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 变体参数乱叠加（如二分+Kmedoids 同时开） | 组合有收益但要理解交互（elkan 只适用于欧氏均值版）；先单一痛点对症下药 |
| 数据是环形/月牙还在这五个里挑 | 不合用！形状问题请直接去下一章密度聚类 |

@@point ⑧ 代码实战：初始值敏感性对照实验
@@need 要解决什么
不亲眼看看"初始值影响"就白学了。写一个对照实验：同一数据，KMeans++ vs random 初始化，看结果差异。

@@idea 核心思路
```python
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

np.random.seed(1)
# 构造一个"拖尾"数据：初始中心没选好容易陷入坏解
X = np.vstack([np.random.randn(80,2),
               np.random.randn(40,2) + [6, 0],
               np.random.randn(40,2) + [0, 6]])
X = StandardScaler().fit_transform(X)

km_pp = KMeans(n_clusters=3, init='k-means++', n_init=1, random_state=0).fit(X)
km_rd = KMeans(n_clusters=3, init='random',   n_init=1, random_state=0).fit(X)

fig, ax = plt.subplots(1, 2, figsize=(10,4))
ax[0].scatter(X[:,0], X[:,1], c=km_pp.labels_, cmap='viridis'); ax[0].set_title("k-means++")
ax[1].scatter(X[:,0], X[:,1], c=km_rd.labels_, cmap='viridis'); ax[1].set_title("random init")
plt.show()
print("SSE++:", km_pp.inertia_, " SSE random:", km_rd.inertia_)
```
观察：某些数据下 random 初始化可能把两个簇的中心都"吸"到一团，SSE++ 更低——初始化的价值一眼可见。（n_init=1 关闭多次重跑，专门暴露单次初始化的差异。）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 实验里 random 结果也"挺好"就下结论"初始化无所谓" | 单次数据未必触发坏解；多换几个 seed/数据分布对比 SSE 才公平 |
| 忘了标准化就直接聚类对比 | 不标准化时俩算法都受量纲误导，对比无意义 |

@@summary
五把手术刀收工：

| 变体 | 治什么病 | 改哪里 | 代价/注意 |
|---|---|---|---|
| KMeans++ | 初始中心差 | 初始化（远点优先） | 免费午餐，默认开启 |
| 二分 KMeans | 局部最优 | 整体流程（贪心逐层 2-Means） | 仍是球形偏好 |
| KMedoids | 离群点/非数值 | 质心=簇内真实代表点 | 计算更贵，需 sklearn-extra |
| elkan | 距离计算慢 | 三角不等式剪枝 | 稠密大数据才划算 |
| Mini-Batch | 内存/速度 | 分批部分更新质心 | 略糙、可在线 |

一句话记住本章：**KMeans 的五个软肋对应五把手术刀——初始差用 KMeans++（默认开），怕局部最优用二分 KMeans，怕离群/要真点用 KMedoids，算得慢用 elkan 的三角不等式，数据大用 Mini-Batch；全是"球形家族"内的取舍，形状问题要交给密度聚类。**

@@quiz
1. 五个变体分别对应 KMeans 的哪五个软肋？
2. KMeans++ 的初始化策略核心是什么？为什么说它"免费"？
3. 二分 KMeans 为什么更不容易卡局部最优？
4. KMedoids 的质心和 KMeans 的质心本质区别是什么？各带来什么优势？
5. elkan 加速的依据是什么？什么条件下不划算？
6. Mini-Batch KMeans 与 Mini-Batch 梯度下降有什么共通思想？
7. 数据是环形结构，这五个变体该不该用？为什么？

@@links
参考|KMeans 聚类变形（6 页）|#
文档|sklearn KMeans init/algorithm 参数说明|https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html
文档|sklearn MiniBatchKMeans 文档|https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html