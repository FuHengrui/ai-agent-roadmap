@@h1 第八章　RDD 行动算子：触发计算与输出结果
@@sub 阶段 13 · 大数据处理与分布式检索技术　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章的转换算子全是"纸面记录"——你写了 map、filter、join，但**数据一行都没真的算**。那 Spark 到底什么时候干活？答案是：**遇到行动算子（Action）时**。行动算子才是"按启动按钮"的那一下：收集结果、保存文件、遍历输出、统计数量。

更需要警惕的是：**很多行动算子行为相似但风险天差地别**。`collect()` 会把全部数据拉回 Driver（大数据直接 OOM），`take(5)` 只取 5 条很安全；`foreach` 在 Executor 跑、`collect` 后遍历在 Driver 跑——用错一个，要么内存爆炸，要么结果完全不对。

学完这一章，你能：**为每个需求选对行动算子（取数/统计/保存/遍历），并规避 collect 类算子的内存陷阱**。

@@prep 开始之前
继续用第三章的 Local 环境，不用装新东西；转换算子的惰性先弄明白，这章正好接上。

@@goal 学到这儿就够了
能按需求选对 collect、take、foreach，并说清谁有 OOM 风险，这章就算过了。

@@map 这一章在整个知识库里的位置
上一章（转换算子）：你会把 RDD 变换来变换去，但还没真正"算出结果"
**本章** ← 你在这里：行动算子——按启动按钮的最后一环，触发计算、产出结果
下一章：Spark 内核——DAG 如何构建、Stage/Task 如何调度（你写的算子终于被"执行系统"接住）
再往后：内核实战 → SparkSQL/Streaming
阶段终点：你能独立用 RDD 完成从读入、变换到输出结果的全链路

@@point ① 行动算子总览：三种"出口"
@@need 要解决什么
行动算子种类不少，第一次看容易蒙。先建立框架：**行动算子本质是"结果的出口"**，而出口只有三种——收集回 Driver、写存储、就地执行。一张表看清全貌，学每个具体算子就有了归属感。

@@idea 核心思路
行动算子定义：**返回值不是 RDD 的算子**（返回数组/数字/Unit等），作用=触发执行计划、按指示做最终处理。

| 出口类型 | 算子 | 干什么 | 数据流向 |
|---|---|---|---|
| 收集回 Driver | `collect()` / `take(n)` / `first()` | 把结果拉回驱动端 | Executor → Driver |
| 统计返回数值 | `count()` / `countByKey()` / `reduce()` / `fold()` / `top()` / `takeOrdered()` | 返回一个数/数组 | 聚合成小结果 |
| 就地执行 | `foreach()` / `foreachPartition()` / `saveAsTextFile()` | 在 Executor 上执行，不回流 Driver | 留在集群侧 |

**选择口诀**：想看 → take/first；要全部结果且数据小 → collect；要统计数字 → count/reduce；要输出/落盘 → saveAsTextFile；要在 Executor 做副作用 → foreach 系列。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为行动算子只干"收集" | 一半行动算子（foreach/save）根本不回 Driver，就地执行。把这两种搞混，代码会跑在你以为的错误地方 |
| 用转换算子判断"算子类型" | 看返回值最准：返回 RDD 是转换；返回其他是行动。`count()` 返回 Long，行动；`countByKey()` 返回 Map，行动 |
| 一个程序里只有一个行动算子？ | 无所谓多少，每个行动算子触发一次完整计算（Job）。多个 collect=多个 Job，重复计算可用 cache 缓解 |

@@point ② collect / take / first：取数据的三种姿势
@@need 要解决什么
"我想看看结果"——这句话的三种写法风险天差地别。数据大时用错直接 OOM，数据小时用对则秒开。本点把取数据的三种姿势和各自的适用边界讲死。

@@idea 核心思路
```python
rdd.collect()    # 全部数据拉回 Driver → 数组
rdd.take(n)      # 前 n 条拉回 Driver（n 一条条取到够为止）
rdd.first()      # 就取第一条
rdd.count()      # 返回元素总数（Long），完全安全
```

| 算子 | 返回 | 大数据上 | 用途 |
|---|---|---|---|
| `collect()` | 全部元素 | ⚠️ OOM 风险 | 结果确定很小才用 |
| `take(n)` | 前 n 个 | ✅ 安全 | 抽样看结构、调试 |
| `first()` | 1 个 | ✅ 安全 | 快速看一条长啥样 |
| `count()` | 条数 | ✅ 安全 | 统计总行数 |

**为什么 collect 危险**：它把**所有分区**的数据通过网络汇总到 Driver 一个进程。几亿条数据 → Driver 内存直接爆 `OutOfMemoryError`。而 take 取够 n 条就停，不拉全量。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 大数据集上 collect 后堆溢出 | 改用 `take(n)` 抽样看，或 `saveAsTextFile` 落盘。**"看一下"永远先用 take** |
| take(n) 取出来的顺序不是自己想的 | take 是按分区顺序抓，不是全局逻辑序。想要有序用 `takeOrdered(n)`（下一点） |
| `count()` 慢 | count 也要全量扫描（每分区数完汇总）。数据大时正常慢，别误以为卡死，看 UI 进度 |

@@point ③ top / takeOrdered：排序取 TopN
@@need 要解决什么
需求是"取销售额前 10 的店铺"、"最大的 5 个数"。你会想：先 `sortBy` 再 `take`——但那样要为全量数据排序，浪费。**top/takeOrdered 用更聪明的"只保住 TopN"方式**，还自带序控制，是 TopN 需求的正解。

@@idea 核心思路
```scala
// top(n)：取降序排序后的前 n 个（默认最大 N 个）
rdd.top(3)                    // [9, 8, 7]  前三大
rdd.top(3)(Ordering.Int.reverse)  // [1, 2, 3]  前三个最小

// takeOrdered(n)：取升序排序后的前 n 个
rdd.takeOrdered(3)            // [1, 2, 3]  前三个最小
rdd.takeOrdered(3)(Ordering.Int.reverse)  // [9, 8, 7]
```

| 算子 | 默认顺序 | 最小/最大的拿法 |
|---|---|---|
| `top(n)` | 先降序再取前 n → **最大的 n 个** | reverse 后取最小的 n 个 |
| `takeOrdered(n)` | 先升序再取前 n → **最小的 n 个** | reverse 后取最大的 n 个 |

**记得**：`Ordering.Int.reverse` 是从大到小/从小到大的开关，极大值小值都靠它。经典坑：想要"最大值"却用了默认按升序取首的 takeOrdered，拿到的是最小值。

**效率**：只维护一个大小 n 的堆，不排全量序——大数据 TopN 用它比全局排序快得多。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 想要最大 n 个却写了 `takeOrdered(3)` | takeOrdered 默认升序取前 n = **最小** n 个。要最大必须 `reverse`。先想"默认是什么序"再决定要不要 reverse |
| 直接调用 `rdd.top(3)` 碰到自定义类型 | 自定义对象无自然序会编译报错。定义 `Ordering`（用 `-x._2` 这类写法）或先 map 成可排序元组 |
| 以为 top 返回的是"排序后的完整结果" | top 只保证"这 n 个是极值"，n 个内部顺序也可能不保证稳定。要严格有序再用 sortBy |
| 分不清 top 和 takeOrdered 哪个最大 | 人类的直觉：top=取顶=最大的 n 个；takeOrdered=按升序取=最小的 n 个。两者正好互补，reverse 互换 |

@@point ④ reduce / fold：整 RDD 归并成一个值
@@need 要解决什么
"全部销售额加起来""所有元素拼成一个字符串"——**把一个 RDD 归并成唯一结果**。这就是 reduce/fold 的用途。它还藏着"分区内+分区间"两段式执行的机制，是理解 Spark 聚合的窗口（fold 的初始值作用在每分区，极易算错）。

@@idea 核心思路
**reduce(func)：对整个 RDD 元素两两应用 func，归并成一个值**（函数需满足结合律）：

```scala
val rdd = sc.makeRDD(List(1, 2, 3, 4, 5))
rdd.reduce(_ + _)   // 15 = 1+2+3+4+5

val pairs = sc.makeRDD(List(("a",1), ("b",2)))
pairs.reduce((x, y) => (x._1 + y._1, x._2 + y._2))  // ("ab", 3)
```

**fold(zero)(func)：带初始值的 reduce**。注意 zero 的"两段式"用法：

```text
数据 1..9 分 3 个分区：[[1,2,3],[4,5,6],[7,8,9]]，zero=10
分区内：10+1+2+3=16，10+4+5+6=25，10+7+8+9=34
分区间：10 + 16 + 25 + 34 = 85      ← 初始值参与每个分区+最终合并！
```

**关键结论**：fold 的初始值**每个分区都要加一次**，最后合并再加一次。`(分区数+1)×zero + 数据总和   # 每个分区一次 + 最后合并一次`——所以 fold 的结果**不等于** zero+sum，这是最容易算错的地方。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| fold 结果和自己手算的 zero+sum 对不上 | 初始值参与了**每个分区内**和**最终合并**，结果 = 元素和 + zero×分区数（本例 45+40=85 才对，不是 45+10=55）。数字诡异时先想分区 |
| reduce 的 func 不满足结合律 | reduce 要求 func 有**结合律**（如求和/乘）。`(a-b)` 这种不可结合的会因分区边界算出不同结果 |
| 初始值类型和 RDD 元素类型不一致 | fold 要求 zero 与元素同一类型（Int RDD → zero 也 Int）。异构聚合（求总和+最大值）用 `aggregate`，下一章实战见 |
| 空 RDD 上调 reduce | 空 RDD reduce 抛异常（无可归并）。先 `rdd.isEmpty()` 或给 reduce 兜底（用 fold 带 zero） |

@@point ⑤ foreach / foreachPartition：在 Executor 上"就地干活"
@@need 要解决什么
"把结果写到数据库""每行调一次外部 API"——这些动作**不需要也不应该把数据拉回 Driver**，直接在 Executor 上执行效率最高。foreach 每元素执行一次；foreachPartition 每分区执行一次，批量场景性能差一个量级。

@@idea 核心思路
```python
# foreach：对每个元素执行一段逻辑（无返回值）
rdd.foreach(lambda x: print(x))

# foreachPartition：对每个分区，把整个分区的数据作为一个迭代器交给函数
def write_batch(iterator):
    conn = create_db_connection()          # 每分区只建一次连接
    for row in iterator:
        conn.insert(row)
    conn.close()

rdd.foreachPartition(write_batch)
```

| 对比 | foreach | foreachPartition |
|---|---|---|
| 执行粒度 | 每个元素 | 每个分区 |
| 函数收到的 | 单个元素 | 整个分区的迭代器 |
| 建连接次数 | 元素数（危险） | 分区数（友好） |
| 适用 | 打印、轻量动作 | 批量写库/调 API/重资源操作 |

**为什么连接放 foreachPartition**：map/foreach 中对每条数据都 `new 连接`，百万条数据建百万次连接——秒挂。每分区建一次连接，遍历分区内所有行，性能提升一个量级。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 在 foreach/map 里建 DB 连接 | 每条数据建一个连接，Driver 端疯狂报 OOM/超时。**连接类资源一律 foreachPartition 每分区建一次** |
| foreach 里打印"没看到输出" | foreach 在 **Executor** 执行，local 模式看得见（同进程），集群模式打印在 worker 日志里，不在 Driver 终端。想回显用 `collect().foreach(print)`（仅小数据） |
| 在 foreach 里改了 Driver 变量的值 | **改不了**——foreach 在 Executor 上跑的是序列化副本，Driver 的变量不会变。跨 Executor 共享用累加器（内核章见），跨 Executor 汇总用累加器、传大只读数据用广播变量（第十一章见）；广播变量本身是**只读**的 |

@@point ⑥ saveAsTextFile：结果落盘的正确姿势
@@need 要解决什么
结果不能总用 collect() 拉回内存——大结果要**写文件**。saveAsTextFile 就是最常用的落盘算子。它有两大特点必须知道：**每个分区写一个文件**、**目录不能提前存在**。用错这俩，要么结果分片找不到、要么报"文件已存在"。

@@idea 核心思路
```scala
rdd.saveAsTextFile("output/result")
// 生成目录（Spark 自动创建）：
// output/result/_SUCCESS          ← 成功标记
// output/result/part-00000        ← 每个分区一个文件
// output/result/part-00001
```

三个硬规则：

1. **输出目录不能已存在**——Spark 为避免覆盖误删，目录已存在直接报错。要么删旧目录、要么换名字
2. **只写文件系统**（本地/HDFS/S3，支持路径前缀），不写数据库——写库走 foreachPartition
3. **数据不经过 Driver**：每个分区的 Executor 直接写自己的 part 文件，所以千分区=千个文件

**悟出规律**：part-00000 的数量 = 分区数。想少文件就先 `coalesce(1)` 合并分区（小数据时），想控制文件粒度就调分区数。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 第二次跑报 `FileAlreadyExistsException` | 输出目录必须全新。作业脚本里先 `rm -rf output/result` 或自动加时间戳目录：`output/result_20261014` |
| 产出 200 个小文件不想要 | part 文件数=分区数。先 `rdd.coalesce(1)`（减分区，尽量不 shuffle）再 save，就一个文件。注意：大量小文件本身是 HDFS 的坑，控制分区数有意义 |
| 只想清空目录里的旧数据 | Spark 不会帮你清，自行先删除再 saveAsTextFile |

@@point ⑦ countByKey / countByValue：按键计数二兄弟
@@need 要解决什么
"每个品类各卖了几单""每个词出现几次"——**按键统计出现次数**。countByKey 对 KV 型 RDD 按键计数、countByValue 对任意 RDD 按值计数。它俩直接返回 Map（Driver 端），小而常用——但**返回值在 Driver**，键太多会占 Driver 内存。

@@idea 核心思路
```scala
// countByKey：对 KV 型 RDD，统计每个 key 的出现次数（注意：是"条数"不是"value 和"）
val pairs = sc.makeRDD(List(("a", 10), ("a", 20), ("b", 5)))
pairs.countByKey()
// Map(a -> 2, b -> 1)    ← key 出现几条，不是 value 相加！

// countByValue：对任意 RDD，统计每个值出现次数
val nums = sc.makeRDD(List(1, 1, 2, 3, 3, 3))
nums.countByValue()
// Map(1 -> 2, 2 -> 1, 3 -> 3)
```

| 算子 | 适用 RDD | 按什么分组 | 返回 |
|---|---|---|---|
| `countByKey()` | KV 型 | key | Map[K, Long] |
| `countByValue()` | 任意 | 元素自身 | Map[V, Long] |

**对比 reduceByKey(_+_)**：countByKey 是"数条数"，reduceByKey 是"合并 value"。求"每个词出现次数"用 WordCount 的 `map((_, 1)).reduceByKey(_ + _)`；直接 countByValue 也一样。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 countByKey 是"value 求和" | 它统计的是**key 出现的记录条数**。value 求和用 reduceByKey(_+_)；两个需求别搞混 |
| 键很多时结果 Map 巨大 | countByKey 返回的 Map 在 **Driver 端**，几千万 key 会撑爆 Driver 内存。键极多时改用 reduceByKey 之后再落盘 |
| countByKey 和 count() 混淆 | `count()` 是总条数一个数；`countByKey()` 是每个 key 的条数 Map。一个"全局一个数"，一个"按键分组" |

@@point ⑧ 其余转换算子速览：sortBy / glom / mapPartitions 等
@@need 要解决什么
还有几个高频转换算子没归到上一章的"核心篇"：排序类 sortBy/sortByKey、分区视图 glom、分区级处理 mapPartitions、自定义分区 partitionBy、采样 sample。它们的定位简单但**签名细节特容易错**——本点把"一句话定义+关键签名+最小用例"打包给你，用到时回来查。

@@idea 核心思路
**① sortBy：指定字段排序（可升降序，可设分区数）**

```scala
rdd.sortBy(x => x._2, ascending = false)   // 按元组第 2 个字段降序
rdd.sortBy(x => x._2, ascending = true, numPartitions = 1)  // 全局有序=1 分区
```

**② sortByKey：KV 直接按键排序（默认升序、分区数不变）**

```scala
rdd.sortByKey()                            // 按键升序，分区数与原来相同
rdd.sortByKey(false, 1)                    // 降序，且结果全局有序 1 分区
```

**③ glom：把"每个分区内的数据"聚成数组，看分区结构**

```scala
rdd.glom().collect()   // [[1,2],[3,4],[5,6]]，一眼看清分区边界
```

**④ mapPartitions：按分区处理（批量）**

```scala
rdd.mapPartitions(iter => iter.map(process))   // 分区级 map，适合批量加工
```

**⑤ partitionBy：自定义分区器重新分区（KV 型）**

```scala
rdd.partitionBy(new HashPartitioner(3))         // 按 key 哈希到 3 个分区
```

**⑥ sample：采样（withReplacement 是否放回，fraction 比例，seed 随机种子）**

```scala
rdd.sample(withReplacement = true, fraction = 0.2, seed = 1)
```

**⑦ coalesce / repartition：改分区数**（上一章讲过，回看）

| 算子 | 用途 | 是否 shuffle |
|---|---|---|
| coalesce(n) | 减分区 | 尽量不 shuffle |
| repartition(n) | 增分区或重分布 | 必 shuffle |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| sortBy 全局有序但分区 >1 | 多分区下每个分区局部有序，**跨分区不确定**。要全局序 `numPartitions=1` |
| sample 的三个参数顺序记不住 | `sample(withReplacement, fraction, seed)`：是否放回、比例（0~1）、随机种子。想复现结果固定 seed；fraction>1 且不放回会报错 |
| partitionBy 只在 KV 型可用 | 它要求 `RDD[(K,V)]`。普通 RDD 想自己定分区用 `mapPartitions` + 重算，或先 map 成 KV |
| glom 后处理逻辑用到原 RDD | glom 返回 `RDD[Array[T]]` 是新类型，别拿它当原来的处理链（它是"看结构"用的，不是正常处理算子） |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **行动算子框架**：三种出口（回 Driver / 统计值 / 就地执行） | 看需求选出口，不会再 collect 滥用 OOM |
| **聚合家族**：reduce / fold / countByKey 的原理与算错点 | 搞懂了"分区内+分区间"机制，Spark 聚合逻辑就没盲区 |
| **输出技能**：saveAsTextFile、foreachPartition 的正确姿势 | 落盘、写库两大高频需求的性能正确写法 |

@@quiz
1. `collect()` 为什么在小数据上安全、大数据上危险？"想看结果"的正确第一选择是什么算子？
2. `top(3)` 和 `takeOrdered(3)` 默认分别取的是最小还是最大的 3 个？想要"最大 3 个"各该怎么写？
3. 数据 1..9 分 3 个分区，`fold(10)(_+_)` 的结果是多少？为什么不是 10+sum？
4. 有一段逻辑"把 RDD 每行写入 MySQL"，应该用 foreach 还是 foreachPartition？为什么？
5. saveAsTextFile 生成的文件数量由什么决定？想只输出一个文件该怎么处理？
6. 判断题：countByKey 统计的是每个 key 的 value 之和。

@@links
参考|Spark 分布式计算框架基础（第 10 章：行动算子 1）|#
参考|Spark 分布式计算框架基础（第 11 章：行动算子 2）|#
官网|RDD API 文档（Action 部分）|https://spark.apache.org/docs/latest/rdd-programming-guide.html#actions
资料|sparkdemo.zip（本章行动算子示例源码）|#