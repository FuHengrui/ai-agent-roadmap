@@h1 第十三章　SparkSQL 与 DataFrame：从 RDD 到"带表头的分布式表"
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★☆

@@why 这一章在解决什么问题
RDD 很好，但用久了你会烦：**没有字段名**（`_._1`、`_._2` 全靠自己记）、**没有列类型约束**（脏数据混进来才知道错）、**没有自动优化**（同样的聚合你写 3 遍、API 各不同）。SparkSQL 就是 Spark 的"升级版数据模型"：**给数据加上表头（Schema）**，让你可以**像查数据库一样用 SQL 查分布式数据**，背后还有 Catalyst 优化器帮你自动写出最优执行计划。

本阶段后半程的主角是 **DataFrame / Dataset**：它们和 RDD 是什么关系、怎么互相转换、为什么 SparkSQL 更快。学完你能：**看懂"RDD → DataFrame"的升级逻辑，会创建和转换 DataFrame，明白"为什么 Spark 官方建议优先用 SparkSQL"**。

@@prep 开始之前
还是第三章那套环境，不用装新东西；RDD 的算子先写过，才看得出 DataFrame 补了什么。

@@goal 学到这儿就够了
能说清 DataFrame 比 RDD 多了什么、Catalyst 优化了什么，并会三种方式造出来，这章就算过了。

@@map 这一章在整个知识库里的位置
前 12 章：RDD 全体系（算子、内核、实战）
**本章** ← 你在这里：SparkSQL 开篇——DataFrame 数据模型、SparkSession、与 RDD 的关系
下一章：SparkSQL 数据源读写（JSON/CSV/Parquet/JDBC）与 Spark On Hive
再往后：DSL / SQL 语法、UDF/UDAF 自定义函数 → 实时 Streaming
阶段终点：从"RDD 编程"平滑升级到"SQL 编程"，两条腿走路

@@point ① SparkSQL 的动机：RDD 时代的三宗罪
@@need 要解决什么
先回答"为什么要学 SparkSQL"：RDD 不是不好，是**表达复杂数据时很累**——没有字段名、没有列类型检查、没有自动优化。三个痛点对应 SparkSQL 的三个价值点，理解了动机，后面每件事都是顺理成章。

@@idea 核心思路
**RDD 三宗罪**：

```text
① 无字段名：rdd.map(x => x._1 + x._2)   ← 这个 _1 是什么？只能靠注释和记忆
② 无类型约束：脏数据混进来，跑到统计才发现类型错爆炸
③ 无优化：同样的逻辑换不同写法（groupByKey vs reduceByKey），性能天差地别，全凭程序员自觉
```

**SparkSQL 的三个回应**：

| RDD 痛点 | SparkSQL 解药 |
|---|---|
| 无字段名 | **DataFrame 有 Schema（表头）**：`user.name`、`df.select("name")`，字段名显式可见 |
| 无类型约束 | 列类型定义在 Schema 里，**读入/转换时校验**，脏数据早暴露 |
| 无自动优化 | **Catalyst 优化器**：把 SQL/DSL 转成最优执行计划（列裁剪、谓词下推自动做） |

**一句话定性**：SparkSQL 是"面向表结构数据"的编程接口，把 RDD 的"怎么算"升级为"算什么"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 有了 SparkSQL 还坚持手动 RDD 优化 | 20 行 RDD 优化代码，SparkSQL 两行 SQL 自动优化完。**能用 DataFrame/SQL 就别手搓 RDD**（官方也这么建议） |
| 以为 SparkSQL 是完全不同的引擎 | 不是！SparkSQL 底层**仍然是 RDD/Task 在跑**，只是加了一层"表模型+优化器"。学好前面的内核依然有用 |
| Schema 和真数据不一致 | 读文件时指定的 Schema 和实际列对不上，会在转换期抛错（这是特性不是 bug）——用 `.printSchema()` 先看再算 |
| 混淆"SparkSQL 模块"和"SQL 语法" | SparkSQL = 模块（含 DataFrame/SQL/Catalyst）；SQL 只是它的一种表达方式，还有 DSL（`select`/`filter` 方法链）。都要学 |

@@point ② 家族关系一张图：RDD / DataFrame / Dataset / SparkSession
@@need 要解决什么
学习 SparkSQL 最大的混乱来源：**RDD、DataFrame、Dataset、SparkSession 有什么关系？** 本点用一张家族图+演进史把它们的关系定死，后续所有 API 都挂在这张图上。

@@idea 核心思路
**演进简史**（记住这条线）：

```text
RDD (Spark 1.0)
  └─ 问题：无 Schema、无优化
DataFrame (Spark 1.3)   = RDD + Schema（分布式 Row 表，弱类型）
  └─ 问题：列访问是 x.row(0) 下标，类型不安全
Dataset (Spark 1.6)     = DataFrame + 强类型（泛型化）
  └─ spark 2.0：DataFrame = Dataset[Row]（统一！）
```

**Spark 2.0 后的现状（一条公式定终身）**：

```text
DataFrame = Dataset[Row]      ← 弱类型：列类型运行时才知（Row 下标/名称访问）
Dataset[T]                    ← 强类型：T 是编译期类型（case class）
RDD                           ← 最底层：无 Schema 无优化

SparkSession                  ← 2.0 统一入口（替代 SparkContext 的"全局入口"角色）
                                  spark.read / spark.sql / spark.createDataFrame
```

**三者的定位**：

| | 类型安全 | Schema | 优化 | 适合 |
|---|---|---|---|---|
| RDD | 强（编译期） | 无 | 手动 | 底层/非结构化处理 |
| DataFrame | 弱（运行时） | 有 | Catalyst | 绝大多数分析 |
| Dataset[T] | 强（编译期） | 有 | Catalyst | 类型安全敏感 + 分析 |

**Scala 里 `spark` 是什么**：SparkSession 实例，`spark.read`、`spark.sql(...)`、`spark.createDataFrame(...)` 全从它发起。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 DataFrame 和 Dataset 是两个不相干的东西 | 2.0 后 **DataFrame = Dataset[Row]**，就是同一个东西的弱类型视图。面试最爱问这题 |
| 在 Python 里纠结 Dataset | PySpark 只有 DataFrame（无强类型 Dataset）——强类型是 **Scala** 的特性，Python 用户只用 DataFrame |
| `spark` 变量哪来的 | 由你创建：`val spark = SparkSession.builder().master("local[*]").appName("x").getOrCreate()`。老教程里的 SparkContext 已被它整合（`spark.sparkContext` 可拿到） |
| 版本 1.x 教程说 DataFrame 升级 Dataset | 1.x 里二者分开；2.x 统一。看教程先确认版本，别套 1.x 的 API 思维 |

@@point ③ DataFrame：一张"带 Schema 的分布式表"
@@need 要解决什么
DataFrame 的本质一句话：**分布式、不可变、带列元数据（Schema）的"表"**——每一行是 Row，每一列有名字和类型。看懂它 = 看懂"SparkSQL 的一切都是表的操作"。它的两个新概念（Row、Schema）是理解关键。

@@idea 核心思路
**DataFrame 的数据模型**：

```text
DataFrame  ≈ 一张表
  ├─ 列: name(String), age(Int), city(String)   ← Schema（列名+类型）
  └─ 行: Row("张三", 25, "北京")                 ← 每条记录是 Row 对象
```

**两个新类型**：

```scala
// Row：一行数据（按下标或列名取）
val row: Row = df.collect()(0)
row.getString(0)          // 按下标取 → "张三"
row.getAs[String]("name") // 按列名取 → "张三"

// Schema 查看
df.printSchema()
// root
//  |-- name: string (nullable = true)
//  |-- age: integer (nullable = true)
```

**关键语义（和 RDD 对照）**：

```text
DataFrame 也是惰性的：dsl/sql 只构建执行计划，遇到行动算子（show/collect/count）才执行
DataFrame 也是分布式：Executor 按分区并行算
DataFrame 不可变：每次变换生成新 DataFrame
差别：多了 Schema + Catalyst 优化，少了"元素级类型安全"
```

**列引用方式**：`df("name")` / `$"name"`（Scala 隐式）/ `col("name")`。写 SQL 时列名就是普通标识符。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DataFrame 的 map 返回的是 Row 不是元素 | `df.map(r => r.getInt(1))`——Row 按下标/列名取字段。想保持表的形态就别 map，用 select/withColumn |
| `_1`/`_2` 访问 DataFrame 报错 | 那是 RDD 元组的玩法。DataFrame 用 `df("列名")` 或 `col("列名")`，列访问语法不同别混 |
| 列名大小写/空格问题 | 列名带空格或特殊字符时用反引号？在 SQL 里写 `` `my col` ``。平时命名用下划线规避 |
| Schema 里 nullable 为 true 却当非空算 | 空值会在聚合/join 里"悄悄消失"。要显式处理用 `df.na.drop()` / `df.filter(col("x").isNotNull)` |

@@point ④ 创建 DataFrame：读文件 + 从集合 + 从 RDD 转换
@@need 要解决什么
有了概念就要有"食材"：**DataFrame 从哪来？** 三条路：读文件（最常见）、从本地集合造、从已有 RDD 转换（老代码升级路径）。本点把三种创建方式一次讲全，后续所有章节都从这里取数据。

@@idea 核心思路
**① 读文件（SparkSession 统一入口）**：

```scala
val spark = SparkSession.builder().master("local[*]").appName("demo").getOrCreate()

val json = spark.read.json("path/users.json")
val csv  = spark.read.option("header", "true").csv("path/users.csv")
val parquet = spark.read.parquet("path/users.parquet")   // 自带 Schema，最快
// Schema 推断：json 默认就推断；csv 默认**全读成 String**，要 .option("inferSchema","true") 或手动 .schema(...)
```

**② 从集合造（测试/演示用）**：

```scala
import spark.implicits._

val df = Seq(
  ("张三", 25, "北京"),
  ("李四", 30, "上海")
).toDF("name", "age", "city")     // toDF 指定列名
```

**③ 从 RDD 转换（老代码升级）**：

```scala
val sc  = spark.sparkContext                      // 拿到底层 SparkContext 才能 makeRDD
val rdd = sc.makeRDD(List(("张三", 25), ("李四", 30)))
val df1 = rdd.toDF("name", "age")                        // 方式一：命名列
val df2 = spark.createDataFrame(rdd).toDF("name", "age")   // 方式二：先变 DataFrame 再命名；不给名就是 _1/_2
// DataFrame → RDD 反向转换：df.rdd
```

**优先级建议**：能用 `spark.read` 直接读的别转 RDD；非要转换，用 `toDF("列名"...）` 最省事。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| csv 第一行被当数据 | 忘了 `option("header", "true")`。读 csv 必加，否则表头变数据行 |
| `toDF` 找不到（Scala） | 需要 `import spark.implicits._`（或 `sparkSession.implicits` 的隐式转换），否则集合没有 toDF 方法 |
| csv Schema 推断把数字读成 String | 推断要额外扫一遍文件，仍可能猜错类型。手动 `.schema(...)` 指定列类型最稳，或读完后 `select(col("x").cast("int"))` 转 |
| 读 json 嵌套结构懵 | json 的嵌套对象会映射成 DataFrame 的 struct 列（`getStruct`）。复杂 json 优先用 SQL：`spark.sql("select x.y.z ...")` 外层探索 |
| 反复 `spark.read` 同文件 | 每次读都重新扫文件。多用一次复用（`val df = spark.read...` 再各自派生） |

@@point ⑤ DataFrame 与 RDD 互转：什么时候该转
@@need 要解决什么
新老代码并存时，**DataFrame ↔ RDD 互转**是绕不开的桥。但"能转"不等于"该转"——绝大多数场景不该转。本点给出转化方法 + **"何时别再转回去"的纪律**（转回去 = 丢掉 Schema 和优化，是性能杀手）。

@@idea 核心思路
```scala
// ① RDD → DataFrame：toDF 命名最常用
val df = rdd.toDF("name", "age")

// ② DataFrame → RDD：df.rdd（每行是 Row）
val backToRdd: RDD[Row] = df.rdd
val ages: RDD[Int] = df.rdd.map(_.getInt(1))     // Row 取字段

// ③ RDD[Row] 也可以再回来（少用）
val dfAgain = spark.createDataFrame(backToRdd, schema)
```

**纪律（什么时候别转）**：

```text
❌ 别再转回 RDD 的场景：
   整个链路都能用 DataFrame/SQL 表达 → 别转（优化器白做）
   RDD 只是为了"更熟" → 别转

✅ 必须转的场景：
   要用 RDD 专属 API（如按分区精细控制、自定义 partitioner）
   与非结构化数据混合处理、底层算子依赖 RDD 语义
```

**性能理由**：转成 RDD 后 Catalyst 优化全部失效——谓词下推、列裁剪不再作用，等于降级回手动优化。**"转出去就别想优化了"**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 为了写 RDD 算子硬把 DataFrame 转回去 | 先在 DataFrame 上找等价 DSL（select/filter/groupBy 都有），找不到再转。转=放弃优化 |
| `df.rdd` 出来是 RDD[Row]，不是 RDD[原类型] | 没错，DataFrame 是 Dataset[Row]。想要强类型先 `.as[CaseClass]` 转 Dataset |
| 互转的 Schema 对不上报错 | DataFrame→RDD→DataFrame 时 Schema 会丢，重建 DataFrame 必须显式再传 Schema（`createDataFrame(rdd, structType)`） |
| 忘记查看转换后类型 | 互转后先 `printSchema()` / `take(2)` 验证形态再往下写，别盲接算子 |

@@point ⑥ Catalyst 优化器：为什么 SparkSQL 可能比你手写更快
@@need 要解决什么
"SparkSQL 快"的第一功臣不是 Faster 的引擎，而是 **Catalyst 优化器**：它把你写的 DataFrame/SQL 转成**最优物理执行计划**。最直观的三个优化：**谓词下推、列裁剪、常量折叠**。听懂它，你就能解释"同样的逻辑，SQL 比手写 RDD 快"。

@@idea 核心思路
**Catalyst 优化四步**：

```text
① 逻辑计划：把你的 DSL/SQL 翻译成"做什么"的树
② 逻辑优化：等价变换（谓词下推、列裁剪……）
③ 物理计划：决定用哪种算子/分区做（join 选 BroadcastJoin 等）
④ 执行：生成 RDD 任务去跑
```

**三大招牌优化**：

```scala
// 例：一张 1TB 的表只需要两个列 + 过滤少量行
df.filter(col("age") > 18).select("name", "city")

// Catalyst 自动做：
// ① 谓词下推：先 filter 再算，只把过滤后的数据送上来（少算 90%）
// ② 列裁剪：只反序列化 name/city 两列，其它 98 列不读
// ③ 常量折叠：where 1=1 这种恒真条件直接删掉
```

**对比手写 RDD**：上面同一逻辑用 RDD，你得自己先 filter 再 map——但**列裁剪在 RDD 层做不了**（每行都是完整对象），除非你手动只保留两列。Catalyst 把这些自动做完，还自动决定 join 用 broadcast（小表自动广播，你不用手写 sc.broadcast）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| SQL 快不快"看命" | 不是命，是优化器能吃多少：**过滤/投影越靠前、写"能折叠"的表达式，优化越充分**。把大表操作放后面、能过滤先过滤 |
| 以为 Catalyst 能优化一切（含 UDF） | **UDF 对优化器是黑盒**——谓词下推/常量折叠对 UDF 失效。能用内置函数（spark.sql.functions.*）就用内置 |
| 小表 join 大表还手动 broadcast | Catalyst 自动广播 <10MB（可配）的表。你手动 broadcast 只在大表上才需要（或调阈值） |
| 看 `explain()` 的计划一脸懵 | 常用 `df.explain(true)` 看物理计划验证"列裁剪/下推生效没"。只想看结果用 `df.explain()` |

@@point ⑦ SparkSession：Spark 2.0 的统一"瑞士军刀"
@@need 要解决什么
老代码里 `SparkContext`、`SQLContext`、`HiveContext` 三件套并存，烦且乱。**Spark 2.0 起统一为 SparkSession**：一个入口管读数据、跑 SQL、做配置。理解它，你就不会被"教程里到底 new 什么"困扰。

@@idea 核心思路
```scala
// 创建（程序入口只有这一个关键对象）
val spark = SparkSession
  .builder()
  .appName("MyApp")
  .master("local[*]")            // 本地跑。注意：代码里写死 master 会**覆盖** spark-submit 的 --master，集群代码应删掉这行
  .config("spark.sql.shuffle.partitions", "200")   // 常用配置
  .enableHiveSupport()           // 要用 Hive 元数据时开
  .getOrCreate()

// 它整合的能力（曾经的三个类都退役到它身上）
spark.sparkContext        // 旧 SparkContext（RDD 系列还在用）
spark.read               // 读数据（json/csv/parquet/jdbc...）
spark.sql("SELECT ...")  // 直接写 SQL
spark.createDataFrame(...) / spark.createDataset(...)
spark.conf.set(...)      // 运行时改配置
```

**常见配置**：

| 配置 | 作用 |
|---|---|
| `spark.sql.shuffle.partitions` | **SQL/DSL 的 shuffle 分区数**（默认 200，RDD 默认并行度不归它管） |
| `spark.sql.autoBroadcastJoinThreshold` | 自动广播 join 的最大表大小 |
| `spark.sql.adaptive.enabled` | AQE 自适应执行（**Spark 3.2 起默认开启**，3.0/3.1 默认关） |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 教程让 new SQLContext 找不到 | 2.0+ 全整合进 SparkSession。用 `spark` 一个对象就够，不要再 new 旧的 |
| `local[*]` 在生产提交时被硬编码 | 写 `master("local[*]")` 是本地演示；集群提交一般由 `spark-submit --master` 指定，但别在集群代码里写死 local（优先级见下一条） |
| `.config` 和 `spark-submit --conf` 谁优先 | 官方优先级：**代码里的 SparkConf 最高**，其次 spark-submit 参数，最后 spark-defaults.conf。所以想留出运维口子，就别在代码里把关键项写死 |
| 一个 JVM 里 getOrCreate 两次 | getOrCreate 是"有就复用，没就建"，一个进程只建一个 SparkSession 是规范。真重复 new 一个会报 `Only one SparkContext may be active per JVM` |

@@point ⑧ 显式 Schema：生产代码为什么都手写类型
@@need 要解决什么
入门教程都让你"自动推断 Schema"，但**生产代码里几乎全手写 StructType**——因为推断有代价：慢（多扫一遍文件）、会猜错（数据类型/精度）、不可控。本点讲清"为什么显式定义"以及怎么写不踩坑。

@@idea 核心思路
**自动推断 vs 显式定义**：

```text
自动（inferSchema）：
  ✅ 写起来快   ❌ 读取时要额外扫文件推断（慢）
               ❌ 猜错类型：字符串"99"被当 int 截断、空值列类型漂移
               ❌ 同一文件不同批次推断结果可能不一致

显式（StructType 手写）：
  ✅ 类型铁定、读得快（免推断扫描） ✅ 字段缺失/类型不符直接报错
  ❌ 代码多几行（但一次写好，长期受益）
```

**写法（生产标准）**：

```scala
val schema = StructType(Seq(
  StructField("user_id", StringType, nullable = false),
  StructField("age", IntegerType, nullable = true),   // 允许空就显式标 true
  StructField("ts", TimestampType, nullable = false)
))

spark.read.schema(schema).json("...")   // 指定 schema 即跳过推断
```

**什么时候能偷懒用推断**：一次性探索 / 数据规模小 / 字段都是标准类型。**要长期服务、进数仓的表：一律显式 schema**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 推断出来类型不对（如日期成字符串） | 推断策略保守，很多情况猜不出 Timestamp/Decimal。显式 schema 一步到位 |
| 指定 schema 后 null 字段报错 | nullable 写错：允许为空的列必须 `nullable=true`，否则运行时抛错。对照数据真实情况修 |
| 推断模式读大文件特别慢 | 推断要预扫描文件。显式 schema 免扫描，大文件用后者能省一大段 |
| schema 字段顺序和文件不一致 | 显式 schema 按**名称**匹配（部分来源按位置）。先 `printSchema()` 看真实结构再写 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **SparkSQL 世界观**：DataFrame=Dataset[Row]=带 Schema 的表，Catalyst 自动优化 | 从"手搓优化"升级到"信任优化器"，写更少代码拿更好性能 |
| **创建与转换能力**：spark.read 全家桶 + toDF + RDD 互转纪律 | 任何数据源都能进 SparkSQL；老 RDD 代码顺利迁移 |
| **SparkSession 入口**：统一对象 + 常用配置 | 不再被多入口教程搞晕，配置改在哪心里有谱 |

@@quiz
1. RDD 时代的三个痛点是什么？SparkSQL 分别怎么解决？
2. Spark 2.0 之后 DataFrame 和 Dataset 的关系是什么？为什么说 DataFrame 是弱类型的？
3. DataFrame 的每一行是什么对象？要不要把整个 DataFrame 转回 RDD 写逻辑？为什么？
4. 创建 DataFrame 的三种方式分别是什么？读 csv 时最容易漏的配置是什么？
5. Catalyst 的"谓词下推"和"列裁剪"分别优化了什么？对 UDF 能生效吗？
6. 判断题：spark.sql.shuffle.partitions 同时控制 RDD 算子的默认并行度。

@@links
参考|SparkSQL （第 1 章：SparkSQL 概述）|#
参考|SparkSQL （第 2 章：DataFrame 与 Dataset）|#
官网|Spark SQL 编程指南|https://spark.apache.org/docs/latest/sql-programming-guide.html
官网|Catalyst 优化器介绍|https://spark.apache.org/docs/latest/sql-performance-tuning.html