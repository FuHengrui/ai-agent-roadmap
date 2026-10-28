@@h1 第十六章　MySQL 库表结构、数据类型与约束
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★★

@@why 这一章在解决什么问题
**接下来三年你会写无数张表。但"表"不是随便划几列就行：每一列是什么类型（整数?日期?）、允不允许空、主键是谁、能不能重复——** 这些"户口政策"决定了数据质量的上限。这一章就是把建库建表从"能跑"升级到"规范"。

学完你能回答：字符集为什么选 utf8mb4、整数类型分哪几档、DECIMAL 和 FLOAT 的差别、主键和外键约束的意义、表建错了怎么改。

@@prep 开始之前
上一章的 MySQL 开着、能连上就能开始，这章不用装新东西，建表练习要自己敲。

@@goal 学到这儿就够了
能按业务选对字段类型，能写出带主键、唯一、非空、自增的表并解释每条约束的作用，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：MySQL 概念安装与 SQL 初识——已能跑通最小闭环
**本章** ← 你在这里：DDL 专场——库、表、类型、约束，把表"建对"
**下一章**：数据操作与单表查询——DML+DQL 对表里的数据动手
**再往后**：函数聚合 → 多表子查询 → 索引事务用户（约束认知将支撑外键/索引理解）

@@note info 学习提示
本章是"背多分+实践"章：数据类型和约束是需要记忆的清单，但真正掌握靠建表练习。建议手边开一个 MySQL 客户端，跟着每个知识点建一张测试表并 SHOW CREATE TABLE 看结果。字符串类型和日期类型的使用场景差异（本章反复出现）是常考点。

@@point ① 字符集：utf8mb4 与排序规则
@@need 要解决什么
**中文乱码、表情包存不进去**——根源90%在字符集。建库时把字符集一次定对：**utf8mb4**。

@@idea 核心思路

```sql
-- 建库时显式指定字符集（推荐）
CREATE DATABASE demo CHARACTER SET utf8mb4;

-- 查看当前字符集
SHOW VARIABLES LIKE 'character%';

-- 建表时也可单独指定列/表字符集（默认继承库）
CREATE TABLE t (
    name VARCHAR(20) CHARACTER SET utf8mb4
);
```

必须知道的真相：

- **utf8mb4 是"真正的 UTF-8"**（4 字节），支持中文、emoji、生僻字；**utf8（utf8mb3）是 3 字节，装不下 emoji**；
- MySQL 8.0 默认字符集就是 utf8mb4；
- 排序规则（collation）与字符集绑定：`utf8mb4_general_ci` 快速、`utf8mb4_unicode_ci` 更精确（大小写不敏感 **ci = case insensitive**）。

一句话原则：**库、表、连接全用 utf8mb4，中文和 emoji 从此无忧。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| emoji 插入报错 Incorrect string value | 字符集不是 utf8mb4；表/列改 utf8mb4 |
| 连接端中文乱码 | 连接语句或工具设置编码 utf8mb4；命令行加 --default-character-set=utf8mb4 |
| 看到 utf8mb3 别慌 | 那是旧别名，与 utf8mb4 不冲突 |

@@point ② 数据库的增删改查
@@need 要解决什么
**数据库层面的 DDL 四件套**：CREATE / SHOW / ALTER / DROP——练习库随便造。

@@idea 核心思路

```sql
-- 创建（可防重复）
CREATE DATABASE IF NOT EXISTS demo CHARACTER SET utf8mb4;

-- 查看有哪些库
SHOW DATABASES;

-- 使用
USE demo;

-- 修改（很少用：改字符集）
ALTER DATABASE demo CHARACTER SET gbk;

-- 删除（练习库随意，生产库三思）
DROP DATABASE demo;
-- 或：DROP DATABASE IF EXISTS demo;
```

提醒：**ALTER DATABASE 改字符集不会改已有表**（每张表有自己设置）；生产环境的"库没了"事故基本都是 DROP 手滑——**养成 IF EXISTS 习惯、对生产库只在确认后执行 DROP。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DROP 手滑删错 | 无后悔药：先 SHOW DATABASES 确认名字再删；生产库用备份 |
| 建库没有指定字符集 | 之后要逐表改；最好建库时就给 utf8mb4 |

@@point ③ 整数类型：INT 家族
@@need 要解决什么
**年龄、成绩、数量用什么类型？** 整数型按"存储空间和范围"分五档，养成就近原则。

@@idea 核心思路
整数类型（有符号范围）：

| 类型 | 字节 | 范围（有符号） | 典型用途 |
|---|---|---|---|
| TINYINT | 1 | -128 ~ 127 | 布尔/小状态（0/1） |
| SMALLINT | 2 | ±3.2 万 | 小型计数 |
| MEDIUMINT | 3 | ±838 万 | 中量计数 |
| INT | 4 | ±21 亿 | **默认主力**（id、数量） |
| BIGINT | 8 | 超大 | 雪花 ID、计数 |

```sql
CREATE TABLE t (
    age TINYINT,          -- 年龄够用
    id INT,               -- 主键常用 INT
    big BIGINT            -- 超大量
);
```

三句话：

- **无符号加 UNSIGNED**（`INT UNSIGNED`，只存非负，范围翻倍）——主键常配；
- 少了放不下会**报错或截断**（严格模式报错），大了浪费空间；
- **选型的直觉：够用且留余量**（id 用 INT 或 BIGINT，状态用 TINYINT）。

主键选择在第 ⑧ 点展开，这里先记住"id 默认 INT"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 插入 200 到 TINYINT 报错 | TINYINT 上限 127（有符号）；换 SMALLINT/INT |
| 负号不见了 | 定义了 UNSIGNED；确认业务是否需要负值 |
| 看到 INT(11) 迷惑 | 8.0 已废弃显示宽度，() 内数字无实际意义 |

@@point ④ 浮点与定点：FLOAT / DOUBLE / DECIMAL
@@need 要解决什么
**钱（99.99）、成绩（88.5）怎么存不出错？** 学完 DECIMAL 你就知道为什么"钱不用 FLOAT"。

@@idea 核心思路

| 类型 | 特点 | 适合 |
|---|---|---|
| FLOAT | 4 字节，精度约 7 位 | 科学计算近似值 |
| DOUBLE | 8 字节，精度约 15 位 | 默认小数（近似） |
| DECIMAL(M,D) | 定点，精确十进制 | **金额、精确结算** |

```sql
CREATE TABLE t (
    price DECIMAL(10, 2),   -- 总共 10 位，小数 2 位：最多 99999999.99
    score FLOAT
);

INSERT INTO t VALUES (99999999.99, 88.5);
```

核心认知：**FLOAT/DOUBLE 是二进制近似（0.1+0.2 ≠ 0.3 的坑），DECIMAL 是精确十进制。** 规则：**金额/对账单/需要精确比较 → DECIMAL；科学计算的近似值 → FLOAT/DOUBLE。**

DECIMAL(M,D)：M 总位数（含小数），D 小数位，D 必须 ≤ M。超出小数位会四舍五入，超出整数位报错。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 0.1+0.2 算出来 0.30000000000000004 | 浮点近似正常；钱类数据换 DECIMAL |
| DECIMAL 小数位不对 | 检查 DECIMAL(M,D) 的 D；按 D 四舍五入 |
| DECIMAL 整数部分溢出报错 | 加大 M（如 DECIMAL(12,2)） |

@@point ⑤ 日期时间类型家族
@@need 要解决什么
**生日（日期）和下单时间（时间戳）不是一回事**——DATE/TIME/DATETIME/TIMESTAMP 四兄弟要分清。

@@idea 核心思路

| 类型 | 格式示例 | 范围 | 用途 |
|---|---|---|---|
| DATE | 2026-10-15 | ~1000-9999 | 生日、日期 |
| TIME | 14:30:00 | -838:59:59 ~ 838:59:59 | 时长、时刻 |
| DATETIME | 2026-10-15 14:30:00 | 1000-01-01 ~ 9999-12-31 | **通用时间戳** |
| TIMESTAMP | 2026-10-15 14:30:00 | 1970-2038（4 字节） | 更新/记录（自动时区） |
| YEAR | 2026 | 1901-2155 | 年份 |

```sql
CREATE TABLE t (
    birthday DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 插入自动记当前时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

四个易混点：

- **DATETIME vs TIMESTAMP**：范围不同（TIMESTAMP 到 2038 年），TIMESTAMP 跟随会话时区、自动取当前时间的能力常用；
- **插入格式**：'2026-10-15'、'2026-10-15 14:30:00' 字符串直接写；
- **DEFAULT CURRENT_TIMESTAMP**：插入时自动填充当前时间（建表好习惯）；
- **ON UPDATE CURRENT_TIMESTAMP**：改行时自动更新时间（审计常用）。

一句话：**要"自动填时间"找 TIMESTAMP/DATETIME + DEFAULT CURRENT_TIMESTAMP；只要日期用 DATE。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| TIMESTAMP 到 2038 报错 | 超范围；换 DATETIME |
| 插入时间变空/报错 | 格式不规范（如 '2026-10' 缺日）；用标准 'YYYY-MM-DD HH:MM:SS' |
| 想自动记时间没生效 | 建表时加了 DEFAULT CURRENT_TIMESTAMP 没有？ |

@@point ⑥ 字符串类型：CHAR / VARCHAR / TEXT
@@need 要解决什么
**姓名、地址、正文——长短不一的字符串怎么选类型。** CHAR 定长 vs VARCHAR 变长是高频考点。

@@idea 核心思路

| 类型 | 长度 | 存法 | 适合 |
|---|---|---|---|
| CHAR(n) | 0-255 字符 | 定长，不够补空格 | 固定长度：手机号、邮编、性别 |
| VARCHAR(n) | 0-65535 字节 | 变长，省空间 | **大部分文本**：姓名、地址 |
| TEXT | 最大 64KB | 长文 | 文章正文、备注 |
| 其他 | —— | BLOB（二进制）、ENUM（枚举） | 文件、固定选项 |

```sql
CREATE TABLE t (
    phone CHAR(11),           -- 手机号定长
    name VARCHAR(20),         -- 姓名变长
    remark TEXT               -- 长文本
);
```

选择逻辑一句话：**长度固定用 CHAR，长度不固定用 VARCHAR，超长文本用 TEXT。**

VARCHAR 说的是"字符数"还是"字节数"？——VARCHAR(n) 的 n 是**字符数**（但总存储受字节上限 65535 约束，中文 1 字符约 3 字节，注意换算）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| CHAR 存 'ab' 取出变 'ab   ' | CHAR 补空格但显示一般会去；对比时用 RTRIM 或直接换 VARCHAR |
| VARCHAR 填不下报错 | 超 n 上限；删减或改 TEXT |
| 65535 上限照搬 | 那是字节不是字符，中文 3 字节/字符，算清楚 |

@@point ⑦ 建表规范与表结构管理
@@need 要解决什么
**把前面类型全用起来，正式建表 + 管理表结构（增删列、改名、看结构）**——DDL 的"施工与装修"。

@@idea 核心思路

```sql
-- 正式建表（五大约束示例，详见下一知识点）
CREATE TABLE student (
    id INT PRIMARY KEY AUTO_INCREMENT,   -- 主键 + 自增
    name  VARCHAR(20) NOT NULL,          -- 非空
    gender CHAR(1) DEFAULT '男',         -- 默认值
    score DECIMAL(5,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name (name)            -- 唯一约束
);
```

```sql
-- 管理表结构
DESC student;                    -- 快速看结构
SHOW CREATE TABLE student;       -- 看完整定义（最准）

ALTER TABLE student ADD COLUMN age INT;               -- 加列
ALTER TABLE student MODIFY COLUMN name VARCHAR(30);   -- 改类型
ALTER TABLE student CHANGE COLUMN name sname VARCHAR(30); -- 改名+改类型
ALTER TABLE student DROP COLUMN age;                  -- 删列

DROP TABLE IF EXISTS student;    -- 删除表
```

写表的小规范：

- **每张表最好有自增主键 id** + 创建时间 created_at 两个"基础设施列"；
- 列定义顺序：主键 → 业务字段 → 时间字段；
- 一个字段一个含义，不要"备注里存两种信息"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| MODIFY 与 CHANGE 混用报错 | CHANGE 要写新名旧名两遍，MODIFY 不用改名；记："CHANGE 改名，MODIFY 只改类型" |
| DESC 看到的默认值不生效 | 插入时显式写了 NULL 会覆盖 DEFAULT 吗？——列允许 NULL 时 insert NULL 会存 NULL |
| ALTER 频繁改大表很慢 | 大表结构变更要做规划和低峰期（生产话题，先有意识） |

@@point ⑧ 约束五虎将：主键、唯一、非空、默认、自增
@@need 要解决什么
**"这一列必须有值""这一列不许重复""这一列自动编号"** ——约束是表的"法律"，让错误数据进不来。

@@idea 核心思路
五大约束一句话记忆：

| 约束 | 关键字 | 作用 |
|---|---|---|
| 主键 | PRIMARY KEY | 唯一 + 非空，一张表只能一个，数据的"身份证" |
| 唯一 | UNIQUE | 值不能重复（可多个 NULL） |
| 非空 | NOT NULL | 必须有值 |
| 默认 | DEFAULT 值 | 不写时自动填充 |
| 自增 | AUTO_INCREMENT | 数字自动 +1（通常配主键） |

```sql
CREATE TABLE student (
    id INT PRIMARY KEY AUTO_INCREMENT,   -- 主键+自增（最常用组合）
    name VARCHAR(20) NOT NULL,           -- 非空
    email VARCHAR(50) UNIQUE,            -- 唯一
    gender CHAR(1) DEFAULT '男'          -- 默认
);

INSERT INTO student (name) VALUES ('张三');   -- id 自动 1，gender 自动 '男'
```

三个易混对比：

- **PRIMARY KEY = UNIQUE + NOT NULL**；
- 一张表**只能一个主键**，但可多个 UNIQUE；
- **AUTO_INCREMENT 必须配索引列**（主键天然是），且只能整数列。

**逻辑主键 vs 业务字段**：id 是逻辑主键（与业务无关），身份证号等业务字段用 UNIQUE 防重——别用身份证号当主键。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 主键重复插入报错 Duplicate entry | 主键/唯一约束生效；查插入逻辑或用 INSERT ... ON DUPLICATE KEY UPDATE |
| AUTO_INCREMENT 不起作用 | 该列不是 INT 或不是索引列/主键；检查定义 |
| NOT NULL 列插 NULL 报错 | 记住这条约束就是防这个的；业务上该字段必须提供 |

@@point ⑨ 外键约束：表间关系
@@need 要解决什么
**订单表里的"客户ID"必须是真实存在的客户**——外键（FOREIGN KEY）把两张表钉在一起，防止脏关联。

@@idea 核心思路

```sql
CREATE TABLE customer (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20)
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cid INT NOT NULL,
    amount DECIMAL(10,2),
    CONSTRAINT fk_orders_customer FOREIGN KEY (cid)    -- 外键名
        REFERENCES customer (id)                       -- 关联主表主键
        -- ON DELETE CASCADE   删除主表行时级联删子表（可选）
);
```

要点：

- 外键列（cid）必须引用**被关联表的主键（或唯一键）**；
- **类型必须一致**（都是 INT）；被引用表的键上有索引（主键天然有）；
- 动作可配：**RESTRICT（默认，删不动）/ CASCADE（级联）/ SET NULL**；
- 建外键=**自动建索引**（查询加速副作用）。

INSERT 一条 cid=99 的订单会**报错**（customer 无 99）→ 外键在守护数据一致性。

**现实观**：互联网大厂生产环境**经常不用物理外键**（用应用层保证 + 逻辑关联），因为级联操作和锁影响性能；但**学习必须会用**，面试常问、理解表关系必备。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 外键建不上提示类型不匹配 | cid 和被引列类型/字符集要一致 |
| 删主表行报错（有子行引用） | 默认 RESTRICT 保护；确认业务意图再决定 CASCADE 或先删子行 |
| 生产讨论"要不要外键" | 学习用物理外键；生产权衡性能后可转逻辑关联（应用层校验） |

@@point ⑩ 检查约束 CHECK 与枚举 ENUM（了解）
@@need 要解决什么
**"成绩必须在 0~100""性别只能是男/女"这类业务规则**——CHECK 与 ENUM 半自动守护。

@@idea 核心思路

```sql
CREATE TABLE student (
    id INT PRIMARY KEY AUTO_INCREMENT,
    score DECIMAL(5,2) CHECK (score >= 0 AND score <= 100),  -- 检查约束
    gender ENUM('男', '女')                                  -- 枚举类型
);

INSERT INTO student (score, gender) VALUES (150, '男');   -- 报错：CHECK 拦截
INSERT INTO student (score, gender) VALUES (90, 'x');     -- 报错：ENUM 不认
```

- **CHECK**：MySQL 8.0.16 起真正强制执行，旧版本只写不查（遇到过就当版本差异）；
- **ENUM('A','B')**：只能取列出的值，适合**固定少量选项**（性别、状态）；
- ENUM 底层按数字存（'男'=1），小心 `ORDER BY` 按**定义顺序**而非字母序。

适用判断：**选项固定且少 → ENUM；规则复杂/范围判定 → CHECK；选项多或会变 → 别用 ENUM（换字典表）。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| ENUM 排序按字母以为是 | ENUM 按定义顺序排（'男'< '女' 取决于定义）；要自定顺序就控制定义先后 |
| 版本不同 CHECK 不拦截 | 8.0.16 前是摆设；升级或用 ENUM/应用层校验 |

@@summary
建表"户口政策"这一章收官：

| 维度 | 记住什么 |
|---|---|
| 字符集 | 一律 utf8mb4，中文 emoji 无忧 |
| 整数 | TINYINT ~ BIGINT，按量级就近选，UNSIGNED 翻倍 |
| 小数 | DECIMAL 精确（钱）；FLOAT/DOUBLE 近似 |
| 日期 | DATE 日期 / DATETIME&TIMESTAMP 时间戳（自动 CURRENT_TIMESTAMP） |
| 字符串 | CHAR 定长、VARCHAR 变长主力、TEXT 长文 |
| 约束 | 主键（唯一+非空）、唯一、非空、默认、自增 |
| 外键 | 引用主表主键、类型一致、RESTRICT/CASCADE |
| 进阶 | CHECK 范围校验、ENUM 固定枚举 |

一句话记住本章：**建库 utf8mb4，建表五大约束（主键唯一非空默认自增）把好门；整数按量级、小数认 DECIMAL、字符串 VARCHAR 为主、时间用 DATETIME + CURRENT_TIMESTAMP 自动记——表建对了，后面查起来才舒服。**

@@quiz
1. 为什么说 utf8mb4 是"真正的 UTF-8"？表情插入失败通常要怎么改？
2. TINYINT 和 BIGINT 的典型用途分别是什么？UNSIGNED 的作用是什么？
3. 为什么金额字段推荐 DECIMAL 而不是 FLOAT？DECIMAL(10,2) 最多能存多大的数？
4. TIMESTAMP 和 DATETIME 的区别有哪些（范围、时区、自动更新）？
5. CHAR(11) 和 VARCHAR(11) 的存储差异是什么？手机号推荐用哪个？
6. PRIMARY KEY、UNIQUE、NOT NULL、DEFAULT、AUTO_INCREMENT 各自的作用是什么？哪个约束"既是唯一又是非空"？
7. 外键建不上通常是什么原因？ON DELETE 的 RESTRICT 和 CASCADE 有什么区别？
@@links
参考|MySQL （158 页）|#
文档|MySQL 数据类型|https://dev.mysql.com/doc/refman/8.0/en/data-types.html
文档|MySQL 约束|https://dev.mysql.com/doc/refman/8.0/en/constraint-primary-key.html