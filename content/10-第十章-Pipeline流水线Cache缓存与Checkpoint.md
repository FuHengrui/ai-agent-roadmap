@@h1 第十章　Pipeline 流水线、Cache 缓存与 Checkpoint
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　6 课时　|　难度 ★★★☆

@@why 这一章在解决什么问题
上一章讲了"一个 Stage 内的窄依赖算子可以连续跑"——但什么叫连续跑？为什么能快？这背后是 **Pipeline 流水线机制**。而第二个用户体验差到爆的问题：**重复计算**——同一段数据被多个 Job 用，每个 Job 都从头算一遍，慢得离谱。解决它的两把钥匙是 **Cache（缓存）** 与 **Checkpoint（检查点）**，但这两个东西长得像、用法完全不同：`cache()` 只是把数据放内存；`checkpoint()` 会把数据落盘**并且切断血缘**。选错了，要么内存白占、要么多一次全量 IO。

学完这一章，你能：**为"这段数据要被复用"的场景，正确选择 Pipeline/Cache/Checkpoint 三种手段，并解释各自的代价**。

@@map 这一章在整个知识库里的位置
上一章：内核第一块（Job/Stage/Task、宽窄依赖、shuffle 机制）
**本章** ← 你在这里：内核第二块——Pipeline 执行、缓存三兄弟（cache/persist/checkpoint）
下一章：内核第三块——并行度设置、广播变量、累加器
再往后：实战项目（UV/PV、二次排序、卡口统计）→ SparkSQL → Streaming
阶段终点：能独立写出"性能心里有底"的 Spark 程序

@@point ① Pipeline 流水线：一个 Stage 内的"无间道"执行
@@need 要解决什么
"map→filter→map 连成一个 Stage"这句话背后的执行真相是什么？**为什么大数据框架爱讲 pipeline 而 Hadoop 被人诟病"慢在半路落盘"？** ——因为 Spark 的窄依赖链可以**一个 Task 从头到尾算完，中间不落盘**。这是 Spark 比 Hadoop MapReduce 快的关键之一，必须讲明白。

@@idea 核心思路
**Pipeline = 一个 Task 处理一个分区时，把该 Stage 内所有算子按顺序一口气算完**（数据在内存里逐算子流转，不写磁盘）：

```text
一个分区 P 进入 Task 后：
P 读取 → map(清洗) → filter(剔除) → map(格式化) → 输出
         ↑ 全程内存中流转，无落盘、无网络，一气呵成

如果有 3 个分区、3 个 Task，3 个 Task 并行各跑各的 pipeline
```

**对比 Hadoop MapReduce**（理解差距）：

```text
Hadoop： map 落盘 → sort 合并落盘 → reduce 读盘    每个阶段都写一次磁盘
Spark：  窄依赖链一次算完不落盘；只有 shuffle 边界才落盘
```

**Pipeline 生效的前提**：Chain 内**全部是窄依赖算子**。一旦中间出现宽依赖（shuffle），就必须"上游 Stage 全部算完落盘"，下游才能开始——流水线在这里断开。

**理解后的推论**：你在 map 里写的每个昂贵操作（建连接、正则、加解密）都会被 pipeline 里的每个元素执行一遍——所以"连接放 mapPartitions、代价高的算子前置"这类优化，本质都是在"给流水线减负"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为每个算子都是"算完一个再算下一个" | 一个 Stage 内是**合并执行**，不是算子间落盘。这也是为什么中途看不到"中间 RDD"——它们只是流水线上的瞬时数据 |
| 想验证每个算子的中间结果 | 用 `take(n)` 在链上打断（断点）看，或者写两个 Job 单独算。正常 pipeline 里没有中间产物可查 |
| 流水线里有一步阻塞全链 | 窄依赖链是串在一个分区上的，某元素处理慢=该分区整个 Task 慢。这就是"个别脏数据拖垮全分区"的原因之一（加 filter 前置或容错处理） |
| 混淆 Pipeline 与"并行" | Pipeline 是**单分区内**的算子合并（时间上的连续），并行是**多分区**同时跑（空间上的并发）。两个维度别搞混 |

@@point ② 重算与容错：血缘是"后悔药"，但救命也花钱
@@need 要解决什么
Executor 挂了、数据丢失了，Spark 怎么办？——**从血缘链重算**。这个机制救了命，但也带来一个经典痛点：**长血缘全量重算巨慢**。什么时候重算、什么时候靠缓存/检查点兜底，是这一点的主题。

@@idea 核心思路
**容错流程**：

```text
某 Task 失败/Executor 挂 → TaskScheduler 重试（默认 3 次）
   ↓
重试仍失败但数据可重算 → Stage 内丢失的分区按血缘重新计算
   ↓
只有源头也不可用（data 文件在 HDFS 且还在）才真失败
```

**重算的代价规律**：

| 血缘链特征 | 重算代价 |
|---|---|
| 短链（2-3 个算子） | 小，可忽略 |
| 长链（20+ 算子，多 shuffle） | 大——上游 shuffle 都要重跑一遍（重新写盘+网络） |
| 数据源超大 | 大——从文件系统重新读全量 |

**三种"防重算"手段的定位**（本章后三个知识点展开）：

```text
cache()       → 内存缓存，防"同一数据被多个 Job 重复算"
persist(级)   → 更细粒度：内存/磁盘/副本，延长生命周期
checkpoint()  → 磁盘持久化 + 切断血缘，免疫"长链重算"灾难
```

**判断口诀**：短链无所谓 → 中链被多 Job 复用 → cache；长链或要容灾 → checkpoint（会吃一次落盘 IO，值得）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 重试 3 次还失败还不放弃 | 检查是不是**确定性错误**（代码 bug/脏数据导致 NPE）——重试无用，直接看堆栈修代码 |
| 长血缘 + 无缓存，重启一次等 10 分钟 | 每次失败都从源头全量重算。中间结果加 checkpoint，让"重算起点"靠近下游 |
| Executor 换了机器，缓存全失效 | 缓存是存在 Executor 本地的！新 Executor 没缓存 → 只能重算。这正是"要跨节点容错必须 checkpoint（落盘可恢复）"的原因 |
| 以为容错是"日志回放" | 不是。Spark 容错=血缘重算（重新执行算子），不是日志恢复。所以血缘链上的每一步都必须"可重放"（纯函数，无外部副作用）——在 map 里写文件/改全局变量会破坏这一点 |

@@point ③ Cache 缓存：把"热数据"留在内存
@@need 要解决什么
同一个 RDD 要被 3 个 Job 各用一次——不缓存就**重算 3 遍**。cache 的本质是：**第一次算完把结果留在 Executor 内存，后续 Job 直接用，杜绝重复计算**。90% 的性能优化第一板斧就是它。

@@idea 核心思路
```scala
val labeled = raw.map(parse).filter(valid)
labeled.cache()                 // 标记缓存（Memory 级别）

// 触发点：cache 是转换！要到第一个行动算子才真正"算并存下"
println(labeled.count())        // 第一次：计算 + 写入内存
println(labeled.count())        // 第二次：直接读缓存，不重算
```

**三个必须知道的细节**：

1. **`cache()` 惰性**：它只是打个"要缓存"的标记，真正缓存发生在第一个行动算子执行时
2. **默认级别 = MEMORY_ONLY**：只放内存，内存不够的分区直接不缓存（下次仍重算）
3. **数据在 Executor 内存**：每个 Executor 存自己那部分分区。UI 的 **Storage Tab** 能看到缓存占用

```text
memory_only 内存不够时：装不下的分区"偷懒不缓存"
              → 该分区下次照样重算（不是报错！）——白配 cache 的人最容易踩这坑
```

**释放**：`labeled.unpersist()` 主动释放，或等 Executor 内存压力自动淘汰（Least Recently Used）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 调了 cache() 却发现没用（Storage Tab 空的） | 忘了跟一个行动算子！cache 是惰性标记，没行动算子=永远不真正缓存 |
| 内存不够时无提示，缓存"部分失效" | 默认 MEMORY_ONLY，放不下的分区**静默不缓存**。压力大就换磁盘级别（下一知识点） |
| 缓存的数据被 GC/淘汰 | 内存压力大时 Spark 会自动淘汰缓存（LRU）。重要数据用 `MEMORY_AND_DISK`，至少落盘不丢 |
| 每个 Job 都想 cache | 缓存占用内存，太贪心反而**挤掉 Executor 的计算内存**（GC 升高）。只缓存"会被多次使用"且"算得贵"的 RDD |

@@point ④ persist：cache 的"可调档"版本
@@need 要解决什么
cache 只有一档（MEMORY_ONLY）——不够用。要"内存+磁盘""只磁盘""带副本"怎么办？**persist(StorageLevel) 让你精确控制缓存策略**。12 种级别记不住没关系，**常用的就 4 种**，本点给你一张决策表。

@@idea 核心思路
```scala
import org.apache.spark.storage.StorageLevel

rdd.persist(StorageLevel.MEMORY_ONLY)        // 内存，不够就不缓存（=cache()）
rdd.persist(StorageLevel.MEMORY_AND_DISK)    // 内存优先，放不下落盘（常用！）
rdd.persist(StorageLevel.DISK_ONLY)          // 只磁盘，省内存但慢
rdd.persist(StorageLevel.MEMORY_AND_DISK_2)  // 上面+2 份副本（容灾）
```

**四档决策表**：

| 级别 | 放哪 | 内存够时 | 内存不够时 | 适用 |
|---|---|---|---|---|
| MEMORY_ONLY | 内存 | 快 | **不缓存，重算** | 数据小、内存足 |
| MEMORY_AND_DISK | 内存→磁盘 | 快 | 落盘，不重算 | **默认推荐** |
| DISK_ONLY | 磁盘 | 慢 | 慢（磁盘） | 数据大、几乎不热 |
| ..._2 系列 | +副本 | 快 | 落盘 | 节点易挂、要容灾 |

**命名规律**：`存储位置_存储位置_副本数`。MEMORY_AND_DISK_2 = 内存优先、磁盘兜底、两份副本。

**与 cache 的关系**：`cache() == persist(MEMORY_ONLY)`，纯语法糖。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 记不住 12 种级别 | 只记 4 个常用档 + 命名规律即可，其它（MEMORY_ONLY_2 等）按规律推 |
| 用了 MEMORY_AND_DISK 还慢 | 说明大量分区落盘了——本质是内存预算不够。看 Storage Tab 的"磁盘占用"比例，要么加大 Executor 内存，要么减少同时缓存的数据 |
| persist 之后忘记取消 | 缓存一直在占内存。用完 `unpersist()` 释放，尤其长作业 |
| 把 DISK_ONLY 当"防丢"用 | DISK_ONLY 只防"内存不够"，不防"节点故障"（本地盘会丢）。真容灾要 _2 副本或 checkpoint（HDFS 多副本） |

@@point ⑤ Checkpoint：落盘 + 断血缘的"终极保险"
@@need 要解决什么
cache/persist 解决"重复计算"，但**解决不了长链重算**：Executor 挂掉，缓存随节点一起没了，还得从源头重算 20 步算子。**checkpoint 把中间结果写进可靠存储（HDFS），并切断血缘**——之后的重算只从检查点开始，且节点故障也不怕。代价是一次全量落盘 IO。

@@idea 核心思路
```scala
sc.setCheckpointDir("hdfs://.../ckpt/")   // ① 先设检查点目录
rdd.map(...).filter(...)...                // 数据链
rdd.checkpoint()                           // ② 标记检查点
rdd.count()                                // ③ 行动算子：先算完，把结果落盘到 HDFS，然后切断血缘
```

**checkpoint 的三步动作（在一个行动算子触发时完成）**：

1. **计算**：正常算完该 RDD
2. **落盘**：把每个分区写入 checkpoint 目录（是可靠存储，如 HDFS，天然多副本）
3. **断链**：此后该 RDD 的血缘被替换成"我从 checkpoint 读"，上游算子链被截断

```text
断链前：textFile → 20 步算子 → rdd      （重算=20 步全跑）
断链后：checkpoint 数据 ──→ 后续算子     （重算=只读一次盘）
```

**和 persist(DISK_ONLY) 的本质区别**（面试爱问）：

| | persist(DISK_ONLY) | checkpoint |
|---|---|---|
| 存储位置 | Executor 本地磁盘 | HDFS/可靠存储（多副本） |
| 血缘 | **保留**，缓存失效仍重算全链 | **切断**，重算起点=检查点 |
| 容灾 | 节点挂=数据丢 | 节点挂不怕（副本在别处） |
| 用途 | 防重复计算 | 防长链重算 + 容灾 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| checkpoint 前没设目录直接报错 | 必须 `sc.setCheckpointDir(...)` 先设置，否则 `checkpoint()` 抛异常 |
| checkpoint 后血缘没断，还在全量重算 | 检查是否真的触发了：checkpoint 跟 cache 一样是**惰性标记**，必须有一个行动算子真正执行完才算完成断链 |
| 忘了 checkpoint 是一次"写"而不是"只读" | 它先把 RDD 算一遍再写盘——**多一次全量 IO**。只在"长链/要容灾"时用，别处处 checkpoint |
| 本地模式 checkpoint 到哪 | 本地跑要设本地目录（`file:///tmp/ckpt`），但生产必须在 HDFS/对象存储，否则没有多副本意义 |

@@point ⑥ 三兄弟对比：Pipeline / Cache / Checkpoint 怎么选
@@need 要解决什么
三个机制都讲完了，最实用的问题来了：**我到底该用哪个、什么时候用？** 本节给出一张"决策流程图"，覆盖日常 90% 场景，照着走就不会错。

@@idea 核心思路
```text
这段数据会被多个 Job 复用吗？
 ├─ 不会 → 什么都不用做（Pipeline 已经最优）
 └─ 会 →
      ├─ 数据量小、内存够 → cache()（MEMORY_ONLY）
      ├─ 数据量较大 → persist(MEMORY_AND_DISK)
      ├─ 数据很大、几乎不用 → 不缓存（重算更省）
      └─ 血缘链超长(20+步/多shuffle) 或 要防节点故障
           → 先 persist(MEMORY_AND_DISK) 再 checkpoint()
              （persist 缓存加速再 checkpoint 落盘，两不误）
```

**典型最佳组合**（长链且复用）——"先缓存后检查点"：

```scala
rdd.cache()          // ① 缓存：让 checkpoint 的"计算+写盘"更快
rdd.checkpoint()     // ② 检查点：落盘+断链
rdd.count()          // ③ 触发：算→写缓存→写 checkpoint→断链
```

**反面教材**（别学）：

- 只 cache 不 checkpoint，集群重启后缓存全丢、长链全重算
- 只 checkpoint 不 cache，每次 checkpoint 都要全量重算再写（白跑两遍）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| cache 和 checkpoint 都设了却仍慢 | 顺序必须**先 cache 后 checkpoint**，且用同一个行动算子触发。先算完写内存再落盘，省一次全量计算 |
| UI 上缓存占比 90% 还在重算 | 缓存被淘汰了（Storage Tab 看绿色是否还在）。数据是"热"但内存小，考虑 MEMORY_AND_DISK / 加内存 |
| Spark 2.x 起 `checkpoint` 在 DataFrame 不生效 | RDD 的 checkpoint 有效；DataFrame 要 `df.createOrReplaceTempView` 后重新读。碰到"检查点好像没跑"先确认 API |
| 为了"保险"全链 checkpoint | 每个廉价中间结果都 checkpoint = 无数落盘 IO，比不 checkpoint 还慢。**只有在"贵 + 复用 + 长链"三个条件都占时才值得** |

@@point ⑦ 缓存反模式：什么时候 cache 反而更慢
@@need 要解决什么
"缓存不是免费的"——**配错 StorageLevel / 缓存对象过大 / 内存被驱逐**时，cache 后可能比不 cache 更慢。识别这些"缓存反模式"，避免好心办坏事。

@@idea 核心思路
**三个常见的"缓存白用"场景**：

```text
① MEMORY_ONLY 但对象太大 → 放不下 → 部分分区被丢弃 → 用到时反复重算（比不缓存还慢）
② 缓存 + 序列化开启但序列化本身很贵 → Kryo 快但 GC 压力换成了序列化 CPU
③ 缓存了"只用一次"的数据 → 白白占内存，还把别的热数据挤出去
```

**正确姿势**（决策三步）：

| 问题 | 答案 |
|---|---|
| 这个 RDD 会被用几次？ | ≥2 次才值得缓存；1 次缓存=纯浪费 |
| 内存够放吗？ | 不够就用 MEMORY_AND_DISK（多一次磁盘兜底，少一次重算） |
| 数据多大？ | 大对象优先 MEMORY_AND_DISK_SER（序列化省内存，代价是 CPU） |

**验证"缓存有没有生效"**：UI 看 Storage 页的缓存占比；如果内存缓存总是 0 或反复被驱逐，就是白 cache。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 缓存后跑得更慢了 | 数据集只用一次，或 MEMORY_ONLY 放不下反复驱逐重算。先确认"用了几次"再 cache |
| Storage 页显示缓存为 0 | 内存不足被驱逐。换 MEMORY_AND_DISK 或调大 executor 内存 |
| 序列化缓存反而慢 | 大对象序列化时 CPU 成瓶颈；对比 Kryo 序列化（spark.serializer 配 KryoSerializer）后重测 |
| cache 后懒执行没生效 | cache 是 transformation，**要一个 action 触发它才真正缓存**；别在 cache 后什么都不做就以为缓上了 |

@@point ⑧ 迭代实战：Cache + Checkpoint 的组合拳
@@need 要解决什么
机器学习/图算法的迭代训练里"每轮都复用同一批数据"：**不缓存=每轮全量重算；光缓存=长血缘链越挂越长、难释放**。组合拳怎么打，是实战高频问题。

@@idea 核心思路
**迭代循环的标准姿势**：

```scala
// 训练数据每轮都用 → 缓存它
val trainData = raw.filter(...).cache()   // ① 每轮复用的数据缓存
trainData.count()                          // ② 触发缓存真正落内存

for (i <- 1 to 100) {
  val result = trainData.map(...).reduce(...)  // 每轮复用缓存数据
  if (i % 10 == 0) {
    result.checkpoint()                      // ③ 每 10 轮断一次血缘
    result.count()                           // ④ 触发 checkpoint 真正落盘
  }
}
```

**为什么每 N 轮 checkpoint**：

```text
不 checkpoint：血缘链随迭代越来越长 → 崩溃后重算要从头推整条链（灾难）
每 10 轮 checkpoint：把"当前结果"固化成独立文件，血缘从这截断
  → 崩溃后只需从最近检查点恢复（重算 ≤10 轮），而不是从头
```

**组合拳结论**：**每轮复用→cache；阶段结果→checkpoint**。两个一起用：缓存保"本轮快"，检查点保"崩溃恢复快"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 迭代 100 轮崩溃后重算卡死 | 没 checkpoint，血缘 100 层从头推。每 N 轮 checkpoint 一次（N≈10） |
| 每轮都 checkpoint 卡 IO | checkpoint 是落盘的，太频繁磁盘成瓶颈。间隔至少缓存/聚合几轮再做 |
| checkpoint 后数据还占内存 | checkpoint 不自动 unpersist；迭代结束记得 `unpersist()` 释放 |
| 缓存和 checkpoint 都忘了触发 | 两者都是懒的：`count()`/action 触发后才真正缓存/落盘。只调用 API 不触发=白配 |

@@summary
这一章你实际拿到的是**两把钥匙 + 一张体检单**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **Pipeline 视角**：Stage 内存接力、省 I/O 的原理与代价 | 看懂 Spark 为什么快，调优不瞎试 |
| **Cache / Checkpoint 双保险**：什么时候缓存、什么时候断血缘 | 长动作快 10 倍，短动作不浪费内存 |
| **调优决策表**：缓存快照 vs 检查点、各 StorageLevel 怎么选 | 面试高频题、线上性能问题的第一反应 |

@@quiz
1. Pipeline 是什么？它要求 Stage 内算子满足什么条件才能生效？
2. `rdd.cache()` 之后为什么 Storage Tab 还是空的？什么时候才真正缓存？
3. MEMORY_ONLY 与 MEMORY_AND_DISK 的内存不够时各自行为是什么？
4. checkpoint 和 persist(DISK_ONLY) 的三点本质区别是什么？
5. 一条 25 步算子的价值链被两个 Job 各自使用，选 cache+checkpoint 组合还是单一手段？为什么？
6. 判断题：checkpoint 之后该 RDD 的血缘链被截断，重算时直接从检查点开始。

@@links
讲义|Spark 内核进阶（第 3 章：Pipeline 计算）|#
讲义|Spark 内核进阶（第 4 章：Cache 与 CheckPoint）|#
官网|RDD 持久化官方文档|https://spark.apache.org/docs/latest/rdd-programming-guide.html#rdd-persistence
官网|Spark 配置（内存相关）|https://spark.apache.org/docs/latest/configuration.html#memory-management