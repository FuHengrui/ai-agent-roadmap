@@h1 第四章　数据库模型与 ORM 层
@@sub 阶段 11 · LegalMind 法律咨询系统　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章骨架跑起来了，Postgres 里却一张表都没有。没有表，用户注册没地方存、案例没地方放、聊天记录没地方写。本章用 **Tortoise ORM**（Python 原生 async ORM）把第一章蓝图里的四张核心表落成代码：`User`（用户）、`Case`（案例）、`ChatSession/ChatMessage`（会话与消息）、`GeneratedDocument`（文书）。
重点是搞懂三件事：**UUID 主键怎么选**、**Postgres 数组（法条列表）在 ORM 里怎么表达**、**外键关系怎么挂**。学完本章，数据库里会有完整表结构，第 9 章的聊天接口和第 3 章的建表逻辑全部打通。

@@prep 开始之前
第 3 章的骨架能启动就能开始，这章不用装新东西，写的是四个模型类。

@@goal 学到这儿就够了
能写出 User/Case/会话/文书这几张表的模型、启动即自动建表，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章（第三章 FastAPI 骨架）：init_db() 已在 lifespan 里调用 Tortoise.generate_schemas(safe=True)，就等模型类
**本章** 你在这里：定义四个 Model 类 + 事务写法——建表、写库、查库的 ORM 能力
下一章：用户认证——User 表在此章定义，密码哈希和 JWT 全靠它
再往后：第 9 章聊天/会话/文书 API 直接复用这些模型读写
阶段终点：Postgres 里出现 5 张实体表，CRUD 全部可验证

@@point ① Tortoise ORM 的定位与 Model 基类
@@need 要解决什么
直接写 SQL 建表很容易，但插入、查询、外键联查全要手写，还容易 SQL 注入。ORM 把"表"变成"Python 类"，把"行"变成"对象"，简化 90% 的数据库操作。
@@idea 核心思路
LegalMind 的模型统一继承 Tortoise 的 `Model` 基类，字段用类型注解声明：
```python
# app/models/user.py
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.UUIDField(pk=True)                    # UUID 主键
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=100, unique=True)
    hashed_password = fields.CharField(max_length=200)
    nickname = fields.CharField(max_length=50, default="")
    created_at = fields.DatetimeField(auto_now_add=True)
```
三条关键语法：
- `pk=True` 声明主键；`unique=True` 建唯一索引（注册查重靠它）。
- `auto_now_add=True`：插入时自动填当前时间，不需手动赋值。
- 每个 Model 一个文件放在 `app/models/`，**文件名 = import 路径**（`app.models.user`），必须与第 3 章 `DB_MODELS` 列表一致。

@@point ② UUID 主键：为什么不用自增 int
@@need 要解决什么
"id = fields.UUIDField(pk=True)" 看着比自增 int 麻烦，为什么项目坚持用 UUID？这不是炫技，是为了在分布式/多端/多表场景下不撞车。
@@idea 核心思路
自增 int 的隐患：
- 容易被枚举遍历（`GET /cases/1`、`/cases/2` 一路爬下来，等于案例库裸奔）。
- 多实例写库时主键冲突（各自维护递增序列很难）。
- 前端拿到的是数字，一旦迁移或 JSON 序列化精度丢失，就错了。
UUID 主键（本项目用 `uuid4`）生成一串全局唯一的字符串：
```python
class Case(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=200)
    case_number = fields.CharField(max_length=50, unique=True)   # 案号唯一
    ...
```
生成的 id 形如 `3f1c2a1e-9c3d-4e5f-8a7b-6c5d4e3f2a1b`，前端当普通字符串处理即可，不存在精度问题。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 前端拿 UUID 当数字 | UUID 是字符串不是 int；前端一律按字符串传参 |
| uuid 列排序/去重慢 | 大数据量时对 UUID 建索引或改有序 UUID 变体（v7）；本项目量级无感 |
| 主键传 null 报错 | create 时让 ORM 自动生成，不要手动塞随机值；`uuid.uuid4()` 交给模型默认值处理 |

@@point ③ Case 模型：案例库 + 法条数组字段
@@need 要解决什么
RAG 的"语料源"就是 cases 表。它既要存给 LLM 看的 summary/内容，又要存过滤用的 court/case_type/date 等结构化字段——一张表两种用途。
@@idea 核心思路
看完整的 Case 模型：
```python
# app/models/case.py
class Case(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=200)          # 案例标题
    case_number = fields.CharField(max_length=50, unique=True)  # 案号
    court = fields.CharField(max_length=100)          # 审理法院
    judgment_date = fields.DateField()                # 裁判日期
    case_type = fields.CharField(max_length=50)       # 民事/刑事/行政/劳动争议
    summary = fields.TextField()                      # 裁判要旨/案情摘要
    content = fields.TextField(null=True)             # 裁判文书全文（详情页用）
…（以下省略 6 行，完整代码见仓库对应位置）
            "title": self.title,
            "case_number": self.case_number,
            "court": self.court,
            "judgment_date": str(self.judgment_date),
            "case_type": self.case_type,
            "summary": self.summary,
            "laws": self.laws,
        }
```
两个设计点：
- **`laws = fields.JSONField(default=list)`**：Tortoise 的 JSONField 映射到 Postgres 的 JSONB。存入 `["民法典第一千零八十七条", ...]`，取出直接是 Python list——法条不需要建"案例-法条"多对多表。
- **`to_dict()`**：自带的序列化收口。前端不需要的 content（全文可能几万字符）不进列表接口，只有详情接口才放行——这叫"列表轻、详情重"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用普通 TextField 存"法条数组"，检索时没法精确过滤 | 数组/JSON 字段能用 JSON contains 查询，逗号拼接的字符串只能 LIKE 碰运气；结构化的就结构化，别图省事拼字符串 |
| 把 Pydantic 的 BaseModel 当成 ORM 模型建表 | Pydantic 管数据校验、Tortoise Model 管持久化，两者不是一回事；ORM 模型必须继承 `tortoise.models.Model` |

@@point ④ 会话与消息：ChatSession / ChatMessage 外键关系
@@need 要解决什么
聊天是"一次会话包含多条消息"，且会话**属于某个用户**。表之间要用外键把"谁发的、属于哪次会话"挂起来，否则消息就成了一堆无主孤儿。
@@idea 核心思路
```python
# app/models/chat.py
class ChatSession(Model):
    session_id = fields.CharField(max_length=64, pk=True)   # 前端生成的 UUID 字符串
    user = fields.ForeignKeyField("models.User", related_name="sessions")
    created_at = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return f"ChatSession({self.session_id})"

class ChatMessageRecord(Model):
    id = fields.UUIDField(pk=True)
    chat_session = fields.ForeignKeyField("models.ChatSession", related_name="messages")
    role = fields.CharField(max_length=20)       # user / assistant
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
```
- **`ForeignKeyField("models.User")`**：跨模型引用用字符串 `models.User`（避免循环 import），Tortoise 会在 **ChatSession 表**里生成 `user_id` 列（`user` 字段定义在 ChatSession 上，列不会加到 user 表）；User 侧拿到的只是反向访问器 `sessions`。
- **`related_name="sessions"`**：反向查询语法 `await user.sessions.all()`——从用户拿他所有会话，一行代码。
- **session_id 不用 UUID 字段而用 CharField**：因为聊天 API 的 session_id 由前端生成（`str(uuid.uuid4())`），存字符串更省事，还能兼容外部系统传入的 ID。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 定义了外键但没配反向名，访问 `session.messages` 报错 | Tortoise 的反向关系要显式声明或按规则匹配；给 ForeignKey 指定 `related_name`，双向访问才可靠 |
| 删了会话，消息变孤儿记录 | 关系字段默认删除策略要显式设置；明确 `on_delete=CASCADE`（连坐删）还是 SET_NULL（保留但置空），别用默认值赌行为 |

@@point ⑤ GeneratedDocument：文书存档
@@need 要解决什么
用户生成起诉状后，这份文书要有"凭据"——下次登录还能查到自己生成过什么。文书表补上最后一块拼图。
@@idea 核心思路
```python
# app/models/document.py
class GeneratedDocument(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="documents")
    type = fields.CharField(max_length=50)        # 起诉状/答辩状/合同...
    title = fields.CharField(max_length=200, default="")
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
```
设计要点：
- 存 `content` 全文（文书可能几千字），列表页只取 title/type/时间，全文在详情加载。
- `user` 外键保证**每个用户只能看自己的文书**——第 9 章查列表时按 `user=current_user` 过滤，这就是"数据隔离"的雏形。

@@point ⑥ 查询进阶：Q 表达式与双下划线过滤
@@need 要解决什么
案例检索要"按法院过滤、按案件类型过滤、按法条包含过滤"，条件可能组合。Tortoise 的查询要么用 filter 链，要么用 Q 表达式做复杂条件。
@@idea 核心思路
案例检索 API 里的过滤逻辑：
```python
# apps/cases.py 搜索接口（第 9 章展开）
filters = {}
if court:
    filters["court"] = court
if case_type:
    filters["case_type"] = case_type

# 按法条过滤：JSONB 数组 contains
if article:
    filters["laws__contains"] = [article]

# 交替用法：Q 表达式做 OR
from tortoise.expressions import Q
await Case.filter(Q(court__icontains="北京") | Q(case_type="劳动争议"))
```
- `字段__操作符` 双下划线语法：`court__icontains` = 法院名称忽略大小写包含。
- JSONField 的数组 contains：`laws__contains=[article]` 直接判断数组包含某法条——Postgres JSONB 的 `@>` 操作被 Tortoise 封装成 `contains`。
- 检索最终落到 `RetrievalAgent.retrieve(query, top_k, filters)`（第 8 章）。注意**两套过滤语义不同**：ORM 侧是 Postgres 语法（`court__icontains`、`laws__contains`），向量侧只认 metadata 的**等值/`$in`** 过滤；像「法条包含某条」这种只能在拉回结果后于内存里筛。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 `filter(Q(a=1), Q(b=2))` 是"或"，其实是"且" | 逗号分隔的多个 Q 是 AND；要 OR 必须显式 `Q(a=1) \| Q(b=2)`；多个条件混用记得加括号 |

@@point ⑦ 种子脚本与 CRUD 实操
@@need 要解决什么
模型定义好了，如何验证表真的建出来了、数据真的能写进去？把 seed_cases.py 跑一遍，用结果确认整条 ORM 链路是通的。
@@idea 核心思路
`scripts/seed_cases.py` 的核心循环：
```python
import asyncio
from app.models.case import Case

async def main():
    await Tortoise.init(db_url=settings.DATABASE_URL, modules={"models": ["app.models"]})
    await Tortoise.generate_schemas(safe=True)

    for item in SAMPLE_CASES:
        await Case.update_or_create(
            case_number=item["case_number"],        # 以案号为主键检查
            defaults={**item}                       # 其余字段更新
        )
        print(f"新增: {item['title']}")

    # 验证查询
    count = await Case.all().count()
    print(f"✅ 种子数据插入完成，当前共 {count} 条案例")

asyncio.run(main())
```
`update_or_create` 是 ORM 的"幂等写"：案号已存在就更新、不存在就创建——脚本反复跑不会产生脏数据。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 跑脚本报 "Table 'cases' does not exist" | 忘了先 generate_schemas 或 DB_MODELS 没包含 case 模块 |
| laws 字段写入报类型错 | JSONField 只能存 JSON 可序列化的值；确保 laws 是 list，不是字符串 |
| update_or_create 更新了旧数据 | 判断条件字段要唯一（case_number），否则可能匹配错行更新 |
| 时间字段 str 化出错 | judgment_date 是 date 对象，转 str 用 `str()` 或 `.isoformat()` |

@@point ⑧ ORM 性能提醒：为什么列表接口要 .limit() 和 order_by()
@@need 要解决什么
会话列表、消息列表如果不限量，数据一多接口就越来越慢。往往调试时没感觉，用户用两周后开始"卡"，所谓性能问题大多是忘了排序和限量。
@@idea 核心思路
第 9 章聊天 API 的列表写法：
```text
# 最近 50 个会话，新的在前
sessions = await ChatSession.filter(user=user_obj).order_by("-created_at").limit(50)

# 最近 50 条消息
messages = await ChatMessageRecord.filter(chat_session=session).order_by("created_at").limit(limit)
```
三个动作缺一不可：
- **filter**：不是自己的不能查（数据隔离）。
- **order_by**：不排序，同一批数据顺序不稳定，前端展示会跳。
- **limit**：不限制，第 1000 条消息时接口返回巨慢——消息接口的 limit 参数就是为此设计的。
- 对称性：会话倒序取最新，消息正序保持对话顺序。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 列表接口不写 .limit()，全表一把梭 | 数据一多内存和耗时一起爆；列表、搜索接口务必 limit + offset 分页，配合 order_by 保持分页稳定 |
| order_by 传 SQL 片段或用户输入 | ORM 里 order_by 该传字段名而不是拼 SQL 字符串，防注入也防字段不存在直接报错 |

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **四个 ORM 模型** | User/Case/ChatSession/ChatMessage/GeneratedDocument 五张表，业务数据有了家 |
| **UUID + JSONB 的设计语感** | 主键不裸奔、法条列表不进关系表——分布式与 JSON 场景的标准解 |
| **CRUD 与查询套路** | update_or_create 幂等写、双下划线过滤、外键反向查询，第 9 章 API 直接复用 |

@@quiz
1. 为什么主键选 UUID 不用自增 int？至少举两个生产场景的理由。
2. `laws = fields.JSONField(default=list)` 底层是什么？怎么判断数组"包含某个法条"？
3. ForeignKeyField 的 related_name 是干嘛的？`user.sessions.all()` 返回什么？
4. `update_or_create` 的"幂等"体现在哪里？判断更新目标要什么前提？
5. 写会话列表接口时，为什么要 order_by + limit 一起用？
6. 一个用户的文书数据隔离是怎么实现的（字段与查询层面分别说明）？
7. Tortoise 的 `filter(court__icontains="北京")` 里的 `__icontains` 是什么语法？

@@links
参考|LegalMind 法律咨询系统：数据库模型与 ORM|#
官网|Tortoise ORM 官方文档|https://tortoise.github.io/
官网|PostgreSQL JSONB 文档|https://www.postgresql.org/docs/current/datatype-json.html