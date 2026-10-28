@@h1 第二十章　MySQL 索引、事务与用户管理
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★★★

@@why 这一章在解决什么问题
**表越来越大、查询越来越慢怎么办？** → 索引。**同学同时改一行会不会互踩？** → 事务与隔离级别。**数据库交给别人用怕被乱删？** → 用户与权限。这三件事是 MySQL 从"会写 SQL"到"能管库"的分水岭，也是数据库面试的三大金刚。

学完你能回答：索引为什么不快查用、为什么不能对每列都建索引、事务的 ACID 是什么、脏读/不可重复读/幻读怎么防、隔离级别怎么选、账号怎么建、授权怎么给。

@@prep 开始之前
上一章的多表查询会写就能开始，这章不用装新东西；改隔离级别和授权要用 root 账号。

@@goal 学到这儿就够了
能判断哪些列该建索引、说清四种隔离级别各挡哪种并发问题，并能用 GRANT/REVOKE 授权，这章就算过了。

@@map 这一章在整个知识库里的位置
**上一章**：多表查询与子查询——查询能力巅峰
**本章** ← 你在这里：MySQL 收官三件套——性能（索引）、并发正确性（事务）、安全（权限）
**再往后**：阶段 17 收官 → 进入阶段 18
**阶段终点**：从"会查"到"会管"，数据库能力闭环

@@note info 学习提示
本章概念浓度高，建议采取"先抓结论、细节查文档"的学法：索引记住"为什么快、什么时候建、别乱建"三件事；事务记住 ACID + 四级别一图流；用户权限记住三句语法模板。前两点靠理解（本质都是"取舍"），第三点靠动手。

@@point ① 索引的本质与代价
@@need 要解决什么
**"百万行查一个 id 为什么这么快？"**——索引是书的目录，用空间换时间。

@@idea 核心思路
- **索引（Index）本质**：为某列（或多列）建的**排好序的结构（B+ 树）**，查询时像查目录一样二分/树查找，**时间复杂度从全表扫 O(n) 降到 O(log n)**；
- **代价是双面的**：
  - 好处：**SELECT 大幅加速**（尤其 WHERE/ORDER BY/JOIN 的列）；
  - 代价：① **占用磁盘空间**；② **写入变慢**（每次 INSERT/UPDATE/DELETE 都要同步维护索引树）；
- 类比：书的目录（索引）查得快，但每次改页都要更新目录。

**一图流结论：读多写少 → 多建索引；写多读少 → 少建索引。** 读和写永远在拔河。

索引对"死数据"毫无帮助还可恶：SQL 里该建索引的常见场景——WHERE 过滤列、JOIN 的 ON 列、ORDER BY 列、唯一性列（唯一索引）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 索引没走（EXPLAIN 看 type=ALL） | 函数包裹列、前导通配符 %、类型不一致都会让索引失效（第 ⑤ 点） |
| 建一堆索引还是慢 | 索引是双向剑：写入反而更慢、占用空间；评估是否真命中查询模式 |
| 不知道效率如何 | EXPLAIN 看执行计划（本章必会工具） |

@@point ② 索引什么时候建、什么时候别建
@@need 要解决什么
**决定"要不要建索引"的判断清单**——建之前先过五关。

@@idea 核心思路
**建议建索引的时机**：
- 该列被**频繁 WHERE 过滤**（如 user_id、status）；
- 该列是 **JOIN 的连接列**（外键列自动有索引，join 快）；
- **ORDER BY / GROUP BY** 的列；
- **唯一性要求**的列（唯一索引兼顾约束+加速）；
- 表**数据量大且读多**（几万行以下全表扫也不慢，不必建）。

**不建议建索引**：
- 列**选择性低**（如性别只有男/女，区分度差，索引收益小）；
- 表**写多读少**（索引维护成本 > 收益）；
- 表很小（<几千行,全扫更快）；
- 大文本/长字符串列（除非用前缀索引 `KEY (col(10))`）。

给一张表定的主键就是**聚簇索引**（表数据按它物理排列），所以主键设计直接影响全表性能——**主键越短、越稳定越好**。

一句话：**"查得频、区分高、写得不频繁" → 建；否则别建。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 对性别建索引没提速 | 区分度低；优化器直接全表扫，索引形同虚设 |
| 长文本整列建索引 | 浪费空间；用前缀索引 KEY(col(10)) |
| 主键用随机 UUID | 聚簇索引乱序插入 → 页分裂；用自增 INT 或有序 ID 更好 |

@@point ③ 索引类型与创建语法
@@need 要解决什么
**索引有哪些形态 + 在建表/改表时怎么加** —— 普通/唯一/主键/组合/前缀/全文，一套语法走位。

@@idea 核心思路

```sql
-- 建表时直接定义
CREATE TABLE t (
    id INT PRIMARY KEY AUTO_INCREMENT,      -- 主键索引
    email VARCHAR(50) UNIQUE,               -- 唯一索引
    name VARCHAR(20),
    idx_name (name)                         -- 普通索引
);

-- 单独追加
ALTER TABLE t ADD INDEX idx_name (name);
ALTER TABLE t ADD UNIQUE INDEX uk_email (email);
CREATE INDEX idx_name ON t (name);          -- 等价写法

-- 组合索引（多列，走最左前缀，见第 ④ 点）
ALTER TABLE t ADD INDEX idx_a_b (a, b);

-- 查看 / 删除
SHOW INDEX FROM t;
DROP INDEX idx_name ON t;
```

类型表：

| 类型 | 关键字 | 特性 |
|---|---|---|
| 普通索引 | INDEX | 加速查找，可重复 |
| 唯一索引 | UNIQUE INDEX | 加速 + 值唯一 |
| 主键索引 | PRIMARY KEY | 唯一 + 非空 + 聚簇 |
| 组合索引 | INDEX(a,b) | 多列联合查找 |
| 全文索引 | FULLTEXT | 文本搜索（MyISAM/8.0 InnoDB） |

命名习惯：`idx_列名`（普通）、`uk_列名`（唯一）——一眼看懂用途。

**外键列注意**：声明 FOREIGN KEY 会自动创建索引（第 16 章提过），不用重复建。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 建重复索引（单独 a + 组合(a,b)） | 浪费空间；能用组合覆盖就别单建（最左前缀原理） |
| FULLTEXT 分词不满意 | 中文分词需配合 ngrm 插件（进阶）；普通场景先用 LIKE 或第三方搜索 |
| 索引名重复 | 同一表索引名唯一；命名带前缀区分类型 |

@@point ④ 最左前缀与组合索引
@@need 要解决什么
**组合索引 (a,b,c) 为什么查 b 不走索引、查 a 走？** ——理解"最左前缀"就不会建错、问错。

@@idea 核心思路
**最左前缀原则**：组合索引 (a, b, c) 相当于同时建了 (a)、(a,b)、(a,b,c) 三个"隐形前缀索引"；查询条件**必须从最左列开始连续命中**才走索引。

```sql
-- 索引 idx_a_b_c ON t (a, b, c)
WHERE a = 1               -- ✅ 走索引（前缀 a）
WHERE a = 1 AND b = 2     -- ✅ 走索引（前缀 a,b）
WHERE a = 1 AND c = 3     -- ✅ 走索引（a 命中，c 的索引部分只过滤 a 后的行）
WHERE b = 2               -- ❌ 不走（没从 a 开始）
WHERE b = 2 AND c = 3     -- ❌ 不走（缺 a）
```

要点解释：

- 索引列顺序 = "从常用条件到次常用"排列：**把区分度最高/最常查的列放最左**；
- 组合索引的另一收益：**覆盖索引**——查询的列全在索引内，无需回表（更快）；
- 一个组合索引可以服务多个查询形态，**比建三个单列索引省空间**。

设计练习：经常 `WHERE user_id AND date` 查订单 → 建 (user_id, date) 组合，别拆两个单列。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 组合索引查不出 b 单独走索引 | 最左前缀如此；或把 b 单独再建一个索引（权衡空间） |
| 列顺序写倒没效果 | (a,b) 与 (b,a) 不同：把最常用放最左 |
| 怀疑没走索引 | EXPLAIN 的 key 列看实际用的索引名 |

@@point ⑤ 事务与 ACID
@@need 要解决什么
**"转账一半断电怎么办？并发下单库存超卖怎么办？"** ——事务（Transaction）把一组操作打包成"要么全成功要么全失败"的原子单元。

@@idea 核心思路
**ACID 四大特性**（面试必背）：

| 特性 | 含义 | 形象理解 |
|---|---|---|
| **A 原子性** | 全部执行或全不执行 | 转账扣款+入账同生共死 |
| **C 一致性** | 事务前后数据规则一致 | 余额不能为负 |
| **I 隔离性** | 并发事务互不干扰 | 各改各的，像串行 |
| **D 持久性** | 提交后永久保存 | 断电也丢不了 |

```sql
START TRANSACTION;              -- 开启事务
UPDATE account SET money = money - 100 WHERE id = 1;
UPDATE account SET money = money + 100 WHERE id = 2;
COMMIT;                         -- 都成功 → 提交（持久化）
-- 出错时：ROLLBACK;            -- 都失败 → 回滚（像没发生过）
```

**InnoDB 是 MySQL 默认且唯一支持事务的引擎**（MyISAM 不支持，8.0 起 InnoDB 一支独大）。

记忆：**"要么全有，要么全无"（A）、"账不会错"（C）、"互不串台"（I）、"落地生根"（D）。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 MyISAM 也有事务 | 只有 InnoDB 支持；8.0 默认 InnoDB，别建 MyISAM |
| 忘记 COMMIT | 不提交=数据还只在事务里，别人看不到；养成显式 COMMIT |
| ROLLBACK 后数据还在 | 回滚只对未提交事务生效；已 COMMIT 无法 ROLLBACK |

@@point ⑥ 显式事务与隐式提交
@@need 要解决什么
**"我明明没开事务为什么自动提交了？"** ——MySQL 默认自动提交（隐式）；操纵"谁算一个事务"用显式事务。

@@idea 核心思路

```sql
-- MySQL 默认 autocommit=1：每条语句自动提交
SELECT @@autocommit;           -- 1：开

-- 显式事务：把多条语句包成一个事务
START TRANSACTION;
...
COMMIT;    -- 或 ROLLBACK;

-- 全局关自动提交（会话级，不推荐在连接池用）
SET autocommit = 0;
```

- **隐式提交**：autocommit=1 时每条 DML 语句自成一个事务，**执行完立刻提交**——所以"UPDATE 忘 WHERE"才会立刻全表修改且无法回滚（除非从头包在事务里）；
- **显式事务的优势**：多条语句一起成功/一起失败、中途可见性可控；
- 注意：**DDL（CREATE/ALTER/DROP）不可回滚**（隐式提交触发），事务只包 DML。

本教程练习场景：把"改密码"这类单条语句写进 START TRANSACTION + ROLLBACK，练手安全。

**安全习惯推广**：生产环境危险操作（DELETE 大范围）先 `START TRANSACTION` → SELECT 核对 → DELETE → 核对 → COMMIT。（21 章后你会感谢这个习惯）

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 想回滚 DDL | 不可能：自动提交；结构变更前先备份 |
| 事务开着没关 | 连接一直持有锁；会话结束自动回滚未提交的 |
| autocommit=0 忘提交 | 所有会话内语句都不提交：查完记得 COMMIT，否则连接池复用会"看到旧数据" |

@@point ⑦ 并发问题：脏读、不可重复读、幻读
@@need 要解决什么
**"两个事务同时改一行/插入新行，读到什么才算合理？"** ——先认识三种并发异常，再谈隔离级别。

@@idea 核心思路
用"读写的三种串台"来记：

| 异常 | 场景 | 一句话 |
|---|---|---|
| **脏读（Dirty Read）** | 事务 A 读到 B 未提交的修改，B 回滚 → A 读了"不该存在"的数据 | 读到**没提交**的改动 |
| **不可重复读** | A 事务内两次 SELECT 同一条，因 B 提交修改 → 两次结果不同 | 同一条数据**前后不一致** |
| **幻读（Phantom）** | A 事务内范围查询两次，B 插入了新行 → 结果集多/少了行 | **行数幻变**（插/删导致） |

区分最容易混的两个：

- **不可重复读 = 同一行内容被改**（UPDATE）；
- **幻读 = 集合范围多了/少了行**（INSERT/DELETE）。

这三兄弟的"防御等级"正好对应隔离级别（下一知识点）——级别越高，防得越全，但并发性能越差。**隔离 = 用并发度换正确性**，没有免费午餐。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 脏读和不可重复读分不清 | 脏读=读未提交的；不可重复读=读已提交但期间被改 |
| 幻读以为只有 INSERT | DELETE 也能造成范围结果变化；本质是范围快照问题 |

@@point ⑧ 隔离级别：Read Uncommitted → Serializable
@@need 要解决什么
**四种隔离级别怎么选？** ——一张表定生死：**级别越高越安全、并发越低**；MySQL 默认 **REPEATABLE READ**。

@@idea 核心思路

| 级别 | 防脏读 | 防不可重复读 | 防幻读 | 并发度 |
|---|---|---|---|---|
| **Read Uncommitted** | ❌ | ❌ | ❌ | 最高 |
| **Read Committed**（Oracle 默认） | ✅ | ❌ | ❌ | 高 |
| **Repeatable Read**（MySQL 默认） | ✅ | ✅ | 基本✅* | 中 |
| **Serializable** | ✅ | ✅ | ✅ | 最低（串行） |

\* MySQL InnoDB 在 RR 下用**间隙锁可防止大部分幻读**（严格来说 RR 标准未完全防幻读）。

```sql
-- 查看 / 设置会话隔离级别
SELECT @@transaction_isolation;
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

选择逻辑：

- 业务默认**留在 REPEATABLE READ（MySQL 默认，无需改）**；
- 追求**更高并发、能容忍"同读不同"**（如报表/日志）→ READ COMMITTED；
- 强一致、低并发（如金融对账敏感操作）→ SERIALIZABLE（极少用）。

理解本质：**隔离级别就是"读的权限"分级——不隔则快，隔则稳。**

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 改隔离级别全局生效不了 | 用 SESSION 或 GLOBAL 明确作用域；连接池需在连接初始化时设 |
| 以为 RR 完全免疫幻读 | InnoDB 间隙锁基本挡掉，但语义上标准 RR 仍有理论风险；理解程度够用即可 |
| 调成 Serializable 变慢 | 正常：串行化=性能牺牲；只有明确一致性场景才用 |

@@point ⑨ 用户管理：用户与主机
@@need 要解决什么
**"老板要个账号看报表、开发要个账号、实习生要个只读账号"** ——用户（user）+ 主机（host）二元身份，权限的最小单位。

@@idea 核心思路

```sql
-- 建用户：'用户名'@'主机'，主机限定"从哪台机器登录"
CREATE USER 'report'@'localhost' IDENTIFIED BY '你的密码';
CREATE USER 'dev'@'%' IDENTIFIED BY '你的密码';     -- % 任意主机

-- 改密 / 删用户
ALTER USER 'report'@'localhost' IDENTIFIED BY '新密码';
DROP USER 'report'@'localhost';

-- 查看用户
SELECT user, host FROM mysql.user;
```

重点：

- **用户身份 = user + host 组合**：`'root'@'localhost'` 和 `'root'@'%'` 是**两个不同账号**；
- **host 写法**：`localhost` 本机、`%` 任意、`192.168.1.%` 网段、具体 IP；
- 密码存储为哈希，**任何工具都看不到明文**（`IDENTIFIED BY` 只负责设置）。

安全铁律（写进你的数据库习惯）：

- **业务账号绝不共用 root**：root 只留本机管理；
- **密码用强密码**，教学示例用"你的密码"占位，真实环境别用弱口令；
- 最小权限原则见下一知识点。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 本地能连远端连不上 | host 没允许（localhost vs %）；按客户端来源分配 |
| 忘了密码 | 服务端用 --skip-grant-tables 重置（危险，需停服务+重启，非紧急别用） |
| 'root'@'%' 建了也连不上 | 检查端口/防火墙/账号 host 三件套 |

@@point ⑩ 权限管理：GRANT / REVOKE
@@need 要解决什么
**"只读账号只让 SELECT、开发账号能增删改但不能删库"** ——授权 = 最小权限原则落地。

@@idea 核心思路

```sql
-- 授权：GRANT 权限 ON 库.表 TO 用户
GRANT SELECT ON demo.* TO 'report'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON demo.* TO 'dev'@'%';
GRANT ALL PRIVILEGES ON demo.* TO 'op'@'localhost';  -- 全部权限（库级）
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost';  -- 全库全表（超级管理员不常用）

-- 收回 / 刷新 / 查看
REVOKE DELETE ON demo.* FROM 'dev'@'%';
FLUSH PRIVILEGES;                       -- 权限变更后刷新内存缓存
SHOW GRANTS FOR 'dev'@'%';
```

常用权限清单：`SELECT / INSERT / UPDATE / DELETE / CREATE / DROP / ALTER / INDEX / ALL PRIVILEGES`；库.表写法：`demo.*`（库内所有表）、`demo.student`（单表）、`*.*`（所有库）。

**最小权限原则**：**账号只给"刚好够用"的权限**——只读报表就给 SELECT；开发的给 DML 不给 DROP；管理才给 ALL。**出事时权限小=损失小。**

```
练习习惯：每建一个账号就 SHOW GRANTS 验证它拿到的是你预期的权限。
```

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 授权立即不生效 | 老版本需 FLUSH PRIVILEGES；8.0 GRANT 自动刷新缓存，但养成刷新习惯无害 |
| 想让某人"能连不能查" | 只有 CONNECT 不给 SELECT；授权粒度可以很细 |
| REVOKE 漏了部分表 | ON 范围要一致：demo.* 收回就收回整个库的 DELETE |

@@point ⑪ 导出、导入与备份恢复
@@need 要解决什么
**"换电脑/迁移/防删库"** —— mysqldump 导出与导入，数据科学家的救命绳。

@@idea 核心思路

```bash
# 导出（mysqldump 在 bin 目录）
mysqldump -u root -p demo > demo.sql          # 整个库（结构与数据）
mysqldump -u root -p demo student > student.sql  # 单表
mysqldump -u root -p --no-data demo > schema.sql # 只要结构

# 导入
mysql -u root -p < demo.sql
mysql -u root -p demo < student.sql           # 指定库导入

# 或 SQL 内：source
mysql> source /path/demo.sql;
```

- **导出是"文本 SQL 文件"**（可压缩、可 diff、可版本管理——**把备份当代码管**）；
- 导入前目标库存在与否看情况（`CREATE TABLE` 在文件里，库要自己先建好）；
- 备份策略三句话：**定期、异地（另一台机器/云）、先验证能恢复**——不能恢复的备份等于没有备份。

对照第 13-14 章：Pandas `read_sql/to_sql` 与 mysqldump 互为补充——分析数据用 Pandas 拉，**库的整体迁移用 mysqldump**。

**给新手的第一个备份脚本**：每天一条 mysqldump 追加日期（`demo_$(date +%F).sql`），配个定时任务——第 17 阶段收官之作。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| mysqldump 提示没命令 | bin 目录未进 PATH；用全路径或加环境变量 |
| 导入中文乱码 | 导出导入都加 --default-character-set=utf8mb4 |
| 备份了但恢复测试失败 | 定期做"恢复演习"：新库导入验证行数=源库 |

@@summary
MySQL 六章收官——索引/事务/权限三大金刚全部落地：

| 主题 | 一句话结论 |
|---|---|
| 索引 | 用空间换时间，读多写少建、区分度低别建 |
| 索引类型 | 主键/唯一/普通/组合/全文；命名 idx_/uk_ |
| 最左前缀 | 组合索引从最左列起连续命中才生效 |
| 事务 | ACID：原子/一致/隔离/持久；START + COMMIT/ROLLBACK |
| 并发异常 | 脏读（未提交）、不可重复读（行被改）、幻读（行数变） |
| 隔离级别 | RC 防脏读、RR（MySQL 默认）防更多、Serializable 全防但最慢 |
| 用户 | user@host 二元身份，localhost 本机 / % 任意 |
| 权限 | GRANT/REVOKE 最小权限；SHOW GRANTS 验证 |
| 备份 | mysqldump 定期+异地+可恢复验证 |

一句话记住本章：**索引是加速的"目录"（读多建、写多慎、组合索引最左前缀）；事务保证 ACID（启动后 COMMIT 提交/ROLLBACK 回滚，MySQL 默认 RR 隔离级别防脏读防不可重复读）；账号 user@host + GRANT 最小权限、mysqldump 定时备份并演练恢复——至此，从建库到运维的 MySQL 能力全链路闭环。**

@@quiz
1. 索引为什么能加速查询？它的两个代价是什么？
2. 给"性别"列建索引通常效果不好，为什么？
3. 组合索引 (a, b) 的"最左前缀"是什么意思？WHERE b = 1 会走这个索引吗？
4. 事务的 ACID 分别是什么？请各用一句话解释。
5. START TRANSACTION 后忘记 COMMIT，数据会怎样？显式事务相比自动提交的优势是什么？
6. 脏读、不可重复读、幻读三者的区别是什么？
7. MySQL 默认的隔离级别是什么？它分别防住了三种异常中的哪些？
@@links
参考|MySQL （158 页）|#
文档|索引与查询优化|https://dev.mysql.com/doc/refman/8.0/en/optimization-indexes.html
文档|事务与锁|https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html