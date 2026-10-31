@@h1 第十四章　SparkSQL 数据源读写与 Spark On Hive
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★☆

@@why 这一章在解决什么问题
分析做得再好，得先把数据**读进来**、把结果**写出去**。Spark 支持的文件格式五花八门：JSON、CSV、Parquet、ORC、JDBC、Hive 表……选错格式：要么读得慢、要么没 Schema、要么写出去别人读不了。而**Spark On Hive** 更是企业里的标配姿势：Spark 负责算、Hive 负责管元数据（表/分区），两边无缝衔接。

学完这一章你能：**用统一 API 读写 5 大数据源、懂得每个格式的取舍、把结果用正确的 SaveMode 和分区方式落盘，并能通过 Spark 直接操作 Hive 表**。

@@prep 开始之前
本地环境就够，准备几个 JSON/CSV 小文件；Hive 那节有 Metastore 才跟着做。

@@goal 学到这儿就够了
能说清五种数据源怎么选、SaveMode 怎么用，以及 Spark 与 Hive 各管什么，这章就算过了。

@@map 这一章在整个知识库里的位置
上一章：SparkSQL 开篇（DataFrame 模型、SparkSession、Catalyst）
**本章** ← 你在这里：数据源全家桶——读进来、写出去、接 Hive
下一章：DSL 与 SQL 编写、UDF/UDAF 自定义函数（怎么"算"）
再往后：SparkStreaming 实时处理
阶段终点：SparkSQL 全套"表处理"能力闭环

@@note info 学习提示
本章大部分是"API 速查 + 取舍判断"，不必死记每个参数——记住"5 种格式怎么选、SaveMode 四兄弟、Parquet 为何是默认"三条主线就够用。

@@point ① 数据源全景：一张表认识 5 大格式
@@need 要解决什么
开始之前先建地图：**Spark 到底能读哪些数据源？** 5 种主流格式各有什么脾气（有没有 Schema、压不压缩、能不能推下推）——知道"什么时候选什么"，是本章最值钱的部分。

@@idea 核心思路
```scala
// 统一 API（所有格式都这套姿势）
spark.read.format("parquet").load("path")        // 读
df.write.format("parquet").save("path")          // 写
// 也有快捷方法：spark.read.json / spark.read.csv / spark.read.parquet / spark.read.jdbc
```

**5 大主流格式对比**：

| 格式 | 有无 Schema | 特点 | 典型场景 |
|---|---|---|---|
| JSON | 自动推断 | 人可读、灵活、慢 | 接口数据、日志、半结构化 |
| CSV | 可推断/手写 | 人可读、简单 | 传统数据交换、Excel 朋友 |
| Parquet | **自带**（列式） | 压缩好、列裁剪、快 | **Spark 默认推荐格式** |
| ORC | 自带（列式） | Hive 生态、压缩更狠 | Hive 存量表、大宽表 |
| JDBC | 数据库自带 | 直连 MySQL/Postgres… | 业务库互导、小表维表 |

**选型口诀**：

```text
给人看的 → JSON/CSV
给机器做分析 → Parquet（首选）/ ORC
从数据库来 → JDBC 直连（别导成文件再读）
```

**Parquet 为什么是默认**：列式存储 + 内嵌 Schema + 谓词下推友好。同样数据量，Parquet 扫描量是 JSON 的十分之一不到。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用 JSON 存 10GB 分析数据 | 慢且占空间。分析场景转 Parquet 一次（`spark.read.json(...).write.parquet(...)`），后续全用它 |
| JDBC 直连大表全量读 | 大表全量拉 JDBC 会超时/撑爆内存。加过滤条件下推（`option("dbtable", "(select ...) as t")`）或换数仓导出 |
| ORC 和 Parquet 谁好纠结 | 都行，跟你生态走：Hive 老表 ORC、Spark 新写 Parquet。性能差距在一个量级内 |
| 忘了 format 写错 | 快捷方法名（json/csv/parquet）比 `.format("x")` 少错字。推荐用快捷方法 |

@@point ② 读 JSON：自动推断 Schema 的双刃剑
@@need 要解决什么
JSON 是最常见"半结构化"输入：字段不确定、有嵌套。Spark 读 JSON 自动推断 Schema——**方便是真的，坑也是真的**：推断出的类型可能不是你要的（年龄 25 是字符串还是 Int？）。

@@idea 核心思路
```scala
// 基本读法
val df = spark.read.json("path/events.json")
// {"name":"张三","age":25,"address":{"city":"北京","zip":"100000"}}
// Schema：name String, age Long(?), address Struct{...}

// 常见处理
df.printSchema()                                // 先看推断
df.select("name", "address.city").show()        // 嵌套字段用点号
```

**推断的坑（三个经典案例）**：

```text
① "24", "25", "abc" 混在 age 字段 → 推断成 String（全字段都变 String）→ 计算报错
② 空值/缺失字段 → 该列 nullable，聚合时被忽略（结果"少了几行"）
③ 部分文件字段不同 → 推断 union 出"超集"，列多出 undefined
```

**正确姿势**：

```scala
// 方式 A：给出显式 Schema（最稳）
import org.apache.spark.sql.types._
val schema = StructType(Seq(
  StructField("name", StringType),
  StructField("age", IntegerType)
))
spark.read.schema(schema).json("path")

// 方式 B：先抽样探 Schema —— DataFrameReader 没有 sample()，用 samplingRatio 让推断只扫一部分
// spark.read.option("samplingRatio", "0.05").json("data/events/")   // 仅在没显式给 schema 时生效
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| age 明明是数字被推断成 String | 首行是字符串或字段缺值导致整列降级。显式 `.schema(...)` 指定类型最干净 |
| 读进来 NaN/Infinity | json 里写 1e999 会变 Infinity。清洗时 `df.filter(col("x") < 1e308)` 或在源端就校验 |
| 嵌套 json 报 NullPointerException | 某个记录缺地址字段 → 访问 `address.city` 为 null。用 `getField` 前 `isNotNull` 或 `.na.fill` |
| json 一个文件一行超长 | json 解析逐行，超大行吃内存。源端按条切分，或干脆转 Parquet 后处理 |

@@point ③ 读 CSV：header / 分隔符 / 引号三件套
@@need 要解决什么
CSV 是"最亲民也最坑"的格式：没有 Schema、分隔符不固定、引号转义一堆。70% 的 CSV 读错都是：**忘了 header、分隔符是分号不是逗号、字段里有逗号被截断**。

@@idea 核心思路
```scala
val df = spark.read
  .option("header", "true")          // ① 首行是表头（最常忘！！）
  .option("sep", ";")                // ② 分隔符：默认逗号，改分号/制表符
  .option("quote", "\"")             // ③ 引号：字段里含分隔符时用引号包
  .option("inferSchema", "true")     // ④ 类型推断（默认全 String）
  .csv("path/data.csv")

// 或手动指定 Schema（类型最可控）
import org.apache.spark.sql.types._
spark.read.schema(StructType(Seq(
  StructField("id", LongType),
  StructField("tag", StringType),
))).option("header", "true").csv("path/data.csv")
```

**读 CSV 完整清单（照着勾）**：

```text
☐ header 开了没？（没开表头会变成第一行数据）
☐ 分隔符对没对？（sep）
☐ 字段里有逗号/换行吗？（要 quote + 源端规范）
☐ 类型要不要自动推断？（inferSchema，默认 String）
☐ 空值/缺失值想不想变统一？（nullValue 选项）
```

**写也会遇到**：`df.write.option("header","true").csv("out/")`——写出去要带表头时同样记得 header 配置（默认不带！）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 第一行表头变成一条数据 | 忘开 `header=true`。读/写都检查一遍这个选项 |
| 中文字段名乱码 | 编码问题：加 `.option("encoding","UTF-8")`（默认 UTF-8，但源文件可能是 GBK 别忘指定） |
| 数字带千分位 `1,234` 读崩 | 该字段带逗号且没引号包 → 列错位。源端或预处理清洗掉逗号再读 |
| CSV 字段数不一致报错 | 少列/多列会在读时补 null 或抛异常。先 `spark.read.option("mode","PERMISSIVE")` 容忍，再统计坏行 |
| 写 CSV 一个目录 N 个文件 | 同 saveAsTextFile：分区数=文件数，`repartition(1)` 出一份（大数据慎用） |

@@point ④ 列式存储：Parquet / ORC 为什么"快"得离谱
@@need 要解决什么
同样一份 100 列的表，JSON 读全表 10 分钟，Parquet 只select 2 列 3 秒——**列式存储的功劳**。搞懂"行式 vs 列式"的存储逻辑，你就明白为什么"分析场景无脑选 Parquet/ORC"，也能回答面试里的经典题。

@@idea 核心思路
**行式 vs 列式**：

```text
行式存储（JSON/CSV/SequenceFile）：
  按"一行完整记录"连续存放
  读任意一列 = 也读到整行所有列数据
  压缩率低（列内类型混杂）

列式存储（Parquet/ORC）：
  按"列"连续存放：第一列所有值→第二列所有值→...
  只读需要的列 = 只扫那几列的数据（列裁剪天然生效）
  同列类型统一 → 压缩率极高（如枚举列压成 0/1）
```

**Parquet 四宝**（回答"为什么快"的四个点）：

1. **列裁剪**：select 2 列，只读那 2 列的数据块
2. **谓词下推**：过滤条件直接在扫描时忽略无关数据块（min/max 统计一跳而过）
3. **高压缩**：列内类型一致 → 字典/RLE 压缩，存储省 70%+
4. **自带 Schema**：读写不用人工指定类型

**Parquet vs ORC 一句话**：功能同源，ORC 压缩略狠、Hive 生态更老；Parquet 更通用（Spark/Impala/Presto 全家支持）。**默认 Parquet，跟 Hive 老表走 ORC**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Parquet 读出来字段类型不对 | Parquet 带 Schema，但**读入时可显式覆盖**（`.schema(...)`）。显式声明的类型和文件不一致时才报错 |
| 老 Parquet 文件字段被删/改名 | Schema 演进：读时 `mergeSchema=true` 可合并新旧 Schema，但列类型冲突仍会报错。规划好表结构再写 |
| 8000 个小 Parquet 文件读巨慢 | 文件块越多元数据开销越大。写时按分区合理切分（`partitionBy` 控制目录粒度） |
| 非要拿 Parquet 给人看 | 它二进制不可读。给业务交付时再转 CSV/JSON 副本，分析链路内部保持 Parquet |

@@point ⑤ 写数据与 SaveMode：overwrite / append / ignore / error
@@need 要解决什么
写完结果落哪？**同一个路径重复写会怎样**？SaveMode 四兄弟解决"写入冲突"：overwrite 覆盖、append 追加、ignore 忽知、errorIfExists 报错。选错模式=生产事故（比如把昨天的结果覆盖成今天的空表）。

@@idea 核心思路
```scala
df.write.mode("overwrite").parquet("out/result")      // 覆盖（默认？NO，默认是 errorIfExists）
df.write.mode("append").parquet("out/result")         // 追加到已有数据
df.write.mode("ignore").parquet("out/result")         // 已存在就啥也不干
df.write.mode("error").parquet("out/result")          // 已存在直接报错（默认行为）
// 等价写法：SaveMode.Overwrite 枚举
```

| SaveMode | 行为 | 危险度 | 适用 |
|---|---|---|---|
| errorIfExists（默认） | 存在即报错 | 安全 | 首次写入 |
| overwrite | 删掉旧的写新的 | **高危** | 确定性重跑、临时表 |
| append | 追加到后面 | 中危（可能重复） | 增量/日志累计 |
| ignore | 存在就跳过 | 安全 | 幂等任务 |

**生产纪律**：

```text
① 默认 errorIfExists：对已有数据先 ask 再决定，防误删
② overwrite：先确定"这次跑出来的就是最终版"再用；跑一半失败会留下半成品！
③ append：保证"同份数据只 append 一次"（用日期/批次字段去重）
④ 配合原子性：先写临时目录 → 校验成功 → rename 到正式目录（推荐做法）
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 重跑任务数据翻倍 | 用了 append 且每跑一次追加一遍。要"覆盖今天"用 overwrite，或 append + 先删除当日分区 |
| overwrite 跑到一半失败，目录半成品 | overwrite 不是原子的！先写 `tmp/` → 成功后 `mv` 覆盖正式目录，是兜底方案 |
| 同路径不同 Schema 写 overwrite | 会混 schema 报错或读崩。不同结构别放同一路径，用子目录隔离 |
| 忘了默认是 errorIfExists | 第一次写没事；第二次写同样路径直接抛"已存在"。换目录/清目录/改 mode 三选一 |

@@point ⑥ 分区写入：partitionBy 与目录布局
@@need 要解决什么
10TB 的数据全塞一个目录？查询会扫全量。**按分区字段（如日期）组织目录**——`dt=2026-10-01/` 这样的布局，让"只查某天"的查询只扫一个目录。这是数仓级性能的分水岭，也是面试必问的"分区表"。

@@idea 核心思路
```scala
// 按日期 + 城市两级分区写
df.write
  .partitionBy("dt", "city")
  .mode("overwrite")
  .parquet("out/sales/")

// 目录布局：
// out/sales/dt=2026-10-01/city=北京/part-00000.parquet
// out/sales/dt=2026-10-01/city=上海/part-00001.parquet
// out/sales/dt=2026-10-02/...
```

**分区带来的效果**：

```text
查询：df.filter(col("dt") === "2026-10-01")
     → 只扫 dt=2026-10-01 目录，其它分区被"分区裁剪"跳过
     → 10 天数据只扫 1/10，性能 ×N
```

**分区设计三原则**：

1. **分区字段选"查询高频 + 低基数"**（日期/地区/业务线）：基数高（如 user_id 百万级）会写出百万目录=灾难
2. **分区粒度合适**：够 SQL 过滤就行，不是越多越好（目录过多元数据开销大）
3. **写时分区和过滤 `where` 对齐**：filter 用哪个字段，partitionBy 就按哪个字段放

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| partitionBy 后文件反而多到爆 | 分区基数太高（按 user_id 分）。分区列选低基数；高频筛选靠二级索引/桶 |
| filter 没写分区字段，白分 | 分区裁剪只对手写分区列的过滤生效。SQL 里 where 没写 dt → 全扫。**写 SQL 的同事要约定好分区条件** |
| 分区目录里 schema 漂移（多一列） | partitionBy 的列**不写进数据文件**（在目录名里），读回时你显式加回分区列。schema 变化用 `mergeSchema=true` |
| 对已存在的分区 overwrite | partitionBy+overwrite 会**清掉整个表再写**，不是只覆盖目标分区。要只覆盖某分区：`df.write.mode("overwrite").option("partitionOverwriteMode","dynamic")`（Spark 3 默认 dynamic 了对非分区表？不对——记得 Hive 分区覆盖语义） |

@@point ⑦ Spark On Hive：算归 Spark，表归 Hive
@@need 要解决什么
企业里"表"的管理者是 **Hive Metastore**（元数据都在这）：表结构、分区、权限。Spark 要跟 Hive 共生——**能读 Hive 的表、能查 Hive 的库、把中间结果存成 Hive 表**。这就是 Spark On Hive：Spark 干活，Hive 管"户口本"。

@@idea 核心思路
**架构一句话**：

```text
Spark 通过 Hive Metastore 服务读"表的户口本"（有哪些库、表、分区、Schema）
真正的数据在 HDFS/对象存储上
Spark 计算时直接读数据文件（不经 Hive 引擎）
```

**启用方式**（二选一）：

```scala
// ① 代码内开启（本程序用）
val spark = SparkSession.builder()
  .enableHiveSupport()                // ← 关键开关
  .config("hive.metastore.uris", "thrift://hive-metastore:9083")
  .getOrCreate()

// ② 配置里全局开（提交时指定也常见）
// spark-submit --conf spark.sql.catalogImplementation=hive ...
```

**连上之后能干嘛**：

```scala
spark.sql("SHOW DATABASES").show()
spark.sql("USE ods").show()

// 直接查 Hive 表（数据在 HDFS）
val df = spark.sql("SELECT * FROM ods.sale WHERE dt='2026-10-01'")

// 把 DataFrame 存成 Hive 表
df.write.mode("overwrite").saveAsTable("dwd.sale_clean")
```

**优点**：不用自己管 schema/分区（都在 metastore）；Hive 同事/BI 工具也能查到你写的表——一份数据两个生态共用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 连不上 metastore 报 `Unable to connect to Hive Metastore` | ① enableHiveSupport 没开 ② metastore 地址没配/地址错 ③ 网络不通。检查这条链路三要素 |
| 本地写 saveAsTable 落哪了 | 分两种：**没开 `enableHiveSupport`** → 用的是内存 catalog，进程一退表就没了；**开了但没配 `hive.metastore.uris`** → 落到本地 **Derby**（一进程一份、不共享）。要共享必须连真正的 Hive Metastore |
| metastore 里没有的表却报"找不到" | 大小写/库名不对：`USE db` 后 `SHOW TABLES` 确认。ODS/DWD 库名也常需要权限 |
| 权限：无写权限报错 | Hive 表写入走 HDFS 权限。检查执行用户对目标路径的写权限（ranger 权限中心也可能拦） |

@@point ⑧ 读写调优两板斧：谓词下推与分区裁剪
@@need 要解决什么
"读 100 个文件实际上只需要 3 个"——Spark 读大数据慢，很多时候不是算得慢，是**读了不该读的东西**。谓词下推（filter 提前到读取端）与分区裁剪（只读需要的分区）是省 I/O 的两大杀器。

@@idea 核心思路
**两板斧原理**：

```text
① 谓词下推（Predicate Pushdown）：
   你写 filter("age > 30")  →  Spark 把它下推到"读数据时"过滤
   → 只读出符合条件的行，而不是全读进来再滤
   列式文件（Parquet/ORC）还能下推"列裁剪"：只读用到的列

② 分区裁剪（Partition Pruning）：
   写 filter("dt = '2026-10-01'")  →  只扫描该分区的文件/目录
   → 100 个分区只读 1 个，I/O 省 99%
```

**怎么写才能被优化**：

```scala
// ✅ 让下推生效的写法：过滤条件尽量"贴近读取"
df.filter(col("dt") === "2026-10-01")
  .filter(col("age") > 30)
  .select("user_id", "age")            // 列裁剪自动

// ❌ 破坏下推的写法：先做复杂变换再过滤
// 对列做表达式运算后再 filter，往往推不下去（如 filter(upper(col("name")) = ...)）
```

**验证是否下推**：`explain()` 看物理计划里 filter 是否出现在 `FileScan` 附近；或 UI 看"读入字节数"是否远小于表大小。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| filter 写了但读入还是全量 | ① 条件引用了非分区列（分区裁剪失效）② 对列做了函数变换（谓词推不下去）。`explain()` 查证 |
| 以为所有过滤都会被下推 | UDF、子查询、某些 join 条件可能推不动。下推是优化器行为，不是所有 filter 必推 |
| 分区数很多但没裁剪 | 分区列必须是 `partitioned` 的表（partitionBy 建的）。普通表按普通字段过滤只能全扫 |
| 列裁剪没用上 | 用了 `select *` 或 `.collect()` 整行。只取需要的列，列式文件才省 I/O |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **数据源全家桶 + 选型口诀**：JSON/CSV 给人看，Parquet 给分析，JDBC 直连库 | 读写不再蒙，为每个数据选对格式 |
| **SaveMode 四兄弟 + 分区布局**：overwrite/append/ignore/error + partitionBy 裁剪 | 落盘不丢数据不重复，查询按分区裁剪快数量级 |
| **Spark On Hive 打通**：enableHiveSupport + saveAsTable + SQL 查 Hive 表 | 与数仓生态共存，一份数据多引擎共享 |

@@quiz
1. 5 大格式里哪两个是列式存储？分析场景为什么默认选它们？
2. 读 CSV 最容易忘的三个 option 是什么？
3. SaveMode 有哪四种？默认是哪个？"重跑任务不想要翻倍数据"该用哪个？
4. partitionBy("dt") 后，SQL 里 where 条件不写 dt 会怎样？分区裁剪的原理是什么？
5. Spark On Hive 中，Spark 和 Hive 各管什么？启用它的两个必要条件是什么？
6. 判断题：df.write.mode("overwrite") 会原子地替换目标目录，跑一半失败也不会留下半成品。

@@links
参考|SparkSQL （第 3 章：数据源读写）|#
参考|SparkSQL （第 4 章：Spark On Hive）|#
官网|Spark SQL 数据源指南|https://spark.apache.org/docs/latest/sql-data-sources.html
官网|Spark SQL 读写数据库（JDBC）|https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html