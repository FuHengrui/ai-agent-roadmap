@@h1 第三章　Local 模式与 WordCount 入门
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章你有了架构图，但还没见过 Spark 长什么样。**理论和代码之间隔着一道坎**：环境怎么搭、第一个程序怎么写、跑通了怎么确认"我确实在用分布式计算"？本章用最轻量的 Local 模式，让你在自己电脑上把第一个 Spark 程序（WordCount）跑通——它是编程界的"Hello World"，也是后续 15 章所有代码的起跑线。

学完这一章，你能：**在本机启动 spark-shell/pyspark，写一个能跑的 WordCount，并从 Web UI 看到它真的跑起来**。

@@map 这一章在整个知识库里的位置
上一章（Spark 架构与运行模式总览）：你有了骨架——Driver/Executor/Task 谁是谁
**本章** ← 你在这里：用 Local 模式把这个骨架第一次跑起来，写出第一个 rdd 程序
下一章：Standalone 独立部署与高可用——把"单机练手"升级成"多机集群"
再往后：YARN 部署 → RDD 五大特性与算子 → Spark 内核 → 实战项目
阶段终点：你能独立用 Spark 处理 TB 级数据的全套流程

@@note info 环境说明
本章基于 Spark 3.2.1（spark-3.2.1-bin-hadoop3.2），配套压缩包在资料「软件」目录。你的电脑需要先装好 JDK 8+ 并配好 JAVA_HOME——这一步不过，后面全是"端口/网关"报错。

@@point ① 环境准备：JDK、Spark 解压与目录结构
@@need 要解决什么
"我按教程敲了代码，怎么一跑就报 Java 相关的错？"——八成是环境变量没配。环境这部分不讲清楚，后面每次报错你都在猜。先把地基打好：**JDK 装没装、SPARK_HOME 配没配、spark 解压包里的东西是什么**。

@@idea 核心思路
三步环境准备：

```cmd
# 1. 验证 Java（Spark 是 JVM 程序，必须 JDK 8+）
java -version

# 2. 解压 spark-3.2.1-bin-hadoop3.2.tgz，记住解压目录，如 D:\soft\spark-3.2.1-bin-hadoop3.2

# 3. 配环境变量（Windows 系统属性 → 环境变量）
JAVA_HOME = C:\Program Files\Java\jdk1.8.0_xxx
SPARK_HOME = D:\soft\spark-3.2.1-bin-hadoop3.2
PATH 追加 %SPARK_HOME%\bin
```

解压后目录结构（认脸即可）：

| 目录 | 里面是什么 | 你什么时候碰它 |
|---|---|---|
| `bin/` | spark-shell、spark-submit、pyspark 等可执行脚本 | 天天用 |
| `sbin/` | start-master.sh、start-worker.sh 等启动脚本 | Standalone 模式用 |
| `conf/` | spark-env.sh、spark-defaults.conf 配置模板 | 部署/调优时改 |
| `jars/` | Spark 所有依赖 jar 包 | 一般不用手动碰 |
| `data/` | 自带示例数据 | 练手用 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `java -version` 有输出但 Spark 报"JAVA_HOME is not set" | 说明系统 Java 通过别的方式可用，但环境变量 JAVA_HOME 没配。**必须设 JAVA_HOME 变量**，指向 JDK 安装根目录（不是 bin 目录） |
| Windows 上 spark-shell 一闪而过/乱码 | 双击脚本是坑。在命令行里跑 `spark-shell.cmd`；中文乱码可设 `PYTHONIOENCODING=utf-8` 或用 cmd 的 `chcp 65001` |
| 下载的 spark 版本和 Hadoop 版本对不上 | 包名里的 `-bin-hadoop3.2` 表示配套 Hadoop 3.2。版本错了运行时会出现奇怪的类加载错误。配套的就是 hadoop3.2 的包，照着来 |

@@point ② Local 模式启动：spark-shell 与 pyspark
@@need 要解决什么
你配好了环境，现在想**亲手启动 Spark 看一眼**。Local 模式怎么进？进去之后是个什么画面？——很多教程直接让你写代码，结果你连"我进的到底是什么界面"都不知道。本点把两个入口讲清楚。

@@idea 核心思路
两个入口，按你用的语言选：

| 入口 | 命令 | 谁用 |
|---|---|---|
| Scala | `spark-shell --master local[2]` | 教程、源码讲解常用（示例用 Scala） |
| Python | `pyspark --master local[2]` | Python 开发者，PySpark 也是主流 |

```cmd
D:\soft\...> spark-shell --master local[2]
# 启动后出现 "Welcome to Spark" 横幅 + scala> 提示符
# 系统自动创建好 sc（SparkContext）和 spark（SparkSession），直接用
scala> sc
res0: org.apache.spark.SparkContext = org.apache.spark.SparkContext@...
```

关键认知：**shell 启动时 Master 已自动创建 sc**，你不用自己写 `new SparkContext`。`local[2]` 的 2 表示用 2 个线程模拟核数；`local[*]` 表示用满本机所有核。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报 `Failed to locate the winutils binary in the Hadoop binaries` | Windows 下常见兼容提示。在 `%SPARK_HOME%` 放一个 `bin/winutils.exe`（GitHub 有），或忽略（纯 local 不做 HDFS 时部分版本可不影响） |
| `pyspark` 里 import 不到 | 用 `pyspark` 命令进入的 shell 已经配好环境；如果自己写脚本 import 报错，用 `pip install pyspark==3.2.1` 在同版本环境跑 |
| 端口 4040 打不开 | Web UI 在**程序运行期间**才有。命令行被占用或自然退出后 UI 就没了，要先让任务跑着、再从浏览器访问 http://localhost:4040 |

@@point ③ WordCount 需求：先想清楚要算什么
@@need 要解决什么
"WordCount"被讲烂了，但正因为烂，很多人直接抄代码，**根本不知道它在解决什么**。先回答这个问题：给你一本书的全文，要统计每个词出现多少次，你的手工做法是什么？——Spark 只是把你这套手工做法分布式化了。

@@idea 核心思路
需求拆解成四步（这就是 WordCount 的本质，也是后续 90% 统计类需求的骨架）：

```text
1. 读入全文，按行拆分        → 每一行是一条数据
2. 把每行按空格拆成单词      → 每行变成多个单词
3. 每个单词变成 (单词, 1)    → 便于计数
4. 相同单词的 1 加起来       → 得到每个词总数
```

映射到 Spark 算子：

| 步骤 | 算子 | 类型 |
|---|---|---|
| 读行 | `sc.textFile("data.txt")` | 创建 RDD |
| 拆词 | `.flatMap(_.split(" "))` | 转换算子 |
| 记数 | `.map(word => (word, 1))` | 转换算子 |
| 求和 | `.reduceByKey(_ + _)` | 转换算子（shuffle） |
| 输出 | `.collect()` / `.saveAsTextFile()` | 行动算子 |

**先手写四步流程，再对照算子**——这才是理解 WordCount 的方式，而不是背代码。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 分不清 `flatMap` 和 `map` 在这儿的区别 | `map` 一对一只换形；`flatMap` 一行拆成多行后**压平**。拆单词必须 flatMap，用 map 会得到一堆数组而不是单词流 |
| 统计出来的词混着标点、大小写 | 真实文本要预处理：`toLowerCase` + 正则 `replaceAll("[^a-zA-Z ]","")` 清洗。直接 split 的结果含 ".",","等垃圾词 |
| 以为 `count` 和 `countByValue` 一样 | `count()` 是统计**总行数**；统计"每个词出现次数"用 `reduceByKey` 或 `countByValue`。搞混了结果差十万八千里 |

@@point ④ 第一个 WordCount 代码：逐行拆解
@@need 要解决什么
光讲算子你还是虚，本点给你**一份能直接跑通的完整代码**，并逐行解释"它在干什么、为什么要这么写"。跑通是第一步，看懂是重点——照抄却不理解是入门最大的坑。

@@idea 核心思路
Scala 版（spark-shell 里可直接粘贴）：

```scala
// 1. 读取本地文件，得到 RDD[String]，每一行是一条数据
val lines = sc.textFile("data/word.txt")

// 2. flatMap：把每行按空格拆成单词，并压平成单词流
val words = lines.flatMap(line => line.split(" "))

// 3. map：每个单词变成 (单词, 1) 的键值对
val pairs = words.map(word => (word, 1))

// 4. reduceByKey：相同单词的 1 累加
val counts = pairs.reduceByKey(_ + _)

// 5. 行动算子：把结果收集到 Driver 并打印
counts.collect().foreach(println)
```

关键点：

- 第 1–4 步全是转换算子，**不真正执行**；第 5 步 `collect` 触发计算。
- `reduceByKey(_ + _)` 是 Scala 简写，`_ + _` 表示 `(a, b) => a + b`。
- 想存文件：把最后一行换成 `counts.saveAsTextFile("output/result")`（output 目录**不能已存在**，Spark 会帮你建）。

Python 版等价写法：

```python
from pyspark import SparkContext
sc = SparkContext("local[2]", "WordCount")
lines = sc.textFile("data/word.txt")
words = lines.flatMap(lambda line: line.split(" "))
pairs = words.map(lambda w: (w, 1))
counts = pairs.reduceByKey(lambda a, b: a + b)
for word, n in counts.collect():
    print(word, n)
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `saveAsTextFile("out")` 报"文件已存在" | **输出目录不能已存在**，这是 Spark 的安全设计。删掉旧目录或换个名字 |
| `_ + _` 看不懂 | 它是 `(x, y) => x + y` 的语法糖，只用于两个同类型参数相加/合并。不熟 Scala 就写完整 lambda |
| 跑完没输出 | `collect()` 把结果拉回 Driver 打印；如果最后一行写的是 `counts.collect()` 但不 foreach，只打印一个数组对象。加上打印语句 |

@@point ⑤ 读文件路径：本地路径与通配符
@@need 要解决什么
`sc.textFile("data/word.txt")` 里的路径，在 local 模式、集群模式、Windows 下含义完全不同。路径写错是新手报错第一大户（`FileNotFoundException`、`Input path does not exist`）。本点把路径规则讲死。

@@idea 核心思路
| 写法 | 含义 |
|---|---|
| `"data/word.txt"` | 相对路径，基于**当前工作目录**（local 模式就在你启动 shell 的目录下） |
| `"file:///D:/soft/data/word.txt"` | 显式指定本地文件系统绝对路径 |
| `"hdfs://node1:9000/data/word.txt"` | HDFS 上的路径（集群模式） |
| `"data/*.txt"` | 通配符，一次读多个文件 |
| `"data/dir/"` | 读整个目录下所有文件（自动拼接） |

```python
rdd1 = sc.textFile("data/word.txt")          # 单文件
rdd2 = sc.textFile("data/logs/*.log")        # 通配多个
rdd3 = sc.textFile("data/part-*")            # 读目录下所有 part 文件
```

注意：**通配符解析发生在 Spark 端**，本地模式就按本机路径解析；如果路径本身不存在，报错要先去确认文件真实位置，而不是瞎改代码。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Windows 下 `textFile("D:/data/a.txt")` 报错 | 本地路径要加 `file:///` 前缀：`"file:///D:/data/a.txt"`；或把文件放到项目工作目录用相对路径 |
| 报 `Input path does not exist` | 90% 是路径写错/文件不存在。先去 `ls` 确认文件真的在那，再检查有没有拼写错、有没有多余空格 |
| 读目录时把无关文件也读进来了 | `textFile("dir/")` 读目录下**所有文件**；只想读一类就用通配 `dir/*.txt`，或先确认目录里只有目标文件 |

@@point ⑥ collect 与 take：别把整个大数据集拉回 Driver
@@need 要解决什么
新手最爱 `collect()`——因为它能打印出结果。但 collect 是"**把分布式算完的所有数据拉回 Driver**"，数据一大，Driver 直接内存爆炸（`Driver stacktrace`、OOM）。你得马上养成**"先 take 再看"**的习惯。

@@idea 核心思路
| 行动算子 | 作用 | 风险 |
|---|---|---|
| `collect()` | 全量收集到 Driver | **大数据集慎用**，会 OOM |
| `take(n)` | 只取前 n 条 | 安全，适合看一眼 |
| `first()` | 取第一条 | 等价 take(1) |
| `count()` | 返回条数 | 安全，只回一个数字 |

```python
# 危险：大数据集上 collect 直接爆
# result = rdd.collect()

# 安全：先 take 看结构
for row in rdd.take(5):
    print(row)

# 想看全部但确定数据小，再用 collect
```

判断口诀：**"我只需要看一眼" → take；"我要把结果全部落盘" → saveAsTextFile；只有在数据确实小、且 Driver 内存够时 → collect。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 大数据集 `collect()` 后 `OutOfMemoryError: Java heap space` | 把行动算子改成 `take(n)`，或直接 `saveAsTextFile` 落盘。collect 是把**全部**数据灌进 Driver 一个节点 |
| 以为 collect 之后才能保存 | `saveAsTextFile` 不需要 collect！它是分布式行动算子，各 Executor 直接写自己的分区，不经过 Driver 汇总 |
| 打印时把结果 println 无穷行 | 先 take(10) 看效果，确认逻辑对再整批落盘，别让终端刷屏卡死 |

@@point ⑦ Web UI：用浏览器看你的任务
@@need 要解决什么
代码跑通了，但"它到底怎么跑的、几个 Task、每个多久、有没有失败重试"——终端看不全。**Web UI（:4040）是 Spark 的门面**，学会看它，等于给架构图装上了实时监控。本点带你把 UI 逛一遍。

@@idea 核心思路
跑任务**期间**，浏览器开 `http://localhost:4040`，页面自下而上分几个标签页：

| 标签页 | 你能看到 |
|---|---|
| **Jobs** | 每个 Job（一次行动算子）的开始时间、状态、耗时 |
| **Stages** | 每个 Job 被切成了几个 Stage，Stage 内部的 Task 数、成功/失败、各 Task 耗时 |
| **Storage** | 你 cache 过的 RDD 占多少内存、存了多少分区 |
| **Executors** | 当前有几个 Executor、每个的核数、内存、active task |
| **Environment** | Spark 配置项、JVM 信息 |

按"Job → Stage → Task"这个顺序点进去，就是上一章架构图的活教程：数一数 Task 数和分区数对不对得上、有没有 Task 失败后自动重试。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 任务跑完 UI 就打不开了 | Web UI 只在**程序运行期间**存在（local 模式进程退出即消失）。要边跑边看，或在 shell 里保持会话再开网页 |
| 4040 被占用 | 报 `Port 4040 is already in use` 时，下一个任务会自动用 4041。也可以 `--conf spark.ui.port=4050` 指定 |
| 集群模式下 4040 看不到 | 集群上 UI 在 **Driver 所在机器**，需要看 driver 的 web UI 地址（YARN 里点 application 的 tracking URL） |

@@point ⑧ 版本选择：为什么锁定 Spark 3.2.1
@@need 要解决什么
网上教程用 2.x 的、3.5 的、4.x 预览版的都有，代码写法差异不小（旧 API 已废弃）。**所以一律用配套的同一版本**，避免"教程能跑我跑不了"。本点讲版本意识。

@@idea 核心思路
配套版本是 **Spark 3.2.1**（Spark 3.x 系列），资料「软件」目录有 `spark-3.2.1-bin-hadoop3.2.tgz`。为什么强调版本：

| 版本差异点 | Spark 2.x | Spark 3.x（本书用） |
|---|---|---|
| SparkSession | 需手动配置 | 默认入口，整合 sc/sql 上下文 |
| DataFrame API | 老 API | 统一、更简洁 |
| 性能 | — | 3.x 引入动态分区裁剪、AQE 等 | 
| 学习资料 | 大量旧博客 | 建议认准 3.x |

你应该做的是：**解压配套包 → 按同一版本跑**。遇到网上教程代码跑不通，先看它是不是 2.x 的老写法（比如 `SQLContext`、`HiveContext` 早已整合进 SparkSession）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 网上教程用了 `SQLContext`/`HiveContext`，你抄下来报错 | 那是 Spark 2.x 老写法，3.x 已整合成 `SparkSession`。`spark.sql(...)` 直接可用，不用再单独建上下文 |
| 用 PySpark 时 `pip install pyspark` 装了最新版 | pip 默认装最新（例 3.5），和 3.2.1 可能有 API 差异。要么 `pip install pyspark==3.2.1`，要么用配套包自带的环境 |
| 以为"大版本一样就能混" | Spark 2.4 → 3.x 有 API 破坏性变更（如 `Dataset` 行为）。跨大版本抄代码，先查对应版本的迁移说明 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **能跑的环境**：JDK + SPARK_HOME + shell 启动 | 后面所有章都有"实验台"了，不再被困在环境上 |
| **第一个完整程序**：WordCount 及其四步拆解思路 | 它是后续一切统计/清洗/聚合代码的母版 |
| **运行可视化**：Web UI 的 Jobs/Stages/Task 视角 | 架构图从此有实况，调优排查有了抓手 |

@@quiz
1. WordCount 的四步流程是什么？分别对应哪个 Spark 算子？
2. `map` 和 `flatMap` 在 WordCount 里为什么不能互换？
3. `collect()` 和 `take(5)` 的区别是什么？为什么说大数据集上 `collect()` 危险？
4. 本地模式 `sc.textFile` 读 `D:\data\a.txt` 的正确路径写法是什么？
5. 判断题：`saveAsTextFile` 之前必须先把结果 `collect()` 回来。
6. 一个任务报了 Web UI 4040 打不开，可能的原因有哪些（至少两条）？

@@links
参考|Spark 分布式计算框架基础（第 3 章：Local 模式与 WordCount）|#
软件|spark-3.2.1-bin-hadoop3.2.tgz|#
官网|Spark 快速入门（Quick Start）|https://spark.apache.org/docs/latest/quick-start.html
资料|sparkdemo.zip（本章 WordCount 源码）|#