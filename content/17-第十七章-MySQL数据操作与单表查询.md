@@h1 第十七章　MySQL 数据操作与单表查询
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★★

@@why 这一章在解决什么问题
**表结构建好了，接下来是每天干的最多的活：往里插数据、改数据、删数据、把数据查出来。** 这是 DML（增删改）+ DQL（单表查询）的完整合集——学完这章，你已经能独立完成"一张表的日常运维"。

学完你能回答：INSERT 的两种写法、UPDATE 忘了 WHERE 有多危险、DELETE 和 TRUNCATE 的区别、WHERE 的条件怎么写、模糊查询、排序、分页口诀。

@@prep 开始之前
上一章建好的表在、能连上就能开始，这章不用装新东西，WHERE 写漏会改全表。

@@goal 学到这儿就够了
能写 INSERT、UPDATE、DELETE 并说清 WHERE 的作用，能用查询加排序分页取数，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：库表结构、数据类型与约束——表的"户口"建好了
**本章** ← 你在这里：DML + DQL 单表——对表里的数据增删改查
**下一章**：SQL 函数与分组聚合——对数据做加工和统计
**再往后**：多表查询子查询 → 索引事务用户管理
**阶段终点**：数据写入与单表取数的基础能力

@@note info 学习提示
本章是 SQL 的"重头戏"，节奏建议：每个语法点都**手敲一遍**（建张练习表反复 INSERT/SELECT）。重点盯三件事：**UPDATE/DELETE 的 WHERE**（忘了就全表遭殃）、WHERE 与 NULL 的坑、LIMIT 分页公式。这一章练熟，后面都是在此之上加花样。

@@point ① INSERT：插入数据的两种写法
@@need 要解决什么
**把数据写进表里**——INSERT 有两种写法：指定列 和 全列。指定列更安全，是全职业习惯。

@@idea 核心思路

```sql
-- 写法 1：指定列（推荐，列顺序可打乱，自增/默认列自动填）
INSERT INTO student (name, age, gender) VALUES ('张三', 20, '男');

-- 写法 2：全列（必须按表结构顺序，一列不少）
INSERT INTO student VALUES (1, '李四', 21, '女');

-- 批量插入（一次多条，效率高）
INSERT INTO student (name, age) VALUES
    ('王五', 22),
    ('赵六', 23);

-- 自增主键不写：AUTO_INCREMENT 自动填充
```

重点：

- **写法 1 的优点**：不依赖列顺序、允许自增/默认列缺省；**团队推荐写法**；
- 批量 VALUES 多条，一次提交比多条 INSERT 快得多；
- 插入时类型要与列类型匹配（字符串单引号、数字裸写）。

**和 Python 联动**：pandas 的 `to_sql`、Python 的 pymysql `executemany` 都是"批量插入"思路，本章 SQL 语法是它们的地基。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 写法 2 报列数不匹配 | 写全所有列（含自增/默认列）或用写法 1 |
| 重复主键 Duplicate entry | 主键已存在：换 INSERT IGNORE 或 ON DUPLICATE KEY UPDATE |
| 中文插入乱码 | 连接字符集没设 utf8mb4（第 16 章开头） |

@@point ② 默认值与自动填充
@@need 要解决什么
**建表时设了 DEFAULT/CURRENT_TIMESTAMP，插入时不写它会怎样？** 理解默认值的补位规则，插数据才不慌。

@@idea 核心思路

```sql
CREATE TABLE student (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL,
    gender CHAR(1) DEFAULT '男',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO student (name) VALUES ('张三');
-- id 自动=1，gender='男'（默认），created_at=当前时间（自动）
```

规则：**插入时没有显式提供的列 → 有 DEFAULT 用默认值，自增自动编号，否则 NULL（若允许）。**

注意三个边界：

- **显式写 NULL 会存 NULL**（除非 NOT NULL）；
- **DEFAULT 表达式**：8.0 支持 DEFAULT (表达式)（如当前时间、UUID）；
- 默认值只在新插入时生效，**已存在的行不会因为改表变更而回填**。

一句话：**"不给就补默认，给了就按给的来"**——但显式 NULL 也算"给了"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为默认值会对老行回填 | 不会；只对新插入行生效 |
| 插入 NULL 到 NOT NULL 报错 | 该列禁止 NULL；业务上要给值或去掉 NOT NULL |

@@point ③ UPDATE：修改数据（WHERE 定生死）
@@need 要解决什么
**改数据是 DML 中最危险的**：UPDATE 不写 WHERE = 全表更新。职业习惯：先 SELECT 验证 WHERE，再 UPDATE。

@@idea 核心思路

```sql
-- 改一列
UPDATE student SET age = 21 WHERE name = '张三';

-- 改多列（逗号分隔）
UPDATE student SET age = 22, gender = '女' WHERE id = 2;

-- 不带 WHERE：全表更新（危险！）
-- UPDATE student SET age = 99;   -- 慎用！所有行都变 99

-- 带条件更新：数值范围
UPDATE student SET score = score + 5 WHERE score < 60;
```

三条铁律：

1. **WHERE 是生死线**：漏了 = 全表遭殃（无后悔药，除非有备份/事务）；
2. 更新可引用自身列做运算（`score = score + 5`）；
3. **安全习惯：先 SELECT 看 WHERE 命中多少行，再改成 UPDATE 执行。**

生产环境大表 UPDATE 要分批（LIMIT 片段）+ 低峰期，这是后话，但"先查后改"的习惯从今天养成。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 全表被更新了 | 无 WHERE 或 WHERE 写错（如 = 写成无）；赶紧查备份/二进制日志（后续章节） |
| 更新没生效很多行 | WHERE 条件范围比想象大：先 SELECT COUNT 核实 |
| 更新报错 lock wait timeout | 别的大事务在锁行；等或看锁（第 20 章事务） |

@@point ④ DELETE 与 TRUNCATE
@@need 要解决什么
**删数据两种手段：DELETE 按条件删、TRUNCATE 清空整表**——区别是高频考点。

@@idea 核心思路

```sql
-- DELETE：按条件删行（DML，可回滚）
DELETE FROM student WHERE id = 3;

-- 不写 WHERE = 删空所有行（比喻：掏空了表，但表还在）
DELETE FROM student;

-- TRUNCATE：清空表（DDL，删掉重建，自增也归零，不可回滚）
TRUNCATE TABLE student;
```

核心区别：

| | DELETE | TRUNCATE |
|---|---|---|
| 分类 | DML | DDL |
| 能不能加 WHERE | 能 | 不能（全清） |
| 事务回滚 | 可以 | 不可以 |
| 自增计数 | 保留（继续累加） | 归零 |
| 速度 | 慢（逐行记日志） | 快（整体重建） |

选择：**清整个表且无所谓回滚 → TRUNCATE（快）；按条件删 → DELETE；有事务需求 → DELETE。**

删除高危提醒：**生产库 DELETE 先 SELECT 验证 + 事务包裹 + 备份，这三板斧缺一不可。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DELETE 后自增还是原来的数 | 正常，DELETE 不动自增位；要归零用 TRUNCATE |
| TRUNCATE 想回滚 | 不能；它算 DDL。真要可回滚清表就 DELETE（带事务） |
| 删指定行忘了 WHERE | 又全清；老规矩：SELECT 验证 WHERE |

@@point ⑤ SELECT 基础与运算符
@@need 要解决什么
**SELECT 是 SQL 的"主菜"**——选列、运算列、起别名，先进"单表取数"的门。

@@idea 核心思路

```sql
-- 选所有列 / 指定列
SELECT * FROM student;
SELECT name, age FROM student;

-- 列运算：算术运算符 + - * / % 
SELECT name, age, age + 1 AS 明年年龄 FROM student;

-- 别名 AS（可省略，但建议写）
SELECT name AS 姓名 FROM student;

-- 常数与函数（没表也能算）
SELECT 1 + 1;                     -- 2
SELECT NOW();                     -- 当前时间
```

重点：

- 运算结果列会自动起名（age+1），用 `AS 别名` 让人看懂；
- 运算符优先级：`* /` 先于 `+ -`，`%` 取余；括号改变顺序；
- **NULL 参与任何算术运算结果都是 NULL**（最阴的坑）。

顺序记忆：SELECT 的"列投影"阶段——选哪些列、怎么变形，还没碰到行筛选（WHERE）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| age + NULL 结果 NULL | NULL 传染一切运算；用 IFNULL(age,0) 兜底 |
| 别名里有中文乱码 | 连接字符集 utf8mb4；别名最好用英文或确保编码 |
| 想改表本身某列试试 SELECT 改不了 | SELECT 只读不改；改是 UPDATE 的事 |

@@point ⑥ 去重、空值与比较运算
@@need 要解决什么
**查出来一堆重复行（每个班 50 个"男"）、列里有 NULL**——DISTINCT 去重、IS NULL 判空，比较运算全家。

@@idea 核心思路

```sql
-- 去重：一行一个不重复值
SELECT DISTINCT gender FROM student;

-- 等值 / 比较：= > < >= <= !=（或 <>）
SELECT * FROM student WHERE age > 20;
SELECT * FROM student WHERE gender = '男';
SELECT * FROM student WHERE age <> 18;    -- 不等于

-- NULL 判断：不能用 =，必须 IS NULL / IS NOT NULL
SELECT * FROM student WHERE phone IS NULL;
SELECT * FROM student WHERE phone IS NOT NULL;
```

重复三遍的关键：**NULL 不是值，是"不知道"，所以 `= NULL` 永远不成立**——判空只能 `IS NULL`。

比较运算对 NULL：结果也是 NULL（既不算 TRUE 也不算 FALSE）→ 条件过滤时 NULL 行会被筛掉（除非专门 IS NULL）。

一页记牢：**`= NULL` ❌、`IS NULL` ✅、`<>` 等于 `!=`、比较结果遇 NULL 变 NULL。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| WHERE phone = NULL 查不出 | 无解的老坑：一律 IS NULL |
| DISTINCT 多列时没去成功 | DISTINCT 作用于整行组合（多列一起去重，不是每列单独去重） |
| age > 20 查不到 NULL 的 age | 正常：NULL 比较为 NULL，被过滤 |

@@point ⑦ 模糊查询与特殊运算
@@need 要解决什么
**"名字带'张'的人""手机号以 138 开头"**——LIKE 模糊查询 + BETWEEN/IN 的快速条件。

@@idea 核心思路

```sql
-- LIKE 模糊：
-- %  任意长度（含 0）
-- _  单个字符
SELECT * FROM student WHERE name LIKE '张%';      -- 张开头的名字
SELECT * FROM student WHERE name LIKE '%三%';     -- 中间带"三"
SELECT * FROM student WHERE name LIKE '张_';      -- "张"+1 个字符（2 字名）

-- 范围：
SELECT * FROM t WHERE score BETWEEN 60 AND 90;    -- 含端点 [60,90]
SELECT * FROM t WHERE score NOT BETWEEN 60 AND 90;

-- 枚举匹配：
SELECT * FROM student WHERE age IN (18, 20, 22);  -- 值集合
SELECT * FROM student WHERE age NOT IN (18, 20);
```

口诀：**% 长、_ 短；BETWEEN 含两端；IN 一串判一堆。**

- LIKE 转义：想搜字面 % 用 `LIKE '%\%%'`（\ 转义）；
- BETWEEN 两端**包含**；
- IN 优于多个 OR（可读性 + 性能）。

大数据下 `LIKE '%xx%'` 前导通配符**不走索引**（第 20 章索引再讲），但学习阶段先用对语法。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| LIKE '张' 查不到"张三" | '张' 精确匹配不等于"开头含"；要 '张%' |
| BETWEEN 边界猜错 | 是闭区间：60 和 90 都算命中 |
| IN 里写 NULL | IN (18, NULL) 行为坑多；NULL 单独 IS NULL 判断 |

@@point ⑧ 逻辑运算与优先级
@@need 要解决什么
**多个条件组合：AND 全满足、OR 任一个、NOT 取反**——以及那个著名的"AND 先于 OR"陷阱。

@@idea 核心思路

```sql
-- 与 / 或 / 非
SELECT * FROM student WHERE age > 20 AND gender = '男';
SELECT * FROM student WHERE age > 20 OR gender = '女';
SELECT * FROM student WHERE NOT age > 20;

-- 优先级陷阱：AND 先算，OR 后算！
-- 想表达"20 岁以上男性，或所有女性"：
-- 写法 1：❌ 会被理解成 age>20 AND (gender='男' OR age>25)=错误
-- 写法 2：✅ 括号说了算
SELECT * FROM student WHERE (age > 20 AND gender = '男') OR age > 25;
```

优先级从高到低：**括号 > NOT > AND > OR**。

一句话：**写多条件组合，别信任记忆，直接加括号**——括号既是给数据库看的，更是给下一个读代码的人看的。

另一个思路：复杂判断在面试/评审里常见"AND 和 OR 混写不括括号"的题，一律先扩括号再讨论。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 查询结果比预期多 | AND/OR 优先级没控制好；永远用括号 |
| NOT 只作用于一部分 | NOT (A AND B) 与 (NOT A) AND B 不同；NOT 后接整体用括号 |

@@point ⑨ ORDER BY 排序
@@need 要解决什么
**结果按成绩从高到低、按年龄从小到大**——ORDER BY 排序，ASC/DESC 双向 + 多列排序。

@@idea 核心思路

```sql
-- 单列排序
SELECT * FROM student ORDER BY score DESC;   -- 成绩从高到低
SELECT * FROM student ORDER BY age ASC;      -- 升序（ASC 可省略，默认升序）

-- 多列：先按第一关键字，相同再按第二关键字
SELECT * FROM student ORDER BY gender ASC, score DESC;

-- 排序可用别名 / 计算列 / 序号
SELECT name, score + 10 AS real_score FROM student ORDER BY real_score DESC;
SELECT name, age FROM student ORDER BY 2 DESC;   -- 第 2 列（不推荐，依赖列顺序）
```

细节：

- **默认 ASC**；DESC 手动写；
- 多列排序**从左到右**逐级生效（先 gender 后 score）；
- **NULL 排序**：默认 NULL 最小（ASC 在最前）；MySQL 8.0 用 `ORDER BY col ASC NULLS LAST` 调整。

**中文排序**默认按字符集排序规则（utf8mb4 按 Unicode 码点），要拼音排序需指定 collation（如 `ORDER BY name COLLATE utf8mb4_zh_0900_as_cs`，了解即可）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 多列排序只看到一个键生效 | 第二键只在第一键相等时生效；检查第一键是否基本全不同 |
| 排序的 NULL 位置不对 | 默认 NULL 在前（ASC）；需要时用 NULLS LAST |
| 想按日期排序但字段是字符串 | 先确保列类型是 DATE/DATETIME（第 16 章），否则按文本排 |

@@point ⑩ LIMIT 分页与 TOP
@@need 要解决什么
**数据一万条，只要前 10 条或第 21~30 条（第 3 页）**——LIMIT 的两种形态 + 分页公式。

@@idea 核心思路

```sql
-- LIMIT 数量：只要前 N 条
SELECT * FROM student ORDER BY score DESC LIMIT 10;    -- 成绩前 10

-- LIMIT 偏移, 数量：跳过 M 条取 N 条
SELECT * FROM student LIMIT 10, 10;    -- 第 11~20 条（第 2 页）

-- 分页公式：LIMIT (页号-1)*每页数, 每页数
-- 第 3 页、每页 10 条 → LIMIT 20, 10
```

理解：

- **LIMIT M, N**：跳过 M 条，取 N 条（M 是偏移量 offset）；
- **分页公式：`(页码-1) × 每页条数`** 是偏移；
- **LIMIT 常和 ORDER BY 连用**（"销量前 10"=先排序再截断）；
- 大偏移（LIMIT 1000000, 10）性能差——深分页优化（用游标/WHERE id > 上次最大）是生产话题。

语法别称：SQL Server 用 TOP、Oracle 用 ROWNUM，**MySQL 是 LIMIT**，别混。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| LIMIT 2, 3 以为是"2 条接 3 条" | 是"跳过 2 条取 3 条"（偏移, 数量） |
| 分页数据出现重复/漏行 | 排序键不稳定（如成绩相同）→ ORDER BY 加第二键（id）保证稳定 |

@@point ⑪ 单表查询完整成型：一条 SQL 的完整流程
@@need 要解决什么
**把前面全部串起来：写一条"过滤→排序→分页"的完整查询，并理解执行顺序**——SELECT 真正毕业。

@@idea 核心思路

```sql
-- 完整示例：找出 60 分以上、按分数降序、每页 5 条的第 2 页
SELECT name, score
FROM student
WHERE score >= 60
ORDER BY score DESC
LIMIT 5, 5;
```

**SQL 书写顺序：**
```sql
SELECT 列        -- 3. 确定输出列
FROM 表          -- 1. 确定来源
WHERE 条件       -- 2. 行级过滤
GROUP BY ...     -- 4.（下章）分组
HAVING ...       -- 5.（下章）组级过滤
ORDER BY ...     -- 6. 排序
LIMIT ...        -- 7. 分页
```

**执行顺序（数据库实际跑的）：** `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT`。

这个顺序是理解后面一切查询的总纲：**先圈出要查的表（FROM），一行行过滤（WHERE），再（分组/聚合/HAVING），最后投影列（SELECT）、排序、截断。**

现在你手里的技能包：建表 → 插改删 → 条件查 → 模糊 → 排序分页——**单表 SQL 毕业。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| WHERE 里用别名报错 | 别名在 SELECT 阶段才定义，WHERE 阶段还没有它（ORDER BY 可以用别名） |
| GROUP BY 里用 WHERE 过滤聚合前数据 | 那是误解：行过滤在 WHERE，组过滤在 HAVING（下章重点） |
| 执行顺序记不住 | 背"FROM→WHERE→SELECT→ORDER→LIMIT"五步主链，GROUP/HAVING 插中间 |

@@summary
单表增删改查全部出师：

| 能力 | 语法 | 一句话 |
|---|---|---|
| 插入 | INSERT INTO t (列) VALUES (...), (...); | 指定列更稳，批量更高效 |
| 默认值 | DEFAULT / AUTO_INCREMENT / CURRENT_TIMESTAMP | 不给就补，自增自动 |
| 更新 | UPDATE t SET 列=值 WHERE 条件; | WHERE 不写=全表更新（先查后改） |
| 删除 | DELETE FROM t WHERE 条件; / TRUNCATE TABLE t; | DELETE 可回滚可条件，TRUNCATE 全清快 |
| 查询 | SELECT 列 FROM t WHERE 条件; | 投影+过滤两大件 |
| 去空比较 | DISTINCT / IS NULL / <> / BETWEEN / IN | NULL 用 IS 判，BETWEEN 含两端 |
| 模糊 | LIKE '张%' / '%三%' / '张_' | % 长 _ 短 |
| 逻辑 | AND / OR / NOT + 括号 | 括号防优先级翻车 |
| 排序分页 | ORDER BY 列 DESC / LIMIT 偏移, 数量 | 分页公式 (页-1)*每页 |

一句话记住本章：**增 INSERT、改 UPDATE（WHERE 必带，先查后改）、删 DELETE/TRUNCATE（前者可回滚）、查 SELECT+WHERE+ORDER BY+LIMIT（FROM→WHERE→SELECT→ORDER→LIMIT 的执行顺序）；NULL 只认 IS NULL、模糊认%和_、多条件加括号——单表 SQL 自此毕业。**

@@quiz
1. INSERT 的"指定列"和"全列"两种写法有什么区别？为什么推荐指定列？
2. 自增主键插入时不写会怎样？DEFAULT 默认值只对哪些行生效？
3. 为什么说 UPDATE 不写 WHERE 是最危险的错误？安全习惯是什么？
4. DELETE 和 TRUNCATE 在"能否 WHERE、能否回滚、自增归零"三个维度上各是什么表现？
5. 表达式 age + NULL 的结果是什么？为什么以及怎么兜底？
6. 判断某列为空为什么不能用 = NULL？正确写法是什么？
7. LIKE '张%'、LIKE '%三%'、LIKE '张_' 分别匹配什么样的字符串？
@@links
参考|MySQL （158 页）|#
文档|MySQL INSERT 语法|https://dev.mysql.com/doc/refman/8.0/en/insert.html
文档|MySQL SELECT 语法|https://dev.mysql.com/doc/refman/8.0/en/select.html