@@h1 第十七章　Spark Streaming 实战：Kafka 接入与生产调优
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　|　难度 ★★★★☆

@@why 这一章在解决什么问题
上一章的 Socket 输入只是教学玩具——**生产环境 90% 的流都来自 Kafka**，因为 Kafka 能存能重放、天然支持"消费状态"管理。而接入 Kafka 有新旧两代 API（Receiver vs Direct），踩的人最多；消费偏移量（offset）管理不当=丢数据或重复消费；Driver 挂掉怎么优雅恢复……这一章把"生产级 Streaming + Kafka"的完整配套讲透：**Direct 模式、偏移量管理、优雅关闭、背压调优**。

学完这一章你能：**用 Direct 模式从 Kafka 消费实时数据做统计，配置偏移量与 checkpoint 保障不丢不重，并让程序可以优雅停止与恢复**。

@@map 这一章在整个知识库里的位置
上一章：Streaming 基础（架构、DStream、窗口、有状态）
**本章** ← 你在这里：生产实战——Kafka 整合、偏移量、优雅关闭、调优
下一章：阶段综合实战与回顾（批+流全链路）
阶段终点：真正的"实时数据处理工程师"入门装备

@@point ① Kafka 是什么：先把"消息枢纽"讲明白
@@need 要解决什么
要接 Kafka，先得知道 Kafka 是什么、术语怎么读：**Topic（主题）/ Partition（分区）/ Consumer Group（消费组）/ Offset（偏移量）**。这四个词后面全要用，本点用一张生产者-消费者图讲透。

@@idea 核心思路
**Kafka 角色模型**：

```text
生产者(Producer)  ──发送消息──▶  Kafka 集群               ◀──拉取──  消费者(Consumer)
                                └─ 按 Topic 分到多个 Partition（有序日志）
                                └─ 每个 Partition 的消息有唯一 Offset（位置编号）
                                └─ 消息有保留期（如 7 天，过期才删）
```

**四个必懂术语**：

| 术语 | 一句话 | 和 Spark 的关系 |
|---|---|---|
| Topic | 一类消息的通道（如"订单事件"） | Spark 从某个 Topic 消费 |
| Partition | Topic 的物理分片（并行度来源） | Spark 分区可以和 Kafka 分区 1:1 映射 |
| Consumer Group | 一组消费者共享消息（同组内一条消息只消费一次） | Spark Streaming 就是"一个大消费组" |
| Offset | 消息在分区里的位置编号 | **消费到哪了**，恢复时接着走 |

**Spark ↔ Kafka 数据流**：

```text
Kafka Topic(t1) 有 3 个 Partition
      │  每个 Kafka 分区 → 对应一个 Spark 任务分区
      ▼
Spark 每批读"当前 offset 之后的新消息" → 算 → 输出 → 记录新 offset
```

**为什么用 Kafka 不用 Socket**：Kafka 是**分布式日志**——消息持久化可回放、多消费者共享、offset 可管理。Socket 是教具，Kafka 是生产。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 Topic 当"队列" | Kafka 是"可重放的日志"，不是用完即删——消费完消息还在（保留期内），**可以重新消费**。这正是 offset 管理的底气 |
| Partition 数和并行度搞混 | Kafka 分区数是"可消费并行度上限"。配 Spark 并行度时参考它：分区太少并行度上不去 |
| 消费组名乱设 | **同组共享消息**（组内一条消息只被一个消费者读）。不同组=各读各的。Spark 作业的 group.id 要么全局唯一、要么与"从哪续读"的语义匹配 |
| Topic 数据越来越多爆盘 | Topic 有保留期/容量配置。真实运维要设 retention，学习时知道有这回事即可 |

@@point ② Receiver 模式（旧）vs Direct 模式（新）：为什么必须用 Direct
@@need 要解决什么
Spark 接 Kafka 曾有两种 API：**Receiver-based（旧）** 和 **Direct（新）**。旧模式有致命缺点（WAL 疲于应付、offset 存 ZooKeeper 与消费不同步、重复消费），官方已废弃。**永远用 Direct 模式**是本节最重要的结论，并附上原因帮你在面试时讲得清。

@@idea 核心思路
```text
Receiver 模式（已废弃，认识即可）：
  Kafka →(Receiver 常驻接收)→ 内存 →(WAL 落盘)→ Spark 处理
  缺点：① Receiver 挂了丢内存数据 ② offset 存 ZK 与消费不同步→重复/丢
       ③ 接收和处理两个阶段，多一次搬运

Direct 模式（Spark 1.3+，唯一正确）：
  Spark 直接在 Executor 上从 Kafka 分区拉取，每个 Kafka 分区 = 一个 RDD 分区
  优点：① 无 Receiver，少一次搬运 ② offset 由 Spark 管理（checkpoint）
       ③ 精确一次语义（配合事务）成为可能
```

**Direct 模式的三好**：

1. **并行度天然对齐**：Spark 分区数 = Kafka 分区数，没有"Receiver 单点瓶颈"
2. **不需要 WAL**：数据直接从 Kafka 拉（Kafka 自己就是持久化存储），丢数据的窗口消失
3. **offset 可控**：偏移量由代码/checkpoint 管理，可回放可重置——"数据出问题，从三天前重放"是常态操作

**一句话结论**：**生产用 Direct，不要再用 Receiver**（旧代码报错/日志也会提示你迁移）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 教程里还在讲 Receiver API | 那是老教程。看 `createDirectStream` 才对了；见到 `KafkaUtils.createStream` 直接跳过 |
| Direct 模式下并行度想调大 | 并行度上限=Kafka 分区数。想加大：Kafka 侧多开分区（repartition），不是 Spark 侧 repartition |
| 以为 Direct 完全不需要 checkpoint | 状态/元数据恢复仍靠 checkpoint；但"数据本身"在 Kafka，不怕 Executor 挂。两者分工不同 |
| Receiver 模式重启丢一批数据 | 这就是废弃它的原因之一。切 Direct 后，数据源变成"Kafka 可重放"，丢数据窗口消失 |

@@point ③ Direct 模式代码：从 Kafka 创建 DStream
@@need 要解决什么
动手环节：**用 createDirectStream 从 Kafka 拉数**。给出生产级写法（含参数表、泛型、依赖提示），并解释每个关键参数的作用——这是"能抄着跑通"的一节，抄完要能讲清每行。

@@idea 核心思路
```scala
import org.apache.spark.streaming.kafka010._

// ① Kafka 消费者参数
val kafkaParams = Map[String, Object](
  "bootstrap.servers" -> "kafka01:9092,kafka02:9092",
  "group.id" -> "spark-analytics",
  "auto.offset.reset" -> "earliest",
  "enable.auto.commit" -> (false: java.lang.Boolean))  // offset 由我们管

// ② Direct 模式：直接创建 DStream
val stream = KafkaUtils.createDirectStream[String, String](
  ssc,
  LocationStrategies.PreferConsistent,
  ConsumerStrategies.Subscribe(Array("user_events"), kafkaParams))

// ③ 取 value 才是业务数据
val lines = stream.map(_.value())
```



**参数表**：

| 参数 | 含义 | 生产建议 |
|---|---|---|
| bootstrap.servers | Kafka 集群地址列表 | 全量 broker，至少 2 个 |
| group.id | 消费组 | 全局唯一且稳定 |
| auto.offset.reset | 无 offset 时从哪开始 | earliest（全量重放）/ latest（只接新的） |
| enable.auto.commit | 是否自动提交 offset | **false**（手动管，防丢/防重） |

**依赖提示**：`spark-streaming-kafka-0-10_2.12` 依赖（版本要和 Spark 匹配），本地开发要先 `--packages` 或加 jar。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ClassNotFound: kafka010 相关类 | 缺 `spark-streaming-kafka-0-10` 依赖。`--packages org.apache.spark:spark-streaming-kafka-0-10_2.12:<版本>` 带上 |
| 消息取出来是 `ConsumerRecord` 不是字符串 | `createDirectStream` 返回的是记录流，必须 `.map(_.value())`（或 `.key()`）取业务数据。直接用报类型错 |
| `auto.offset.reset` 写错单词 | 它是 `auto.offset.reset`，值 `earliest`/`latest`（注意不是 small/largest）。大小写敏感 |
| Kafka 版本和 spark-streaming-kafka 不搭 | 0-10 依赖对 Kafka 0.10+ 都兼容新版本 broker 基本没压力；遇到 API 报错先核对依赖版本 |

@@point ④ 偏移量管理：不丢不重的关键
@@need 要解决什么
流的"账本"就是 offset：**消费到哪了**。不管理 offset 的后果：程序重启从头消费（重复爆炸）或跳过一批（丢数）。Direct 模式给了你"手动控制权"，本点给出三种策略与推荐方案：**checkpoint 自动存 / 手动提交 / 外部存储**。

@@idea 核心思路
**offset 在哪管的三条路**：

```text
方式一：checkpoint 自动存（默认推荐起步）
   Spark 把 offset 与状态一起 checkpoint。
   ✅ 简单   ❌ 升级/换代码后 checkpoint 不可用（兼容性问题）

方式二：手动提交（enable.auto.commit=false）
   在 foreachRDD 处理成功后，把"本批已消费的 offset"提交
   ✅ 精确控制   ❌ 处理失败时小心重复

方式三：外部存储（生产最佳实践）
   offset 存 Redis/MySQL/HDFS，恢复时自己读
   ✅ 与代码解耦、可审计   ❌ 要自己实现存储逻辑
```

**方式二的代码形态**：

```scala
stream.foreachRDD { rdd =>
  val offsetRanges = rdd.asInstanceOf[HasOffsetRanges].offsetRanges  // 本批各分区 offset
  // ... 处理并输出（成功后才提交）
  stream.asInstanceOf[CanCommitOffsets].commitAsync(offsetRanges)   // 提交
}
```

**消费语义三档（面试必答）**：

```text
At-most-once：处理前提交 offset → 挂了丢数据（不推荐）
At-least-once：处理后提交（可能重复）→ 常见默认，配合幂等输出
Exactly-once：output + offset 事务化 → 最强，工程成本最高
```

**推荐组合**：**checkpoint 或外部存 offset + 输出幂等** = 生产通用配置。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 程序重启重复消费最近几批 | 提交时机不对（处理**前**提交了）或 checkpoint 恢复点落后。改成"处理成功后再提交"；输出要幂等 |
| 想改消费起点（重放某段） | Direct 可指定起始 offset：`ConsumerStrategies.Subscribe(topics, params, offsets)` 传入指定偏移量——这是"修数据"的救命手段 |
| checkpoint 里 offset 与外部进度不一致 | 别两套混管（checkpoint+手动提交同时用会打架）。选一条路管理 |
| commitAsync 失败没察觉 | commitAsync 是异步的；要确认用 `commitSync`（阻塞）或回调检查。生产对"提交成功"要有水位告警 |

@@point ⑤ 优雅关闭（Graceful Shutdown）：让 Driver 体面退场
@@need 要解决什么
生产上下线、发布新版本时直接 kill 进程会怎样？——**正在处理的那批任务被腰斩、offset 错乱、checkpoint 损坏**。优雅关闭（Graceful Shutdown）让程序"处理完手头这批、提交完 offset、再退出"，是生产发布的基本修养。

@@idea 核心思路
**优雅关闭的三要素**：

```text
① 收到停机信号（如 kill -TERM / 配置文件开关 / HTTP 接口）
② 停止接收新批（不再产生新的 Job）
③ 等正在执行的批跑完 → 提交 offset → 才真正退出
```

**两种实现**：

```scala
// 方案 A：StreamingContext 自带机制（配合外部信号轮询）
ssc.stop(stopSparkContext = false, stopGracefully = true)
// stopGracefully=true 才是优雅：等当前批处理完再停

// 方案 B：自定义监听（Spark 2.3 起，StreamingListener 或主线程轮询标志）
// 被保护：StreamingQueryListener / check 全局 flag → ssc.stop(true, true)
```

**生产常见的"优雅停止"套路**：

```text
用调度系统（如 YARN 的 preempt / K8s 的 SIGTERM）→ 程序捕获信号
→ 设置"停止标志"（或直接调 stopGracefully）
→ 最后一批完成后 Driver 退出 → 下次启动从 checkpoint 接着消费
```

**配套要求**：优雅关闭能否"接着从停点消费"，依赖第④点的 checkpoint/offset 存储——**停止与恢复是一对**，别只实现一半。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Ctrl+C 直接 kill -9 | 组内任务被腰斩。生产用 `kill -TERM`（SIGTERM）让程序自己收尾；kill -9 是最后手段 |
| 优雅关闭后重启重复一批 | 最后一批"跑了但没提交 offset"→ 重启会重放（at-least-once）。正常！输出幂等即可 |
| stop(sparkContext=true) 误杀 | `stop(sparkContext=true)` 会连 SparkContext 一起停（如果还有别的作业用它就崩）。只停流：false |
| 优雅关闭等待时间过长 | 某批处理卡住会让关闭卡住。配超时：关闭触发后 N 秒强杀（列队不能无限等） |

@@point ⑥ 背压与并行度调优：让"处理速度"跟上"数据速度"
@@need 要解决什么
数据来得比算得快会怎样？——**一批没算完下一批又开始，内存积压、延迟暴涨**。两个解法：**背压（Backpressure）**让系统自动限速；**并行度调优**让处理更快。本点给出 Streaming 性能体检表和针对动作。

@@idea 核心思路
**核心指标**：处理耗时 vs 批间隔

```text
每批处理耗时 < 批间隔 → 健康（有空闲）
每批处理耗时 ≈ 批间隔 → 临界
每批处理耗时 > 批间隔 → 积压！批队列越排越长（延迟飙升）
```

**第一招：背压（自动限速）**：

```scala
// Spark 2.x：默认开启（spark.streaming.backpressure.enabled=true）
// 系统根据处理能力自动限制每秒拉取量，防止积压
// 可配最低速率：spark.streaming.backpressure.initialRate=... 控制起步
```

**第二招：并行度与资源**：

```text
① 分区数对齐 Kafka 分区：并行读 = Kafka 分区数
② 宽依赖（reduceByKey/窗口）增加分区：重分区或调 shuffle 分区数
③ 批间隔：处理不过来 → 适当加大批间隔（延迟容忍内），或加 Executor
```

**第三招：内存**：

```text
窗口长 → 缓存批多 → 内存要够（spark.executor.memory）
Task 序列化溢出 → 调 spark.memory.offHeap 或减少同时缓存
```

**体检流程**（照做）：UI 看"每批处理时长"→ 超间隔先开背压 → 还不够就加并行度/分区/资源 → 再不行加大批间隔。**先处理后限速，最后才加间隔**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 背压开了还积压 | 背压只是"限速"，不解决"算得慢"本身。查瓶颈：窄依赖算子慢（单点）还是 shuffle 慢（分区/倾斜） |
| 批间隔调大后报表延迟变大 | 延迟=批间隔的量级，业务要 5 秒就要 5 秒内算完，调大间隔是最后手段 |
| Kafka 分区 1 个，并行度上不去 | 上游 Topic 分区太少=天花板。加主题分区（Kafka 侧）或消费后 repartition 摊开 |
| 内存不大但窗口很长 | 窗口把多批数据都缓存着。缩短窗口/加大内存/减少同时缓存（多窗口分散时段）三选一 |

@@point ⑦ Structured Streaming：新一代"结构化流"（前瞻）
@@need 要解决什么
Spark 2.x 起官方主推 **Structured Streaming**：用 DataFrame API 写流，语法和批处理**几乎零差别**，还自带事件时间、窗口、故障恢复。了解它，你就知道"学完 DStream 后下一步往哪走"——本点做概览对比，不深入细节。

@@idea 核心思路
```python
# Structured Streaming：写法和静态 DataFrame 几乎一样！
from pyspark.sql.functions import *

df = spark.readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "...") \
  .option("subscribe", "user_events") \
  .load()

# 解析 + 聚合（就是普通 DataFrame API！）
parsed = df.selectExpr("CAST(value AS STRING) as json")...
agg = parsed.groupBy(window(col("ts"), "1 minute"), col("city")) \
             .count()

# 输出：writeStream 而不是 write
query = agg.writeStream \
  .outputMode("complete") \
  .format("console") \
  .start()
query.awaitTermination()
```

**DStream vs Structured Streaming 对照**：

| | DStream（本阶段） | Structured Streaming |
|---|---|---|
| API | RDD 风格 | DataFrame/DSL/SQL 风格 |
| 学习曲线 | 先学本阶段 | 学了前 15 章直接上手 |
| 优势 | 成熟、灵活底层 | 语义简单、自动优化、Exactly-once 内置 |
| 定位 | 理解流本质 | 生产首选（新项目） |

**给你的路线**：先把 DStream 的思想学透（微批次/窗口/状态/offset），再切 Structured Streaming——**思想完全通用，只是换 API**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 DStream 的 API 套到 Structured Streaming | 两个 API 不同源：DStream 算子（flatMap/reduceByKey）和 DF API（select/groupBy）不通用。新项目直接学 Structured Streaming |
| 以为 DStream 被彻底淘汰 | 老项目大量在用，且思想通用。两条都会更稳 |
| 输出模式 complete/append/update 搞混 | complete=全量结果；append=只新结果；update=更新行。选错报警——去读官方文档对应语义即可 |
| Python 里没有 DStream | PySpark 只支持 Structured Streaming。学 DStream 用 Scala 示例，理解为主 |

@@point ⑧ 全链路串讲：一份"生产就绪"的 Streaming 作业配置
@@need 要解决什么
前面知识点各有各的坑，最后把它们**串成一份能上生产的完整配置清单**：从提交命令到代码骨架到监控，一个不漏。照着这份清单核对，你的作业才配叫"生产就绪"。

@@idea 核心思路
**生产就绪五件套（缺一不可）**：

```text
① Direct 模式接 Kafka（第③点）
   createDirectStream + group.id 全局唯一 + 手动管 offset

② offset 与状态恢复（第④点）
   checkpoint 目录（HDFS，别放本地）+ 处理成功后提交 offset
   → 崩溃重启从检查点续跑，不丢不重

③ 优雅关闭（第⑤点）
   捕获 SIGTERM → ssc.stop(stopSparkContext=false, stopGracefully=true)
   → 发布新版本时体面退出，不等任务腰斩

④ 背压与资源（第⑥点）
   spark.streaming.backpressure.enabled=true + 核数分区匹配
   → 数据洪峰自动限速，处理不过来不积压

⑤ 监控（容易被忽略！）
   StreamingListener 记录每批处理耗时/调度延迟，超出阈值告警
   → 积压/掉线第一时间发现，而不是业务吐槽了才知道
```

**提交命令长这样（对照检查）**：

```bash
spark-submit --master yarn --deploy-mode cluster \
  --executor-memory 4G --executor-cores 2 --num-executors 8 \
  --conf spark.streaming.backpressure.enabled=true \
  --packages org.apache.spark:spark-streaming-kafka-0-10_2.12:3.2.1 \
  --class com.demo.StreamingJob app.jar
```

**验收标准**：kill 掉 Driver 再重启 → 能从检查点续跑且不重不漏；高峰期 ui 无积压；监控告警能收到。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| checkpoint 放本地目录 | 本地路径在集群模式下各节点不共享，恢复必失败。**放 HDFS/对象存储** |
| 五件套只配了前 3 个 | 没背压=洪峰积压雪崩；没监控=故障黑盒。生产上线前逐项打勾 |
| 发布操作直接 kill -9 | 优雅关闭失效。运维流程里定义信号 → 程序捕获 → 等待收尾 |
| 本地测试通过就当生产 OK | 本地 local 模式没有集群恢复/多 Executor 语义。真正验收要在集群跑一次"杀掉重启"演练 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **Kafka + Direct 模式**：createDirectStream 生产写法 + 术语表 | 生产实时管道的"标准接法"，直接可抄可跑 |
| **offset 管理三策略 + 消费语义**：checkpoint/手动/外部存储 | 不丢不重、可回放可恢复，流式生产的"账本" |
| **生产配套**：优雅关闭、背压、处理耗时体检法 | 发布不事故、积压不失控，从"能跑"到"能运维" |

@@quiz
1. Kafka 的 Topic/Partition/Consumer Group/Offset 分别指什么？
2. Direct 模式相比 Receiver 模式的三点优势是什么？并行度由什么决定？
3. createDirectStream 得到的是 DStream[ConsumerRecord]，取业务数据要做什么操作？
4. 消费三种语义（at-most-once / at-least-once / exactly-once）各自含义？生产常用哪种+什么配套？
5. 优雅关闭为什么不能直接 kill -9？stopGracefully=true 的语义是什么？
6. 背压（backpressure）解决什么问题？处理耗时超过批间隔时按什么顺序调优？
7. 判断题：Structured Streaming 的 API 与静态 DataFrame 完全不同，需要另学一套算子。

@@links
参考|SparkStreaming （第 5 章：Kafka 整合）|#
参考|SparkStreaming （第 6 章：优雅关闭与调优）|#
官网|Spark Streaming + Kafka 集成指南|https://spark.apache.org/docs/latest/streaming-kafka-0-10-integration.html
官网|Structured Streaming 编程指南|https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html