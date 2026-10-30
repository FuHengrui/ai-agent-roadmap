@@h1 第七章　RDD 转换算子：核心数据处理工具
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★★

@@why 这一章在解决什么问题
RDD 有了，但你还没法"处理"它。原始数据长什么样都有：混乱的文本要拆词、脏数据要过滤、日志要按用户分组、订单要和商品表关联……**这些"变换数据"的操作，Spark 统称为转换算子（Transformation）**。它们是你在 RDD 上写代码的主要方式，一个真正的 Spark 程序 80% 的代码都由转换算子构成。

转换算子有一个核心特点必须先记住：**惰性（lazy）**——调用它们只是"记下要做的事"，不立刻执行。这个特点让 Spark 能优化执行计划，也让新手反复困惑"为什么没跑"。本章把最常用的转换算子逐个讲透：**它解决什么问题、怎么写、有哪些坑**。你会建立自己的"算子工具箱"。

学完这一章，你能：**熟练用 map/flatMap/filter/groupBy/reduceByKey/distinct/union/join/sortBy 等 10+ 个转换算子组合出完整的数据处理流水线**。

@@prep 开始之前
还是第三章的 Local 环境，不用装新东西；RDD 怎么创建先弄明白，不然算子没东西可操作。

@@goal 学到这儿就够了
给一个需求能挑对算子并拼成流水线，还能说清为什么调用后没立刻跑，这章就算过了。

@@map 这一章在整个知识库里的位置
上一章（RDD 抽象）：你会创建 RDD 了，但还不会"处理"
**本章** ← 你在这里：转换算子——RDD 数据处理的主力军（惰性执行、返回新 RDD）
下一章：行动算子——触发计算、产出结果的另一半（collect/foreach/save 等）
再往后：Spark 内核（DAG/调度）→ RDD 实战项目（PVUV/排序/topN/卡口）→ SparkSQL
阶段终点：你能独立用 RDD API 完成完整的数据分析任务

@@note info 学习提示
算子多但不是死记——**每个算子对应一个数据处理需求**（拆词→flatMap，过滤→filter，按 key 合并→reduceByKey）。建议按"遇到什么需求用哪个算子"来学，而不是按算子列表背。

@@point ① 转换算子是什么：惰性执行的"变形器"
@@need 要解决什么
开始列算子前，必须先搞清转换算子这个"类"的统一规则。不然后面你写的代码**一段都不跑**，还以为环境坏了。转换算子的定义、特点和"为什么要惰性"是本章总纲。

@@idea 核心思路
**定义：返回值仍然是 RDD 的算子 = 转换算子（Transformation）。**

```python
rdd2 = rdd.map(lambda x: x * 2)      # 返回新 RDD → 转换算子
rdd3 = rdd.filter(lambda x: x > 3)   # 返回新 RDD → 转换算子
result = rdd.collect()               # 返回数组 → 不是转换，是行动算子
```

**核心特点：懒加载（惰性）。** 转换算子调用时**不执行**，只是把"计算步骤"记录进血缘链，直到遇到行动算子（collect/save/foreach 等）才真正开跑：

```text
你的代码：textFile → map → filter → reduceByKey → collect
执行时机：         ← 全是记录 →  ← 真正执行从这里开始
```

为什么惰性？两个原因：① 省资源（不急着算就不占内存）；② **给 Spark 优化空间**——它能看到完整计算链，把能合并的步骤合起来一次执行（pipeline），避免每步落盘。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 写了转换算子没反应 | 正常！惰性设计。确认"到底跑没跑"：必须有个行动算子结尾（collect/count/saveAsTextFile 等） |
| 一行 `rdd.map(...)` 后面没赋值 | 转换算子生成**新 RDD**，原 RDD 不变，返回值要接住：`new_rdd = rdd.map(...)`。丢了返回值=白写 |
| 排查"哪一步出的错" | 惰性导致报错可能出现在很远之后的行动算子处。用 `rdd.take(5)` 分阶段验证中间结果，别等最后一把梭 |

@@point ② map：一对一变换，数据处理第一算子
@@need 要解决什么
需求一：把数据"换一种形态"。比如日期字符串转时间戳、数字乘 2、给文本加前缀——**每条记录变成另一条记录**。这是最基础的变换，所有数据处理都从这里开始。

@@idea 核心思路
**map 功能：对 RDD 中每条数据执行同一个函数，一一对应地返回新数据**（一条进一条出）。

```scala
val rdd = sc.makeRDD(List(1, 2, 3, 4))
val rdd2 = rdd.map(_ * 2)        // 每个元素乘 2
// rdd2 = [2, 4, 6, 8]

val rdd3 = rdd2.map(_ + "!")     // 转字符串加后缀
```

三个关键点：

1. **类型可以变**：`RDD[Int]` 可以 map 成 `RDD[String]`，输入输出类型不必相同
2. **函数是参数**：`map(函数)`，Scala 里 `_ * 2` 是 `x => x * 2` 的简写（只适用于 lambda）
3. **一对一的"形变"**：map 永远 1 进 1 出，条数不变

**使用场景**：清洗字段、格式转换、类型转换、字段抽取（如把每行日志拆成结构化字段）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 在 map 里做"一行变多行" | map 是一对一，一行只能出一行。想一行拆多行用 `flatMap`（见下一点），这是初学者最高频的错误 |
| `_ * 2` 这种简写看不懂/写错 | `_` 代表 lambda 参数（出现过一次可省略 `x =>`）。多个 `_` 代表多个参数（`_ + _` 即 `(a,b) => a+b`）。不熟就写完整 lambda |
| map 函数里做耗时操作（建连接等） | map 对**每条数据**执行，建连接会建 N 次。连接类资源用 `mapPartitions`（每分区建一次），性能差一个量级 |

@@point ③ flatMap：一行拆多行，文本处理神器
@@need 要解决什么
需求二：一行文本拆成多个词、一行的 JSON 拆成多条记录、一个用户的多条轨迹压平……**"一行进，多变出"** 是数据处理的常规需求。用 map 做不到，用 flatMap。

@@idea 核心思路
**flatMap = map + 压平**：先按函数把每条数据"展开"成一串，再把所有串**连平**成一个 RDD。

```scala
val rdd = sc.makeRDD(List("a b c", "d e"))   // 两条字符串
val words = rdd.flatMap(_.split(" "))        // 拆词再压平
// words = ["a", "b", "c", "d", "e"]  5 个元素（而不是 2 个数组）
```

对比 map 与 flatMap 的差别：

```text
输入:  ["a b c", "d e"]
map(_.split(" "))      → [["a","b","c"], ["d","e"]]   2 个数组
flatMap(_.split(" "))  → ["a","b","c","d","e"]         5 个词
```

**使用场景**：单词统计、日志拆字段、解析嵌套数组、把"一行用户多个标签"展开成"每个标签一行"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 拆完发现是 `RDD[Array]` 而不是 `RDD[元素]` | 用了 map 而不是 flatMap。拆行/拆词必须 flatMap 压平 |
| 数据有空行/空串 | `" ".split(" ")` 会产生空串元素，配合 filter 先清洗：`flatMap(_.split(" ")).filter(_.nonEmpty)` |
| 输入本身是数组 `RDD[List]` 时混乱 | flatMap 把"集合元素"逐个摊开：`flatMap(identity)` 可直接展开一层嵌套集合。理解"展开+压平"两个动作就不会乱 |

@@point ④ filter：按条件留数据，脏数据清扫器
@@need 要解决什么
需求三：日志里有垃圾行、数据里有负数和空值、只要"昨天"的记录——**把所有不满足条件的数据扔掉**。没有 filter，你得写循环一个个判，有了它一行搞定。

@@idea 核心思路
**filter 功能：对每条数据执行布尔判断，返回 true 的留下，false 的丢弃**（条数只减不增）。

```scala
val rdd = sc.makeRDD(List(1, 2, 3, 4, 5, 6))
val even = rdd.filter(_ % 2 == 0)    // 留偶数
// even = [2, 4, 6]

val clean = rdd.filter(x => x > 3 && x < 6)  // 条件可组合
```

三个关键点：

1. **函数必须返回布尔**：filter 的函数签名是 `T => Boolean`，返回非布尔直接编译错
2. **不改变数据形态**：过滤前后的类型一样，只删不换
3. **和 where 是兄弟**：DataFrame 里叫 where，RDD 里叫 filter，一回事

**使用场景**：清洗空值/异常值、按时间/状态/范围过滤、剔除停用词。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| filter 里写了非布尔表达式 | 比如 `filter(x => x * 2)`，乘以 2 结果不是布尔，编译直接报 `Type mismatch`。判断条件写得"完整"些 |
| 过滤条件写反 | `filter(!x)` 留下的是假值。写完先 `take(5)` 看留下的是不是你要的 |
| 想同时改数据又过滤 | filter 只负责"留/删"，改数据另写 map。组合链：`rdd.map(清洗).filter(条件)` 两步走 |

@@point ⑤ groupBy 与 groupByKey：按 key 分组
@@need 要解决什么
需求四：统计"每个城市的销售额"、分析"每个用户的行为序列"——**数据按某个 key 归组**。Spark 给两个分组算子：groupBy（自定义 key）和 groupByKey（KV 型按 key），搞不清区别就会用错。

@@idea 核心思路
**groupBy：对任意 RDD，按你自定义的规则分组**：

```scala
val rdd = sc.makeRDD(List(("男", 3), ("女", 4), ("男", 5)))
val gb = rdd.groupBy(_._1)          // 按元组第一个元素分组
// gb = [(男, Iterable[(男,3),(男,5)]), (女, Iterable[(女,4)])]
```

**groupByKey：专用于 KV 型 RDD，直接按键分**：

```scala
val pairs = sc.makeRDD(List(("a", 1), ("a", 2), ("b", 3)))
val gbk = pairs.groupByKey()
// gbk = [(a, Iterable[1,2]), (b, Iterable[3])]
```

| 对比 | groupBy | groupByKey |
|---|---|---|
| 适用 | 任意 RDD | KV 型 RDD |
| 分组依据 | 自己写函数 | key 本身 |
| 返回 value | 整条原始数据 | 仅 value 集合 |

**共同点：都会触发 shuffle**（按键把数据重分布），成本不低——能先 map 减小数据量再分组就值得做。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 分组后想"对每组求和"却在 groupBy 里硬写 | groupBy 只是**分**，后续统计要再 map：`gb.map(x => (x._1, x._2.size))`。想一步聚合用 reduceByKey（下一知识点） |
| 用 groupByKey 但数据不是 KV | groupByKey 要求 `RDD[(K,V)]`，不是 KV 型编译报错。先用 map 转成元组 |
| groupByKey 全量 shuffle 后 OOM | 单个 key 数据极多（数据倾斜）会打爆分区。后续实战章专门讲倾斜处理；能用 reduceByKey 就地聚合就优先用它 |

@@point ⑥ reduceByKey：按 key 聚合，最常用也最高效
@@need 要解决什么
"统计每个词出现几次"→ 所有 kv 对按键归并；"算每个用户消费总额"→ 同 key 的金额相加。这类**分组 + 聚合**是统计类需求的主旋律。为什么不用 groupByKey 再算？——因为 **reduceByKey 边分组边合并**，效率高得多。

@@idea 核心思路
**reduceByKey(func)：自动按 key 分组，组内用 func 合并 value**（要求 value 类型不变）：

```scala
val pairs = sc.makeRDD(List(("a", 1), ("a", 2), ("b", 3)))
val sum = pairs.reduceByKey(_ + _)
// sum = [(a, 3), (b, 3)]

// WordCount 中的灵魂一行
val counts = words.map((_, 1)).reduceByKey(_ + _)
```

和 groupByKey 的本质区别：

```text
groupByKey:  先全量 shuffle 出 (a, [1,2,3,4,...])  再在本地求和
reduceByKey: shuffle 前先在每个分区内"预聚合"（combine），
             网络只传合并后的少量结果，再到下游合并
```

**所以：能 reduceByKey 就别 groupByKey**——网络传输量差一个量级，大数据的性能窟窿少一半。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `reduceByKey(_ + _)` 的 `_` 数量 | 函数是二元 `(x,y) => x+y`，所以写两个 `_`。写错成单 `_` 会类型不匹配 |
| 聚合逻辑不是加法（找最大/拼接字符串） | func 可以任意：`reduceByKey(math.max)`、`reduceByKey(_ + _)`；要拼分隔符写成 `reduceByKey((a, b) => a + "," + b)`。但**两次函数返回类型必须都是 V**（value 类型不变） |
| 以为 reduceByKey 和 groupByKey 结果一样 | 前者已聚合（value 是标量/合并结果），后者是集合（Iterable）。需求"只要统计值"用 reduceByKey |

@@point ⑦ distinct / union / 交集差集：集合操作家族
@@need 要解决什么
需求五：清洗重复数据（去重）、合并两个来源的数据（并集）、找出两边都有/只在一边的数据（交集/差集）——**集合运算**是数据合并分析的标配。四个算子一锅端。

@@idea 核心思路
**① distinct：去重**

```scala
val rdd = sc.makeRDD(List(1, 1, 2, 3, 3))
rdd.distinct()          // [1, 2, 3]
```

**② union：并集（**不去重**、无方向）**

```scala
rdd1.union(rdd2)        // 两份拼接，重复的保留
```

**③ intersection：交集（共有数据）**

```scala
rdd1.intersection(rdd2) // 两边都有的元素
```

**④ subtract：差集（A 有 B 没有）**

```scala
rdd1.subtract(rdd2)     // 只在 rdd1 的元素
```

| 算子 | 方向性 | 去重吗 | 类型要求 |
|---|---|---|---|
| distinct | - | 去 | 任意 |
| union | 无 | 不去重 | 同类型即可 |
| intersection | 无 | 去（结果唯一） | 同类型 |
| subtract | **有**（rdd1-rdd2） | 去 | 同类型 |

**使用场景**：用户去重（distinct）、多日数据合并（union）、黑名单过滤（subtract）、两边共有的 VIP（intersection）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| union 出来的重复数据"不该有"却有了 | union **不去重**是设计如此（保留重复）。想合并后干净 → `union(...).distinct()` |
| subtract 方向写反 | `a.subtract(b)` 是"a 有 b 没有"，反过来结果完全不同。写之前想清楚"谁减去谁" |
| 两 RDD 类型不同还在 union | `RDD[Int].union(RDD[String])` 类型不兼容编译错。类型不一致先 map 对齐再合并 |

@@point ⑧ join 关联算子：两张表"对上号"
@@need 要解决什么
需求六：用户表和订单表要拼出"用户+他的订单"；商品表和分类表要关联查分类名——**两张 KV 数据按 key 关联**。这正是 SQL 里 JOIN 的 RDD 版。

@@idea 核心思路
Spark 提供 join 家族（以 `RDD[(key, v1)] join RDD[(key, v2)]` 为例）：

```scala
// 学生表：(id, 姓名)；职业表：(id, 职业)
val stu = sc.makeRDD(List((101, "鲁班"), (102, "凯")))
val job = sc.makeRDD(List((101, "射手"), (102, "战士"), (103, "法师")))

// inner join：只有两表都有的 key（内连接）
stu.join(job)
// [(101, ("鲁班","射手")), (102, ("凯","战士"))]

// leftOuterJoin：左表全保留，右表缺的为 None
stu.leftOuterJoin(job)
// [(101, ("鲁班", "射手")), (102, ("凯", "战士"))]  + 右表缺失的 key 右边为 None

// rightOuterJoin：右表全保留
stu.rightOuterJoin(job)
```

**注意一个设计差异**：RDD join 是**按 key 关联 value**（`(101, ("鲁班","射手"))`），而 SQL join 是拼整行——RDD 更底层，拼好后你再 map 展平。

| join 类型 | 结果包含 | 口诀 |
|---|---|---|
| join | 两表都有的 key | 内连接 |
| leftOuterJoin | 左表全部 + 右表能匹配的 | 左全 |
| rightOuterJoin | 右表全部 + 左表能匹配的 | 右全 |
| fullOuterJoin | 全部 key（匹配不上的补空） | 全外 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| join 只按键的"完全相等" | 它是等值连接。范围 join（key 在区间内）RDD 做不了，得上自定义 partitioner 或 DataFrame 的复杂条件 |
| 把 join 结果当"整行"直接 show | 结果是 `(key, (v1, v2))` 嵌套结构，记得 map 成你要的形态 |
| 数据倾斜时 join 巨慢 | 同 key 数据集中在一个分区（如热点品牌）。实战章有处理方案；简单场景先考虑过滤/分解 key |
| 忘了 rightOuterJoin/fullOuterJoin 存在 | 只会 inner join 会漏需求：要保留左表全量用户（含无订单的）必须 leftOuterJoin |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **惰性世界观**：转换算子=记录、行动算子=执行 | 不再困惑"为什么没跑"，会主动用行动算子验证 |
| **核心算子工具箱**：map/flatMap/filter/groupBy/reduceByKey/集合运算/join | 80% 的数据处理需求直接用这些拼出来 |
| **性能意识**：能 reduceByKey 不 groupByKey、连接不放 map | 同样的代码，性能差一个量级 |

@@quiz
1. 转换算子的两大特点（返回值必须是 RDD + 惰性）分别意味着什么？
2. 一句话说清 map 与 flatMap 的区别，并举一个必须用 flatMap 的场景。
3. `rdd.map(x => x).filter(_ > 0).take(5)   # take 作用在 RDD 上，别先 collect 拉全量` 这段代码有什么问题？（提示：算子顺序）
4. reduceByKey 相比 groupByKey 高效在哪？
5. 用户表 `(id, 姓名)`、订单表 `(id, 金额)`，要输出"所有用户及其订单（含没下过单的）"，用哪个 join？
6. 判断题：union 会自动去重，所以两个 RDD 合并后一定没有重复元素。

@@links
参考|Spark 分布式计算框架基础（第 8 章：转换算子 1）|#
参考|Spark 分布式计算框架基础（第 9 章：转换算子 2）|#
官网|RDD API 文档（Transformation 部分）|https://spark.apache.org/docs/latest/rdd-programming-guide.html#transformations
资料|sparkdemo.zip（本章算子示例源码）|#
