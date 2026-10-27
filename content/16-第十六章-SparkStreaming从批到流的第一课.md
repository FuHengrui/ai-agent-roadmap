@@h1 第十六章　Spark Streaming：从"批"到"流"的第一课
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★★

@@why 这一章在解决什么问题
前面的分析都是"一次算完一批"（批处理）：昨天的日志今天算。但**实时世界等不了**：双 11 大屏的实时成交额、风控对每笔交易的即时判断、推荐系统对刚发生的点击立刻响应——数据**一到就要算**。这就是流处理。

Spark 对实时的答案叫 **Spark Streaming**，核心思想很优雅：**把"连续不断的数据"切成"一段一段的小批"，每一小批用你熟悉的 Spark 批处理来算**（微批次模型）。这意味着前面学的 RDD 算子、内核、调优**全部直接复用**——学它几乎没有新算子的负担，只有几个新概念：DStream、窗口、有状态。

学完这一章你能：**理解微批次架构、用 DStream 做无状态/有状态/窗口实时统计，并为 Streaming 程序配置 checkpoint**。

@@map 这一章在整个知识库里的位置
前 15 章：批处理全体系（RDD → SQL）
**本章** ← 你在这里：实时第一课——Streaming 架构与 DStream 编程
下一章：Streaming 实战——Kafka 接入、偏移量、优雅关闭、调优
再往后：阶段综合实战与回顾
阶段终点：批+流两条腿都走，覆盖"能预埋数据也能应对实时"

@@note info 学习提示
Spark Streaming 的算子绝大多数和 RDD 一样——**别背新算子，先想"这是不是我又见过的 map/reduceByKey"**。真正新的只有三个：窗口、有状态、Kafka 接入。

@@point ① 为什么需要流处理：批处理的天花板
@@need 要解决什么
先明确"流"要解决什么问题：**数据延迟**。批处理是 T+1 才能看昨天的报表；实时业务要"秒级看到最新"。理解批与流的分界线，才知道 Streaming 该用在哪、别用错地方。

@@idea 核心思路
**批 vs 流对比**：

| | 批处理 | 流处理 |
|---|---|---|
| 数据 | 已落盘的历史文件 | 源源不断到达的事件 |
| 触发 | 手动/定时跑一次 | 数据一到就处理 |
| 延迟 | 分钟~天 | 秒~分钟 |
| 典型 | 报表、数仓 T+1 | 实时大屏、监控告警、风控 |
| Spark 方案 | RDD / SparkSQL | Spark Streaming / Structured Streaming |

**Streaming 的两条技术路线**（本阶段学经典版）：

```text
Spark Streaming（DStream）    —— 本阶段主角，基于 RDD 微批次，成熟稳定
Structured Streaming（结构化流）—— Spark 2.x 新一代，基于 DataFrame 微批次
                          —— 表达更简单；本阶段末尾提一下，重点学 DStream 思想
```

**核心心智模型**：流 = "**很多个连续的小批**"。每秒钟来 1 万条事件 = 每 2 秒切一个 2 万条的小批算一次。**流处理 = 批处理的"重复执行 + 自动推进"**。

**适用判定**：延迟敏感 + 数据流式到达 → 流；历史全量分析 → 批。两者常配合：流处理实时结果 + 批处理离线校准。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用流处理重算历史数据 | 流不擅长"从头重扫大文件"（它会一直等新数据）。历史用批，实时用流，各司其职 |
| 以为 Streaming 延迟是毫秒级 | 微批次最小间隔通常 500ms~几秒，不是毫秒。毫秒级要 Flink 这类真正的流引擎——接受 Spark 的"准实时"定位 |
| 把"定时跑批"当流处理 | 定时跑批（cron+spark-submit）是批的自动化，不是流。流的特征是"数据驱动、持续运行" |
| 选错当项目天线 | 汇报/面试时先答清楚：Streaming 是**微批次准实时**方案，跟 Flink 的差异是面试加分点 |

@@point ② 微批次架构：Streaming 的运行方式
@@need 要解决什么
Spark Streaming 怎么做到"数据一到就算"？答案是**微批次（Micro-batch）**：把实时流按固定时间间隔切成小批，每批走一次"你熟悉的 Spark Job"。看懂这张架构图，Streaming 的每个概念都有了挂靠。

@@idea 核心思路
```text
实时数据流（Kafka/Socket/文件）
     │  按 batchInterval（如 2 秒）切分
     ▼
 ┌────────────┐   ┌────────────┐   ┌────────────┐
 │ Batch 1    │   │ Batch 2    │   │ Batch 3    │
 │ (0-2 秒)   │   │ (2-4 秒)   │   │ (4-6 秒)   │
 └────────────┘   └────────────┘   └────────────┘
     │  每个 batch = 一个 RDD（必须 Spark Job 算）
     ▼            ▼            ▼
   spark 批处理引擎（完全复用 RDD/算子/内核 那套）
```

**三个组件**：

```text
DStream（离散化数据流）：代表"整个流"，本质是"一连串按时间切开的 RDD"
  └─ 每 2 秒切出一个 RDD → 这个 RDD 就叫一个"批次"
输入源 → DStream 输入（Socket/文件/Kafka）→ 转换（算子）→ 输出（foreachRDD/print）
```

**关键点**：

1. **DStream 内部就是 RDD 序列**：DStream 的每个转换，都是对"每个时间片的 RDD"执行同样的 RDD 算子
2. **batchInterval 决定延迟与开销**：间隔越小延迟越低，但**每批都有调度+启动 Job 的开销**——100ms 的 Job 开销占比巨大，通常 1~5 秒起
3. **Job 数 = 批次数**：跑 10 分钟、2 秒一批 = 300 个 Job，Spark UI 上会看到 Jobs 飞速切换（正常）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| UI 上 Job 多到刷屏以为崩了 | 正常！一批一个 Job。关注"处理耗时 vs 批间隔"：处理耗时接近/超过间隔=**背压**（处理不过来），要调并行度/间隔 |
| batchInterval 设 100ms 很爽但巨卡 | 调度开销 > 实际计算。务实从 2~5 秒起步，看 UI 里每批处理耗时再调小 |
| 以为 DStream 是一个超大 RDD | DStream 是"RDD 序列"，不是一个 RDD。它没有 collect/take 这种行动算子（那是单个 RDD 的） |
| 流跑在 local[*] 上每批都慢 | 本地模式并行度受限；生产要 spark-submit 均匀分布 Executor |

@@point ③ DStream 编程模型：一张"时间维度的 RDD"
@@need 要解决什么
正式开始写 DStream：**输入从哪来、怎么创建 StreamingContext、算子怎么用**。这一节解决"第一个 Streaming 程序写出来长什么样"——Socket 实时 WordCount 是经典的入门例，跑通它=摸清 DStream 编程骨架。

@@idea 核心思路
```scala
import org.apache.spark._
import org.apache.spark.streaming._

// ① 创建 StreamingContext（批间隔 2 秒）
val ssc = new StreamingContext(sc, Seconds(2))

// ② 输入源：Socket 文本流（测试常用；生产用 Kafka，下章）
val lines: DStream[String] = ssc.socketTextStream("localhost", 9999)

// ③ 转换（和 RDD 算子几乎一样，按时间片应用）
val words = lines.flatMap(_.split(" "))
val pairs = words.map((_, 1))
val wc = pairs.reduceByKey(_ + _)

// ④ 输出：print() 每批打前 10 条
wc.print()

// ⑤ 启动流并等待（真正开跑）
ssc.start()
ssc.awaitTermination()          // 阻塞，Ctrl+C 才停
```

**整套骨架五步**：建 context → 接输入 → 转换 → 输出 → 启动。和批处理的唯一区别是**多了 ssc.start()**。

**DStream 算子和 RDD 算子的关系**：

```text
DStream.map(f)  ==  每个时间片 RDD 都执行 .map(f)
DStream.reduceByKey(...)  ==  每批 RDD 各自 reduceByKey（批间不合并！）
```

**注意**：DStream 的 `reduceByKey` 是**每批内**聚合；跨批聚合要用有状态/窗口（本知识点后面）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘写 ssc.start() 程序"没反应" | 流是懒的，start 才真正开始接收+计算。骨架五步缺一步都会"空转" |
| awaitTermination 后还想干别的 | awaitTermination 阻塞当前线程。要用 `ssc.start()` 后另起线程做别的，或 `awaitTerminationOrTimeout(ms)` |
| shutdown hook 没配 | 生产 Ctrl+C 会直接杀，没跑资源清理。裹 try-finally 或配优雅关闭（下章讲） |
| 一个 ssc 只能 start 一次 | start 之后不能再次 start，stop 后也不能重启同一 ssc。重跑要 new StreamingContext |

@@point ④ 无状态转换：DStream 里"每批独立"的算子
@@need 要解决什么
DStream 转换分两大类，**无状态（stateless）** 是第一类：每个时间片独立处理，**批与批之间不互相影响**。map/filter/reduceByKey/join 全是这类——和批处理一模一样，心理负担为零。关键是理解"每批独立"的边界，别把"批间累计"的期望错安在它们身上。

@@idea 核心思路
```scala
// 无状态：每批独立，输出只和本批输入有关
val nums = ssc.socketTextStream("localhost", 9999).map(_.toInt)
nums.map(_ * 2)                    // 批内×2
nums.filter(_ > 100)               // 批内过滤
nums.reduce(_ + _)                 // 本批之和（只算本批！）
nums.reduceByKey(_ + _)            // 本批按键聚合（跨批不累计）

// 双流 join（同时间片对齐再关联）
val a: DStream[(Int, String)] = ...
val b: DStream[(Int, String)] = ...
a.join(b)                          // 每个时间片上做 join
```

**无状态算子的特点**：

1. **每批独立计算**：输出不携带历史状态，天然无记忆
2. **转换函数和 RDD 极像**：`map`/`flatMap`/`filter`/`reduceByKey`/`join`/`transform`，签名几乎一致
3. **性能模型**：N 批 = N 个独立 Job，互不阻塞

**最有用的特殊算子 `transform`**：把 DStream 转成 RDD 做"批处理专属操作"（如和静态 RDD 做 broadcast 关联）：

```scala
val bigDict: RDD[Map[String, String]] = ...
ds.transform(rdd => rdd.leftOuterJoin(bigDict))   // 每批 RDD 与静态维表 join
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 reduceByKey 是"全流累计" | 不是！无状态版**每批各自聚合**。想全流累计两个办法：有状态 updateStateByKey（下下点）或窗口 |
| transform 里创建了新的 StreamingContext | transform 内只能用已有 RDD/SSC 对象，**不能在算子内 new StreamingContext**（报错 "not allowed after stop"） |
| 无状态算子输出延迟=批间隔 | 对，无状态天然"一批一拍"。需要更细粒度用窗口（可控制统计粒度） |
| join 两流时间片没对齐 | DStream join 是按时间片对齐的：两个流的同一时间片才关联。间隔不同会各自处理后再 join——先确认两个流的批次间隔一致 |

@@point ⑤ 有状态转换：updateStateByKey 与 mapWithState
@@need 要解决什么
"实时累计网站总 PV"——**跨批保存状态**就是有状态转换：每个 key 维护一份"历史状态"，每批进来更新它。经典实现 **updateStateByKey**（简单但全量更新）与 **mapWithState**（高效增量）。本点把两种都说清，并给"必须开 checkpoint"这个硬约束。

@@idea 核心思路
```scala
// updateStateByKey：维护每个 key 的累计状态
// 状态函数：把"本批新增值 + 历史状态"合成新状态
def updateFunc(newValues: Seq[Int], runningState: Option[Int]): Option[Int] = {
  Some(newValues.sum + runningState.getOrElse(0))     // 本批和 + 历史值
}

val pairs = ...: DStream[(String, Int)]
val total = pairs.updateStateByKey(updateFunc)
// 每批输出：每个 key 的"历史累计值"
```

**两种有状态算子对比**：

| | updateStateByKey | mapWithState |
|---|---|---|
| 更新范围 | **每批全量**重新输出所有 key | 只输出**被更新的 key** |
| 性能 | 慢（全量） | 快（增量） |
| 复杂度 | 简单 | 略复杂（超时/初值回调） |
| 适用 | 入门/数据量小 | 生产/按键量大 |

**必须记：有状态必须先开 checkpoint**：

```scala
ssc.checkpoint("hdfs://.../streaming_ckpt")    // ← 状态存这
// 不设 checkpoint → 跑起来直接报错（No checkpoint directory）
```

原因：状态要跨批持久化、Driver 挂了状态要能恢复——**checkpoint 就是 Streaming 的"进度+状态存根"**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 有状态算子没配 checkpoint 直接报错 | 硬性要求：`ssc.checkpoint(path)` 必配（状态+元数据+RDD 都在里面） |
| updateStateByKey 每批输出"所有 key"太慢 | key 量大时换 mapWithState；或缩小批次数据量。尽量把"不活跃 key"超时清理（mapWithState timeout） |
| 状态函数返回值类型写错 | updateFunc 签名：`(Seq[V], Option[S]) => Option[S]`；泛型前后一致，错了编译直接警告 |
| Driver 重启后状态恢复错位 | 恢复要"从 checkpoint 重开"：`StreamingContext.getOrCreate(ckpt, creatingFunc)` 模式。直接 new 会从头跑丢状态 |

@@point ⑥ 窗口操作：按时间窗做"滑动统计"
@@need 要解决什么
"最近 10 分钟的成交额""近 1 小时的活跃用户"——**时间窗（Window）**统计是流处理最常见需求：窗口有长度（看多久）和滑动步长（多久刷新一次）。Spark 用 `window()` 和一个神算子 **reduceByKeyAndWindow** 实现，比 updateState 更"时间友好"。

@@idea 核心思路
```scala
// 窗口 = 把多个批合并成"一个大批"来算
// window(窗口长度, 滑动间隔) 都必须是批间隔的整数倍
val windowed = pairs.window(Seconds(60), Seconds(10))
// 每 10 秒输出一次"最近 60 秒"的聚合

// 经典：滑动窗口内按键聚合（最常用）
pairs.reduceByKeyAndWindow(
  (a: Int, b: Int) => a + b,      // 窗口内聚合
  Seconds(60), Seconds(10)        // 窗口 60 秒，每 10 秒刷新
)

// 反向版本（减旧加新，高级优化）：窗口滑过时"加新减少"，避免全量重算
pairs.reduceByKeyAndWindow(_ + _, _ - _, Seconds(60), Seconds(10))
```

**窗口的两个参数语义（必考）**：

```text
窗口长度（windowLength）：每个窗口覆盖多久的数据
滑动间隔（slideInterval）：每多久算一次（新窗口起点）

窗口 60s + 滑动 10s = 每 10 秒出一个"过去 60 秒"的统计
窗口 = 滑动时：滚动窗口（每窗口互不重叠）
窗口 > 滑动时：滑动窗口（相邻窗口有重叠，常见）
```

**注意后缀**：窗口必须整数倍于批间隔（batchInterval 2s → 窗口 6s/10s/... 都可以，3s 不行）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 窗口参数报 "window duration must be multiple of slide duration" | 窗口/滑动都要是**批间隔整数倍**。检查两者和 batchInterval 的关系 |
| 窗口统计结果"滞后一个窗口长度" | 正常：输出的是**窗口起止段**的聚合，不是当前瞬间。报表要标注窗口口径 |
| 窗口大了内存暴涨 | 窗口长 → 同时缓存多个批的数据。内存不足：加大 Executor 内存、缩小窗口，或开 spark.streaming.backpressure 自动调 |
| 不知道用 window 还是 updateStateByKey | 要"最近 N 时间"→窗口；要"历史累计"→有状态。窗口有"过期自动丢"，后者永久累计 |

@@point ⑦ 输出算子与 checkpoint：foreachRDD 的正确姿势
@@need 要解决什么
算完的结果**写到哪**？foreachRDD 是 DStream 的输出主力：每批 RDD 让你自定义"落盘/写库/发通知"。但新手极易把"连接对象建在 foreachRDD 外"导致每批重建连接或序列化错误——**连接要建在每批内部/分区内**，这和 map 里建连接的坑同源同病。

@@idea 核心思路
```scala
// 输出到外部存储（Redis/MySQL/Kafka）：连接作用域的经典坑
result.foreachRDD { rdd =>
  val conn = createConnection()          // ✗ 错：Driver 上建一次，Task 序列化不了
  rdd.foreach(row => conn.insert(row))
}

// 正确姿势一：连接建在每个 executor 的任务里（每 Task 一份，太浪费）
result.foreachRDD(_.foreachPartition { rows =>
  val conn = createConnection()           // ✓ 每分区一个，遍历写入
  rows.foreach(row => conn.insert(row))
  conn.close()
})

// 正确姿势二：连接缓存到静态对象 + 分区内取（生产推荐，配连接池）
result.foreachRDD(_.foreachPartition(rows => connectionPool.borrow().use{...}))
```

**checkpoint 的作用再强调**（这里它管"输出不重复不丢"）：

```text
checkpoint 里存三样：
  ① 元数据（配置/上下文）→ Driver 恢复
  ② RDD 数据 → 已算待输出数据的落点（Exact-once 的基础）
  ③ 状态 → 有状态算子的当前累计
```

**输出幂等性**：流式输出面临"重试重放"（Task 失败重跑一批），写库要幂等（主键去重/批次号）——这是流式落库的工程必修。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| foreachRDD 外建连接报序列化错 | 连接必须建在**任务内**（分区/批内部）。全局连接用 object 单例+连接池 |
| 每批都重建连接，几分钟后就超时/慢 | 用连接池（静态缓存）复用；别在 Driver 建、也别在 Task 里每行建 |
| 输出成功了却看不到（本地模式） | foreachRDD 里 println 在 Executor 打印，本地 local[2] 能看到部分；生产看日志文件。想收回到 Driver 用 collect（小结果） |
| 忘记幂等导致重复写入 | 流重放机制会重复执行输出。目标库加唯一键/批次号做去重，别只靠"应该只跑一次" |

@@point ⑧ 批间隔怎么定：延迟与吞吐的博弈
@@need 要解决什么
Streaming 的"心跳"是批间隔（batch interval）——每多久收一批新数据。**间隔设短=延迟低但任务调度频繁；设长=吞吐高但延迟大**。100ms 还是 10s？本点给一套可操作的决策法。

@@idea 核心思路
**批间隔的核心矛盾**：

```text
间隔太小：一批还没算完，下一批已到 → 任务积压，延迟反而爆炸
间隔太大：数据攒久了才算 → 延迟高，但调度开销低

正确目标：找到"能稳定跑完一批"的最小间隔
```

**三步定间隔（实操）**：

```text
① 初选：先按业务容忍延迟定个上界
     大屏仪表盘 → 1~5 秒；离线报表补实时 → 30 秒~1 分钟

② 实测：以该间隔跑 10 分钟，UI 看"每批处理时长"
     处理时长 << 间隔 → 可以再调小（吃到更低延迟）
     处理时长 ≈ 间隔 → 正好，保持
     处理时长 > 间隔 → 积压！先调大间隔或优化处理（见上一点背压）

③ 收敛：在"不积压"前提下压到最小间隔 == 延迟最优
```

**和窗口的关系**（易混点）：批间隔是"采样的频率"，窗口长度/滑动是"统计的跨度"——**窗口可以大于间隔**（如每 5 秒批一次、统计 1 分钟窗口），两者独立设置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 间隔设 100ms 以为越快越好 | 处理跟不上就积压，延迟爆炸。以"处理耗时 < 间隔"为唯一健康判据 |
| 批间隔和窗口长度混为一谈 | 间隔=多久采一次样；窗口=统计多长跨度。独立设置，别当成一个数 |
| 改间隔只改代码不测 | 间隔变化要先跑 10 分钟看积压。`Streaming tab` 的 Scheduling Delay 持续 >0 就要调 |
| 处理耗时忽高忽低 | 可能是 GC/资源争抢。先稳资源（核数/内存）再谈间隔精调 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **微批次世界观**：流 = 连续的小批 = DStream = RDD 序列 | 批处理知识无缝迁移，学流几乎没有新算法负担 |
| **流式算子三条线**：无状态（批内）/ 有状态（跨批）/ 窗口（时间窗） | 实时统计的三种思维：独立算、累计算、滑窗算 |
| **checkpoint 铁律**：有状态必配、驱动恢复靠它、输出幂等防重 | 流程序的"安全带"，不配=生产事故 |

@@quiz
1. Spark Streaming 的"微批次"模型是什么意思？batchInterval 与延迟/开销的关系？
2. DStream 和 RDD 的关系是什么？DStream.map(f) 实际做了什么？
3. 无状态 vs 有状态转换的区别？reduceByKey 在 DStream 里是哪种？
4. updateStateByKey 为什么要配 checkpoint？checkpoint 存了哪三样东西？
5. window(60s, 10s) 每多久输出一次？输出的是什么时段的聚合？窗口和滑动的限制条件是什么？
6. foreachRDD 里建数据库连接的正确位置在哪？为什么不能建在 Driver 且不能每行建？
7. 判断题：DStream 的窗口参数可以是任意秒数，不必是批间隔的整数倍。

@@links
参考|SparkStreaming （第 1-2 章：架构与 DStream）|#
参考|SparkStreaming （第 3-4 章：有状态与窗口）|#
官网|Spark Streaming 编程指南|https://spark.apache.org/docs/latest/streaming-programming-guide.html
官网|Spark Streaming 性能调优|https://spark.apache.org/docs/latest/streaming-programming-guide.html#performance-tuning