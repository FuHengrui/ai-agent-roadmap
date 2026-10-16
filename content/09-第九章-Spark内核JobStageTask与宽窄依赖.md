@@h1 第九章　Spark 内核：Job / Stage / Task 与宽窄依赖
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　8 课时　|　难度 ★★★★

@@why 这一章在解决什么问题
前面的章节你学会了写算子，但 Spark **内部究竟怎么把你的代码跑起来的**——没人跟你说过。这也是"能写但不会调优"的分水岭：看到报错不知道卡在哪、两个数据源 join 慢成狗不知道为什么、缓存到底该 cache 还是 checkpoint……

这一切的答案都在**执行流程**里：你写的一段程序经过三个层次被拆解——**Job（作业）→ Stage（阶段）→ Task（任务）**；而拆解的标尺是**宽窄依赖**（shuffle 边界）。这一章把这条链路从头到尾讲透：你写的 `rdd.map(...).reduceByKey(...)` 是怎么变成 DAG、怎么被切成 Stage、怎么调度到 Executor 上跑的。

学完这一章，你能：**看着 Spark UI 的 DAG 图，讲出每个 Stage 在干什么、为什么这样切、瓶颈在哪**。

@@map 这一章在整个知识库里的位置
前面三章：会创建 RDD、会用转换/行动算子写程序了
**本章** ← 你在这里：内核第一块——执行流程、Stage 划分、宽窄依赖
下一章：内核第二块——pipeline 流水线计算、cache / checkpoint 缓存与容错
再往后：内核第三块——并行度、广播变量、累加器 → 实战项目
阶段终点：能读懂进程/执行机制，为调优和面试打底

@@note info 学习提示
本章概念多但每条都能在 Spark UI 上验证——跑一遍你的 WordCount，对照 UI 上的 DAG 图和 Executor 列表看，印象深十倍。

@@point ① 三个层次：Job / Stage / Task 到底是什么
@@need 要解决什么
最让人懵的 Spark 术语就是这三个词：Job、Stage、Task。搞懂它们是理解一切执行细节的前提——它们不是同一个东西的三种说法，而是**层层拆解的三级结构**。先建立整体模型，后面所有机制都填进这张图里。

@@idea 核心思路
一段 Spark 程序运行时，被拆成三层：

```text
你的程序（一个 SparkContext 应用 Application）
   └── 每个行动算子 = 一个 Job          （count/collect/save 各触发一个 Job）
          └── 每个 Job 按 shuffle 切成多个 Stage（阶段）
                 └── 每个 Stage = 一组 Task（任务，每个分区一个）
                        └── Task 是真正在 Executor 上跑的最小执行单元
```

| 层次 | 触发方式 | 数量级 | 比喻 |
|---|---|---|---|
| Application | 提交一个程序 | 1 个 | 一本菜谱 |
| Job | 一个行动算子 | 每行动 1 个 | 一道菜 |
| Stage | shuffle 划分 | 每 Job 多个 | 一个步骤 |
| Task | 每个分区一个 | 几十~几千 | 一个厨师炒一份 |

**关键点**：
1. **Task 数量 = 该 Stage 的 RDD 分区数**（10 个分区 = 10 个 Task）
2. Spark UI 上"Jobs / Stages / Tasks"三个 Tab，就是这三个层次的可视化
3. 一个 Job 串行依赖的 Stage 可能有多个，但同一轮可以并行执行无依赖的 Stage

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 一个程序里写了 3 个行动算子 | 会生成 **3 个 Job**，各自独立算一遍（无缓存时重复计算）。想复用中间结果，用 cache/persist（下一章） |
| UI 上"Tasks"数量巨大吓人 | 那是分区数总和，正常。分区太多会调度开销大，太少并行度低——调优章讲平衡 |
| 以为 Stage 之间是顺序执行的 | 无依赖的 Stage 会并行跑（如两个独立分支）。只有 shuffle 依赖强制先后 |
| 分不清 Application/Job 谁大 | 提交一次 = 1 个 Application；里面的每个行动算子 = 1 个 Job。一个 Application 通常有多个 Job |

@@point ② RDD 血缘 Lineage：执行的"施工图"
@@need 要解决什么
Spark 怎么知道一个 RDD 是怎么来的？数据丢了怎么恢复？——全靠**血缘（Lineage）**。每个 RDD 都记录着自己的"祖先链条"（由哪些算子从哪个 RDD 变来的）。它是 DAG 构建的基础，也是容错恢复的底牌。

@@idea 核心思路
**血缘 = RDD 的依赖图谱**：每个 RDD 都保存"我是从哪些 RDD、经哪个算子变来的"。

```text
rdd = sc.textFile("hdfs://.../log.txt")     ← 根（无血缘）
  .flatMap(_.split(" "))                     ← 依赖 rdd：flatMap 转换
  .map((_, 1))                               ← 依赖上一步：map 转换
  .reduceByKey(_ + _)                        ← 依赖上一步：reduceByKey（有 shuffle）

// 血缘链：textFile → flatMap → map → reduceByKey → (collect 触发)
```

血缘的两个用途：

1. **构建 DAG**：Spark 从行动算子出发，沿血缘链回溯，画出完整计算图（就是 UI 上的 DAG 图）
2. **容错**：某个分区数据丢失/计算失败，Spark 顺着血缘**重算这一条链**即可恢复，无需像 Hadoop 那样整个重跑

```text
找回丢失的数据 = 从源头重新执行该分区的血缘链
每次重算=重新执行该 RDD 所有上游转换（所以缓存能加速）
```

**血缘 vs 缓存的关系**：血缘是"不打折的重算"；cache 是"把中间结果存下来避免重算"。有 cache 时优先用缓存，缓存没了才走血缘重算。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 每次重算都极慢 | 说明没有 checkpoint/cache，每次失败都从源头全量重算。长血缘链（几十步变换）尤其伤——中间落 checkpoint（下章讲） |
| 血缘链太长导致恢复费时 | 超长血缘用 checkpoint 截断：把中间结果持久化后，后续 RDD 的血缘就"从检查点开始"，不再是全链（下章） |
| 以为血缘是存数据 | 血缘存的是"怎么算"，不是"算好的结果"。内存放的是数据，血缘只是元信息 |
| 改动上游 RDD 会影响下游？ | 不会，RDD 不可变，转换生成新 RDD，血缘只增不改。这也是 Spark 容错简单的原因 |

@@point ③ 窄依赖：父子分区一对一，流水线的基础
@@need 要解决什么
血缘链上有两种"父子关系"，这是一种全链路绕不开的核心区分：**窄依赖（Narrow Dependency）**。搞不清它，就解释不了"为什么有的算子快、有的算子要 shuffle"，也看不懂 Spark 为什么能"流水线"执行。

@@idea 核心思路
**窄依赖定义：父 RDD 的每个分区，最多只被子 RDD 的一个分区使用**。

```text
父分区:   [P1]  [P2]  [P3]
           ↓    ↓    ↓
子分区:   [C1]  [C2]  [C3]     ← 各管各的，无交叉

map / filter / flatMap / union
（union 是特例：一个子分区依赖多个父分区，但仍算窄依赖——因为父分区只被一个子分区用）
```

三个特征（记住它们就是判断依据）：

1. 每个父分区**最多**对应一个子分区（不跨分区传递数据）
2. **不需要 shuffle**——数据在哪个分区就在哪个分区处理
3. 可以**管道式（pipeline）连续执行**：map→filter→map 在同一分区上连着跑，不落盘、不等待

**为什么窄依赖快**：不涉及网络传输数据，一个 Stage 内所有窄依赖算子可以"一条流水线"跑完。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为窄依赖=一个父分区对一个子分区 | 一对一是一种，union 是一对多（一个父分区 → 多个子分区）也算窄依赖。判断标准是"父分区是否被多个子分区用"，不是数量对称 |
| 在窄依赖算子链中途缓存 | 窄依赖本身快且可 pipeline，多数情况没必要在中间 cache，浪费内存。缓存通常放在"宽依赖之前"或"会被多 Job 复用"的位置 |
| 反链：把窄依赖算子误以为要 shuffle | 不用。filter/map 永远不触发 shuffle，别担心它们慢 |
| 忘记窄依赖是 Stage 内部的基础 | 记住"窄依赖算子连续执行=一个 Stage"，这是 Stage 划分的钥匙（见第⑥点） |

@@point ④ 宽依赖：父子分区一对多，shuffle 的源头
@@need 要解决什么
与窄依赖相对的另一半：**宽依赖（Wide Dependency）**——reduceByKey/groupByKey/join 这些"按 key 重分布"的操作。它需要的 **shuffle 是全 Spark 最贵的动作**：跨节点搬运数据、落盘、排序…… 性能问题的 90% 都出在它身上。这必须彻底理解。

@@idea 核心思路
**宽依赖定义：父 RDD 的一个分区，可以被子 RDD 的多个分区使用**。

```text
父分区:     [P1]   [P2]   [P3]
              \    / \    /
               \  /   \  /
子分区:       [C1]   [C2]   [C3]
              ↑ 按 key 重新分发：同一个 key 可能来自不同父分区

reduceByKey / groupByKey / join / distinct / sortBy
（一切"按 key 重新分区"的算子）
```

**宽依赖必然伴随 Shuffle（洗牌）**，三个子动作：

1. **Map 端**：每个分区处理完，把结果**按 key 哈希**分桶到对应下游分区
2. **落盘 + 网络传输**：写本地文件 → 传输到对应 Executor
3. **Reduce 端**：每个分区从各个 Map 端拉取自己那份数据，再合并聚合

**代价**：网络 IO + 落盘 IO + 可能排序。这就是"宽依赖贵"的全部来源。

**窄依赖 vs 宽依赖一句话**：

| | 窄依赖 | 宽依赖 |
|---|---|---|
| 父分区 → 子分区 | 最多 1 个 | 1 个 → N 个 |
| shuffle | 无 | 必发生 |
| 典型算子 | map/filter/flatMap/union | reduceByKey/groupByKey/join |
| 一个 Stage 内 | 可连续 pipeline | 是 Stage 的分界线 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 shuffle 只在网络慢时才严重 | shuffle 的落盘 + 网络 + 可能排序是固定成本，本来就是最贵动作。宽依赖算子能省则省（如前面学的 reduceByKey 替代 groupByKey） |
| join 慢就加并行度 | 并行度过高 shuffle 的小文件翻倍，IO 反而爆炸。调优先看数据量和倾斜，不是无脑加分区 |
| 把 distinct 当成窄依赖 | distinct 要去重必须全局比对 → 也是宽依赖（shuffle），别小看它 |
| 判断依赖只看算子名 | 必须看实现：union 是窄依赖但 groupBy 是宽依赖。判断依据永远是"父分区是否被多个子分区用" |

@@point ⑤ Shuffle 机制：一场"按 key 分快递"的全过程
@@need 要解决什么
宽依赖触发的 shuffle 到底**内部怎么运作**？为什么会有"Map 端输出文件"这个说法？搞清楚 shuffle 的完整链路，你才能看懂 Spark UI 的 Shuffle Read/Write 指标，也能理解为什么会"磁盘 IO 爆炸"。

@@idea 核心思路
Spark 的 Shuffle 分两大阶段（以 reduceByKey 为例）：

```text
【Map 端（Shuffle Write）】            【Reduce 端（Shuffle Read）】
P1: [a,1][c,1]                          R1: 拉取所有 key∈[a..m] 的数据
P2: [b,1][a,1]                          R2: 拉取所有 key∈[n..z] 的数据
P3: [c,1][b,1]
                                          ↓
每个 Map 分区按 key 哈希生成 2 个分桶文件   每个 Reduce 分区从每个"上游文件"拉自己那份
（分区数 = 下游分区数）                  再做聚合（合并相同 key）
```

**关键细节**：

1. **Map 端落盘**：每个上游分区为每个下游分区写一个小文件（`Shuffle Write` 指标），所以 `上游分区数 × 下游分区数` 可能=成千上万小文件——这就是"小文件爆炸"
2. **数据倾斜时**：某个 key 数据量巨大 → 对应那个 Reduce 分区拉取极慢 → 单个 Task 拖垮整个 Job（UI 上能看到"某 Task 耗时远超其他"）
3. **Shuffle 可能排序**：部分算子（sortByKey）要求 shuffle 时排序，额外开销

**调优常识**：Spark 会把 Map 端的小文件聚合批量写（shuffle 合并），但根本出路还是控制分区数和避免不必要的宽依赖。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 日志报 `Too many open files` | Shuffle 小文件过多（上游×下游 文件数爆炸）。调低分区数，或开 shuffle 文件合并 |
| UI 上 Shuffle Write 巨大 | 数据在网络搬运前全落盘了，正常但说明 shuffle 量真的大。考虑 map 端先预聚合（reduceByKey 的 combine）减少传输 |
| 一个 Task 特别慢、其他早就完了 | 经典**数据倾斜**：那个分区 key 太多。前处理：过滤热点 key / 加盐（实战章细讲） |
| 怀疑 shuffle 丢数据 | 不会丢。Spark 的 shuffle 有完整性校验（写类/校验和），失败会重试。真丢了是代码逻辑问题不是框架问题 |

@@point ⑥ Stage 划分：shuffle 是切菜刀
@@need 要解决什么
现在三个概念齐了（Job/Stage/Task、窄/宽依赖、shuffle），把它们拧到一起的**最关键机制**就是 Stage 划分：**以 shuffle 为界，把 Job 切成若干个 Stage**。看懂这个，Spark UI 的 DAG 图你就能完全读懂了。

@@idea 核心思路
**划分规则极简**：从行动算子往前回溯，**遇到宽依赖就切一刀**；两个 shuffle 之间（或 Job 起点到第一个 shuffle 之间）的连续窄依赖，合为一个 Stage。

```text
textFile → flatMap → map ──reduceByKey(shuffle)──→ map → filter ──join(shuffle)──→ map → collect
   [ Stage 0 ]                        [  Stage 1 ]                  [   Stage 2  ]
（窄依赖连片=一个 Stage）    （shuffle 一刀  （再一刀）
                               又切出新 Stage）

3 个 Stage = 2 次 shuffle
```

**从 DAG 图怎么验证**：UI 上每个 Stage 块内部是一条条连续算子（窄依赖堆叠），两个 Stage 之间有个明显的"条带"连接——那个条带位置就是 shuffle。

**Stage 为什么这样切**（不只是为了好看）：

- 窄依赖可以 pipeline 一口气算完（算子全部合并执行，不落盘）
- shuffle 是硬边界：数据要从"源头重分布"，只能先算完上游全部，再启动下游

**Stage 的执行方式**：一个 Job 里，Stage 按依赖拓扑执行——无依赖的 Stage 并行（同一批 Task 发出），有依赖的等上游完成。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| UI 上 Stage 个数和自己预期对不上 | 数"shuffle 次数+1"即可（每个宽依赖算子切一刀）。join/reduceByKey/distinct/sortByKey 每个都是一刀 |
| 想减少 Stage 数 | 少用宽依赖算子=少 shuffle=少 Stage。能用窄依赖重写的就别宽依赖（如 filter 前置减少 shuffle 数据量） |
| 一个 Stage 里有 join 却只有一个 Stage | 不会发生——join 就是宽依赖必切。Stage 只含窄依赖链 |
| Stage 是"串行执行"的误解 | 无依赖 Stage 并行。DAG 图上看左右并排的 Stage 同时跑，上下串的才分先后 |

@@point ⑦ DAGScheduler 与 TaskScheduler：执行系统的两员大将
@@need 要解决什么
讲完"怎么切"，还得讲"谁来切、谁来调度"。Spark 的执行系统由两个调度器分工：**DAGScheduler（划分 Stage）** 和 **TaskScheduler（派发 Task）**。面试爱问、理解后看日志也不懵。

@@idea 核心思路
```text
Action 触发 Job
   │
   ▼
DAGScheduler（DAG 调度器）── 在 Driver 里
   │  ① 建 DAG ② 按宽依赖切成 Stage
   │  ③ 为每个 Stage 生成一组 Task（每分区一个）
   │  ④ 提交 TaskSet 给 TaskScheduler
   ▼
TaskScheduler（任务调度器）── 也在 Driver 里
   │  ① 为每个 Task 寻找空闲 Executor
   │  ② 通过 RPC 把 Task 发给 Executor
   │  ③ 收结果、失败重试（黑名单机制）
   ▼
Executor（执行器）── 在 Worker 节点上
   真正跑 Task，跑完把结果返回 Driver
```

| 角色 | 位置 | 职责 | 出错处理 |
|---|---|---|---|
| DAGScheduler | Driver | 建 DAG、切 Stage、生成 TaskSet | Stage 失败→重提丢失的部分 |
| TaskScheduler | Driver | 把 Task 派到 Executor、调度 | Task 失败→重试（默认 3 次） |
| Executor | Worker | 执行 Task、存缓存数据 | - |

**看日志的技巧**：日志里 `INFO DAGScheduler: Submitting N missing tasks...` = 正在切 Stage 派任务；`INFO TaskSchedulerImpl: Adding task set...` = 在派 Task。对应上就不慌。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报错定位到 DAGScheduler | 通常是某个 Stage 里所有 Task 反复失败（如代码异常、缺依赖 jar）。看具体异常堆栈，不是调度器的问题 |
| Task 失败重试 3 次仍失败 | 看是"可重试错误"（网络瞬断，重试有效）还是"确定性错误"（代码抛异常，重试无用）——后者要修代码/bloom 过滤脏数据 |
| 以为调度器在 Executor 上 | 两个调度器都在 **Driver** 进程里。理解这点才能解释"Driver 挂了整个应用没了" |
| 混淆"Executor 执行"和"Driver 执行" | collect 在 Driver 收数、foreach 在 Executor 执行（前面讲过）。调度只在 Driver，执行在 Executor |

@@point ⑧ 实战视角：用 Spark UI 读一遍自己的程序
@@need 要解决什么
前面全是概念，这一节把它们**落到体检工具上**：Spark UI（默认 4040 端口）自带 Jobs / Stages / Storage / Executors 四个 Tab，能可视化验证本章所有说法。学会读 UI = 真正"看见"执行流程，调试和面试都直接受益。

@@idea 核心思路
跑一个 `spark-submit` 或本地 `local[*]` 程序，访问 `http://localhost:4040`，四个核心 Tab：

**① Jobs Tab**：列出每个 Job（一个行动算子）——看到 N 个 Job，就对应你写的 N 个行动算子

**② Stages Tab（最精华）**：
- 每个 Job 切成几个 Stage 一目了然
- 点进 Stage 看 **DAG Visualization**：方块=Stage，内部是 pipeline 的算子链，圆角条带=shuffle 边界
- 顶部指标：`Shuffle Write` / `Shuffle Read` 各多少字节
- 各 Task 的耗时列表：**找数据倾斜**（少数 Task 巨慢）、**找慢节点**

**③ Storage Tab**：你 cache/persist 过的 RDD 在这里显示——内存占用、是否被清理（storageLevel 生效的标志）

**④ Executors Tab**：每台机器几个 Executor、各用多少内存、GC 时间。GC 时间占比高 = 内存不足 → 数据溢写/重算

```text
一句话体检流程：
先看 Stages 有几个（结构对不对）
→ 看 Shuffle 大小（哪里在搬运数据）
→ 看 Task 耗时分布（有没有倾斜/慢节点）
→ 看 Storage（缓存有没有生效、被清没）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 本地跑完程序 UI 就没了 | UI 随 Application 结束而关闭。想边跑边看用 `--driver-ui-port` 或开 `spark.ui.retainedJobs` 持久化；跑完看日志里的统计也行 |
| 4040 端口打不开 | 多实例冲突：4040 被占 → 自动 4041/4042……看启动日志里实际的 UI 地址 |
| UI 上 DAG 有"蓝色盒子带漩涡" | 那是 **广播变量** 的标志（下下章讲），正常的 |
| 前端端口在生产环境不可达 | 生产看历史服务器（History Server）——`spark.eventLog.enabled=true` 落盘事件后，任意时间回看 UI。作业加这个配置就是给"事后体检"留下档案 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **执行三层框架**：Application → Job → Stage → Task | 全 Spark 运行时概念的总骨架，报错/UI/调优都挂在这骨架上 |
| **宽窄依赖判定力**：窄=无 shuffle=Stage 内，宽=必 shuffle=Stage 边界 | 能预判哪些算子贵、为什么贵，答案全在 shuffle |
| **UI 体检法**：DAGScheduler/TaskScheduler 分工 + 四个 Tab 怎么看 | 从"盲写代码"升级到"看图调优"，排障效率质变 |

@@quiz
1. 一个程序里有 3 个行动算子，会产生几个 Job？为什么？
2. 判断下面算子是窄依赖还是宽依赖：map、filter、reduceByKey、union、join、distinct，并说明判断标准。
3. 为什么窄依赖算子（如 map→filter→map）可以合并成一个 Stage 连续执行？
4. 5 个上游分区 + 8 个下游分区，Map 端会产生多少个 shuffle 文件（不做合并时）？
5. DAGScheduler 和 TaskScheduler 各自的职责是什么？它们分别在哪个进程里？
6. 一个 Job 含 2 次 shuffle，会切成几个 Stage？
7. 判断题：窄依赖一定会触发 shuffle；宽依赖一定不会。

@@links
讲义|Spark 内核进阶（第 1 章：DAG 与 Stage 划分）|#
讲义|Spark 内核进阶（第 2 章：宽窄依赖与 Shuffle）|#
官网|Job Scheduling 官方文档|https://spark.apache.org/docs/latest/job-scheduling.html
官网|RDD 编程指南（容错章节）|https://spark.apache.org/docs/latest/rdd-programming-guide.html#rdd-persistenc