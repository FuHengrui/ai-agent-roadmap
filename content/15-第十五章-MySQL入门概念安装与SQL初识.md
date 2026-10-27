@@h1 第十五章　MySQL 入门：概念、安装与 SQL 初识
@@sub 阶段 17 · 数据科学与智能分析基础　|　数据存储　|　难度 ★★☆

@@why 这一章在解决什么问题
**做数据分析，光有 Pandas 还不够：百万行数据要存"进库"，多表关系要靠数据库管理。** MySQL 是全世界用得最多的开源关系型数据库，也是你那台电脑上"数据科学的仓库"。

学完你能回答：关系型数据库是什么、MySQL 怎么装、怎么连上去、SQL 分成哪几类、SQL 的语法规则是什么——SQL 之旅的"安检与登机"。

@@map 这一章在整个知识库里的位置
**上一章**：Pandas 收官的统计、可视化与性能——数据分析的计算端
**本章** ← 你在这里：MySQL 六章的开篇——概念地基 + 安装 + SQL 总览
**下一章**：库表结构、数据类型与约束——"建表定户口"
**再往后**：增删改查 → 函数聚合 → 多表子查询 → 索引事务用户
**阶段终点**：Pandas 分析完 to_sql 入库，形成完整数据链路

@@note info 学习提示
本章是"认识 + 上手"。安装部分跟着向导点，装完务必做一次命令行连通验证（第 ⑤ 点）；SQL 分类要把 DDL/DML/DQL 三兄弟先记熟，后面几章全围着它们转。本章不写复杂查询，先建库建表。

@@point ① 数据、数据库与 DBMS
@@need 要解决什么
**先厘清三个概念**：数据、数据库、数据库管理系统（DBMS），否则后面全在说黑话。

@@idea 核心思路
- **数据（Data）**：描述事物的符号记录，如"张三 20 岁"；
- **数据库（DataBase，DB）**：长期存储在计算机内、有组织、可共享的数据集合；
- **数据库管理系统（DBMS）**：管理数据库的软件，负责增删改查、安全、并发、备份——MySQL 就是一款 DBMS；
- **数据库系统（DBS）**：DB + DBMS + 应用 + 人员（DBA）+ 硬件，比 DBMS 更大的概念。

一句话记忆：**DB 是"仓库"，DBMS 是"仓库管理员"，DBS 是整个"物流公司"。**

MySQL 和 Excel 的对比（帮老朋友快速理解）：

| 维度 | Excel | MySQL |
|---|---|---|
| 本质 | 电子表格（单文件） | 数据库（服务器管理） |
| 容量 | 几万行就卡 | 亿级可行 |
| 并发 | 单人多看 | 多用户同时读写 |
| 关系处理 | 手动 VLOOKUP | 表间 JOIN |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 说"装数据库"装的是管理器 | 装的是 MySQL（DBMS 软件），库是它管理的逻辑容器 |
| 分不清 DB 和 DBMS | DB 是数据本身，DBMS 是管数据的软件 |

@@point ② 关系型 vs 非关系型数据库
@@need 要解决什么
**面试和选型常见问题**：MySQL/Oracle/SQL Server 与 Redis/MongoDB 的区别在哪。

@@idea 核心思路
按"数据组织方式"分两大类：

- **关系型（SQL）**：数据存**表**，表间通过**主外键**关联，用 SQL 操作。代表：**MySQL、Oracle、SQL Server、PostgreSQL**。特点：**事务强（ACID）、关系清晰、适合业务系统**。
- **非关系型（NoSQL）**：键值对（Redis）、文档（MongoDB）、列族（HBase）、图（Neo4j）。特点：**灵活、高并发、读写快**，适合缓存、日志、海量非结构化数据。

给数据科学选型的直觉：

- 结构化业务数据、要算账要事务 → 关系型 MySQL；
- 缓存/高并发热数据 → Redis；
- 灵活 JSON 文档 → MongoDB。

关系型数据库还有个共同点：**二维表、每行一条记录、每列一个字段、SQL 统一操作**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 NoSQL 会取代 SQL | 两者定位不同：OLTP 业务仍以关系型为主，Redis 等是互补 |
| 版本方说"关系型不支持海量" | 关系型能支持很大，只是要分库分表；NoSQL 更易水平扩展 |

@@point ③ MySQL 简介与版本选择
@@need 要解决什么
**装之前先选对：MySQL 有哪些版本、社区版/企业版/发行版怎么挑。**

@@idea 核心思路
- **MySQL**：Oracle 旗下开源关系型数据库，最流行的开源 DB；跨平台、免费社区版功能完整。
- 常见版本家族：
  - **MySQL Community Server**：官方免费社区版，学习/个人用这个足够；
  - **MySQL Enterprise**：官方收费版，多运维/安全组件（企业才需）；
  - **MariaDB**：MySQL 分支（开源托管社区维护），API 兼容；
  - **Percona Server**：高度兼容的优化分支；
  - 国内云上还有腾讯云/阿里云 RDS（托管版，免装）。

机器上装什么？**下载官方 MySQL Community Server（或 MySQL Installer 向导安装版）**。学习轨迹建议：Windows 用 **MySQL Installer** 图形安装；生产环境一般用命令行 yum/apt 装 + 配置。

版本号怎么看：8.0.x 是当前主流大版本（MySQL 8.0），语法与 5.7 基本兼容但默认排序规则等有差异。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 官网下载了 Enterprise 点下一步变成收费 | 明确选 Community Server 下载页 |
| 装了最新 8.4/9.x 教程命令对不上 | 教程按 8.0 讲，8.x 兼容良好；个别提示符差异正常 |

@@point ④ Windows 安装 MySQL（向导版）
@@need 要解决什么
**在 Windows 上把 MySQL 装好**，并配置 root 密码（本教程教学场景先设简单密码、生产必须强密码）。

@@idea 核心思路
推荐用 **MySQL Installer（MSI 向导）** 最低阻力安装：

1. 官网下载 MySQL Installer → 选 **Developer Default**（含 MySQL Server、MySQL Shell、Workbench）；
2. 到 **Type and Networking** 页：端口保持 **3306**，默认即可；
3. **Authentication Method**：选 "Use Strong Password Encryption"（8.0 默认，兼容性最好）；
4. **Accounts and Roles**：设置 **root 密码**（教程先用 root 连接；生产环境应另建最小权限账号并用强密码）；
5. **Windows Service**：勾选 "Configure MySQL Server as a Windows Service"，开机自启方便学习；
6. Apply 完成后，MySQL 会自动作为服务启动。

检查安装是否成功：任务管理器找 `mysqld` 进程，或（后一点）命令行连一下。

**安全提示（教学 vs 生产）**：本地练习用 `root` + 简单密码是为了跟教程走，**真实环境严禁**——root 只留本机运维，业务用独立账号最小权限。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 端口 3306 被占用 | 检查是否已装旧版/其他服务；改端口要全程一致 |
| 密码忘了 | 用 MySQL 的 --skip-grant-tables 重置（危险操作，见第 20 章）；平时记在密码管理器 |
| 装的是 zip 版没有安装向导 | 压缩包版需手动初始化（mysqld --initialize-insecure）再建服务 |

@@point ⑤ 命令行连接与常用工具
@@need 要解决什么
**装完怎么验证、日常怎么连**——mysql 命令行 + 图形工具两招。

@@idea 核心思路

```bash
# 命令行连接（Windows）
mysql -u root -p
# 输入密码后出现 mysql> 提示符即成功

mysql -h 127.0.0.1 -P 3306 -u root -p   # 显式主机/端口/用户

# 查看数据库列表
mysql> SHOW DATABASES;
```

连上后的第一个动作：`SHOW DATABASES;` 应看到默认的 `information_schema`、`mysql`、`performance_schema`、`sys`。

图形工具三选一：

- **MySQL Workbench**（官方，安装自带）；
- **Navicat**（商业，图形化强）；
- **DBeaver**（开源免费，通用）。

退出连接：命令行 `exit;` 或 `\q`。

**SQL 习惯**：命令用大写关键字 demo 里是惯例（不区分大小写，但要保持风格一致）；每条语句以**分号 `;` 结束**——忘了分号是新手第一坑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 提示 access denied | 密码错或用户/host 不匹配；检查 root@localhost or root@% 授权（第 20 章） |
| 写入命令后没反应 | 大概率漏了分号；补 `;` 回车即可 |
| 'mysql' 不是内部或外部命令 | 未加入 PATH：用安装目录全路径 C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql 或者重装勾选加入 PATH |

@@point ⑥ SQL 五大分类
@@need 要解决什么
**SQL 不是一种语言，是五类命令的合称**——先有分类意识，后面每章都是某几类的细分。

@@idea 核心思路

| 分类 | 全称 | 干什么 | 关键字 |
|---|---|---|---|
| **DDL** | Data Definition Language | 定义结构 | CREATE / ALTER / DROP / TRUNCATE |
| **DML** | Data Manipulation Language | 操作数据 | INSERT / UPDATE / DELETE |
| **DQL** | Data Query Language | 查询数据 | SELECT |
| **DCL** | Data Control Language | 权限控制 | GRANT / REVOKE |
| **TCL** | Transaction Control Language | 事务控制 | COMMIT / ROLLBACK / SAVEPOINT |

记忆顺口溜：**"定义 DDL、增改删 DML、查询 DQL、授权 DCL、事务 TCL"**。

学习主线：16 章 DDL 建库建表 → 17 章 DML+DQL 增删改查 → 18-19 章 DQL 进阶 → 20 章 TCL 事务 + DCL 权限。五兄弟一次认全，后面章章节节对号入座。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| TRUNCATE 算 DDL 还是 DML | DDL（删表重建，不需事务日志），不同于 DELETE（DML）——20 章会再对比 |
| GRANT 忘了哪个分类 | 授权是 DCL；事务提交是 TCL，别混 |

@@point ⑦ SQL 语法规则与注释
@@need 要解决什么
**写 SQL 的"交规"**——大小写、分号、注释、书写习惯，一次记住省无数报错。

@@idea 核心思路

```sql
-- 语法规则
SELECT 列名 FROM 表名 WHERE 条件;   -- 单行注释：--
# 这是单行注释的另一种写法
/* 这是
   多行注释 */

-- 习惯：关键字大写，库表名小写（不强制，但规范）
SELECT * FROM student;

-- 字符串用单引号
SELECT * FROM student WHERE name = '张三';
```

规则清单：

1. **每条语句以分号结尾**；
2. 关键字、表名、列名**大小写不敏感**（Windows/Linux 下库表名大小写敏感性有差异，统一小写最稳）；
3. 注释：`-- 空格` 或 `#` 单行，`/* */` 多行；
4. 字符串常量用**单引号** `'张三'`（MySQL 下双引号也兼容但别依赖）；
5. 一个 SQL 文件习惯以 `;` 分段，可用 `source 文件路径` 批量执行。

**命名习惯**：库名/表名小写 + 下划线（student_score），避免与关键字冲突、避免中文名（能用但很麻烦）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报 syntax error 找不到原因 | 查分号；查字符串是否用了英文引号；查保留字当列名（加反引号 `\`列名\`` 转义） |
| 中文变乱码 | 连接与表字符集要 charset utf8mb4（第 16 章建库统一处理） |

@@point ⑧ 增删改查的"最小闭环"体验
@@need 要解决什么
**装都装完了，先跑通"建库→建表→插数据→查出来"最小闭环**，建立"我确实会用了"的信心。

@@idea 核心思路

```sql
-- 1. 建库
CREATE DATABASE demo;

-- 2. 用库
USE demo;

-- 3. 建表（最简单版）
CREATE TABLE student (
    id INT,
    name VARCHAR(20)
);

-- 4. 插数据
INSERT INTO student VALUES (1, '张三');

-- 5. 查
SELECT * FROM student;

-- 收尾：删库（练习完清理）
DROP DATABASE demo;
```

跑通这个闭环，等于把 DDL（建库建表）+ DML（INSERT）+ DQL（SELECT）+ DDL（DROP）四类 SQL 全部亲历一遍。后面章节就是给每个环节加细节（类型、约束、条件、函数）。

**练习心态**：数据库删了不心疼，练习库随便造，生产库才需要敬畏。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 建同名库报 already exists | 先 DROP 再建；或 CREATE DATABASE IF NOT EXISTS demo |
| USE demo 报错 unknown database | 先确认建库成功（SHOW DATABASES；）再 USE |

@@summary
MySQL 六章的地基打完了：

| 问题 | 答案 |
|---|---|
| DB、DBMS、DBS 是什么 | 数据仓库 / 管理软件 / 整个系统 |
| 关系型 vs NoSQL | 表+外键+SQL+事务 vs 灵活+高并发+场景化 |
| 选哪个版本 | Community Server（官方免费）8.0 即可 |
| 怎么装（Windows） | MySQL Installer 向导：端口 3306、设 root 密码、注册服务 |
| 怎么验证 | mysql -u root -p → SHOW DATABASES; |
| SQL 五分类 | DDL 结构 / DML 数据 / DQL 查询 / DCL 权限 / TCL 事务 |
| 语法老三样 | 分号结尾、单引号字符串、注释 -- # /* */ |

一句话记住本章：**MySQL 是关系型数据库管理系统，装好向导选 3306+设 root 密码，mysql -u root -p 连上后 SHOW DATABASES 验活；SQL 五兄弟 DDL/DML/DQL/DCL/TCL 中，接下来 16 章先由 DDL 登场建库建表。** 安全红线：root 密码教学可简、生产必强。

@@quiz
1. DB、DBMS、DBS 三者的关系是什么？
2. 关系型数据库和非关系型数据库的核心区别是什么？MySQL、Redis、MongoDB 各属于哪类？
3. 学习/个人使用应下载 MySQL 的哪个版本？Windows 上推荐用什么方式安装？
4. 安装向导中通常需要设置哪几项关键配置（端口、账号、服务）？
5. 如何用命令行连接本机 MySQL 并验证成功？
6. SQL 分为哪五类？CREATE、INSERT、SELECT、GRANT、COMMIT 分别属于哪一类？
7. SQL 语句末尾漏了分号会怎样？字符串常量应该用单引号还是双引号？
@@links
参考|MySQL （158 页）|#
工具|MySQL 官网下载|https://dev.mysql.com/downloads/
文档|MySQL 官方文档|https://dev.mysql.com/doc/