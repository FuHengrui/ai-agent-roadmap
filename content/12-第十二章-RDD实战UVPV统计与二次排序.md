@@h1 第十二章　RDD 实战：UV / PV 统计与二次排序
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　|　难度 ★★★☆

@@why 这一章在解决什么问题
前 11 章的算子、内核、并行度、共享变量——**是骡子是马拉出来遛遛**。本章用三个经典实战需求把它们串成完整程序：**PV（页面浏览量）/ UV（独立访客数）统计**（网站运营最基础的两个指标）和 **二次排序**（先按第一字段排、再按第二字段排——面试题里的常客、业务里找"同一天内最新记录"的刚需）。

同时实战逼出两个真问题：两遍统计怎么避免重复计算（cache 用武之地）、RDD 排序怎么自定义排序规则（Ordering 的用武之地）。跑通这三个案例，你就真正"会用 Spark 做数据分析"了。

学完你能：**从日志文件出发独立写完 UV/PV/二次排序三个程序，并解释每一步为什么这么写**。

@@map 这一章在整个知识库里的位置
前面 11 章：算子 + 内核 + 共享变量的完整知识
**本章** ← 你在这里：RDD 实战收尾——把知识拧成程序（UV/PV、二次排序、卡口统计）
下一章：SparkSQL——用 SQL 思维做同样的统计（更简洁、更优）
再往后：SparkSQL 进阶 → Streaming 实时
阶段终点：从"会算子"到"会项目"，再升级到"会用 SQL+流"

@@point ① 案例总览：一份访问日志，四个统计需求
@@need 要解决什么
先看全貌：这章围绕一份**网站访问日志**展开。需求拆解是数据分析的第一步——**先想清楚要输出什么，再设计算子链**，这是专业和业余的分界线。四个需求依次升级难度，正好覆盖前面学的所有核心算子。

@@idea 核心思路
**数据长这样**（一行一条访问记录）：

```text
2026-10-01 08:12:33  192.168.1.10  /home      Mozilla/5.0
2026-10-01 08:15:41  192.168.1.10  /product   1   ← 用户 1 再次访问
2026-10-01 09:01:02  192.168.1.20  /home
2026-10-01 09:03:55  192.168.1.30  /cart
2026-10-01 09:44:11  192.168.1.10  /home      ← 用户 1 三次访问
...
```

**字段**：时间 | IP（代表用户）| 访问页面 | 浏览器 UA（可省）

**四个统计需求**：

| 需求 | 含义 | 对应算子思想 |
|---|---|---|
| ① PV | 页面总浏览量（每行算一次） | count / map+sum |
| ② UV | 独立访客数（IP 去重后数） | distinct().count() |
| ③ 热门页面 Top5 | 每个页面的访问量排序 | map→reduceByKey→sortBy→take |
| ④ 每人访问次数分布 | 每个访客访问几次 | reduceByKey → 再 countByValue |

**为什么选这四需求**：PV/UV 是业务指标准入门；Top5 用排序+TopN；频次分布用二次聚合。**覆盖变换、聚合、排序、取前 N 全链路**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 需求定义不清就开写 | 先写"输入格式→输出形式"一句话（如"返回 (页面, 次数) 数组，按次数降序"）。样例数据先手工算一遍结果再对程序 |
| 把 UV 想成"统计 IP 相同行数" | UV=**去重后的个数**。同时有"每个 IP 访问几页"（频次）和"有多少个 IP"（UV），先分清楚问的是哪个 |
| 日志里有脏行（字段缺失/格式坏） | 实战第一关：清洗。filter 保证解析安全（见下一个知识点），不然程序跑一半 NPE |
| 需求"稍后再说" | 本案例需求已定死。但真实工作里"先给口径再写码"永远是第一原则 |

@@point ② 数据准备：读入、解析与清洗（ETL）
@@need 要解决什么
任何统计程序的第一步：**把日志文件读进来、拆成结构化的字段、扔掉脏数据**。这一步的成败直接决定后续质量——脏数据不洗，统计结果就是错的；解析不安全，程序直接崩。这是"能用"和"能上线"的分水岭。

@@idea 核心思路
```scala
// 读入：textFile 可多路径/目录
val raw = sc.textFile("hdfs://.../logs/20261001/")

// 解析 + 清洗：一行变字段元组；解析失败或字段缺失的丢弃
case class Log(time: String, ip: String, page: String, ua: String)

val logs = raw.flatMap { line =>
  val arr = line.split("\\s+")
  if (arr.length >= 4 && arr(2).startsWith("/"))   // 校验长度+页面格式
    Some(Log(arr(0)+" "+arr(1), arr(2), arr(3), arr(4)))
  else None                                       // 脏行 → None 被压平丢弃
}
```

**要点**：

1. **flatMap + Option** 是解析标准姿势：`Some(解析成功)` / `None(丢弃)`，一次搞定"解析+过滤"
2. **先 filter 后其它算子**：把"字段数不足""明文乱码"的脏行在最前面滤掉，后续算子就不会踩空
3. **解析当场校验**：`startsWith("/")` 这种格式断言，比到统计时才发现类型错误强万倍

**清洗准则**：宁可"先滤后算"多写两行，也不让一个脏数据进统计。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 日志一行被 split 成 3 段（有空行/制表符） | 用 `split("\\s+")`（正则吸多个空白）而不是 `split(" ")`；同时校验长度再取字段 |
| 解析函数在每一行抛异常中断 | 解析内 try-catch 或 Option 化。**绝不让解析异常炸掉整个 Job** |
| 清洗太狠把好数据滤了 | 先 `take(20)` 人工看数据长什么样，再定清洗规则。规则要紧扣样本格式 |
| 没有缓存直接两遍统计 | 同一份 logs 要算 PV 又算 UV → 第一遍算完忘缓存 → 第二遍全量重读。**在 logs 上 cache()**（下一知识点验证） |

@@point ③ PV 统计：页面浏览量
@@need 要解决什么
最朴素的统计：**一共产生了多少次访问**（每次页面请求 = 1 PV）。它简单，但作为第一个跑通的程序，把"统计程序的最小骨架"演示清楚：读入→清洗→聚合→输出。同时引出"同一数据被多个统计复用时必须缓存"的工程习惯。

@@idea 核心思路
```scala
logs.cache()                        // ① 复用前先缓存（后面 UV/频次还用它）

// 方案 A：直接 count（PV=行数）
val pv = logs.count()
println(s"PV = $pv")

// 方案 B：若只要页面维度再按页统计
val pagePv = logs.map(log => (log.page, 1))
                  .reduceByKey(_ + _)
// (主页, 12345) (商品页, 8765) ...
```

**所以 PV 有两个粒度**：

```text
总 PV  = logs.count()                         （1 个数）
分页 PV = map(→(page,1)) + reduceByKey(_+_)  （(页面,次数) 列表）
```

**为什么先 cache**：本次要算 PV+UV+频次=多次遍访 logs。第一次 count 触发的计算，把结果留在内存，后续遍历直接读缓存——从"重读全量三遍"变成"算一遍+读缓存两遍"。

**输出姿势**：结果小 → `collect().foreach(println)`；结果大 → `saveAsTextFile`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 算完 PV 忘了 cache，UV 又从头读一遍 | 把 `logs.cache()` 放在所有统计**之前**，且第一个行动算子（count）放在 cache 之后立即执行（真正触发生效），后面全复用 |
| 只算一个指标还是习惯性 cache | 单次使用不必缓存（多此一举占内存）。缓存判断 = **被多次使用 且 计算代价高** |
| 页面字段里有查询串 `?x=1` 导致一页两行 | 清洗阶段按需规整：`page.split("\\?")(0)` 截掉参数再统计 |
| count 结果和文件行数对不上 | 清洗 filter 滤掉的行不算（正常）。想核对"滤了多少"：累加器计数，两数相加=原始行数 |

@@point ④ UV 统计：独立访客数
@@need 要解决什么
PV 是"访问次数"，UV 是"来了多少人"——**同一 IP 只算一次**。UV 看似只比 PV 多了个去重，但去重的实现选择（distinct vs reduceByKey）和它的 shuffle 代价，恰是性能优化的观察窗口。读懂 UV，你就读懂了"去重类需求"的通用解法。

@@idea 核心思路
```scala
// 方案 A：distinct 后 count（思路最直白）
val uv = logs.map(_.ip).distinct().count()
println(s"UV = $uv")

// 方案 B：reduceByKey 去重（边去重边计数，shuffle 量更小）
val uv2 = logs.map(_.ip).map((_, 1)).reduceByKey(_ + _).count()
```

| 方案 | 本质 | 性能对比 |
|---|---|---|
| distinct | 全量去重后数 | distinct 内部也是一次 shuffle，但只传 IP |
| reduceByKey | 每个 IP 归并后 count | 同 shuffle，可先在 map 端把同 IP 压成 1 条（**省传输**） |

**进阶优化**（面试亮点）：**map 端预聚合**——同一个 Executor 内相同 IP 只留 1 条，再 shuffle 时数据量骤减：

```scala
val uv3 = logs.map(_.ip)
              .distinct()          // first：本地去重（窄依赖）
              .map((_, 1))
              .reduceByKey(_ + _)  // 全局合并
              .count()
```

**UV 的内在**：distinct 和 reduceByKey 都是宽依赖（要全局知道"这个 IP 出现过没有"），所以 UV **天然要 shuffle 一次**——这是去重需求的物理底线，别指望快过它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| UV 比 PV 大（不可能） | 肯定写错了：可能把 count 用在未去重 RDD 上，或用 map 错位。UV ≤ PV 恒成立，拿这个做自检 |
| distinct 后还想保留"每个 IP 访问次数" | distinct 只剩 IP，丢信息了。要频次用 reduceByKey（不 distinct） |
| 重复计算 IP 数量（IP 同时出现在脏行） | 清洗先行。UV 统计前 logs 必须已过滤脏行，否则把"坏 IP"也算进访客 |
| 大日志 UV 巨慢 | 去重必 shuffle，正常。优化空间：map 端先 distinct 再 reduceByKey（预聚合），或采样估计（不要求精确时） |

@@point ⑤ 热门页面 Top5：聚合 + 排序 + 取前 N
@@need 要解决什么
"哪个页面最火"——**按页面聚合 → 按次数排序 → 取前 5**。这个三段式（聚合/排序/截断）是所有"TopN 排行榜"的通式，SortBy、reduceByKey、take 在此首次合体。搞定它，排行榜类需求全都会了。

@@idea 核心思路
```scala
val hotPages = logs.map(log => (log.page, 1))
                   .reduceByKey(_ + _)                       // ① 聚合：页面→次数
                   .sortBy(_._2, ascending = false)          // ② 排序：按次数降序
                   .take(5)                                   // ③ 截断：只取前 5
// Array[(String, Int)]  →  [(主页,12345), (商品页,8765), ...]
```

**三步各自的道**：

1. **reduceByKey 聚合**：同页面的访问次数放一起（宽依赖，必 shuffle，但已 map 端预聚合过，量小）
2. **sortBy 全局排序**：注意**多分区需要全局有序**，此时分区数变 1 才对——大数据量下全排序开到 1 个分区会慢，**改进版用 takeOrdered（堆顶 N，不排全序）**：

```scala
// 更优：只要 Top5，不必全量排序
val hot5 = logs.map(log => (log.page, 1))
               .reduceByKey(_ + _)
               .map(_.swap)                 // (次数, 页面)
               .takeOrdered(5)(Ordering.Tuple2(Ordering.Int.reverse, Ordering.String))
// 直接取"次数最大"的 5 个，不排全量
```

**TopN 通用公式**：`聚合 → 转(值,键) → takeOrdered(n)(倒序)`；数据量小/要全序时用 `sortBy + take`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| sortBy 后 take 依然全局有序？（分区>1） | sortBy 是多分区**局部有序**，take 抓的是"最先碰到的分区"——可能不是全局最大。**要么 sortBy 设 numPartitions=1，要么用 takeOrdered** |
| takeOrdered 默认是取最小的 5 个 | 想要最大 5 个必须把顺序倒过来（见上面 `Ordering.Int.reverse` 或 `排序键取负`：`takeOrdered(5)((a,b) => b._1 - a._1)`） |
| 忘了 `.swap` 让次数做排序主键 | `(页面, 次数)` 直接 takeOrdered 是按**页面**排序（String 顺序），不对。swap 成 (次数, 页面) 才能按次数 |
| 全排序 1 个分区太慢 | 大数据别用全局 sortBy；TopN 一律用 takeOrdered 只保头部 |

@@point ⑥ 二次排序：需求与直觉"陷阱"
@@need 要解决什么
"先按日期升序，同一天内再按时间升序"——**两个字段依次排序**就叫二次排序。听起来简单，但**直接 sortBy 过一次后第二次 sortBy 会把第一次排序打乱**——这是最大的直觉陷阱。RDD 里的二次排序需要一次搞定的正确姿势。

@@idea 核心思路
**业务场景**：取"每个用户最新一条记录"（date desc, time desc）、按班级排序后班内按成绩排（成绩榜）——都是二次排序。

**错误直觉（必踩）**：

```scala
rdd.sortBy(_._1).sortBy(_._2)   // ✗ 第二刀会打乱第一刀！！
// 结果：全局只按第 2 字段有序，第一字段顺序丢了
```

**正确姿势**：**把两个字段合成一个"组合键"，一次排序完成**。

```scala
// 数据：(日期, 时刻, 内容) → 想 date 升序、同 date 内 time 升序
val rdd = sc.makeRDD(List(
  ("2026-10-01", "09:00", "A"),
  ("2026-10-01", "08:00", "B"),
  ("2026-10-02", "10:00", "C"),
  ("2026-10-01", "07:00", "D")))

// 组合排序键：(date, time) 作为排序主键
val sorted = rdd.sortBy(x => (x._1, x._2))
// (2026-10-01,07:00,D)(2026-10-01,08:00,B)(2026-10-01,09:00,A)(2026-10-02,10:00,C)
```

**本质**：元组 (a,b) 默认比较规则 = 先比 a，相同再比 b——**天然就是二次排序**。所以 `sortBy(x => (第一键, 第二键))` 一行搞定。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 两次 sortBy 顺序混乱 | **排序只排一次**，两个字段合成元组/自定义类一次排。多轮 sortBy 只保留最后一次的序（中间序被破坏），别信"先排再排" |
| 元组排序是字典序不是数值序 | `("10", "9")` 字符串序会 10<9。数字必须存成 Int/Long 再排（解析日志时转类型） |
| 需求"date 升序 + time 降序"混合方向 | 元组内嵌不动全局方向，混合方向用 `sortBy(x => (x._1, -x._2))`（数值取负）或自定义 Ordering |
| 排序键相等还要第三/第四字段 | 元组加长即可 `(k1,k2,k3)`——"N 次排序"= 合成 N 维键一次排 |

@@point ⑦ 二次排序进阶：自定义对象 + Ordering
@@need 要解决什么
元组能处理"基础类型组合"，但业务里经常遇到：**要按对象多个属性排序、要自定义比较逻辑**（如按"次数降序，次数相同按名称升序"）。这时就是**自定义 Ordering / 自定义类**的用武之地。这也是面试必考的自定义排序题。

@@idea 核心思路
**场景**：按 (次数 desc, 名称 asc) 排序——混合方向的真实需求：

```scala
case class Item(name: String, count: Int)

// 方式一：元组取负（最简，数值字段可负）
rdd.map(x => (-x.count, x.name, x))
   .sortByKey()
   .map(_._3)
// 先排 -count（升序=count 降序），再排 name（升序）

// 方式二：自定义 Ordering（最通用，任意对象/任意规则）
implicit val ord: Ordering[Item] = Ordering.by(i => (-i.count, i.name))
val sorted = rdd.sortBy(identity)        // 用隐式排序
// 或
val sorted2 = rdd.sortBy(i => i)(Ordering.by(i => (-i.count, i.name)))
```

**两种方式的选用**：

| 方式 | 代码量 | 适用 |
|---|---|---|
| 元组取负 | 少 | 数值字段、方向混合简单 |
| 自定义 Ordering | 中 | 对象排序、规则复杂、要复用 |

**为什么自定义 Ordering 是"正确姿势"**：`Ordering.by(f)` 把"提取排序键"和"比较"分离——规则一处定义，sortBy/takeOrdered/max 全部复用；改规则只改一处。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 隐式 Ordering 写了但 sortBy 不生效 | 作用域问题：隐式值要在 sortBy 调用处**可见**。二选一：放伴生对象让编译器找到，或直接显式传 sortBy 第二参数 |
| 自定义类忘了实现/定义 Ordering | 直接 `sortBy(identity)` 会编译错（类无可比性）。先写 Ordering 再排 |
| 排序规则"次数降序+名称降序"字节序搞混 | 元组 `(-count, name)`：第一维取负=降序，第二维原样=升序。规律：**要降序就取负，要升序就原样** |
| 用自定义 Ordering 时数值类型不对 | Ordering.by 返回的类型必须可比较。`(String, Int)` 注意先转类型 |

@@point ⑧ 组合实战：卡口统计四需求（综合演练）
@@need 要解决什么
最后上一个多算子组合的真实案例：**卡口车辆通行统计**。它是"取当天 + 聚合 + TopN + 二次排序"四样东西的同场考试：数据长（车辆卡口通过记录）、需求多（4 个）、互相复用（需要缓存设计）。跑通它=本章所有技能的综合验收。

@@idea 核心思路
**数据**：车辆通过卡口的记录 `(车牌, 卡口编号, 通过时间)`：

```text
京A12345  卡口01  2026-10-01 08:10:22
京A12345  卡口02  2026-10-01 08:15:03
沪B67890  卡口01  2026-10-01 08:11:57
...
```

**四个需求（拆解出公共数据流）**：

```scala
// 公共：解析 + 清洗 + 缓存（四个统计都要复用）
val pass = rawLogs.map(parse).filter(valid)
pass.cache()

// 需求 1：当天总车流量（每行=一次通过）
val total = pass.count()

// 需求 2：每个卡口通过量（聚合 TopN：哪个卡口最堵）
val perGate = pass.map(r => (r.gateId, 1)).reduceByKey(_ + _)
val topGate = perGate.sortBy(_._2, false).take(3)

// 需求 3：当天通过的车辆数（UV：去重）
val carUv = pass.map(_.plate).distinct().count()

// 需求 4：每个卡口最先通过 / 最晚通过（组内时间排序=二次排序）
val firstPass = pass.map(r => (r.gateId, r.time, r.plate))
                    .groupByKey()
                    .mapValues(_.toList.sorted.head)   // 组内按时间排序取最早
```

**要点回顾**：

- `cache()` 让 4 个需求共享一次解析结果
- 需求 2 用"聚合+排序+TopN"，需求 4 用"groupBy + 组内排序"——**两种思路在同一案例里各归其位**
- 需求 4 是"分组后组内 Top1"，本质是**组内二次排序取极值**——面试和业务都高频

**验证习惯**：每完成一个需求立即 `take(5)` 人工核对（对照样例手算值），全对再接下一个。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| groupBy 后 mapValues 排序又能用 sortByKey | 组内处理按"数据结构"选：Iterable 小集合可 sorted；想省内存用 reduceByKey 聚合出最值（`reduceByKey((a,b)=>if(a<b)a else b)`） |
| 需求 4 想"组内降序取最大" | groupBy + mapValues(_.max)（用 Ordering）或 reduceByKey 取 max。别拆两次排序 |
| 四个需求各写一遍解析 | 解析只写一次，之后都从 `pass` 派生（这就是"公共 RDD + cache"思想）——**别复制粘贴三段解析代码** |
| 忘记对产生多个 Job 的链做"先验证后全量" | 先小数据样本验证语义，再放大数据跑。生产直接跑大数据，错一次等 10 分钟 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **完整统计骨架**：读入→清洗→缓存→聚合→输出 的通用流水线 | PV/UV/TopN 全是一套骨架的变体，任何日志统计直接套 |
| **排序三连招**：元组多字段、取负调方向、自定义 Ordering | "先 a 后 b"混合排序一次写对，不再被二次 sortBy 骗 |
| **复用意识**：公共 RDD + cache 支撑多需求 | 实战工程的性能命根子，也是"会不会设计数据流"的检验 |

@@quiz
1. 一个统计程序要算 PV、UV、分页 PV 三个指标，日志 RDD 为什么要先 cache？cache 放在哪个位置最合理？
2. UV 统计用 `distinct().count()` 和 `map((_,1)).reduceByKey(_+_).count()` 有什么区别？哪个更省 shuffle 数据量？
3. 为什么 `rdd.sortBy(a).sortBy(b)` 不能得到二次排序？正确做法是什么？
4. 数据 `("10","9")` 按字符串排和按数字排结果分别是什么？为什么日志字段要转类型再排序？
5. 要求"次数降序、次数相同按页面名升序"取 Top5，写出 RDD 代码（用元组取负或 Ordering 任一）。
6. 判断题：groupBy 之后用 mapValues(_.toList.sorted) 取组内最早记录，这一步属于"组内排序"，不需要额外 shuffle。

@@links
参考|Spark 分布式计算框架基础（第 12 章：实战 UV/PV）|#
参考|Spark 内核进阶（第 7 章：二次排序与卡口统计）|#
官网|排序与 takeOrdered 示例|https://spark.apache.org/docs/latest/rdd-programming-guide.html#transformations
资料|sparkdemo.zip（本章全部案例源码）|#