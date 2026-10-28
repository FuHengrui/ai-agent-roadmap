@@h1 第四章　Standalone 独立部署模式与高可用
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★

@@why 这一章在解决什么问题
上一章 Local 模式把 Spark 跑通了，但 Local 是"一台机器假装集群"——**真正的生产环境要的是多台机器组成集群**：一台当老大（Master）管分配，多台当工人（Worker）跑任务。本章部署 Spark 自带的 **Standalone 模式**：不依赖 Hadoop，轻量、好理解，是你理解"集群到底是什么"的最好教材。

更重要的是：集群有个致命问题——**Master（老大）挂了，整个集群就瘫了**。本章还要带你做**高可用（HA）**：用 ZooKeeper 让集群"老大挂了自动换人"，业务不中断。这是从"能用"走向"上线"的关键一步。

学完这一章，你能：**手写 Standalone 集群的配置与启动脚本，搭出带高可用的双 Master 集群**。

@@prep 开始之前
要动手，也得有机器：三台 CentOS 节点（可一台虚拟机克隆）加 ZooKeeper，上一章的 Local 先跑通。

@@goal 学到这儿就够了
能手写 Master/Worker 配置起一套集群，再用 ZooKeeper 做 Master 高可用，这章就算过了。

@@map 这一章在整个知识库里的位置
上一章（Local 模式与 WordCount）：你在单机上跑通了第一个 Spark 程序
**本章** ← 你在这里：把程序搬到真正的多机集群（Standalone），并给它装上"老大挂了自动换人"的高可用
下一章：Spark On YARN——在 Hadoop 的资源平台上跑 Spark，企业生产主流
再往后：RDD 编程 → 内核调度 → 实战项目 → SparkSQL/Streaming
阶段终点：你能独立部署并运维一套 Spark 集群，处理 TB 级数据

@@note info 环境说明
本章需要多台机器（或虚拟机）。典型环境是 node1/node2/node3 三台 CentOS 节点，你照此拓扑练习；只有一台电脑时可用虚拟机克隆三台。

@@point ① Standalone 是什么：Spark 自带的最小集群
@@need 要解决什么
Local 模式下"进程里套进程"不算真集群，而 YARN 又依赖 Hadoop 太重。你想要一个**不装 Hadoop 就能跑起来的多机集群**——这就是 Standalone。它的价值是：人是 Spark 社区自己写的调度器，配起来最简单，还最容易看懂"Master/Worker"的概念。

@@idea 核心思路
**Standalone = Spark 内置的集群资源管理器**。它有两个角色：

| 角色 | 进程 | 干什么 |
|---|---|---|
| Master | `Master`（老大） | 管资源分配：收 Worker 上报，把 Executor 调度到 Worker 上 |
| Worker | `Worker`（工人） | 在节点上注册资源（内存、核数），按 Master 指令启动 Executor |

```text
        +----------Master----------+
        |  资源调度中枢（1~2台）    |
        +-----------+--------------+
                    | heartbeats
   +----------------+-----------------+
   |                |                 |
+--Worker--+   +--Worker--+      +--Worker--+
| Executor |   | Executor |      | Executor |
+----------+   +----------+      +----------+
      node1           node2           node3
```

和 Local 的区别：**Standalone 是真多机**，每个 Worker 在独立机器上起独立 JVM 进程，Executor 也在独立进程里——这才是生产形态。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Standalone 就是"Spark 单机版" | 恰恰相反：Standalone 是**多机集群版**，Local 才是单机版。命名容易误导，看进程数量即可区分 |
| 以为 Master 也要参与计算 | Master 只做**资源分配**，本身不算数据。它的机器可以不装数据、不跑 Executor |
| 混淆 Standalone 与 standalone 部署包 | 那个发音一样的词指"单机部署模式"？——不，Spark 术语里 Standalone 就是上面这套集群模式，别被网文绕晕 |

@@point ② 集群拓扑设计：三台机器怎么分工
@@need 要解决什么
搭集群第一件事是**规划拓扑**：谁当 Master、谁当 Worker、各台机器干什么。没规划就乱启动，节点之间谁也找不到谁。本点给出标准的三节点拓扑，这是你反复要参考的标准布局。

@@idea 核心思路
标配三节点（node1/node2/node3，建议同网段、互通 hostname）：

| 节点 | 角色 | 说明 |
|---|---|---|
| node1 | Master（主） + Worker | 老大坐镇第一台，顺便当工人 |
| node2 | Worker | 纯工人 |
| node3 | Worker | 纯工人 |

配套三件事提前做好：

1. **免密钥登录**：`ssh-keygen` + `ssh-copy-id`，让 node1 能无密码 ssh 到 node2/node3（启动脚本要远程拉起 Worker）
2. **hostname 互通**：三台机器的 `/etc/hosts` 里互相写上 ip → hostname 映射（`node1 192.168.x.1` 等），否则互相找不到
3. 时间同步（`ntpdate`），Spark 调度对时钟敏感

```cmd
# node1 生成密钥并分发
ssh-keygen -t rsa -P ""
ssh-copy-id node2
ssh-copy-id node3
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 节点间互相 `ssh node2` 却连不上 | hostname 没写进 /etc/hosts，或 ssh 服务没开。先 `ssh node2` 手动连通，通了再谈集群 |
| `start-all.sh` 只起来 Master、Worker 起不来 | 免密没配好：启动脚本用 ssh 远程启 worker，要 Key 就直接失败。`ssh-copy-id` 后手动 `ssh node2 hostname` 验证 |
| 用 IP 也能通但 Spark 内部解析怪 | Spark 集群组件按 hostname 找彼此。统一用 hostname，别 IP 一半 hostname 一半 |

@@point ③ 配置文件：spark-env.sh 与 slaves/workers
@@need 要解决什么
Standalone 启动前，Spark 需要知道"Master 在哪、Worker 有哪些"。这些写在 `conf/` 目录的配置里——**改错一行，集群起不来或互相找不到**。本点带你逐行看透两个关键配置文件。

@@idea 核心思路
在 `%SPARK_HOME%/conf/` 下，模板文件去掉 `.template` 后缀即可编辑：

**① spark-env.sh**（定义各角色环境）：

```bash
# 每台机器都要写，或只在 Master 写后同步
export JAVA_HOME=/usr/java/jdk1.8.0_x
export SPARK_MASTER_HOST=node1          # Master 所在机器 hostname
export SPARK_MASTER_PORT=7077           # 默认端口，见下方 trap
export SPARK_WORKER_CORES=2             # 每 Worker 给几个核
export SPARK_WORKER_MEMORY=2g           # 每 Worker 给多少内存
```

**② workers 文件**（旧版叫 slaves，3.x 叫 workers，一行一个 Worker 主机名）：

```text
node1
node2
node3
```

启动命令（在 Master 即 node1 上执行会使 worker 集群按 workers 文件远程启动）：

```bash
$SPARK_HOME/sbin/start-all.sh   # 或 start-master.sh + start-workers.sh
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 端口 7077 连不上 | Master 默认监听 7077 供 Worker/Driver 连接。防火墙没放行、SPARK_MASTER_PORT 写错、或 Master 没起来是第一排查顺序（`jps` 看进程） |
| 改完配置不生效 | 配置读于**启动时**：改 spark-env.sh 后必须**重启 Master/Worker**。热改不生效，这是小白最容易白等的地方 |
| 3.x 里没有 slaves 文件 | Spark 3.0+ 更名为 `workers`。网上 2.x 教程让你改 slaves，3.2.1 里没有——去改 workers |
| `start-all.sh` 报权限问题 | 脚本无执行权限：`chmod +x $SPARK_HOME/sbin/*.sh` |

@@point ④ 启动集群与验证：jps 和 Web UI
@@need 要解决什么
配置写完了，怎么确认集群真的起来了？"我以为起了"和"真起了"之间差一些验证手段。**`jps` 看进程 + 8080 端口看 Web UI** 是标准两道检查，缺一不可。

@@idea 核心思路
启动后用两个命令验证：

```bash
# 每台机器上查看 JVM 进程
jps
# 期望看到：
# node1: Master  Worker  （外加你要跑的 driver）
# node2: Worker
# node3: Worker

# 浏览器访问 Master Web UI
# http://node1:8080
# 应看到 3 个 Worker 在线，每行显示 host、cores、memory
```

"Worker 数、可用核数、内存"三列，将是你后面调并行度的依据——**Executor 申请能不能满足，全看这里有多少剩余资源**。

此外，提交任务时用 `--master spark://node1:7077`，明确告诉 Driver "资源从这套集群要"：

```bash
$SPARK_HOME/bin/spark-submit \
  --master spark://node1:7077 \
  --class com.example.WordCount \
  wordcount.jar data/word.txt
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `jps` 有 Master 但 8080 打不开 | 8080 是 Master 的 Web UI 端口，防火墙放行或用 `curl http://node1:8080` 验证；打不开先在本机 curl，分清"没起"还是"防火墙" |
| Web UI 显示 Worker 是 DEAD | Worker 进程起来了但和 Master 心跳断了：查网络、hostname 互通、时间同步。一般 `start-workers.sh` 重启 |
| `spark-submit --master` 忘写 | 不写默认 local 模式，任务在提交机器本地跑，集群白搭。**提交命令必须带 `--master spark://node1:7077`** |

@@point ⑤ 提交任务：spark-submit 完整参数
@@need 要解决什么
`spark-submit` 是从命令行把 Jar/Py 程序送上集群的唯一入口，参数多且各有用处——配错一个，任务要么本地跑、要么资源不够。本点把最常用的参数讲透，让你"看着命令能读、要改知道改哪"。

@@idea 核心思路
```bash
spark-submit \
  --master spark://node1:7077 \
  --name "MyWordCount" \
  --executor-memory 1g \
  --executor-cores 1 \
  --total-executor-cores 3 \
  --class com.example.WordCount \
  app.jar input.txt output_dir
```

| 参数 | 含义 | 对应架构角色 |
|---|---|---|
| `--master` | 连哪套资源 | Cluster Manager 地址 |
| `--executor-memory` | 每个 Executor 内存 | Executor |
| `--executor-cores` | 每个 Executor 核数 | Executor 并行度 |
| `--total-executor-cores` | 总核数上限 | 全集群 |
| `--class` | 主类（Java/Scala 程序） | 程序入口 |
| 最后两个位置参数 | 程序入参 | 你的 main(args) |

一条命令读法："我要从 spark://node1:7077 申请总 3 核、每 Executor 1 核 1g，跑 WordCount 这个类处理 input.txt，结果写 output_dir"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 任务一直"Pending"卡住 | 申请的资源**超过集群可用**（如要 10 核但 Worker 只给了 3 核）。看 8080 页面剩余资源，把 `--total-executor-cores` 调小 |
| `--executor-memory 1g` 报 "requested ... exceeds max" | Worker 内存 `SPARK_WORKER_MEMORY` 小于请求值。请求小于 Worker 分配即可（如 Worker 2g 则 executor 1g 或 1.5g） |
| 忘加 `--master` 任务跑在提交机 | 老毛病但高发。看 Web UI 的 Jobs 页 top 处显示的 master 地址，local 字样说明你又忘了 |

@@point ⑥ 高可用为什么需要 ZooKeeper
@@need 要解决什么
单 Master 有个致命伤：**Master 挂 = 集群瘫痪**（新任务进不来，旧 Executor 无法再分配）。生产环境必须容忍"老大挂了"。Spark 的答案是用 **ZooKeeper 选主**——先理解它解决什么问题，再谈配置。

@@idea 核心思路
**ZooKeeper（ZK）是一个分布式协调服务**，核心能力两条：

1. **选主**：集群里同时跑两个 Master（node1 主、node2 备），ZK 决定谁是"当前老大"，老大挂了，备胎自动上位
2. **持久化元数据**：Master 的注册信息、应用状态存 ZK，新 Master 上任能接续旧状态

高可用模式下的角色：

| 进程 | 位置 | 职责 |
|---|---|---|
| Master（Active） | node1（如） | 当前掌权，正常服务 |
| Master（Standby） | node2 | 待命，监听 ZK，Active 挂了立即上位 |
| ZooKeeper | 三台都起 | 选主 + 状态存储，共同决定"谁是老大" |

一句话：**没有 ZK 的集群是"单点故障"集群；有 ZK 的集群，老大挂了业务不断**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为开两个 Master 就自动高可用 | 两个 Master 同时 Actvie 会**脑裂**（指挥混乱）。必须由 **ZK 仲裁**谁是 Active，没有 ZK 就只开一个 Master 别作死 |
| ZK 挂一个就以为高可用失效 | ZK 是集群（通常 3 台只要 >一半在线），单台挂不影响选主。真正要保证的是 **ZK 多数派存活** |
| 以为高可用解决"Worker 挂" | 高可用保的是 **Master 不空窗**；Worker/Executor 挂由 Spark 任务重试机制兜底——两回事，别混 |

@@point ⑦ 配置高可用：spark-env.sh 三处修改
@@need 要解决什么
理论有了，动手配。**高可用配置集中在 `spark-env.sh`**，三个关键点：Master 要告诉 ZK 在哪、备胎要等 ZK 发话、启动脚本要改。一步一步来，错一个地方集群就起不全。

@@idea 核心思路
编辑所有节点的 `conf/spark-env.sh`（三处）：

```bash
# ① 声明使用 ZK 做高可用
export SPARK_DAEMON_JAVA_OPTS="-Dspark.deploy.recoveryMode=ZOOKEEPER \
  -Dspark.deploy.zookeeper.url=node1:2181,node2:2181,node3:2181 \
  -Dspark.deploy.zookeeper.dir=/spark"

# ② Active Master 所在机器（node1）加：
export SPARK_MASTER_HOST=node1
```

然后在 **node2（备胎）** 上也解压一份 Spark、配同样的 spark-env.sh，但 Master 启动方式改：备胎 Master 不主动抢权，等 ZK 通知。

启动顺序（关键）：

```bash
# 1. 先起 ZooKeeper（三台都起，命令是 zkServer.sh start）
# 2. node1 起主 Master + 两个节点起 Worker
node1: $SPARK_HOME/sbin/start-master.sh
node1: $SPARK_HOME/sbin/start-workers.sh
# 3. node2 起备胎 Master（同样 start-master.sh，ZK 会知道谁是备）
node2: $SPARK_HOME/sbin/start-master.sh
```

验证：正常时 8080 页面只有 node1 的 Master 是 ALIVE，node2 的是 STANDBY；**杀掉 node1 的 Master 进程，几秒后 node2 自动变 ALIVE**——这就是高可用在工作。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 起完两个 Master 都显示 ALIVE | 说明 ZK 配置没生效（没配 SPARK_DAEMON_JAVA_OPTS 或 ZK 没起）。先 `zkServer.sh status` 确认 ZK 三台都在，再重启 Master |
| 备胎 Master 抢权失败一直 STANDBY | 正常！备胎本该 STANDBY。**主动把主 Master 杀掉测试**，几秒内看它是否变 ALIVE |
| 改了 spark-env.sh 但 Master 没重启 | 配置只在启动时读。**改配置 → 杀 Master 进程 → 重启**，缺一步都白改 |
| 客户端提交时 master 地址写死 node1 | 高可用下应写 `spark://node1:7077,node2:7077`（逗号分隔两个候选），这样 node1 挂了客户端自动找 node2 |

@@point ⑧ 运维验证：故障演练与自检清单
@@need 要解决什么
集群搭完不验证等于没搭。**要主动做故障演练**：杀掉 Master、杀掉 Worker、停掉一个 ZK，看集群各反应。这套"自检动作"是你以后排查一切集群问题的标准打法，也最能让"高可用"从概念变成手感。

@@idea 核心思路
一套标准自检清单（建议按顺序做一遍）：

```bash
# ① 进程自检：每台 jps，确认 Master/Worker/ZK 都在
jps

# ② 页面自检：http://node1:8080 看 Worker 全 ALIVE、资源数字正确

# ③ 功能自检：提交一个 wordcount，确认真的跑在集群
spark-submit --master spark://node1:7077 ... 

# ④ 高可用自检：杀掉主 Master，看备胎几秒内 ALIVE
kill -9 <node1 Master PID>
# 浏览器刷新两节点 8080：node2 应变为 ALIVE

# ⑤ Worker 容错自检：kill 一个 Worker，看 Job 是否自动换 Executor 重跑
```

结论口径：**高可用 = Master 不空窗 + 任务不中断**；而数据不丢要靠后面学的 Checkpoint 等机制，两者配合才是完整可靠性。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 杀 Master 后任务也一起没了 | 正在跑的 Task 由 Executor 执行，Master 切换**不中断已运行的 Task**；但**新任务**要等新 Master 就绪。这是正常行为 |
| 演练把自己搞糊涂：Worker 也杀了 | 分场景演练：杀 Master 验证高可用；杀 Worker 验证容错重跑。**一次只动一个变量**，否则结果无法归因 |
| 验证完不恢复原状 | 演练后把杀掉的进程全部重启、确认集群回到 ALIVE 3 Worker 状态，再进下一章 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **真集群**：三节点 Standalone 部署与验证 | 从"单机练手"迈入"多机生产"的第一步 |
| **提交能力**：spark-submit 完整参数认识 | 后面所有任务的"上集群姿势"，一看就会调 |
| **高可用**：ZooKeeper 选主 + 故障演练 | 生产可用性的核心认知：老大挂了业务不断 |

@@quiz
1. Standalone 模式里 Master 和 Worker 分别负责什么？Master 自己算数据吗？
2. 配置文件 `spark-env.sh` 和 `workers` 分别管什么？改完配置为什么不生效？
3. 一个任务一直 Pending 不跑，最可能的原因是什么？去哪确认？
4. 为什么没有 ZooKeeper 时不能同时开两个 Master？（提示：脑裂）
5. 高可用演练的正确动作顺序是什么？（起 ZK → 双 Master → 杀主 Master → 观察备胎上位）
6. 判断题：高可用（Master 自动切换）能保证正在运行的 Task 不丢。

@@links
参考|Spark 分布式计算框架基础（第 4 章：Standalone 模式）|#
软件|spark-3.2.1-bin-hadoop3.2.tgz|#
官网|Spark Standalone 模式文档|https://spark.apache.org/docs/latest/spark-standalone.html
资料|部署脚本与示例配置|#