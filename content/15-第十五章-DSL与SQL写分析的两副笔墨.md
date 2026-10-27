@@h1 第十五章　DSL 与 SQL：写分析的两副笔墨 + UDF 自定义函数
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★★

@@why 这一章在解决什么问题
SparkSQL 给数据分析两副笔墨：**DSL**（用代码方法链写：`df.select(...).groupBy(...)`）和 **SQL**（把 DataFrame 注册成临时表直接写 `SELECT`）。一副适合"代码里嵌逻辑、类型检查友好"，一副适合"复杂关联/复用已有 SQL 经验"。而真正让你"想算什么算什么"的，是 **UDF/UDAF**：内置函数不够用时自定义函数，比如部门自定义的加密算法、特殊的字符串清洗、业务独有的聚合口径。

学完这一章你能：**DSL 和 SQL 随时切换、会用开窗函数做分组 TopN、能写 UDF/UDAF 扩展 Spark 的内置函数库**。

@@map 这一章在整个知识库里的位置
上一章：数据源读写（数据进来了）
**本章** ← 你在这里：SQL/DSL 表达 + 自定义函数（怎么算）
下一章：SparkStreaming——从批处理走向实时
阶段终点：SparkSQL 完整闭环（读→算→写→自定义）

@@point ① DSL vs SQL：两副笔墨怎么选
@@need 要解决什么
同一需求两种写法，学哪个？**都学**——但不是平均用力：逻辑简单用 DSL（编译期检查、可调试），复杂关联/聚合用 SQL（表达力强、可复制给 BI）。本点先给你一张"切换地图"，后面两节分别展开。

@@idea 核心思路
**同一个需求，两种写法对照**：

```scala
// DSL（方法链）
df.filter(col("age") > 18)
  .groupBy("city")
  .agg(count("*").as("cnt"),
       avg("age").as("avg_age"))
  .orderBy(desc("cnt"))
  .show()

// SQL（先注册临时视图）
df.createOrReplaceTempView("users")
spark.sql("""
  SELECT city, COUNT(*) AS cnt, AVG(age) AS avg_age
  FROM users
  WHERE age > 18
  GROUP BY city
  ORDER BY cnt DESC
""").show()
```

**选择策略**：

| 场景 | 推荐 | 原因 |
|---|---|---|
| 逻辑简单、代码内嵌 | DSL | 编译期查列名错误、好调试 |
| 复杂 join/多次聚合/子查询 | SQL | 表达力强，SQL 老司机直接写 |
| 团队协作、BI 复用 | SQL | 可复制到 Hive/Impala/可视化工具 |
| 需要动态拼条件（循环/参数化） | DSL 或 SQL 拼接都要小心 | 别注入；DSL 天然参数安全 |

**共同底层**：DSL 和 SQL **最终都走 Catalyst 优化成同一套执行计划**——性能差异可忽略。趁手就行，别纠结。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DSL 里列名拼错编译期才发现（Python） | PySpark 是运行时才报错；Scala 有类型检查。两个语言体验不同，写 Python 多用 `.printSchema()` 自查 |
| SQL 字符串里列名错了 | 运行时才报 `cannot resolve column`。先 `df.printSchema()` / `SHOW COLUMNS` 核对 |
| 两种写法混在一个项目 | 团队约定：简单链路 DSL，复杂查询 SQL，别一人一套。可读性优先 |
| 以为 SQL 比 DSL 快 | 两种都被 Catalyst 转成一个计划，没有"SQL 更优"这回事。别为了"更快"换写法 |

@@point ② DSL 核心操作：select / filter / withColumn / drop
@@need 要解决什么
DSL 的"日常四件套"先配齐：**选列（select）、过滤（filter/where）、加列/改列（withColumn）、删列（drop）**。配合列的几种造法（文字量/表达式/函数），覆盖 80% 的代码内嵌逻辑。

@@idea 核心思路
```scala
// 选列
df.select("name", "age")                              // 字符串列名
df.select(col("name"), $"age" + 1)                    // 列表达式（$"age" 是隐式转换）
df.selectExpr("name", "age * 10 as age10")            // SQL 表达式字符串

// 过滤（filter / where 同义）
df.filter(col("age") > 18)
df.where("age > 18")                                  // 字符串版

// 加列 / 改列（返回新 DataFrame，原表不变）
df.withColumn("age_plus", col("age") + 1)
  .withColumn("name_upper", upper(col("name")))

// 删列
df.drop("tmp_col")
```

**列表达式全家桶**（`org.apache.spark.sql.functions._`）：

```scala
// 数值/字符串/条件
col("a") + 1, abs(col("x")), round(col("x"), 2)
upper(lower(trim(col("name")))), length(col("name"))
when(col("age") > 60, "老人").otherwise("其他")      // 条件分支

// 时间
to_date(col("dt")), year(col("dt")), unix_timestamp(col("t"))
date_sub(col("dt"), 1)

// 取空处理
coalesce(col("a"), lit(0))     // a 为空给 0
isnull(col("x")) / isNotNull
```

**注意**：`withColumn` 不改原 DataFrame，要接住返回值；同时改多列用 `select` + 表达式一次搞定更简洁。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了收 withColumn 返回值 | DataFrame 不可变，`.withColumn(...)` 不写赋值=白做。链式写法 `df = df.withColumn(...)` 或直接链到最后行动算子 |
| `lit()` 是什么 | 字面量：`df.withColumn("k", lit(1))` 加常量列。字符串比较要用；忘了 import functions 会找不到 |
| when/otherwise 条件表达式写错 | `when(条件, 值).when(条件2, 值2).otherwise(默认)`，otherwise 必须有（否则 null）。条件是列表达式，不是布尔 |
| select 里混用字符串列名和表达式 | `select("name", col("age")+1)` 混着写可以，但字符串会被当列名——表达式必须用 col()/表达式写法 |

@@point ③ 聚合：groupBy + agg，DSL 的统计主力
@@need 要解决什么
SQL 的 `GROUP BY` 在 DSL 里就是 `groupBy + agg`。Famous 聚合函数（count/sum/avg/max/min）+ `agg` 一次多聚合 + `groupBy 多列`，把"按分组做多个统计"两个字写清。

@@idea 核心思路
```scala
import org.apache.spark.sql.functions._

// 单列分组 + 多个聚合（agg 一次出多列）
df.groupBy("city")
  .agg(count("*").as("cnt"),
       sum("amount").as("total"),
       avg("amount").as("avg_amt"),
       max("time").as("latest"))
  .show()

// 多列分组（城市+日期）
df.groupBy("city", "dt").agg(...)

// 数值直方图/分桶可以 groupBy 表达式
df.groupBy(floor(col("age") / 10) * 10).count()
```

**聚合函数常用表**：

| 函数 | 语义 | 备注 |
|---|---|---|
| count(*) / count(col) | 行数/非空行数 | count(col) 忽略 null |
| sum / avg / max / min | 和/均值/最大/最小 | 数值列 |
| collect_list / collect_set | 组内收集成数组 | set 去重 |
| first / last | 组内首/末值（无序时不可靠） | 要可靠用窗口+排序 |
| countDistinct | 组内去重计数 | `approx_count_distinct` 更快 |

**groupBy 之后的形态**：分组键 + 聚合列；非分组列不能直接 select（要用聚合函数包起来）——这是 SQL 语义，DSL 同样遵守。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| agg 里忘了 .as 列名 | 会生成默认名（sum(x) 等，SQL 里要反引号才能引用）。好习惯：每个聚合都 .as("有意义名称") |
| 分组后想 select 未分组列 | SQL 语义禁止：要么加进 groupBy，要么用聚合函数包（first/collect_list） |
| sum 数值列遇到 null | sum 忽略 null；但整列 null 结果也是 null → 用 coalesce(sum(x), lit(0)) 兜底 |
| count(*) 和 count(col) 数不一样 | 对！count(col) 只数非空。要"行数"用 count(*)；要"该字段有几个有效值"用 count(col) |

@@point ④ 开窗函数：分组内排序与 TopN（row_number / rank）
@@need 要解决什么
"每个班级取成绩前 3""每个用户最近一笔订单"——**分组内排序取前 N** 是分析题里最高频的题型。groupBy 做不了（会折叠行），要靠**开窗函数（Window）**：先按窗口分组，组内排序，再附加行号/名次列。

@@idea 核心思路
```scala
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

// 定义窗口：按 dept 分组、按 salary 降序
val win = Window.partitionBy("dept").orderBy(desc("salary"))

// 组内行号/名次
df.withColumn("rn",        row_number().over(win))
  .withColumn("rank_",     rank().over(win))
  .withColumn("dense_rank",dense_rank().over(win))
```

**三兄弟区别（必考）**：

```text
数据: 工资 [100, 90, 90, 80]（按降序）

row_number()  → 1, 2, 3, 4    行号，并列也硬排（唯一且连续）
rank()        → 1, 2, 2, 4    跳号并列（90 并列占 2、3，下一个是 4）
dense_rank()  → 1, 2, 2, 3    连续并列（90 并列占 2，下一个还是 3）
```

**取每组 TopN 标准动作**：

```scala
// 每组按工资取前 2
df.withColumn("rn", row_number().over(win))
  .filter(col("rn") <= 2)
```

**窗口还能聚合**（滑动/累计）：

```scala
// 累计求和（orderBy 窗口）
val win2 = Window.partitionBy("user").orderBy("dt")
df.withColumn("cum", sum("amount").over(win2))   // 截止每天的累计销售额
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 并列要"都算 Top3"用了 row_number | 并列需求用 rank/dense_rank（按业务口径：并列第 2 是否占用名额）。row_number 是硬排不给并列 |
| 忘了 partitionBy 只 orderBy | 窗口就是全表一个大分区=全局排序取 TopN，多数情况不对。**先想"按什么分组"** |
| 窗口排序的某列有 null | orderBy 默认 null 排最后（desc 时反而在最前！）。用 `orderBy(desc_nulls_last(col("x")))` 控制 |
| 窗口 + distinct/orderBy 次序问题 | 先 distinct 再去窗口，别窗口里 distinct；先去重再开窗是一般顺序 |

@@point ⑤ spark.sql 与临时视图：SQL 老司机的正确姿势
@@need 要解决什么
团队里总有"SQL 很溜、代码生疏"的同事；你写好复杂关联也想偷懒——**把 DataFrame 注册成临时视图，直接用 SQL 查**。这就是 `createOrReplaceTempView` / `createGlobalTempView` 的用武之地：DataFrame 与 SQL 语言互通。

@@idea 核心思路
```scala
// 注册临时视图（会话级，当前 SparkSession 可见）
df1.createOrReplaceTempView("users")
df2.createOrReplaceTempView("orders")
df3.createOrReplaceTempView("items")

// 直接用 SQL 查多表
val result = spark.sql("""
  SELECT u.name, o.amount, i.item_name
  FROM users u
  JOIN orders o ON u.id = o.user_id
  JOIN items i ON o.item_id = i.id
  WHERE o.dt >= '2026-10-01'
  ORDER BY o.amount DESC
  LIMIT 10
""")
```

**两个视图的区别**：

| | createOrReplaceTempView | createGlobalTempView |
|---|---|---|
| 生命周期 | 当前 SparkSession（会话） | 跨会话（全局，需 `global_temp.` 前缀访问） |
| 用完谁删 | 会话结束 / dropTempView | 显式 dropGlobalTempView |
| 使用频率 | **99% 用它** | 极少用 |

**最佳姿势**：读入用 `spark.read` → 注册临时表 → 复杂逻辑用 SQL → 结果再回 DataFrame 链路（DSL）收尾。**各取所长**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| SQL 里找不到刚注册的表 | ① 视图是会话级，别的 SparkSession 看不到 ② 名字写错/大小写。用 `spark.catalog.listTables()` 确认 |
| 同一个名字注册两次丢第一个 | createOrReplaceTempView **替换**同名视图，不会报错。想保留两个就起不同名 |
| 全局视图要 `global_temp.xxx` 才查得到 | createGlobalTempView 后 SQL 必须写 `FROM global_temp.xxx`，裸名查不到（跨会话也不同 SparkContext 时更是） |
| 临时视图和 Hive 表同名 | SQL 里临时视图优先于 Hive 表（同名时）。要显式查 Hive 表就换名字或用库名限定 |

@@point ⑥ UDF：自定义单行函数
@@need 要解决什么
内置函数（upper/sum/to_date...）之外，业务常有"私有处理逻辑"：公司特有的脱敏算法、特殊的文本解析、行业规则判断——**内置没有就得自己写 UDF（User Defined Function）**。它把任意"一行进一行出"的 Scala/Python/Java 函数注册成 Spark 可调用的函数。

@@idea 核心思路
```scala
// ① 先写普通函数
def maskPhone(phone: String): String =
  if (phone == null) null else phone.take(3) + "****" + phone.takeRight(4)

// ② 注册成 Spark 函数（可指定返回类型）
spark.udf.register("mask_phone", maskPhone _)

// ③ SQL / DSL 里直接用
spark.sql("SELECT mask_phone(phone) FROM users").show()
df.withColumn("masked", callUDF("mask_phone", col("phone")))

// Python（PySpark）同样：
// from pyspark.sql.functions import udf
// @udf("string") 或 spark.udf.register("mask_phone", lambda p: ...)
```

**UDF 的代价（重要）**：

```text
⚠️ UDF 对 Catalyst 是黑盒：
   不能做谓词下推/列裁剪/常量折叠 → UDF 处优化停摆
   Python UDF：行数据要序列化跨进程传递，比内置函数慢一个量级
```

**三条纪律**：

1. **能用内置就用内置**（json 解析、字符串、时间都有内置），UDF 只补内置没有的
2. **UDF 内别做重活**（连库/调 API）——它是每行执行的，跟 map 里建连接一个道理
3. Python UDF 重逻辑考虑 **Vectorized UDF（pandas UDF）**：批量传入，性能接近内置

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| UDF 注册了 SQL 用不了 | 注册要 `udf` 方法名与 SQL 调用名一致；scala 里 `_` 转函数、Python 用 @udf 装饰器。检查注册是否在当前 session |
| UDF 处理 null 崩溃 | 输入列有 null → 函数收到 null 要自己兜底（判空返回 null/默认值），Spark 不会帮你跳过 |
| UDF 慢到怀疑人生 | 先看是不是 Python 非向量化 UDF——改用 pandas UDF（`@udf(returnType, PandasUDFType.SCALAR)`）或用内置表达式重写 |
| UDF 里用了外部大字典 | 又踩闭包陷阱：字典随 Task 复制。**先广播字典**，UDF 里用广播变量取值 |

@@point ⑦ UDAF：自定义聚合函数
@@need 要解决什么
UDF 处理"行→行"；还有一类需求是"**组内多行→一行**"：比如自定义"方差口径"、业务特有的"去重并算占比"——内置的 sum/count 满足不了。这就是 **UDAF（User Defined Aggregation Function）**：给你"缓冲累加"机制的聚合函数。

@@idea 核心思路
```scala
// 以"自定义方差 UDAF"为例（重点看"缓冲"思想）
class VarianceUDAF extends UserDefinedAggregateFunction {
  def initialize(buffer: MutableAggregationBuffer): Unit =  // 分组初始值
    buffer(0) = 0.0; buffer(1) = 0.0; buffer(2) = 0L
  def update(buffer: MutableAggregationBuffer, input: Row): Unit = {
    buffer(0) = buffer.getDouble(0) + input.getDouble(0)   // 累加 x
    buffer(1) = buffer.getDouble(1) + math.pow(input.getDouble(0), 2) // 累加 x^2
    buffer(2) = buffer.getLong(2) + 1L                     // 计数
  }
  // merge 合并各分区的缓冲；evaluate 输出 E[x^2]-E[x]^2（略）
}
spark.udf.register("my_var", new VarianceUDAF)
df.groupBy("dept").agg(callUDF("my_var", col("salary")))
```


**四个钩子对应聚合的三段式**（和 reduceByKey 的"分区内+分区间"同构）：

```text
initialize → 每个分组的初始缓冲
update     → 分区内逐行聚合（窄依赖阶段）
merge      → 分区间聚合（shuffle 阶段把多个缓冲合并）
evaluate   → 最终一个值
```

**实践建议**：需要 UDAF 的场景：直接先用 `groupBy + agg(内置组合)` 或自定义表达式拼，真搞不定再写 UDAF——它的开发成本远高于 UDF。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| UDAF 结果和手算不一致 | 检查 update/merge 是否**可交换可结合**（shuffle 会乱序合并）。顺序敏感的状态（如"取第一个非空"）在 distributed 下不可靠 |
| evaluate 里对缓冲顺序敏感 | 缓冲字段位置要写死并与定义一致。改 Schema 时四个钩子同步改，漏一个必错 |
| Python 里写 UDAF 麻烦 | PySpark 原生只支持 UDF；聚合逻辑用 `groupBy.agg(expr("..."))` 内置拼，或把聚合下沉到 SQL/UDF 组合 |
| 想对"分组内排序后再聚合" | 窗口函数 + 内置聚合函数就能做（row_number 后聚合），别急着写 UDAF |

@@point ⑧ explain：让执行计划告诉你"为什么慢"
@@need 要解决什么
同样的 SQL 同事写得飞快，你的慢 10 倍？**执行计划（Explain Plan）就是"看透引擎内心"的 X 光**。学会读它，你能精准定位慢的根源，而不是瞎改。

@@idea 核心思路
**怎么拿到执行计划**：

```scala
df.select(...).groupBy(...).explain("extended")   // 物理计划
spark.sql("EXPLAIN SELECT ...")                    // SQL 方式
```

**看物理计划里的四个关键信号**：

| 信号 | 含义 | 警惕点 |
|---|---|---|
| `FileScan` | 从文件读 | 有没有分区裁剪/列裁剪（见 14 章⑧）|
| `BroadcastHashJoin` | 广播 join（小表分发）| ✅ 好，别乱打破 |
| `SortMergeJoin` | 排序归并 join | 无广播条件时默认，看两侧大小 |
| `Exchange`（shuffle）| 数据重分布 | 出现越多 shuffle 越贵，看它引发了几个 Stage |

**一段"为什么慢"的诊断示例**：

```text
看到：SortMergeJoin(两边都 1 亿行) + 多个 Exchange + 无下推
结论：join 走全量 shuffle → 该加小表广播（broadcast hint）或提前过滤/聚合两边
```

**改完必验**：`explain()` 看 Exchange/Join 类型是否变化、Stage 数是否减少——**以计划变化验证优化，不靠感觉**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| explain 全是执行代码看不懂 | 先只看 4 类关键词：FileScan / Join 类型 / Exchange / filter 位置。其余技术细节略过 |
| 逻辑计划和物理计划分不清 | `简单 explain()`给物理计划（引擎真跑的）；`explain("extended")`才含逻辑计划。看物理即可 |
| 小表 join 却走 SortMerge | 小表超过广播阈值（默认 10MB）或两边都大。用 `/*+ BROADCAST(t2) */` hint 或调 `spark.sql.autoBroadcastJoinThreshold` |
| 改完 plan 没变化 | 有些优化加了也没生效（如函数变换后的 filter 推不动）。以 plan 和实测耗时双确认 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **DSL+SQL 双写能力**：随时切换、选择策略 | 代码人/SQL 人都能协作，一个需求两种表达成本最小 |
| **窗口函数**：row_number/rank/dense_rank + 分组 TopN | 榜单/最新记录/占比分析三大类题型的通用解法 |
| **UDF/UDAF 纪律**：黑盒代价、广播配合、四钩子结构 | 扩展能力不被黑盒坑，自定义函数的正确姿势 |

@@quiz
1. DSL 和 SQL 哪个更快？什么场景推荐用 SQL？
2. `withColumn` 会修改原 DataFrame 吗？不接返回值会怎样？
3. count(*) 和 count(col) 区别是什么？sum 遇到整列 null 的结果是什么？
4. 数据 [100, 90, 90, 80] 降序时 row_number/rank/dense_rank 结果分别是什么？分组 TopN 该用哪个？
5. UDF 为什么比内置函数慢？Python UDF 性能补救方案是什么？
6. UDAF 的四个钩子 update/merge/initialize/evaluate 分别对应聚合的哪个阶段？
7. 判断题：UDF 可以直接用闭包里的 Driver 变量，性能不受影响。

@@links
参考|SparkSQL （第 5 章：DSL 与 SQL）|#
参考|SparkSQL （第 6 章：开窗函数与 UDF/UDAF）|#
官网|Spark SQL 函数库（内置）|https://spark.apache.org/docs/latest/sql-ref-functions.html
官网|UDF/UDAF 官方文档|https://spark.apache.org/docs/latest/sql-ref-functions-udf-scalar.html