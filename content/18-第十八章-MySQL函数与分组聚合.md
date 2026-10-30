@@h1 第十八章　MySQL SQL 函数与分组聚合
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★★

@@why 这一章在解决什么问题
**原始数据躺在表里，但业务要的是"加工过的信息"：姓名要大写、日期取年份、每班的平均分、每个部门的最高工资。** 前一半是 SQL 函数（一行一把刀），后一半是分组聚合（GROUP BY 把行归堆再统计）——查询从"取数"升级为"算数"。

学完你能回答：常用字符/数字/日期函数有哪些、CASE WHEN 怎么写、聚合函数五兄弟、GROUP BY 和 HAVING 什么时候用、WHERE 和 HAVING 到底差在哪。

@@prep 开始之前
上一章的单表查询会写就能开始，这章不用装新东西，聚合和分组要在表上多试几遍。

@@goal 学到这儿就够了
能用字符、日期、CASE WHEN 加工字段，能用 GROUP BY 加 HAVING 出分组统计，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：数据操作与单表查询——单表取数（无加工）
**本章** ← 你在这里：函数加工 + 分组聚合——单表查询"会算数"
**下一章**：多表查询与子查询——跨表 JOIN 与嵌套子查询
**再往后**：索引事务用户管理 → 阶段收官
**阶段终点**：查询能力从"取"到"算"，为 Pandas 的 groupby 提供 SQL 对照

@@note info 学习提示
函数部分：**先记三组主角**（字符/数字/日期），每组记 3 个就够用（CONCAT/LENGTH/SUBSTRING、ROUND/ABS/MOD、NOW/YEAR/DATE_FORMAT），用到再翻文档。分组部分是本路核心：**GROUP BY 把相同的行并成一组，HAVING 过滤组**——理解"行 vs 组"两个层次是本章成败关键。

@@point ① 字符函数
@@need 要解决什么
**字符串加工：拼接、取长度、截取、大小写**——CHAR 系列函数是最常用的一组。

@@idea 核心思路

```sql
SELECT CONCAT('你', '好');           -- 拼接：你好
SELECT CONCAT_WS('-', 'a', 'b');     -- 带分隔符拼接：a-b
SELECT LENGTH('hello');              -- 字节数：5
SELECT CHAR_LENGTH('你好');          -- 字符数：2（重要！）
SELECT LOWER('ABC'), UPPER('abc');   -- 小写/大写
SELECT SUBSTRING('abcdef', 2, 3);    -- 从第 2 位取 3 个：bcd
SELECT TRIM('  hi  ');               -- 去两端空格
SELECT REPLACE('a-b-c', '-', '+');   -- 替换：a+b+c
```

三个易错点：

- **LENGTH 数的是字节**（中文 1 字=3 字节），**CHAR_LENGTH 数的是字符**——判断"用户名长度"用后者；
- **SQL 下标从 1 开始**（不像 Python 从 0）；SUBSTRING(str, 起始, 长度)；
- CONCAT 遇 NULL 输出 NULL（注意脏数据）。

函数可以套用：`SELECT UPPER(TRIM(name)) FROM student;`——一层层剥洋葱。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| LENGTH('你好') 显示 6 | 中文 3 字节/字；要看"字的个数"用 CHAR_LENGTH |
| SUBSTRING 取出来不对 | 起始位置从 1 开始数，仔细核对 |
| CONCAT 结果 NULL | 有 NULL 成员；用 IFNULL(col,'') 预清洗 |

@@point ② 数字函数
@@need 要解决什么
**数字加工：四舍五入、绝对值、取整、取余、随机数**——数字函数是"运算列"的强化版。

@@idea 核心思路

```sql
SELECT ROUND(3.14159, 2);     -- 四舍五入到 2 位：3.14
SELECT ROUND(3.5);            -- 取整（四舍五入）：4
SELECT CEIL(3.1);             -- 向上取整：4
SELECT FLOOR(3.9);            -- 向下取整：3
SELECT ABS(-5);               -- 绝对值：5
SELECT MOD(10, 3);            -- 取余：1
SELECT RAND();                -- 0~1 随机数
SELECT RAND() * 100;          -- 0~100 随机：配合 ROUND 取整
```

- **ROUND(x, n)：保留 n 位小数；ROUND(x)：四舍五入取整；**
- **CEIL 上天、FLOOR 落地、MOD 取余**；
- **RAND() 每次调用不同**，`ORDER BY RAND()` 可随机取行（但大表很慢，慎用）。

组合示例：`SELECT ROUND(RAND() * 100) AS 随机分;` ——联考随机分就是这么来的。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ROUND 负数位想不通 | ROUND(123, -2)=100（往十位进位）；少见但要知道 |
| MOD 和 % | 等价；MOD(10,3)=1 |
| ORDER BY RAND() 卡死 | 全表排序超慢；大表随机取样换 id 区间法 |

@@point ③ 日期时间函数
@@need 要解决什么
**对时间做加工：取当前时间、拆年/月/日、格式化**——日期函数配合第 13 章 Pandas 时间轴正好一套。

@@idea 核心思路

```sql
SELECT NOW();                    -- 当前日期时间 2026-10-15 14:30:00
SELECT CURDATE();                -- 当前日期
SELECT CURTIME();                -- 当前时间

SELECT YEAR(NOW());              -- 年：2026
SELECT MONTH(NOW());             -- 月：10
SELECT DAY(NOW());               -- 日：15
SELECT DAYOFWEEK(NOW());         -- 星期几（1=周日）

SELECT DATE_ADD(NOW(), INTERVAL 7 DAY);   -- 7 天后的日期时间
SELECT DATEDIFF('2026-10-20', '2026-10-15');  -- 相差天数：5

-- 格式化输出：%Y 年 %m 月 %d 日 %H 时 %i 分 %s 秒
SELECT DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s');   -- 2026-10-15 14:30:00
```

记忆卡片：**NOW() 全家桶（YEAR/MONTH/DAY 拆件）、DATE_ADD 加区间（INTERVAL n DAY/MONTH/YEAR）、DATEDIFF 差天数、DATE_FORMAT 换脸。**

业务经典：近 30 天订单 `WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DAYOFWEEK 以为 1=周一 | MySQL 是 1=周日；别记错 |
| DATE_FORMAT 格式串写错 | 大小写敏感 %Y%m%d vs %y%m%d；对照文档 |
| DATEDIFF 参数顺序反了 | DATEDIFF(大日期, 小日期) 得正数 |

@@point ④ 类型转换与通用函数
@@need 要解决什么
**字符串 '123' 要变数字、NULL 要兜底**——CAST 转换 + IFNULL 空值处理是数据分析前处理必备。

@@idea 核心思路

```sql
-- 类型转换：CAST(值 AS 类型)
SELECT CAST('123' AS SIGNED);              -- 字符串 → 整数 123
SELECT CAST('3.14' AS DECIMAL(5,2));       -- → 3.14

-- 空值兜底：IFNULL(expr, 替代值)
SELECT IFNULL(phone, '未留手机号') FROM student;

-- 条件取值：IF(条件, 是, 否)
SELECT IF(score >= 60, '及格', '不及格') FROM student;

-- 分支多条件：CASE WHEN（下一个知识点专讲）
```

- **CAST 常用目标**：SIGNED（整数）、DECIMAL、CHAR、DATE；
- **IFNULL 是"空值填默认"**——报表必备（NULL 参与运算全变 NULL，先兜底）；
- **IF(条件, A, B)** 是单条件二选一的快速写法。

和 Python 对照：CAST ≈ int()/float()，IFNULL ≈ fillna，IF ≈ np.where。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| CAST('abc' AS SIGNED) 变 0 | 转不动的字符串给 0 不报错——先确认数据可转 |
| IFNULL 只处理 NULL | 空字符串 '' 不算 NULL，要 TRIM 后判断 |

@@point ⑤ CASE WHEN：条件分支
@@need 要解决什么
**"90+ 优秀、80~89 良好、60+ 及格、否则不及格"**——CASE WHEN 是 SQL 里的 if-elif-else。

@@idea 核心思路

```sql
SELECT name, score,
    CASE
        WHEN score >= 90 THEN '优秀'
        WHEN score >= 80 THEN '良好'
        WHEN score >= 60 THEN '及格'
        ELSE '不及格'
    END AS 等级
FROM student;
```

写法要点：

- **CASE 开始、END 结束**，`END AS 别名` 给结果列命名；
- **WHEN 条件 THEN 值**逐条判断，**命中第一个就返回**（顺序很重要：90 先于 80 判断）；
- `ELSE 兜底` 可选，不写则未命中返回 NULL；
- 两种语法：`CASE 表达式 WHEN 值 THEN ...`（等值判断）vs `CASE WHEN 条件 THEN ...`（任意条件）。

**中断原则**：CASE 一旦命中某 WHEN 就短路，后面的不再判断——所以区间要"从大到小"或"从小到大"排好。

业务案例：等级划分、年龄段分桶、订单状态映射（1→已支付）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 等级判断错乱 | WHEN 顺序不对（如 60 写在 90 前）；区间判断按"大→小"写 |
| 漏写 END 报错 | CASE 必须 END 收尾；漏了必报 syntax error |
| ELSE 缺了输出 NULL | 想兜底就写 ELSE；想留空故意不写 |

@@point ⑥ 聚合函数五兄弟
@@need 要解决什么
**整个表（或一组）的统计：多少行、总和、平均、最大最小**——COUNT/SUM/AVG/MAX/MIN 是 SQL 的"统计心脏"。

@@idea 核心思路

```sql
SELECT COUNT(*) FROM student;            -- 总行数（含 NULL）
SELECT COUNT(phone) FROM student;        -- 非空 phone 的个数
SELECT COUNT(DISTINCT gender) FROM student;  -- 去重计数

SELECT SUM(score) FROM student;          -- 求和（忽略 NULL）
SELECT AVG(score) FROM student;          -- 平均值（忽略 NULL）
SELECT MAX(score), MIN(score) FROM student;  -- 最大最小

-- 搭配使用全书名
SELECT COUNT(*), MAX(score), AVG(score) FROM student;
```

三个必须记住的差异：

- **COUNT(*) 数所有行；COUNT(列) 数该列非 NULL 个数**——统计"填了手机号的人"用后者；
- **SUM/AVG 自动忽略 NULL**（不是报错，直接跳过）；
- **MAX/MIN 可用于数字也可用于字符串/日期**（取最早/最晚时间超常用）。

聚合函数返回**一行**结果（多行压缩成一行）——这就是"聚合"两个字的含义，为 GROUP BY 铺垫。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| COUNT 和 SUM 结果对不上 | COUNT 是行数、SUM 是数值和；明确要数啥 |
| AVG 里有 NULL 算少了 | AVG 忽略 NULL 再除非空个数；要严格就 IFNULL 后 AVG |
| MAX 时间列 OK 但比大小不对 | MAX 对 DATE/DATETIME 直接比，能取"最近时间" |

@@point ⑦ GROUP BY：分组聚合
@@need 要解决什么
**"每个班的平均分""每个部门多少人"**——GROUP BY 按列分组，每组各算一次聚合。

@@idea 核心思路

```sql
-- 按性别分组，每组统计（student 表里真有 gender，照抄就能跑）
SELECT gender, COUNT(*), AVG(score)
FROM student
GROUP BY gender;

-- 多列分组：班 × 性别
> 下面几节为了演示「按班级分组」，用到 `class_id` 这一列。第 16 章建的 `student` 表里**没有**它——
> 先把列补上再照抄：
>
> ```sql
> ALTER TABLE student ADD COLUMN class_id TINYINT;
> ```

SELECT class_id, gender, COUNT(*)
FROM student
GROUP BY class_id, gender;
```

规则三连：

- **GROUP BY 把相同值的行并成一组**，聚合函数每组各算一次（结果行数=组数）；
- **SELECT 里出现的非聚合列必须是 GROUP BY 里的列**（如 class_id）——这是 SQL 标准约束，MySQL **8.0 默认开启 `ONLY_FULL_GROUP_BY`**：SELECT 里的非聚合列必须出现在 GROUP BY 里，否则直接报错（老版本才宽松）；
- **WHERE 在分组之前过滤行**（先滤后组）。

**执行顺序**（接上章总纲）：`FROM → WHERE → GROUP BY → 聚合 → HAVING → SELECT → ORDER BY → LIMIT`——分组在过滤后、投影前。

对照 Pandas：GROUP BY class_id + agg = Pandas 的 `df.groupby('class_id').agg(...)`——同一思维，两种语法。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| SELECT 非分组列未进 GROUP BY（ONLY_FULL_GROUP_BY 报错） | 严格模式是好事：把多余列删掉或加进 GROUP BY |
| WHERE 想过滤"组"的条件 | WHERE 只能过滤行；组的过滤用 HAVING（下一知识点） |
| 分组忘了聚合列 | GROUP BY 请与聚合函数同框出现，否则分组没意义 |

@@point ⑧ HAVING：过滤组 + WHERE 与 HAVING 对比
@@need 要解决什么
**"只要平均分超过 80 的班""只要人数超过 3 人的组"**——聚合结果算完还要筛，就得 HAVING。

@@idea 核心思路

```sql
-- 平均分 >= 80 的班
SELECT class_id, AVG(score) AS avg_score
FROM student
GROUP BY class_id
HAVING avg_score >= 80;

-- 人数 > 3 的班
SELECT class_id, COUNT(*) AS cnt
FROM student
GROUP BY class_id
HAVING cnt > 3;
```

**WHERE vs HAVING 终极对比**：

| 维度 | WHERE | HAVING |
|---|---|---|
| 过滤对象 | **行**（分组前） | **组**（分组后） |
| 能否用聚合函数 | 不能（WHERE SUM(score)>300 报错） | 能（HAVING AVG(score)>80） |
| 执行时机 | GROUP BY 之前 | GROUP BY 之后 |
| 别名可用？ | 否 | 可用（MySQL 宽松） |

顺序铁律：**WHERE 先滤行 → 分组 → 聚合 → HAVING 滤组 → 输出。**

一起用的完整例子：

```sql
-- 成绩非空的学生中，平均分 >= 80 的班级
SELECT class_id, AVG(score) AS avg_score
FROM student
WHERE score IS NOT NULL
GROUP BY class_id
HAVING avg_score >= 80
ORDER BY avg_score DESC;
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| WHERE 里写聚合函数报错 | 聚合过滤归 HAVING；WHERE 只滤行 |
| HAVING 不用 GROUP BY 可行吗 | 语法可以（全表一组），但语义怪；正常都要分组 |
| HAVING 用了没在 SELECT 的列 | 可（HAVING 只看分组结果），但可读性差，建议放 SELECT 或注释 |

@@summary
函数的刀 + 分组的框，单表查询彻底毕业：

| 函数族 | 主角们 | 一句话 |
|---|---|---|
| 字符 | CONCAT / CHAR_LENGTH / SUBSTRING / TRIM / REPLACE | 拼、数（字符数！）、切、清、换 |
| 数字 | ROUND / CEIL / FLOOR / ABS / MOD | 舍入上天落地、绝对值取余 |
| 日期 | NOW / YEAR / DATE_ADD / DATEDIFF / DATE_FORMAT | 现在拆件加区间差天数换脸 |
| 通用 | CAST / IFNULL / IF | 转型、兜底、单条件 |
| 分支 | CASE WHEN ... ELSE ... END | SQL 的 if-elif-else，命中即短路 |
| 聚合 | COUNT / SUM / AVG / MAX / MIN | 行数总和均值最大最小，忽略 NULL |
| 分组 | GROUP BY 列 + 聚合 | 相同值并组，每组各算 |
| 滤组 | HAVING | WHERE 管行、HAVING 管组（后者能用聚合） |

一句话记住本章：**字符函数用 CHAR_LENGTH 数字符、CASE WHEN 做分支（区间从大到小）、五兄弟聚合（COUNT 数行其他算值且跳 NULL）配合 GROUP BY 按组统计，组的过滤交给 HAVING——记住 WHERE 管行、HAVING 管组，SQL 就通了。**

@@quiz
1. LENGTH('你好') 和 CHAR_LENGTH('你好') 的返回值分别是什么？为什么？
2. SUBSTRING('abcdef', 2, 3) 的结果是什么？SQL 的下标从几开始？
3. ROUND、CEIL、FLOOR 三者的区别是什么？
4. 写出 3 个日期函数，并说明 DATEDIFF('2026-10-20', '2026-10-15') 的返回值。
5. IFNULL 和 IF 的使用场景差异是什么？为什么 NULL 参与运算前要先 IFNULL？
6. CASE WHEN 判断 90/80/60 三个挡位时，为什么 90 的判断要写在最前面？
7. COUNT(*) 和 COUNT(phone) 的结果可能不同，为什么？
@@links
参考|MySQL （158 页）|#
文档|MySQL 函数索引|https://dev.mysql.com/doc/refman/8.0/en/functions.html
文档|GROUP BY 优化|https://dev.mysql.com/doc/refman/8.0/en/group-by-optimization.html