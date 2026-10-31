@@h1 第四章　数据模型与 Aerich 迁移
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
上一章我们有了配置好的工程与数据库 URL，但 Tortoise-ORM 还不认识数据库里那 8 张表。本章解决两件事：**一是把其中 7 张表翻译成 Python 模型类**（`t_models` 暂时不建模，它要到后面的「模型管理」才用得上，只由建表 SQL 维护）（定义字段、类型、约束、表名），**二是用 Aerich 完成初始化迁移**，让迁移框架能持续追踪表结构变化。

关键认知：**模型定义必须与建库 SQL 完全一致**——字段名、类型、表名、默认值一处对不上，启动即崩或查询即错。这也是这类示例工程最容易翻车的地方：建库 SQL 与代码里的 models.py 偶有细节出入，必须以 models.py 为准。

@@prep 开始之前
第 3 章的 uv 工程和 config.py 能跑就能开始；aerich 已随依赖装好，不用另装。

@@goal 学到这儿就够了
能写出八张表的模型类、说清 `aerich init` / `migrate` / `upgrade` 各干什么、已有库为什么不能直接跑 `init-db`，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：后端工程搭建——uv 工程 + config.py 数据源配置就绪
**本章** ← 你在这里：数据模型与迁移——7 张表的 Python 化身（`t_models` 暂不建模）+ Aerich 迁移启动
下一章：应用启动与测试——main.py、生命周期、CORS、跑起服务
再往后：JWT → 前端 → Coze → 配图 OSS

@@point ① 模型文件布局：app/models 目录
@@need 要解决什么
模型多了之后，全部塞一个文件会越来越乱。项目怎么组织模型文件？

@@idea 核心思路
后端模型放在 `app/models/` 包下，且必须有 `__init__.py` 暴露所有模型类。因为 Tortoise 扫描的是**模块路径**（config 里写的 "app.models"），只有 __init__.py 导出类，`from app.models import User` 才能工作，Aerich 才能发现它们。

models 目录常见组织：
```
app/models/
├── __init__.py      # 统一 re-export：User, Section, Title, ...
├── user.py          # t_users
├── section.py       # t_sections
├── title.py         # t_titles
├── image.py         # t_title_images
├── style.py         # t_style
├── model.py         # t_models
├── publish.py       # t_publish_records / t_publish_images
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 模型建了但查询报"表不存在/模型不存在" | __init__.py 没有导出该类，或 Tortoise 扫描的模块路径不含该文件 |
| 迁移时漏掉某一张表 | models 模块里没 import 就定义，Aerich 只扫描 reachable 的类 |

@@point ② 模型基类写法：字段类型对照
@@need 要解决什么
SQL 类型要正确翻译成 Tortoise 字段类型，这是模型层的核心语法。

@@idea 核心思路
先看一个样例模型的完整写法：

```python
from tortoise import fields, models

class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=255)
    name = fields.CharField(max_length=50)
    department = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "t_users"
        table_description = "用户表"
```

SQL ↔ Tortoise 类型对照表（本项目用到的）：

| SQL 类型 | Tortoise 字段 | 说明 |
|---|---|---|
| INT 主键 | fields.IntField(pk=True) | 自增主键 |
| BIGINT | fields.BigIntField(pk=True) | 大 ID（如图片表） |
| VARCHAR(n) | fields.CharField(max_length=n) | 必须显式给 max_length |
| TEXT | fields.TextField() | 长文本 |
| SMALLINT | fields.SmallIntField(default=0) | 枚举码值 |
| DATETIME | fields.DatetimeField(auto_now_add=True) | 创建时间自动填充 |
| 更新时间 | fields.DatetimeField(auto_now=True) | 每次保存自动更新 |

注意 **Meta.table**：默认表名是模型名（如 user），本项目里全部显式指定 `table="t_xxx"` 与建库 SQL 对齐。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| CharField 忘写 max_length，启动直接报错 | Tortoise 的 CharField 强校验 max_length，不给就抛异常 |
| 表名写成默认模型名去查库 | 模型 Meta.table 没指定，默认表名与 SQL 库表不一致，查库报表不存在 |

@@point ③ t_users 模型与密码字段设计
@@need 要解决什么
用户表模型要承担登录认证，username 唯一性、密码可升级性都在模型层约束。

@@idea 核心思路
```python
class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(50, unique=True)   # 唯一索引在模型层保证
    password = fields.CharField(255)
    name = fields.CharField(50)
    department = fields.CharField(50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "t_users"
```

要点：unique=True 让数据库层拒绝重复用户名；password 255 长度与上章设计呼应。`null=True` 的字段（比如 `department`）在查询里可以用 `department__isnull=True` 过滤空值。

@@point ④ 选题类模型：Section 与 Title 外键关系
@@need 要解决什么
板块与标题是 1:n 关系，要在模型上用外键表达，并支持按板块查标题、按标题拿正文。

@@idea 核心思路
```python
class Section(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    source_name = fields.CharField(255, null=True)
    name = fields.CharField(100)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    class Meta:
        table = "t_sections"

class Title(models.Model):
    id = fields.IntField(pk=True)
    section_id = fields.IntField()
    title = fields.CharField(255)
    sort_order = fields.IntField(default=1)
    content = fields.TextField(null=True)
    status = fields.SmallIntField(default=0)      # 0 未生成 / 1 已生成 / 2 已发布 / 3 已废弃
    view_count = fields.IntField(default=0)
    like_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    class Meta:
        table = "t_titles"
```

设计取舍（源码实录）：**Section/Title 之间的"外键"用普通 IntField 保存 id，而不是 Tortoise 的 fields.ForeignKeyField**。为什么？因为生成时是"批量插入再一次性查询"，用普通 id 字段省去 FK 的异步加载与级联复杂度，查询时自己控制 `filter(section_id=...)`。

⚠️ 代价与坑：这种简化写法下，**必须自己在业务代码里保证引用一致性**——删板块不会自动删标题（无级联），查询时若标题的 section_id 指向不存在的板块，关联信息就不完整。代码里采用"先写 Section 拿 id 再逐条写 Title"的流程天然避免孤儿数据，但直接手写库的读者要注意。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 想像 Django 那样 title.section.name 直接访问 | 没有 FK 字段就没有反向访问器，也没有 `select_related`（它依赖 FK 关系）；只能查两次、自己在内存里按 id 拼 |
| 手工删了 section 忘删 titles | 无数据库级联，set null 或同步删除要靠业务代码，漏删即出孤儿数据（代码里用"批量插入事务"规避） |

@@point ⑤ 素材类模型：Style 与 Image
@@need 要解决什么
风格表存提示词片段，图片表存生成结果并归类用途——这两个模型是配图功能的基石。

@@idea 核心思路
```python
class Style(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    fengge = fields.TextField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)
    class Meta:
        table = "t_style"

class TitleImage(models.Model):
    id = fields.BigIntField(pk=True)
    user_id = fields.IntField()
    title_id = fields.IntField()
    image_url = fields.CharField(500)
    image_type = fields.SmallIntField(default=0)  # 0正文图 1封面图 2缩略图
    sort_order = fields.IntField(default=1)
    file_size = fields.BigIntField(null=True)
    width = fields.IntField(null=True)
    height = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    class Meta:
        table = "t_title_images"
```

要点：image_type 默认 0（正文图），业务插入时显式传值；file_size/width/height 可空——本地生成阶段可能拿不到真实尺寸，OSS 版要补录。

@@point ⑥ 发布类模型：Record 与 PublishImage
@@need 要解决什么
一次发布对应一条记录、多条图片；记录要快照平台/状态/表现数据，图片要记录用途与顺序。

@@idea 核心思路
```python
class PublishRecord(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    title_id = fields.IntField()
    platform = fields.SmallIntField(default=1)     # 1小红书 2抖音 3快手 4公众号
    publish_status = fields.SmallIntField(default=0) # 0待发布 1发布中 2成功 3失败 4删除
    publish_time = fields.DatetimeField(null=True)
    content = fields.TextField(null=True)
    view_count = fields.IntField(default=0)
    like_count = fields.IntField(default=0)
    comment_count = fields.IntField(default=0)
    share_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    class Meta:
        table = "t_publish_records"

class PublishImage(models.Model):
    id = fields.IntField(pk=True)
    publish_id = fields.IntField()
    image_id = fields.BigIntField()   # 指向 TitleImage.id（BIGINT），用 IntField 会在 ID 变大后截断
    image_type = fields.SmallIntField(default=1)  # 1正文图 2封面图 3详情图（注意码值！）
    sort_order = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)
    class Meta:
        table = "t_publish_images"
```

再次强调：**PublishImage.image_type 的码值（1/2/3）与 TitleImage.image_type（0/1/2）不同**，这是代码里如实存在的不一致，后端转换必须按表处理。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 发布图片类型张冠李戴 | 两张表 image_type 语义不同，直接复用码值会传错用途 |
| publish_status 从 0 直接改 2 | 业务应走状态机（0→1→2/3），跳变会破坏重试与统计逻辑 |

@@point ⑦ Aerich：初始化与首次迁移
@@need 要解决什么
模型定义好了，怎么让数据库"知道"？Aerich 把模型 diff 同步到数据库并记录版本。

@@idea 核心思路
Aerich 三连（在 operation 工程根目录执行，需先配置好 config.py）：

```
aerich init -t app.config.TORTOISE_ORM     # 初始化，读取配置并生成 migrations 目录
aerich init-db                              # 按当前模型生成全部表并创建 aerich 版本表
aerich migrate --name change_something      # 后续改模型后生成迁移文件（down/upgrade 脚本）
aerich upgrade                              # 应用迁移到数据库
```

逐条理解：
- `init -t app.config.TORTOISE_ORM`：**-t 指向 config.py 里的 TORTOISE_ORM 字典**，Aerich 靠它知道连哪个库、扫哪些模型。
- `init-db`：**只在首次空库时用**——它会去建表。库已经被 SQL 建好时（我们的场景）不要跑它，否则撞已有表报错。要让迁移接着现有结构走，通常得**手动补一条与当前结构一致的初始迁移**；或者干脆把这个库当基线，以后只用 `migrate` / `upgrade`。
- 和第 2 章的分工：**建表交给 SQL 脚本，Aerich 只负责后面的结构变更**——别指望它替你把历史建库重放一遍。
- `migrate`：diff 模型与库，产出 `migrations/models/xxx_描述.py`（里面是 `upgrade()` / `downgrade()` 两个函数，不是 json + sql）。
- `upgrade`：执行未应用的迁移。

本项目实际链路：**SQL 已建库 → Aerich 用于追踪后续模型演进**——所以重点是 `init → migrate → upgrade` 的组合，首次 init-db 对应"代码自建库"场景。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| init-db 报"表已存在" | 库已被 SQL 建过；init-db 只用于全新空库，已有库改走 migrate+upgrade 或清库重来 |
| migrate 生成的迁移与 SQL 建的表对不上 | 模型与 SQL 字段细节不一致（如默认值、长度）；以 models.py 为准重跑 diff，必要时手工修正迁移 |
| aerich 命令找不到 | 忘了在虚拟环境里执行；uv 下用 `uv run aerich ...`，系统 python 里没装 |

@@point ⑧ 迁移文件长什么样（读懂不慌）
@@need 要解决什么
看到 migrations/ 里的文件别慌：每个版本是**一个 `xxx.py`（里面是 `upgrade()` / `downgrade()` 两个函数）+ 同名的 `.json` 模型快照**，**没有 .sql**——真正的 SQL 是 Aerich 按这两个函数在运行时执行出来的。

@@idea 核心思路
一个典型迁移目录：
```
migrations/models/
├── 0_20250401120000_init.py    # 首次 init-db 或 migrate 的升级脚本
├── 1_20250401123000_names.py   # 后续每次改动的迁移
└── ... 
```
迁移脚本核心是 upgrade/downgrade 两个方法：
- upgrade：apply 时执行（建表/加列/改类型）；
- downgrade：回滚时执行（反向操作）。

读迁移文件能回答三类问题：**哪张表哪个字段在哪次变更引入**、**当前库能否升上去**、**回滚是否安全**。排查"库表结构与代码不符"时，第一个看的就是 migrations 最后几个文件。

@@summary 这一章你学到了什么
- 模型放 app/models/ 包，__init__.py 必须导出全部类，Tortoise 按模块路径扫描
- SQL ↔ Tortoise 类型对照：IntField/CharField(max_length)/TextField/SmallIntField/DatetimeField(auto_now_add)
- Meta.table 显式对齐建库 SQL 表名，"user" ≠ "t_users"
- 7 张表的模型逐类写法与字段约束（unique、null、default、auto_now）；`t_models` 说明为何暂不建模
- Section/Title 用普通 IntField 存外键 id 而非 ForeignKeyField：批量插入快但无级联，靠业务保证一致性
- 两套 image_type 码值（title 0/1/2, publish 1/2/3），转换必须按表区分
- Aerich 命令链：init -t config → init-db（空库）/ migrate+upgrade（已有库）
- 迁移文件结构：upgrade/downgrade 成对出现，排查表结构不一致看这里

@@quiz
1. 模型放在 app/models/ 下还必须满足什么才能被 Tortoise 发现？
   A. 文件名必须大写　　B. __init__.py 中导出类　　C. 文件名要与类名一致　　D. 必须写 Meta.table
2. Tortoise 的 CharField 必须提供哪个参数？
   A. default　　B. null　　C. max_length　　D. unique
3. 模型的表名如何与建库 SQL 的 t_users 对齐？
   A. 模型名写 User　　B. Meta.table = "t_users"　　C. 类名小写　　D. 无法对齐
4. 本章 Section/Title 的外键采用什么实现？
   A. ForeignKeyField　　B. 普通 IntField 存 id　　C. 中间表　　D. 不用关联
5. 库已被 SQL 建好时，迁移的正确操作是？
   A. 直接 aerich init-db　　B. aerich init → migrate → upgrade　　C. 什么都不用做　　D. 删库重来
6. TitleImage.image_type=1 与 PublishImage.image_type=1 分别表示？
   A. 都是封面图　　B. 前者封面图，后者正文图　　C. 前者缩略图，后者详情图　　D. 无法确定
7. aerich init 的 -t 参数指向什么？
   A. 模板文件　　B. config 模块中的 TORTOISE_ORM　　C. 模型文件　　D. 数据库地址

@@links
参考|智能运营平台.pdf|#
官方|Tortoise-ORM 模型文档|https://tortoise.github.io/models.html
官方|Aerich 文档（源码仓库）|https://github.com/tortoise/aerich