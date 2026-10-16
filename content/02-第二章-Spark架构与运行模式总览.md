@@h1 第二章　Spark 架构与运行模式总览
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　6 课时　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章你知道了 Spark 能把一堆机器组织起来一起算。但"组织"到底怎么组织？你在笔记本上写一个 `sc.textFile(...)`，然后它凭什么让 100 台机器动起来、算完的结果又是怎么回到你面前的？如果完全没有概念，后面看日志、调参数、排查报错都会像看天书——**"Driver"“Executor”“Task"这些词你会反复见到，但不知道谁是谁**。

这一章把 Spark 的**骨架**装进你脑子：集群里有哪几种角色、各管什么事、一份代码从提交到出结果的完整路径。学完再去碰部署模式（Local/Standalone/YARN），你会发现它们只是"谁当老板"的区别而已。

学完这一章，你能画出 Spark 的架构图，并说清**Driver、Executor、Task 各是什么**。

@@map 这一章在整个知识库里的位置
上一章（Spark 简介）：你知道了 Spark 解决什么问题、为什么快、生态由谁组成
**本章** ← 你在这里：Spark 的骨架——架构角色与作业执行路径
下一章：Local 模式与 WordCount 入门——把架构落到第一行能跑通的代码上
再往后：Standalone/YARN 部署 → RDD 编程 → 内核调度 → 实战项目 → SparkSQL/Streaming
阶段终点：你能独立完成 Spark 从部署、编程到调优的全链路

@@note info 学习提示
本章仍然没有代码，但有一个**贯穿全书的核心心智模型**：`Driver 是老板，Executor 是工人，Task 是一条具体的活`。请带着这个比方读完全章。

@@point ① Spark 集群三大角色：Driver / Executor / Cluster Manager
@@need 要解决什么
一段 Spark 代码跑起来后，进程里至少会冒出几种"角色"。如果你不提前知道它们的分工，遇到 `ExecutorLostFailure`、`driver 内存不足`这类报错时，连"谁挂了"都判断不了。先建一张**人员架构图**。

@@idea 核心思路
Spark 集群（无论哪种部署模式）本质上只有三种角色：

| 角色 | 类比 | 职责 |
|---|---|---|
| **Driver** | 包工头/老板 | 跑你的 `main` 程序，创建 SparkContext，把代码翻译成任务分派下去，收结果 |
| **Executor** | 干活的工人 | 真正执行任务的进程，跑在各 Worker 节点上，持有数据块和缓存 |
| **Cluster Manager** | 劳务市场/房东 | 只负责"分配机器资源"，不参与具体计算（Standalone 的 Master / YARN 的 ResourceManager 都在此列） |

关键认知：**计算永远发生在 Executor 上，Driver 自己几乎不算数据**。你的 `map`、`reduce` 这些算子，都是 Driver 打包成任务发到 Executor 上执行的。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Driver 要参与计算，把大集合放 Driver 又遍历 | Driver 是"发号施令"的，真正的数据计算在 Executor。把几百 GB 数据 `collect()` 回 Driver 会直接 OOM |
| 报错里出现 `ExecutorLostFailure` 就慌 | 这是某个 Executor 挂了（OOM、节点宕机等）。Spark 会自动把它的任务换到别的 Executor 重跑，先看后续日志是不是自动恢复了 |
| 以为"核数"就是 Executor 数 | 每个 Executor 内部可以并行跑多个 Task，Task 才是真正并行的最小单位（本章第 ⑦、⑧ 点详述） |

@@point ② Driver 与 SparkContext：一切的入口
@@need 要解决什么
每份 Spark 代码都有个神秘的开头：`from pyspark import SparkContext` 然后 `sc = SparkContext(...)`。这个 `sc` 到底是什么？没有它你敢不敢说自己"在用 Spark"？——它是**你与集群之间的唯一通道**。

@@idea 核心思路
**SparkContext（sc）就是 Spark 程序的入口和核心**，它做的事包括：

- 与 Cluster Manager 协商，申请 Executor 资源
- 把你写的每个转换算子记录下来，构建 DAG（有向无环图）
- 把 DAG 切成 Stage、Stage 切成 Task，调度到 Executor 执行
- 维护广播变量、累加器等跨节点共享的东西

一个 Driver 里一般只有一个 SparkContext。现代写法里你常用 `SparkSession`（SparkSQL 引入），它**内部就包了一个 SparkContext**——两者别当成两个体系。

```python
from pyspark import SparkContext
sc = SparkContext("local[2]", "MyFirstApp")  # master + appName
rdd = sc.textFile("data/hello.txt")          # sc 是唯一的"入口"
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 代码里同时建了两个 SparkContext | 同一个 JVM 里默认只能有一个活动 sc，再建会报 `Only one SparkContext should be running in this JVM`。用 SparkSession 时别手动再 new SparkContext |
| 一运行就报 `Java gateway process exited before sending its port number` | 常见于环境问题：JAVA_HOME 没配好、PySpark 与 Spark 版本不匹配。先 `java -version` 和 `pyspark --version` 对一下 |
| 以为 `sc` 和 `spark` 是同一个东西 | `spark`（SparkSession）是更高层封装，`sc = spark.sparkContext` 是从它拿到底层句柄。在 PySpark 里直接用 `spark.sparkContext.textFile(...)` 等价于 `sc.textFile(...)` |

@@point ③ Executor：真正干活的人，以及它的两片内存
@@need 要解决什么
Executor 是工人，但工人干活要有"工作台"和"仓库"。Spark 的 Executor 有**两种内存区域**，分不清会导致：缓存了数据后代码反而 OOM、或明明内存够却喷 `java.lang.OutOfMemoryError`。你需要知道 Executor 的内存怎么划分的。

@@idea 核心思路
每个 Executor 是一台机器上的一个 JVM 进程，内存大致分两片（Spark 3.x 起用统一内存模型，但理解上仍可分）：

| 区域 | 干什么 | 满了会怎样 |
|---|---|---|
| **Storage（存储）** | 放缓存（cache/persist）的数据块 | 会自动逐出旧缓存，不会立刻崩 |
| **Execution（执行）** | 放 shuffle、join、聚合的中间结果 | 会触发溢写到磁盘，还满就 OOM |

关键认知：这两块内存是**弹性的**——执行内存不够时可以向存储内存借用，反之亦然（spark.memory.fraction 控制总份额，默认约 0.6 给计算用）。所以"缓存越多越好"是错的：缓存占了，执行内存就少，重 shuffle 任务反而变慢。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 无脑 cache 所有 RDD，以为内存无限 | 内存是共享的：缓存挤占执行内存 → shuffle 溢写 → 任务反而变慢。只缓存**会被多次复用**的数据 |
| 报 `ExecutorLostFailure` + `OutOfMemoryError` | Executor JVM 堆不够：调 `spark.executor.memory`，或缩小单条数据（分区数调大），别只盯着缓存 |
| 搞不清 `--executor-memory` 和 `--driver-memory` | 前者是每个工人分多少内存，后者是老板分多少。数据量大主要加 executor，collect 回 Driver 的操作要加 driver |

@@point ④ Cluster Manager：只管资源，不管计算
@@need 要解决什么
三种部署模式（Local/Standalone/YARN）名字不同、配置不同，但你是不是隐约觉得它们有共同点？本点把"模式差异"压缩成一个问题：**谁在当 Cluster Manager（分配资源的中介）**。搞懂这个，三种模式你就一通百通。

@@idea 核心思路
Cluster Manager（资源管理器）的职责只有一条：**Driver 说要 20 个 Executor，它就把机器资源划出来**。至于任务怎么算，它完全不参与。

| 部署模式 | Cluster Manager 是谁 | 一句话特点 |
|---|---|---|
| Local | 无（Driver 就在本机，自给自足） | 单机练手，后面第三章讲 |
| Standalone | Spark 自带的 Master | 不依赖 Hadoop，轻量，后面第四章讲 |
| YARN | Hadoop 的 ResourceManager | 和 Hadoop 生态统一管资源，生产常用，后面第五章讲 |

这套"A 请求资源 → B 分配资源 → C 干活"的模型是统一的，所以**一份代码在三种模式下不用改逻辑**，只改提交命令里的 `--master` 参数。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Standalone 的 Master 就是 YARN 的 ResourceManager | 两者**职责一样但实现不同**：Master 是 Spark 自带的，ResourceManager 是 Hadoop 的。别混着配（配 YARN 时去配 Master 的配置项，任务永远起不来） |
| 以为"换了模式就要改代码" | 常规 RDD/DataFrame 代码与部署模式**无关**，改的是 `--master` 和资源配置参数。只有少数资源相关的配置（如走 HDFS）要随环境调 |
| 生产环境纠结"Standalone 还是 YARN" | 已有 Hadoop 集群选 YARN（统一资源、共享队列）；独立小集群、不想碰 Hadoop 选 Standalone。没有"绝对最好"，只有"符合现状" |

@@point ⑤ 一次作业的完整旅程：代码 → Task
@@need 要解决什么
你写的 `.map(...).filter(...).reduce(...)` 一整串，Spark 是怎么把它拆成一个个能在集群里并发执行的小任务的？"魔法"在哪一步发生？——把这条链讲清，之后看日志里的 `Job/Stage/Task` 层级就一目了然。

@@idea 核心思路
一次提交的完整链路（务必记住这个层级）：

```text
你写的代码 (Application)
   └─ 被拆成若干 Job        ← 每遇到一个行动算子（Action）就是一个 Job
        └─ 每个 Job 按宽依赖切成若干 Stage（阶段）
             └─ 每个 Stage 按分区切成若干个 Task（最小任务单元）
                  └─ Task 被调度到 Executor 上并发执行
```

打个比方：Job 是"盖一栋楼"；Stage 是"打地基/砌墙/封顶"这些大工序（工序之间有交接点）；Task 是"砌第 3 面墙的第 2 排砖"这种一个小工一上午能干完的具体活。

**触发拆分的开关是行动算子（Action）**：`collect()`、`saveAsTextFile()`、`count()` 这类"出结果"的操作。没有它们，前面的 map/filter 只是记录在案、不真跑（这叫惰性求值，后面 RDD 章细讲）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 日志里 `Job 0`、`Stage 1`、`Task 12` 分不清 | Job=一次行动算子；Stage=Job 里按宽依赖切出的段；Task=按分区并行的最小单元。三者是**包含关系**：Job > Stage > Task |
| 以为写一行 `.map` 就立刻执行 | 转换算子（map/filter 等）是**惰性**的，只记不跑；直到出现行动算子才真正触发。这个"延迟"常让人以为代码没执行 |
| 数不清"我的任务起了多少并行" | 并行度由**分区数**和 **Executor 核数**共同决定：Task 数 = 分区数，可同时跑的 Task 数 = 总核数。分区多核少会排队 |

@@point ⑥ 本地模式：一台电脑也能"假装"集群
@@need 要解决什么
你还没集群，但想**立刻上手写 Spark 代码**。本地模式就是干这个的——但你要知道它是怎么"以假乱真"的，否则会把本地模式和集群模式的行为搞混（比如以为本地没 Executor）。

@@idea 核心思路
**Local 模式 = 所有角色挤在一台机器的一个 JVM 进程里**。Driver、Executor、Task 的调度逻辑全跑在本地，用线程模拟并行，读写本地文件系统。

```python
# 用线程数模拟核数："local" 单线程，"local[2]" 2 线程，"local[*]" 用满所有核
sc = SparkContext("local[2]", "Demo")
```

它和集群模式的区别：

| 维度 | Local | 集群（Standalone/YARN） |
|---|---|---|
| Executor 在哪 | 当前进程内 | 别的 Worker 节点上的独立进程 |
| 数据从哪读 | 本地文件/内存 | HDFS、远端存储 |
| 用途 | 学习、开发调试、小数据 | 生产、大数据 |

**本地模式出现的报错和集群大多一致**（OOM、任务失败等），所以它是绝佳的"练习场"。很多企业做开发调试也用 local 模式跑小数据。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 `local[*]` 在 8 核笔记本上开满，自己 IDE 一起跑就卡死 | `*` 用满所有核，开发和跑 IDE 抢资源。练手用 `local[2]` 或 `local[4]` 足够 |
| 本地读 `hdfs://...` 路径 | local 模式默认没有 HDFS 客户端环境，读不到。本地就用 `file:///` 或相对路径 |
| 本地数据几百 GB 想直接"练" | local 模式数据一大就 OOM/慢，练手数据控制在百 MB 级，真大数据上集群 |

@@point ⑦ 并行度：核、分区与 Task 的三角关系
@@need 要解决什么
"为什么我这个任务这么慢？""为什么一个 Executor 空闲另一个忙死？"九成答案在并行度。但你经常看到三个词（核数、分区数、Task 数）被混着说——本点把它们的关系一次钉死。

@@idea 核心思路
```text
Task 数 = 分区数（分区是数据的最小逻辑块，每个分区对应一个 Task）
可同时跑的 Task 数 = 所有 Executor 的核数总和
```

- 分区数 < 核数 → 有核闲着，白花钱
- 分区数 > 核数 → 排队执行，多了会好（分散不均匀的慢任务），但太多调度开销大
- 分区数由输入决定（读 HDFS 文件默认按块分），可以用 `repartition(n)` / `coalesce(n)` 调整

```python
rdd = sc.textFile("data/raw.txt", minPartitions=4)   # 读时指定最少分区
rdd2 = rdd.repartition(8)   # 重分区（会 shuffle）
rdd3 = rdd.coalesce(2)      # 减小分区（少 shuffle，尽量用这个）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 调大分区就一定变快 | 机器学习里常见误解。分区超过总核数后，增加的是调度开销；数据倾斜时调大分区反而有用（把大 key 拆细） |
| `repartition` 和 `coalesce` 傻傻分不清 | `repartition` 增/减都会发生 shuffle；`coalesce` 只能减、尽量不 shuffle（合并相邻分区）。**减分区用 coalesce，要 shuffle 再算才用 repartition** |
| 以为自己设的分区数就是最终数 | 行动算子（如 `groupByKey`）可能自己重新分区。最终看日志里实际 Task 数，别只用"我以为" |

@@point ⑧ 日志是照妖镜：从日志读架构
@@need 要解决什么
Spark 日志又长又密，初学一看到 `INFO` 刷屏就关。但**架构里听不懂的地方，日志里全都有**——学会读日志，Debug 能力立刻上一个台阶。本点教你在日志里找四样东西。

@@idea 核心思路
跑一个简单 WordCount，日志里高频出现的四行及其含义：

```text
INFO SparkContext: Running Spark version 3.2.1          ← 版本
INFO SparkContext: Submitted application: MyApp          ← Driver 提交应用
INFO ExecutorAllocationManager: ... executor 2 is running ← Executor 起来了
INFO DAGScheduler: Job 0 finished: reduce at ...         ← 一个 Job 干完
```

四件事分别对应架构里的：

| 日志关键字 | 对应角色/环节 |
|---|---|
| `SparkContext: Running/Submitted` | Driver 启动并提交应用 |
| `ExecutorAllocationManager` / `CoarseGrainedSchedulerBackend` | 资源申请、Executor 上线 |
| `DAGScheduler` | DAG → Stage 的切割（看到它就知道在规划阶段） |
| `TaskScheduler` / `TaskSetManager` | Stage → Task 的分发调度 |
| `Stage N ... Finished` | 某个 Stage 完成，可对照 UI 看耗时 |

**Web UI（默认 :4040）比日志更好用**：打开后 Jobs / Stages / Executors 三个标签页，就是架构图的活生生呈现。跑任务时开着它，你会看到 Driver 的规划、Executor 的并行，全都可视化。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 日志全 INFO 以为没事 | INFO 是正常进度，红线是 `ERROR`/`WARN` 里的真实异常。用代码把日志级别调到 WARN：`sc.setLogLevel("WARN")`，屏幕清净很多 |
| 只看最后 10 行日志 | 异常栈往往在中间（"Caused by" 在底部但前后有上下文）。报错时把日志完整存文件再搜关键字 |
| 4040 端口打不开 | local 模式下 Web UI 默认开启且随程序结束而关闭——程序运行中从浏览器开 `http://localhost:4040`；集群上要先看 Driver 地址 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **架构心智模型**：Driver 老板 / Executor 工人 / Manager 房东 | 所有报错、调参、日志阅读都建立在这张图上 |
| **作业旅程**：Application → Job → Stage → Task | 看懂调度层级，才知道程序慢在哪一步、并行度是谁决定的 |
| **部署统一观**：三种模式只是"谁当房东"不同 | 后面三章你只学"改哪个参数"，不慌 |

@@quiz
1. 用一句话说清 Driver、Executor、Task 三者的关系（可以打比方）。
2. 一份 Spark 程序里有 3 个 `collect()`，一共有几个 Job？为什么？
3. Executor 的内存分哪两片？只 cache 不清缓存为什么可能导致任务反而变慢？
4. 你现在只有一台笔记本，想跑一个 200MB 的练习任务，该选什么模式？`local[*]` 和 `local[2]` 的区别是什么？
5. 判断题：Spark 的 Cluster Manager 会参与数据的计算与聚合。
6. `repartition(8)` 和 `coalesce(2)` 的适用场景分别是什么？
7. 日志里出现 `DAGScheduler: Job 0 finished` 说明哪个环节完成了？

@@links
讲义|Spark 分布式计算框架课程介绍（docx）：架构与运行模式节|#
讲义|01-Spark 分布式计算框架基础（第 2 章：架构）|#
官网|Spark 集群模式概览|https://spark.apache.org/docs/latest/cluster-overview.html
资料|讲义源码目录 sparkdemo.zip|#