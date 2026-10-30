@@h1 第五章　Spark On YARN 与 spark-submit
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★

@@why 这一章在解决什么问题
上一章你搭了 Spark 自己的 Standalone 集群。但真实企业里，Hadoop 生态往往**早就存在**：HDFS 存数据，YARN 管资源。这时候再为 Spark 单独搭一套 Standalone，等于**同一个机房养两套资源调度**——浪费、难管、还容易打架。企业的标准答案是：**让 Spark 跑在 YARN 上**，和 MR、Flink、Tez 等框架**共享同一批资源**。

本章你要理解 YARN 是谁、Spark On YARN 的两种部署方式（Client/Cluster）区别，并把 `spark-submit` 讲透——它也是后面所有章节提交任务的通用姿势。

学完这一章，你能：**把 Spark 程序以 YARN 模式提交到 Hadoop 集群，并能说清 Client/Cluster 两种方式的差异与选型**。

@@prep 开始之前
最好手上有一套 Hadoop/YARN 环境；没有也别卡住，重点看两种部署方式的区别和提交参数。

@@goal 学到这儿就够了
能说清 Client 与 Cluster 的选型差别，会用 spark-submit 提交到 YARN，这章就算过了。

@@map 这一章在整个知识库里的位置
上一章（Standalone）：你有了 Spark 自己的多机集群，理解了 Master/Worker/HA
**本章** ← 你在这里：让 Spark 寄生在 Hadoop 的 YARN 上——企业主流生产形态
下一章：RDD 数据抽象——从"部署环境"转回"编程模型"，开始学 Spark 的核心 API
再往后：RDD 创建/算子 → 内核调度 → 实战项目 → SparkSQL/Streaming
阶段终点：你能独立完成 Spark 从部署、编程到调优的全链路

@@note info 学习提示
本章是部署主线的最后一环。如果你没有 Hadoop 环境，重点理解**两种模式的区别和 spark-submit 参数**；有环境就照着示例把 On YARN 任务提交一遍。

@@point ① YARN 是谁：Hadoop 的资源调度平台
@@need 要解决什么
你听说过 YARN 但不知道它到底管什么。**先讲清它解决什么问题**：一个大数据平台同时跑 Spark、MapReduce、Flink，如果每个框架各管各的机器资源，有的忙死、有的闲死，还互相抢。YARN 就是那个**统一的资源房东**——所有框架都向它租房。

@@idea 核心思路
YARN（Yet Another Resource Negotiator）核心角色：

| 角色 | 类比 | 职责 |
|---|---|---|
| ResourceManager（RM） | 总房东 | 全局资源分配，我们提交任务的入口 |
| NodeManager（NM） | 分房东 | 每台机器上的管理者，启动/监管容器 |
| ApplicationMaster（AM） | 包工头 | **每个应用一个**，向 RM 申请该应用需要的资源、调度任务 |
| Container | 一间房 | 分配到的内存+核数的单元，Executor 就住在里面 |

关键认知：**Standalone 的 Master/Worker 和 YARN 的 RM/NM 是同一件事的两个实现**——都是"资源房东"。Spark 换到 YARN 上，只是把"谁当房东"从 Spark 自己换成了 Hadoop。

```text
      Spark On YARN 架构
Driver ── 提交给 ──> ResourceManager
                         │ 分配 AppMaster + Containers
                         ▼
                   NodeManager(node1/2/3)
                     └─ Container 里跑 Executor
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 YARN 是"大数据计算框架" | YARN 不计算，只**分配资源**。算的是跑在它容器里的 Spark/Flink/MR |
| 混淆 ResourceManager 和 NodeManager | RM 是全局唯一的"总房东"；NM 每台节点一个"分房东"。改配置时 `yarn-site.xml` 里两者配置项不同 |
| 以为 Spark On YARN 后 Standalone 就没了 | 两种模式都存在：企业有 Hadoop 用 YARN，独立小集群用 Standalone。按现有环境选，不是取代关系 |

@@point ② 为什么要 On YARN：资源统一 + 数据本地性
@@need 要解决什么
"我没 Hadoop 也能跑 Spark，为什么企业非要 On YARN？"——这个问题不解决，你不懂生产为什么这么选。本点给两个**硬理由**，让你面试/答辩都能讲出来。

@@idea 核心思路
两大理由：

**① 资源统一管控。** 公司一台 64 核机器，MR 和 Spark 都想用。各自为政会一个占满一个饿死。YARN 统一分配：你给 Spark 队列 30 核、给 MR 队列 30 核，互不越界。还可以**多租户**：多个团队共用一套集群，配额清清楚楚。

**② 数据本地性（Data Locality）。** 数据存在 HDFS 上（node1 有两块，node2 有三块……）。YARN 知道数据在哪台机器的哪个块，调度时**优先把 Executor 放到数据所在机器**，任务读本地数据不走网络——这是大数据性能的第一大杀器。

```text
NodeManager 调度优先级：
本地节点（同机数据）> 同机架 > 跨机架
任务尽量"数据在哪，计算就在哪"
```

一句话：**On YARN = 资源共享 + 计算跟着数据走**，这是单机/独立集群给不了的。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 YARN 只对 Spark 有用 | YARN 是通用资源层，MR/Flink/Spark 都可跑。你这家公司可能 Hadoop 先在了，Spark 才"寄人篱下" |
| 以为数据本地性在 Standalone 里没有 | Standalone 也尽量本地，但**没有 YARN 对数据位置的精确调度**。数据在 HDFS 时 On YARN 的本地率一般更高 |
| 把"资源共享"理解成"谁都能抢" | 是**按队列/配额**分，不是抢。YARN 的 Capacity Scheduler 保证不饿死别人 |

@@point ③ 两种部署模式：YARN Client 与 YARN Cluster
@@need 要解决什么
`--deploy-mode client` 和 `cluster` 让你选择困难。它们的差别**只有一件事：Driver 跑在哪**。搞清楚这个，你就能根据场景选对模式——这是 Spark On YARN 最常被问、也最容易答错的知识点。

@@idea 核心思路

| 维度 | YARN Client | YARN Cluster |
|---|---|---|
| Driver 跑在哪 | 提交任务的机器（本地进程） | YARN 容器里（集群内） |
| 谁提交 | Driver 先起，再去 RM 申请 Executor | 先提交 AM，AM 里再起 Driver |
| 日志看哪 | 看提交机终端（方便调试） | 看 YARN 的 container 日志（有 web 界面） |
| 适用 | 开发调试、交互式 spark-shell | 生产任务（脚本提交、定时调度） |
| 退出后 | 终端退出=Driver 没了=任务没了 | 终端可关闭，Driver 在集群里继续跑 |

生产选型口诀：**调试用 Client（日志直观），上线用 Cluster（任务不依赖提交机在线）**。

```bash
# 开发调试：Driver 在本地，终端直接看日志
spark-submit --master yarn --deploy-mode client app.py

# 生产提交：Driver 进集群，提交完终端可关
spark-submit --master yarn --deploy-mode cluster app.py
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 生产任务用 client，关了终端任务就没了 | client 模式 Driver 在本地，**终端一关 Driver 被杀**。要长期跑的任务必须 cluster |
| cluster 模式找不到日志 | 日志在 YARN Web UI（RM 的 8088 端口 → 该 application → logs）。去那看，不在本机终端 |
| `--master yarn` 但没写 deploy-mode | 默认是多少取决于配置，一般默认 client。**显式写清楚**，别靠默认值 |
| 搞混"yarn"和"yarn-client"/"yarn-cluster" | 旧写法 `--master yarn-client` 现在是 `--master yarn --deploy-mode client`。3.x 统一成 master+yarn + deploy-mode |

@@point ④ spark-submit 全参数：一份命令读完整
@@need 要解决什么
spark-submit 参数十几个，网上表格各有侧重，真用时还是懵。本点给一份**按"角色"归类的参数地图**——资源类、环境类、程序类，让你拿到任何一份 submit 命令都能快速读懂、按需改。

@@idea 核心思路
```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name "DailyReport" \
  --queue default \
  --num-executors 10 \
  --executor-cores 2 \
  --executor-memory 4g \
  --driver-memory 2g \
  --conf spark.default.parallelism=40 \
  --jars deps.jar \
  --class com.demo.Report main.jar  2026-10-14
```

按角色分组：

| 分组 | 参数 | 一句话 |
|---|---|---|
| 集群连接 | `--master` / `--deploy-mode` | 连谁、Driver 在哪 |
| 资源 | `--num-executors --executor-cores --executor-memory --driver-memory` | 要多少房、多大房 |
| 环境 | `--name --queue --jars --packages` | 显示名、队列、依赖 |
| 调优 | `--conf key=value` | 一切 Spark 配置的兜底入口 |
| 程序 | `--class` + 位置参数 | 主类 + 传给 main 的参数 |

**记忆锚点**：资源四件套（executors/cores/memory/driver）是日常改最多的；`--conf` 是万能钥匙，任何 `spark.*` 配置都能从这传。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `--queue default` 不存在的队列 | YARN 按队列限资源，队列名写错直接拒绝（`Queue default not found`）。去 YARN 看实际队列名 |
| 报 `Application ... is rejected by queue` | 配额不够：请求资源超过队列上限（如队列 max 20 核你要 30）。调小 num-executors，或让管理员扩队列 |
| `--jars` 的依赖没生效 | 依赖 jar 要能被所有节点访问（HDFS 路径最稳），本地路径只有提交机能读。传 `hdfs://node1:9000/libs/xxx.jar` |
| 提交命令忘了加 `--class` 的程序 | 无主类直接报 `Main class [org.apache.spark.deploy.SparkSubmit] not found` 之类——先确认 `--class` 写的是你自己 jar 里的主类全名 |

@@point ⑤ 动态资源与并行度：--conf 控制粒度
@@need 要解决什么
集群是大家的，你写死 40 个 Executor 太浪费、10 个又太慢。**动态资源分配**让 Spark 按需伸缩——空闲缩、高峰扩。但"动态"不是默认开的，配错还会白折腾。本点把开关和配套说清。

@@idea 核心思路
开启动态资源（在企业，一般集群级统一开好）：

```bash
--conf spark.dynamicAllocation.enabled=true \
--conf spark.dynamicAllocation.minExecutors=2 \
--conf spark.dynamicAllocation.maxExecutors=50 \
--conf spark.shuffle.service.enabled=true   # YARN 下建议同时开
```

配合的并行度概念：

| 配置 | 作用 |
|---|---|
| `spark.default.parallelism` | 默认分区数（shuffle 后、未指定时新 RDD 的分区数） |
| `spark.sql.shuffle.partitions` | SQL 类 shuffle 默认分区（默认 200） |

**经验值**：分区数 ≈ 总核数 × 2~3（每个核 2~3 个 task 轮流跑，摊平不均匀）；`spark.sql.shuffle.partitions` 别用默认 200 硬背，按数据量调。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 开了动态资源却没伸缩 | `spark.shuffle.service` 必须配套；且 Spark 3.x 里本地 shuffle 服务是基本要求，不开会导致 Executor 回收后 shuffle 数据丢失（`FetchFailed`） |
| 动态分配和 `--num-executors` 同时写 | 冲突。动态分配开启时 `num-executors` 是**初始**值，范围由 min/max 控制。要么固定要么动态，别又全又乱 |
| 以为 `default.parallelism` 控制一切 | 它只管"未指定时的默认"。`textFile` 明着给了 `minPartitions`、`groupByKey` 也有自己的分区逻辑——最终 Task 数以日志为准 |

@@point ⑥ 生产参数模板：一份能抄的 submit
@@need 要解决什么
参数单独认识是一回事，**组合成一份能直接用的命令**是另一回事。本点给一份经过调优的"生产模板"以及每行的理由——你以后写 submit 照这个结构来，出错率大幅下降。

@@idea 核心思路
```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --name "Stage13Manual" \
  --queue default \
  --num-executors 8 \
  --executor-cores 2 \
  --executor-memory 4g \
  --driver-memory 2g \
  --conf spark.sql.shuffle.partitions=64 \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  --class com.demo.Main app.jar /data/input /data/output
```

模板理由（每条都有依据）：

- 8 executor × 2 core × 4g：均衡起步，不给单 Executor 超过 5g（更大单 Executor 对 GC 不友好）
- `shuffle.partitions=64`：中等数据量，别用默认 200 空转
- 动态分配关掉：定时任务按固定资源跑更可预期
- KryoSerializer：默认 Java 序列化慢，Kryo 省空间省时间（自定义类需注册）

**改动原则**：模板是起点不是终点，根据数据量、集群规格微调这三个维度——数据总量、可用核数、单条数据大小。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 单 Executor 内存贪大（如 32g） | 内存大 GC 暂停时间长、故障面大。通用建议 4~8g，核 2~4；超大单 Executor 是新手最爱踩的坑 |
| 用 Kryo 但不注册类 | 不注册也能跑（自动反射），但失去性能意义且警告刷屏；自定义数据类用 `--conf spark.kryo.registrator=...` 注册 |
| 改参数"感觉没用" | 每个参数有没有生效，看 Web UI → Environment 标签页里的**生效值**。改完先确认 Spark 真读到了，别在猜 |

@@point ⑦ 一次提交的生命周期：从 submit 到完成
@@need 要解决什么
参数懂了，但"一条 submit 命令跑出去之后，后台到底发生了什么"——串起来你才能真正排查问题。本点把 **YARN Cluster 模式**全流程按时间串一遍，这是架构知识的总复习。

@@idea 核心思路
以 `--deploy-mode cluster` 为例：

```text
① 本机 spark-submit 把 jar 传给 RM
② RM 分配一个 Container，启动 ApplicationMaster（AM）
③ AM 内部启动 Driver（跑你的 main）
④ Driver 就在 AM 进程内（cluster 模式），它直接用 AM 的 AMRMClient 向 RM 申请 executors 的 Container
⑤ RM 在 NodeManager 上启动 Executor 容器并回注册
⑥ Driver 把 DAG 切成 Task 调度到 Executor 执行
⑦ 任务完成，Driver 向 AM 汇报，AM 让 RM 释放所有 Container
```

每一步对应你会在日志/UI 看到的东西：

| 步骤 | 观察点 |
|---|---|
| ① | RM Web UI (8088) 出现 application SUBMITTED |
| ②③ | application 变 ACCEPTED/RUNNING，AM 启动 |
| ④⑤ | Executors 页出现 N 个 Executor 并注册 |
| ⑥ | Jobs/Stages 页开始刷进度 |
| ⑦ | 状态变 FINISHED，容器释放 |

**排查口诀**：Application 卡在哪个状态，问题就出在哪一步——SUBMITTED/ACCEPTED 不动查资源队列；RUNNING 里 Executor 起不来查 Worker 上日志；FINISHED 但结果错查你代码逻辑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只看 application 状态不看阶段 | 状态机每一格的卡点含义不同。**按上面表格逐格对照**，别一句"任务失败了"就完事 |
| Cluster 模式里 term 关了任务还在跑 | 对，这就是设计：Driver 在集群里与提交机无关。想停任务用 `yarn application -kill <app-id>` |
| 误以为 Executor 数是固定的 | 动态分配开时 Executor 会增减。看**当前时刻** Executors 页，别拿"申请数"说"实际数" |

@@point ⑧ On YARN 常见故障速查
@@need 要解决什么
讲部署不讲排障是耍流氓。本章最后给一份 **On YARN 高频故障速查表**：遇到这些报错，直接对号入座，少走弯路。后面 13 章遇到"任务起不来"都能回来查这页。

@@idea 核心思路
| 报错/现象 | 根因 | 处理 |
|---|---|---|
| `Queue ... not found` / 提交被拒 | 队列名错/配额超限 | 查实际队列名；调小资源或找管理员 |
| 任务一直 ACCEPTED 不 RUNNING | 资源不足在排队 | 调小 num-executors/内存；看 YARN 队列利用率 |
| `Container ... beyond virtual memory limits` | 容器内存超限被杀 | 加 `yarn.nodemanager.vmem-check-enabled=false`（谨慎）或调大容器内存 |
| Executor 起不来反复重启 | 提交机/节点 classpath 缺依赖 | 把所有依赖 `--jars` 放 HDFS |
| `ApplicationMaster ... killed` | Driver OOM 或被杀 | 加 `--driver-memory`；看 AM 日志确认 |
| Shuffle FetchFailed 随机出现 | 动态资源+executor 被回收 | 开 `spark.shuffle.service` 或关动态分配 |
| 8088 能开 8080 打不开 | 你找错端口了 | On YARN 没有 8080（那是 Standalone Master 的），全在 YARN 侧看 8088 |

记忆方法：故障 = **资源（队列/内存/核）问题占八成**。先查资源，再查代码。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 一报错就慌着改代码 | On YARN 的错大半在**资源/环境**层。先按速查表排除资源类，再怀疑代码 |
| 把 Standalone 的排查习惯带过来 | Standalone 看 8080/7077，YARN 看 8088/container 日志。**先分清你现在跑在哪个模式** |
| 只学"这个报错这样解"不求甚解 | 每条根因都是**资源/内存/依赖/权限**四类之一。记住这四类，新报错也能归因 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **企业形态认知**：为什么 Spark 跑在 YARN 上 | 资源共享 + 数据本地性，这是生产的硬道理 |
| **模式选型**：Client 调试 / Cluster 上线 | Driver 在哪决定了它俩的一切区别 |
| **submit 全套能力**：参数地图 + 模板 + 生命周期 + 故障速查 | 以后所有任务的"提交-排查"一条龙 |

@@quiz
1. YARN 的 ResourceManager、NodeManager、ApplicationMaster 分别是什么角色？
2. YARN Client 和 YARN Cluster 的本质区别是什么？生产定时任务选哪个？
3. 你的任务一直 ACCEPTED 不 RUNNING，最可能的原因和排查动作是什么？
4. 为什么企业愿意把 Spark 放上 YARN 而不是自己再搭一套 Standalone？
5. 报 `Container beyond virtual memory limits`，原因和至少一种处理方式是什么？
6. 判断题：Spark On YARN 模式下，Spark 自己的 8080 Web UI 依然可用（选错说明你还没分清两种模式）。

@@links
参考|Spark 分布式计算框架基础（第 5 章：Spark On YARN）|#
官网|Spark 提交应用文档|https://spark.apache.org/docs/latest/submitting-applications.html
官网|Apache Hadoop YARN 文档|https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/YARN.html
资料|spark-submit 示例脚本|#