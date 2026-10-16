@@h1 第十九章　MySQL 多表查询与子查询
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★★★

@@why 这一章在解决什么问题
**业务数据天然分表：客户在客户表、订单在订单表——想一次查出"客户的订单"，就必须把两张表连起来。** 多表查询（JOIN）是 SQL 的最高难度之一，也是数据库面试的第一座山。这一章从"为什么会连出几万行"讲起，把连接的本质、四种连接、两张表多次连接、嵌套子查询一次讲透。

学完你能回答：笛卡尔积为什么可怕、等值连接和 JOIN 的关系、自连接什么时候用、LEFT JOIN 和 INNER JOIN 的行数差异、子查询和 JOIN 怎么选、ANY 和 ALL 的区别。

@@map 这一章在整个知识库里的位置
**上一章**：SQL 函数与分组聚合——单表内"会算数"
**本章** ← 你在这里：连接 + 子查询——突破"单表"边界，数据库的精华章
**下一章**：索引、事务与用户管理——多表时代的性能与安全
**再往后**：阶段收官 → 完成数据链路
**阶段终点**：与第 13 章 Pandas merge 形成完整对照（ON = merge 的 on，JOIN 类型 = how）

@@note info 学习提示
本章两张表以上练习建议用**同一批小数据反复演练**（建 3 张各 5 行的表），亲手对比 INNER/LEFT/RIGHT 的行数和 NULL。节奏建议：先理解笛卡尔积与 n-1 规律 → 再逐类连接 → 最后子查询。**看懂"连接结果集长什么样"比背语法更重要。**

@@point ① 为什么需要多表 & 笛卡尔积
@@need 要解决什么
**一步到位理解连接的本质：把每对可能的行都拼起来（笛卡尔积），再用条件筛掉多余的。**

@@idea 核心思路

```sql
-- 两张表直接逗号连接 = 笛卡尔积（交叉连接）
SELECT * FROM 客户表, 订单表;   -- 行数 = 3 × 4 = 12

-- 等价写法：CROSS JOIN
SELECT * FROM 客户表 CROSS JOIN 订单表;
```

先讲清楚"为什么要拆表"：

- **范式**：客户信息存一次（客户表），订单只存"客户ID"外键指向它——避免"一个客户 100 单就复制 100 份信息"的冗余；
- **查询时再拼回来**：JOIN 就是把拆开的表按老板键重新合成一张宽表。

**笛卡尔积 = 每行 × 每行**（3 客户 × 4 订单 = 12 行）。绝大多数是"噪声"——只保留"客户ID 对得上"的行，这就是连接条件。

一句话：**连接 = 先笛卡尔积（全拼），再用 ON 条件"修剪"出有效配对。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 查询结果突然多了 N 倍 | 忘了连接条件：JOIN 时没 ON 或 ON 写错，变成笛卡尔积 |
| 想数"有效连接"用不上 | 见下一知识点 n-1 规律：有效行数通常 ≤ 较小表行数 |

@@point ② 连接条件与 n-1 规律
@@need 要解决什么
**多表连接时建几个连接条件才不漏不错？** 记住经典口诀：**n 张表连接，至少 n-1 个连接条件。**（不然又笛卡尔积）

@@idea 核心思路

```sql
-- 2 张表：1 个连接条件
SELECT * FROM 客户表 c, 订单表 o
WHERE c.id = o.cid;      -- 条件 1 个（2-1=1）

-- 3 张表：2 个连接条件
SELECT * FROM 客户表 c, 订单表 o, 商品表 g
WHERE c.id = o.cid
  AND o.gid = g.id;      -- 条件 2 个（3-1=2）
```

规律本质：**每多一张表，就要多一个"把新表钉住"的条件**，否则新表又和现有结果做笛卡尔积。

表别名：**多表查询必起别名**（c/o/g），短且避免列名冲突；引用列用 `表别名.列名`。

96 年经典写法（SQL92/隐式连接）vs 现代化写法（SQL99/JOIN 语法）——两种都要认识：**WHERE 版是"老写法"，JOIN ... ON 是"新写法"**，新写法把"连接逻辑"和"过滤逻辑"分开，更清楚。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了追加连接条件 | 加一张表加一个 ON/WHERE 条件（n-1 口诀） |
| 列名冲突（两边都有 id） | 用别名限定：c.id、o.id |
| 老代码用逗号连接读不懂 | 把它当"省略 ON 的 JOIN"，先补全连接条件 |

@@point ③ 等值连接与非等值连接
@@need 要解决什么
**连接条件除了"相等"还有"区间"**：等值连接（=）最常见，非等值连接（> < BETWEEN）处理"薪水等级"这类区间对应。

@@idea 核心思路

```sql
-- 等值连接：ON 条件是相等（90% 场景）
SELECT c.name, o.amount
FROM 客户表 c
JOIN 订单表 o ON c.id = o.cid;

-- 非等值连接：条件不是相等
-- 给每个员工按薪资区间匹配等级表
SELECT e.name, e.salary, g.grade
FROM 员工表 e
JOIN 薪水等级表 g
  ON e.salary BETWEEN g.low AND g.high;
```

理解：

- **等值连接**：ON 两边相等（最常见，主外键配对）；
- **非等值连接**：ON 用区间/比较（BETWEEN、>、<）——"一个人的薪资落进哪个档位"就是典型；
- 连接的本质是"配对规则"，规则可以是等值也可以是区间——**别被"连接"二字锁死成"="**。

一个表可以和多个表连接，也可以和非等值条件混用（如：员工 → 部门等值 + 员工 → 等级非等值同处一条 SQL）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只记得 = | 配"等级/区间对应"场景要用 BETWEEN；条件类型取决于业务配对规则 |
| 非等值连接漏 ON | 还是 n-1 规律：每个新表都要有配对条件 |

@@point ④ 自连接：一张表和自己连接
@@need 要解决什么
**"员工的领导也是员工""商品的上一级分类也是商品"——同一张表内部的行互相配对**，就得自连接（自己 JOIN 自己，起两个别名）。

@@idea 核心思路

```sql
-- 员工表 emp(id, name, mgr_id)：mgr_id 指向本表的另一个 id
SELECT e.name AS 员工, m.name AS 领导
FROM emp e
LEFT JOIN emp m ON e.mgr_id = m.id;

-- 用法要点：同一张表出现两次，用不同别名区分角色
```

为什么需要它：**一对多关系可能藏在单表内部**（经理-下属、分类-子分类、好友关系）。自连接把它"展开"成明面上的两列。

关键：**同一张表连接自己，必须起两个别名（e 和 m）**，否则表名重复报错、列无从区分。

用 LEFT JOIN 而非 INNER 是为了**保留没有领导（mgr_id 为 NULL）的 CEO**——外连接的用处提前预热（第 ⑥ 点）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 自连接忘了别名 | 表名重复必定报错；一张表两个别名必须 |
| 领导为 NULL 的员工丢了 | 用 LEFT JOIN 保留无配对的左表行 |
| 递归层级深（上级的上级） | 自连接一次只展开一层；多层递归 MySQL 8.0 用递归 CTE（进阶） |

@@point ⑤ 内连接 INNER JOIN
@@need 要解决什么
**只保留两边都配对成功的行**——INNER JOIN 是默认的"严格版"连接。

@@idea 核心思路

```sql
-- 标准写法（推荐）
SELECT c.name, o.amount
FROM 客户表 c
INNER JOIN 订单表 o ON c.id = o.cid;

-- INNER 可省略（默认）
SELECT c.name, o.amount
FROM 客户表 c
JOIN 订单表 o ON c.id = o.cid;
```

特性：

- **只输出 ON 条件成立的行**；哪一侧没配对，那一侧的行就不出现；
- **行数**：以"有效配对"为准——一个客户 5 单 → 5 行；没订单的客户消失；
- 语义类似 Pandas merge how='inner'、集合论"交集"。

记忆：**INNER = 交集 = 两边都得有。** 上面第 ④ 点用 LEFT 而非 INNER，正因为它会丢 CEO；同理"没下过单的客户"也要 LEFT 才留得住（下一知识点）。

写出"每个客户下单次数（含没下单的 0）"，就要 LEFT JOIN + COUNT(cid)。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 想保留左边没配对的客户却没了 | 内连接天然丢弃单边；要保留选 LEFT JOIN |
| 把 JOIN 写成了逗号无 ON | 那是笛卡尔积；条件对齐后才是 INNER |

@@point ⑥ 外连接 LEFT / RIGHT / FULL
@@need 要解决什么
**"左边表的行一个都不能少"**——LEFT JOIN 保留左表全部行，没配对的右侧填 NULL；RIGHT 反之；FULL 两个都留。

@@idea 核心思路

```sql
-- LEFT JOIN：左表全保留
SELECT c.name, o.amount
FROM 客户表 c
LEFT JOIN 订单表 o ON c.id = o.cid;   -- 没下单的客户出现，o.amount 为 NULL

-- RIGHT JOIN：右表全保留（一般用 LEFT 改写，习惯统一）
SELECT c.name, o.amount
FROM 订单表 o
RIGHT JOIN 客户表 c ON c.id = o.cid;

-- FULL OUTER JOIN：两边都保留（MySQL 不支持，用 UNION 模拟，见下）
```

成对记忆：**“左表是老大”是 LEFT 的核心语义**；RIGHT 就是把"老大"换到右边（为保持代码可读性，实战多用 LEFT 改写）。

**MySQL 8.0 不支持 FULL OUTER JOIN**——要"两边都留"用 UNION 拼接两个 LEFT：

```sql
SELECT ... FROM a LEFT JOIN b ON ... 
UNION 
SELECT ... FROM a RIGHT JOIN b ON ...;
```

常用判据：**要"无配对的左表行也出现"（如没买过的客户、没领导的老大）→ 外连接；只说"都有关系"→ 内连接。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| LEFT JOIN 后行数比左表多 | 正常：左表一行可配右表多行（一对多展开） |
| 过滤条件写在 WHERE 里把 NULL 那行筛没了 | WHERE 右表列 = '值' 会把 NULL 过滤成内连接；要筛配对列请写进 ON |
| 想 FULL JOIN 报语法错误 | MySQL 无 FULL；UNION 两个 LEFT 模拟 |

@@point ⑦ SQL99 交叉连接/自然连接（认识）
@@need 要解决什么
**见到 CROSS JOIN / NATURAL JOIN 不慌**——它们分别是"全拼"和"自动找同名列"的语法糖，实战较罕见但要认识。

@@idea 核心思路

```sql
-- CROSS JOIN = 笛卡尔积（显式写法）
SELECT * FROM a CROSS JOIN b;      -- 行数 = a×b

-- NATURAL JOIN：自动按同名同类型列等值连接（不用写 ON）
SELECT * FROM a NATURAL JOIN b;    -- 自动用两表同名列连接
```

三句话认识它们：

- **CROSS JOIN**：就是笛卡尔积的 SQL99 写法（隐式逗号写法的显式版）——几乎不当业务查询用，用在造数据/测试；
- **NATURAL JOIN**：省略 ON，**自动用两边所有同名同类型列**等值连接——方便但"隐式行为"（命名一变查询就变），大团队禁用居多；
- 同族还有 **USING(列名)**：显式指定"用这张公共列连接"——比 NATURAL 安全一点，用途相近。

结论：**认识即可，实战主力是 INNER/LEFT JOIN + ON（下一知识点）。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| NATURAL JOIN 结果列从哪来 | 两表公共列自动合并；列变名结果就变——难维护 |
| CROSS JOIN 忘了 WHERE/ON | 它就是无条件的；要条件请换 JOIN ... ON |

@@point ⑧ 子查询：SELECT 里套查询
@@need 要解决什么
**条件本身是个"要现查才知道的数"**（工资高于平均工资的人）——内层查询的结果喂给外层用，这就是子查询（嵌套查询）。

@@idea 核心思路

```sql
-- 单行子查询：内层返回一个值（一行一列）
SELECT name, salary
FROM emp
WHERE salary > (SELECT AVG(salary) FROM emp);   -- 高于全体员工平均薪

-- WHERE 里也能嵌套子查询（多行时配 IN）
SELECT name FROM emp
WHERE dept_id IN (SELECT id FROM dept WHERE location = '北京');
```

主句子查询出现位置：**SELECT 子句、FROM 子句（派生表）、WHERE 子句（最常见）**。

三种"喂法"按返回值分类：

- **标量子查询**：返回单个值 → 配 `=` `>` 等比较符；
- **行子查询**：返回一行多列（进阶）；
- **表子查询**：返回多行 → 配 `IN / ANY / ALL / EXISTS`。

**执行顺序**：子查询先执行，结果给外层用（MySQL 优化器也会改写，但理解按"先内后外"）。

例子中的两个量词：`> (平均)` 比较单个值；`IN (列表)` 判断是否在集合里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 标量子查询返回多行报错 | 内层查出了多行；确认加了合适的条件（如只取一条） |
| 子查询返回 NULL | 外层运算是 NULL → 结果空；子查询条件考虑 IS NOT NULL |
| 用 = 接多行结果 | 多行集合要用 IN/ANY/ALL，= 只接单值 |

@@point ⑨ 多行子查询：IN / ANY / ALL 与 EXISTS
@@need 要解决什么
**内层返回"一堆数"时怎么比**：IN（属于集合）、ANY（任一）、ALL（全部）、EXISTS（存在即真）——四个操作符一次分清。

@@idea 核心思路

```sql
-- IN：值在集合里
SELECT name FROM emp
WHERE dept_id IN (SELECT id FROM dept WHERE location = '北京');

-- ANY：比集合中"任意一个"大（> ANY = 大于最小值）
SELECT name FROM emp
WHERE salary > ANY (SELECT salary FROM emp WHERE dept_id = 10);

-- ALL：比集合中"全部"都大（> ALL = 大于最大值）
SELECT name FROM emp
WHERE salary > ALL (SELECT salary FROM emp WHERE dept_id = 10);

-- EXISTS：内层有行返回即真（相关子查询常用）
SELECT d.name FROM dept d
WHERE EXISTS (SELECT 1 FROM emp e WHERE e.dept_id = d.id);
```

终极记忆表：

| 操作符 | `> ANY` | `> ALL` | IN |
|---|---|---|---|
| 含义 | 大于最小那个 | 大于最大那个 | 在集合内 |
| 等价 | 比集合里随便一个都行 | 比集合里所有都大 | = 任一 |

再加脚注：

- **EXISTS 配"相关子查询"**（内层引用外层别名的列 d.id）——外层一行一行问"有没有"；
- **EXISTS vs IN**：字段大时 EXISTS 更快（只关心"有/没有"）；IN 语义直白；
- **子查询 vs JOIN**：**能 JOIN 优先 JOIN**（可读性/性能普遍更好）；子查询适合"先把条件算出来"的中间量。

一句话收官：**能 JOIN 就别子查询；必须子查询时，单值用 =、多值用 IN、大集合判断用 EXISTS。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ANY 和 ALL 搞反 | > ANY=大于最小、> ALL=大于最大；用"最小/最大"锚点记 |
| 子查询结果含 NULL 导致 IN 不匹配 | IN 遇 NULL 行为反直觉：考虑先排除 NULL |
| 相关子查询不熟悉别名作用域 | 内层能引用外层列；外层不能引用内层（作用域方向是单向的） |

@@point ⑩ 多表查询综合实战
@@need 要解决什么
**把 JOIN + 分组 + 子查询全串成一条真实业务 SQL**——"SQL 进阶考试"最后一道大题。

@@idea 核心思路

```sql
-- 场景：每个"有订单的部门"的订单总金额，按金额倒序，取前 3
SELECT d.name, SUM(o.amount) AS total
FROM dept d
JOIN emp e ON e.dept_id = d.id
JOIN orders o ON o.emp_id = e.id
GROUP BY d.name
HAVING total > 0          -- 有订单（行过滤交给 WHERE，组过滤给 HAVING）
ORDER BY total DESC
LIMIT 3;
```

解题方法论（多表 SQL 五步）：

1. **定结果列**：要什么（部门名+总金额）；
2. **定表与连接**：涉及几张表、主外键配对（n-1 条 ON）；
3. **过滤**：行级 WHERE 先写（有无）；
4. **分组聚合**：GROUP BY 维度 + 聚合函数；
5. **组级过滤/排序/分页**：HAVING / ORDER BY / LIMIT。

对照 Pandas（第 13-14 章）：这条 SQL 相当于 `df.merge(...).groupby('dept').sum().sort_values().head(3)`——**两种语言同一套分析思维**，正是本阶段的设计意图。

**性能提醒**：多表 JOIN 之前先 WHERE 过滤（先收窄再连）效果更好；索引能大幅加速 JOIN 的 ON 列（第 20 章）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| JOIN 太多结果爆炸 | 按 n-1 检查每个 ON；先 WHERE 收窄再做连接 |
| 分组后的非聚合列拿不到 | 想带出某列要么加进 GROUP BY 要么用聚合包装 |
| 不知道从哪张表入手 | 从"主表"开始（业务主体：订单/员工），再逐张外挂信息表 |

@@summary
多表与子查询收官——SQL 高原上的主峰翻过去了：

| 主题 | 关键结论 |
|---|---|
| 连接本质 | 笛卡尔积 + ON 修剪；n 表至少 n-1 个连接条件 |
| 等值/非等值 | = 常见；BETWEEN/比较做区间配对 |
| 自连接 | 同表两别名：员工-领导、分类-子类 |
| INNER JOIN | 交集：两边都有才出现 |
| LEFT/RIGHT/FULL | 保左边/保右边/FULL 用 UNION 模拟 |
| 交叉/自然连接 | CROSS=全拼、NATURAL=自动同名（认识即可） |
| 子查询 | 先内后外；单值 = / 多值 IN / 存在 EXISTS |
| ANY/ALL | >ANY=大于最小、>ALL=大于最大 |
| 五步法 | 定列→连表→WHERE→GROUP→HAVING/ORDER/LIMIT |

一句话记住本章：**连接是"先笛卡尔积再用 ON 修剪"（n-1 个条件防爆表），INNER 交集、LEFT 保左、自连接起两个别名；子查询先内后外，单值用 =、集合用 IN、存在性用 EXISTS，>ANY 大于最小、>ALL 大于最大——能 JOIN 优先 JOIN，与 Pandas merge 同一个分析脑回路。**

@@quiz
1. 为什么说连接的本质是"笛卡尔积 + 修剪"？3 张表连接至少需要几个连接条件？
2. 等值连接和非等值连接的区别是什么？薪水按区间匹配等级属于哪种？
3. 自连接为什么必须给同一张表起两个别名？"领导也为员工"的查询用 LEFT JOIN 而不是 INNER 的原因是什么？
4. INNER JOIN 和 LEFT JOIN 的行数差异可能出现在哪些场景？
5. MySQL 不支持 FULL OUTER JOIN 时，用什么语法模拟？
6. CROSS JOIN 和 NATURAL JOIN 分别是什么？为什么实战不常用 NATURAL？
7. 标量子查询和表子查询分别应该用哪些比较操作符来承接结果？
@@links
讲义|MySQL 讲义（158 页）|#
文档|JOIN 语法|https://dev.mysql.com/doc/refman/8.0/en/join.html
文档|子查询|https://dev.mysql.com/doc/refman/8.0/en/subqueries.html