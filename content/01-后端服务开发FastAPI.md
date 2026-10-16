@@h1 第一章　后端服务开发 FastAPI
@@sub 阶段 2 · AI 智能体 Web 系统构建实战　|　71 课时　|　难度 ★★☆

@@why 这一章在解决什么问题
上一阶段你训练出了能对话的模型，但**模型住在哪、别人怎么调用它，还没着落**。只靠 Python 命令行自己玩，模型就永远走不出你的电脑。

这一章做两件事：

- **给你的模型装上"正门"**——用 FastAPI 写后端接口，浏览器、网页、手机 App 甚至另一个程序，都能通过 HTTP 来调用你的能力
- **给数据找个能住的地方**——用 MySQL 存用户、订单、配置，别再把数据塞在列表里，一重启就丢

学完这一章，你手里多的是：**一个能随时启动、有自动文档、带参数校验、能存能查数据的 Web 后端**。它是后面所有"智能体系统"的地基——没有它，智能体再聪明也只是一段跑在自己电脑上的脚本。

@@map 这一章在整个知识库里的位置
第八章 模块：把代码拆到文件、做出了完整项目 —— 你有"写程序"的能力了
**本章** ← 你在这里：把程序变成"别人能用的服务"，并配上数据库
第二章 FastAPI 进阶：依赖注入 + DDD 分层 —— 让服务变大之后不乱
阶段终点：一个能对外的、结构清晰的智能体 Web 系统

@@note info 为什么先学数据库再学 FastAPI 也成立
课程把 MySQL（24 课时）排在 FastAPI（47 课时）之前，讲义也配套了 `Mysql.pdf`。因为**后端接口十有八九是操作数据**：注册就是往用户表插一行，登录就是查一行。先懂"数据长什么样"，写接口时才知道自己在干什么。本章先沉淀数据库概念和 SQL 基础，再进入 FastAPI 主线，后半部分 ORM 会直接用上它。

@@point ① FastAPI 是什么：为什么 AI 后端都选它
@@need 要解决什么
你写了个函数，怎么让外面的程序调用它？最原始的办法是开一个 TCP 端口自己解析请求——但每个请求长什么样、怎么解析、怎么回，全要自己写，一个接口都要几百行。FastAPI 就是来解决这个的：**把"函数"变成"网上可调用的接口"，你只管写逻辑。**
@@idea 核心思路
FastAPI 是一个 Python Web 框架：你在函数上贴一个装饰器，它就把这个函数变成一个 HTTP 接口。

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}
```

启动后访问 `http://127.0.0.1:8000/hello`，就能拿到 `{"message": "Hello World"}`。

**它凭什么快（开发效率 + 运行性能）**：

| 特性 | 它解决了什么 |
| **类型提示** | 函数参数写 `id: int`，FastAPI 自动做类型转换和校验，不用手写 if/else 检查 |
| **自动文档** | 启动后自带 `/docs` 交互式接口文档，前端同事直接照着调，不用你写文档 |
| **异步 ASGI** | 高并发请求不阻塞，一个进程能扛住更多请求 |
| **数据校验** | 基于 Pydantic，请求体写错字段自动返回 422，不会让脏数据进你的业务逻辑 |

**它是怎么一步步演进来的**（理解这个就知道它强在哪）：

```cmd
# CGI（最初）：来一个请求，启动一个进程 → 太慢
# WSGI（之后）：进程常驻，但同步处理 → 一个请求卡住，全队等
# ASGI（现在）：进程常驻 + 异步 → FastAPI 就在这层
```

**性能感受**（课程里的压测数据，量级感受即可）：
FastAPI 约 **3000 请求/秒**，Flask 约 1000，Django 约 800。不是说你必须用它，而是异步 + 轻量让它特别适合做 AI 服务的对外层。

**和 AI 的关系**：你现在学的这条路线上，FastAPI 几乎就是"模型服务的标准出口"——把模型包装成一个接口，任何客户端都能来调。
@@trap 把 AI 生成的代码当黑盒
课程专门有一节讲"AI 生成代码的局限性与核心能力"。用 AI 帮你写接口**没问题**，但你得能看懂它生成了什么：路由装饰器、参数类型、返回结构。不然报错时既说不清问题，也没法让 AI 修得对。**AI 是乘法器，不是替代品——你懂核心，它才有用。**

@@point ② 第一个 API：环境搭建与启动
@@need 要解决什么
配置环境是最劝退的一步：装完跑不起来、端口被占、改了代码不生效。这一节把"从零到跑通"的完整路径钉死，后面所有代码都在这条路上。
@@idea 核心思路
**装依赖就两个包**：

```cmd
> pip install fastapi
> pip install "uvicorn[standard]"
```

- `fastapi`：框架本体
- `uvicorn`：ASGI 服务器——真正监听端口、收发 HTTP 的进程，FastAPI 应用靠它跑起来

**写最小应用**（比如存成 `aaa.py`）：

```python
from fastapi import FastAPI

app = FastAPI()                # 创建一个应用实例，名字约定叫 app

@app.get("/")                  # 声明 GET 方式、路径 /
async def root():
    return {"message": "Hello FastAPI"}
```

**启动项目**（两种等价写法）：

```cmd
> uvicorn aaa:app --reload
#  文件:实例   ↑自动重载（改代码自动重启，开发必备）
```

```python
# 也可以在文件里直接写，然后 python aaa.py 运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("aaa:app", host="127.0.0.1", port=8000, reload=True)
```

**启动后你有两个入口**：

| 地址 | 是什么 |
| `http://127.0.0.1:8000/` | 接口本体，返回你写的内容 |
| `http://127.0.0.1:8000/docs` | **自动生成的交互文档**，能直接点按钮测接口 |

**运行模式建议**：开发时开 `--reload`（改代码自动生效），上线时关掉它（省资源、更稳定）。
@@trap 三个经典启动报错
| 现象 | 原因 / 怎么办 |
| `module 'aaa' has no attribute 'app'` | `uvicorn.run` 写的名字和文件名/实例名对不上，检查 `"文件名:实例名"` |
| `Address already in use` | 端口被占，换 `port=8001`，或用 `netstat -ano \| findstr 8000` 找占用进程 |
| 改了代码不生效 | 没开 `--reload`，重启进程 |

@@point ③ 三条最常用的取数通道：路径参数、查询参数、请求体
@@need 要解决什么
前端把数据传给你的方式有好几种：有的写在 URL 里（`/user/5`），有的跟在问号后面（`?page=2`），有的放在请求正文里（登录时要传账号密码）。**接口的第一道工序就是"把参数接住"**，接错了后面的逻辑全是白写。
@@idea 核心思路
**① 路径参数**——数据"长在" URL 路径里，适合标识资源：

```python
@app.get("/args2/{id}")          # 花括号声明占位
async def get_id(id: int):       # 类型写 int，FastAPI 自动转类型
    return {"id": id, "type": type(id).__name__}
```

访问 `/args2/5` 返回 `{"id": 5, "type": "int"}`；访问 `/args2/abc` 直接 422——**写 `id: int` 就自动校验了**。

**② 查询参数**——URL 里 `?key=value` 的部分，适合筛选、分页、排序：

```python
@app.get("/items")
async def list_items(skip: int = 0, limit: int = 10):   # 带默认值 → 可选
    return {"skip": skip, "limit": limit}
```

访问 `/items?skip=20&limit=5` 就能取到分页参数。**有默认值 = 可选参数，没默认值 = 必填**。

**③ 请求体**——放在 HTTP 正文里的 JSON，适合传复杂、敏感、成块的数据（注册、下单）：

```python
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    tags: list[str] = []

@app.post("/items")
async def create_item(item: Item):
    return {"created": item}
```

**Pydantic 模型在这一步干了三件事**：声明数据结构、自动校验字段类型、自动生成文档。这是 FastAPI 数据这一侧的灵魂。

@@trap 函数参数顺序就是路由顺序
同路径下多个路由，**先定义的先匹配**。想用 `/users/me` 表示"当前用户"，又用 `/users/{id}` 查具体用户，**必须把 `me` 写前面**，否则 `users/me` 会被当成 `id=me` 去解析（然后类型校验失败）。
# 正确顺序：
@app.get("/users/me")      # 先：特殊性优先
@app.get("/users/{id}")    # 后：通配兜底

@@point ④ 参数验证：Query / Path / Field
@@need 要解决什么
只靠类型 `int` 挡不住"页码为 -1""分页数 10000"这种**值合法但业务不合法**的数据。你要的是：不合规矩的请求在门口就被拦下，而不是进到业务逻辑里到处 if 判断。
@@idea 核心思路
FastAPI 提供三个验证器，作用在三种参数上：

| 验证器 | 管谁 | 常用参数 |
| `Query` | 查询参数 | `ge`（≥）、`le`（≤）、`gt`、`lt`、`max_length`、`description` |
| `Path` | 路径参数 | 同上，另加 `title` 等 |
| `Field` | Pydantic 模型字段 | 同上，写在模型里 |

**Query 示例（分页参数）**：

```python
from fastapi import Query

@app.get("/items")
async def list_items(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
):
    return {"page": page, "page_size": page_size}
```

`page=0` → 422；`page_size=500` → 422。**非法输入在门口被拦，业务代码里零检查**。

**Path 示例**：

```python
from fastapi import Path

@app.get("/items/{item_id}")
async def get_item(
    item_id: int = Path(..., ge=1),     # ... 表示必填（路径参数本来就必填）
):
    return {"item_id": item_id}
```

**Field 示例（模型内部约束）**：

```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    price: float = Field(..., gt=0)
```

**精髓一句话**：**把规则写在"数据进门前"，而不是"逻辑运行中"。** 校验失败返回统一 422，前端好处理，后端好维护。
@@trap 三个容易踩的点
| 现象 | 原因 / 怎么办 |
| 写了 `Query` 但没传参数报 422 | 确认是否要必填：`Query(...)` 必填，`Query(默认值)` 可选 |
| `Path` 参数忘了写 `...` | 路径参数本来就必须存在，用 `Path(...)` 显式声明 |
| 校验规则不生效 | 检查是写在**函数参数**（Query/Path）还是**模型字段**（Field），写错位置规则不生效 |

@@point ⑤ 表单、异步与文件上传
@@need 要解决什么
不是所有请求都是 JSON。**登录表单**是 `application/x-www-form-urlencoded`，**上传图片/文件**是 `multipart/form-data`，还有**耗时操作**（调模型、查数据库）不能卡死整个服务。这节把这三类"非典型请求"一次讲清。
@@idea 核心思路
**① 表单数据**——网页 <form> 提交时用，`Form` 声明：

```python
from fastapi import Form

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username}
```

**② 文件上传**——`File` + `UploadFile`：

```python
from fastapi import File, UploadFile

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()          # 异步读取，不会阻塞
    return {"filename": file.filename, "size": len(content)}
```

`UploadFile` 是异步接口，适合大文件；它自动处理了 multipart 解析，你不用碰底层。

**③ 异步处理**——`async def` 是 FastAPI 的性能引擎：

```python
import asyncio

@app.get("/slow")
async def slow_task():
    await asyncio.sleep(3)               # 模拟耗时操作
    return {"done": True}
```

**为什么 async 重要**：请求来了不占着线程等，**等待期间去服务别的请求**，高并发不卡。AI 场景尤其关键——调用大模型可能要等几秒，做成异步，整个服务才扛得住并发。
@@trap 异步别乱用
| 现象 | 原因 / 怎么办 |
| 用了 `async def` 却调阻塞库（如同步 requests） | 会**卡死整个事件循环**。异步函数里只调异步 IO；非要用同步库，就写普通 `def`，FastAPI 会丢线程池跑 |
| 上传大文件直接 `read()` | 一次性读进内存。超大文件用 `await file.read(chunk_size)` 分块读 |

@@point ⑥ Request 对象与响应格式全家桶
@@need 要解决什么
一个接口不仅要会"接"，还要会"回"：**回 JSON 还是列表？要不要分页？要不要下文件？要不要重定向？** 统一好响应风格，前端才好接、后端才好维护。这也是企业接口和玩具接口的分水岭。
@@idea 核心思路
**Request 请求对象**——想拿请求头、方法、原始 URL 时直接用：

```python
from fastapi import Request

@app.get("/info")
async def info(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
    }
```

**响应格式怎么选**（`from fastapi.responses import ...`）：

| 响应 | 场景 | 示例 |
| **dict 直接返回** | 单个对象 | `return {"id": 1, "name": "Foo"}` —— 自动转 JSON |
| **response_model=模型** | 企业级：核对响应结构 + 进文档 | `@app.get("/items", response_model=Item)` |
| **列表 / 分页封装** | 查列表、分页 | 见下方分页容器 |
| **FileResponse** | 下载文件 | `return FileResponse(path="a.pdf", filename="file.pdf", media_type="application/pdf")` |
| **StreamingResponse** | 大文件/视频流 | 用生成器分块 yield |
| **RedirectResponse** | 跳转 | `return RedirectResponse("/hello")` |
| **HTMLResponse** | 返回页面片段 | `return "<h1>操作成功</h1>"` |
| **Response + headers** | 自定义 | 手动拼 Content-Disposition 等 |

**企业级推荐写法：响应用模型胶住**——`response_model` 让接口的"回话格式"可校验、进文档：

```python
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    tags: list[str] = []

@app.get("/items/model", response_model=Item)
async def get_item_model():
    return Item(id=2, name="Bar")
```

**分页列表封装**（列表响应 = 数据 + 分页元数据 + 状态）：

```python
from typing import List, Optional
from fastapi import Query

class Pagination(BaseModel):
    total: int; page: int; page_size: int; total_pages: int

class ListResponse(BaseModel):
    status: str = "success"
    data: List[Item]
    pagination: Pagination

@app.get("/items3", response_model=ListResponse)
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    items = []                       # 这里换成真实查询结果
    total = len(items)
    return ListResponse(
        data=items,
        pagination=Pagination(total=total, page=page,
                              page_size=page_size,
                              total_pages=(total + page_size - 1) // page_size),
    )
```

**`response_model_exclude_unset=True`**：过滤掉没设值的可选字段，避免把 `null` 一堆堆给前端。组合响应可以用 `Union[SuccessResponse[Item], ErrorResponse]`，让"成功/失败"都进文档。
@@trap 只回 dict 的两个坑
| 现象 | 原因 / 怎么办 |
| 文档里响应没结构 | 直接 return dict 只有返回示例没有模型校验；企业接口用 `response_model` |
| 返回了不该暴露的字段 | 模型定义了 password 就别放进 response_model；或用 `response_model_exclude` 排除 |

@@point ⑦ ORM 与 Tortoise：让 Python 对象替你写 SQL
@@need 要解决什么
数据要落到数据库，但你不想在代码里到处拼 SQL 字符串——拼错一个引号就炸，数据库从 MySQL 换成 PostgreSQL 又全要改。**ORM 就是"用 Python 对象操作数据库"的翻译官。**
@@idea 核心思路
**ORM（对象关系映射）**：把数据库表映射成 Python 类，一行数据 = 一个对象，一列 = 一个属性。你 `User.create(...)` 它替你翻译成 `INSERT`，`User.filter(...)` 翻译成 `WHERE`。

**优点**：可读性好、少写 SQL 减少出错、换数据库改一行配置、自动管理关系和事务。
**缺点**：复杂查询性能略低于原生 SQL；特别诡异的查询还是得手写 SQL。

**生态怎么选**：

| ORM | 特点 | 适合 |
| **SQLAlchemy** | 约 80% 企业首选，成熟完备 | 传统企业项目 |
| **Tortoise-ORM** | 全异步、语法像 Django ORM | 异步优先的 FastAPI 项目（本课程选择） |
| GINO | 轻量，基于 SQLAlchemy Core | 追求极致性能的小服务 |

**提示：FastAPI 官方不绑定任何 ORM，Tortoise 只是异步生态里趁手的一把。**

**Tortoise 接入全流程**（三步）：

**1. 安装**：

```cmd
> pip install tortoise-orm==0.25.0 aerich==0.9.0 aiomysql==0.2.0 tomlkit==0.13.2
```

**2. 配置连接**（SQLite 开发 / MySQL、PostgreSQL 生产）：

```python
TORTOISE_ORM = {
    "connections": {
        # "default": "sqlite://db.sqlite3",                    # 开发：文件库，零配置
        # "default": "postgres://user:pass@localhost:5432/db",  # 生产：PostgreSQL
        "default": "mysql://user:password@localhost:3306/dbname",  # 生产：MySQL
    },
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],   # 你的模型 + 迁移用模型
            "default_connection": "default",
        }
    },
    "use_tz": False, "timezone": "UTC",
    "db_pool": {"max_size": 10, "min_size": 1, "idle_timeout": 30},  # 高并发建议开
}
```

**3. 注册进 FastAPI**（启动时连库，开发环境自动建表）：

```python
from tortoise.contrib.fastapi import register_tortoise

app = FastAPI(title="FastAPI with Tortoise-ORM")
register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,        # 开发期自动建表；生产别开
    add_exception_handlers=True,
)
```
@@trap 生产环境三件套别忘
| 事项 | 怎么处理 |
| `generate_schemas=True` 留在生产 | 生产用 **Aerich 迁移** 管表，别自动建 |
| 密码明文写配置 | 放 `.env`，别提交进 git |
| 时区不设 | 生产建议 `use_tz=True` + 明确 timezone，避免时间字段错 8 小时 |

@@point ⑧ Aerich 迁移与模型定义：表结构怎么演化
@@need 要解决什么
项目上线后表结构要加字段、改长度，**直接改模型再重启没用，数据库里的表还是旧的**。你需要在"模型"和"数据库表"之间做版本管理——这就是迁移工具的事。
@@idea 核心思路
**Aerich = Tortoise 的"表结构版本管理"**，和 Django 的 migration 一个思路：

```cmd
# 1. 初始化（生成 pyproject.toml 配置 + migrations/ 目录）
> aerich init -t main.TORTOISE_ORM

# 2. 首次建表
> aerich init-db

# 3. 以后模型改了，生成迁移文件 → 应用
> aerich migrate --name "add_email"
> aerich upgrade

# 4. 看历史 / 回滚
> aerich history
> aerich downgrade
```

**模型定义 = 一张表**，继承 `Model`，类属性 = 列：

```python
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(pk=True)                          # 主键自增
    username = fields.CharField(max_length=50, unique=True) # 唯一用户名
    email = fields.CharField(max_length=100, index=True)   # 带索引
    is_active = fields.BooleanField(default=True)
    credit = fields.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = fields.DatetimeField(auto_now_add=True)   # 首次保存自动记时间

    class Meta:
        table = "auth_users"          # 自定义表名（默认是类名小写）
        ordering = ["-created_at"]    # 默认排序：创建时间倒序
```

**常用字段类型速查**：

| 字段 | 数据库类型 | 常用参数 |
| `CharField` | VARCHAR | `max_length` 必填、`unique`、`index` |
| `TextField` | TEXT | `null=True` |
| `IntField` / `BigIntField` | INTEGER/BIGINT | `pk=True`、`default` |
| `DecimalField` | DECIMAL | `max_digits=10, decimal_places=2`（货币必须用它） |
| `BooleanField` | BOOLEAN | `default=True` |
| `DatetimeField` | DATETIME | `auto_now_add`（仅建时）、`auto_now`（每次保存更新） |
| `JSONField` | JSON/JSONB | 存 dict / list |
| `UUIDField` | UUID | 主键时默认生成 UUID4 |
| `BinaryField` | BLOB | 二进制，不支持过滤/更新 |

**Meta 类两个加强项**：`unique_together=[("name", "date")]` 联合唯一；`indexes=[("location",)]` 联合索引。字段还能挂 `validators=[函数]` 做自定义校验。
@@trap 迁移的两个常见翻车
| 现象 | 原因 / 怎么办 |
| 改了模型但库里没变 | 只改模型不跑 `aerich migrate` + `upgrade`，表不会自己变 |
| 迁移文件冲突 | 多人同时改模型。和 git 里解决冲突一样：先 `history` 看基线，再合并迁移 |

@@point ⑨ Tortoise 的 CRUD：增删改查怎么写
@@need 要解决什么
模型定义好了，接下来是**每天写最多的四类操作**：加一行、查几行、改一行、删一行。Tortoise 的 API 是异步的（`await` 前缀），和 FastAPI 的 async 天生一对。
@@idea 核心思路
以 Student 表为例（`id` 自增、`name`、`age` 可空、`email` 唯一）：

```python
from tortoise import fields, models

class Student(models.Model):
    id = fields.IntField(pk=True, description="学生ID")
    name = fields.CharField(max_length=50, description="姓名")
    age = fields.IntField(null=True, description="年龄")
    email = fields.CharField(max_length=100, unique=True, null=True)

    class Meta:
        table = "students"
```

**增（Create）**：

```python
student = await Student.create(name="张三", age=18, email="z@x.com")
# 邮箱重复会抛 IntegrityError —— 记得 try/except 包住
```

**查（Read）**——四个高频姿势：

```python
stu = await Student.get(id=1)                 # 精确查一条（没有会抛 DoesNotExist）
stus = await Student.filter(name__contains="张")   # 模糊查：字段名__contains
stus = await Student.all()                    # 查全部
one = await Student.get_or_none(email="z@x.com")  # 查不到返回 None，不抛异常
```

**改（Update）**——允许只改部分字段：

```python
stu = await Student.get(id=1)
stu.age = 20            # 改属性
await stu.save()        # 保存（只持久化变化的字段）
```

**删（Delete）**：

```python
stu = await Student.get(id=1)
await stu.delete()
```

**异常怎么收**：`DoesNotExist`（没查到）、`IntegrityError`（唯一约束冲突，如邮箱重复）——CRUD 都要包 try/except，尤其"查了不存在"和"插了重复"是高发区。

**函数化封装**：把每个操作包成一个 async 函数（`create_student`、`get_students_by_name`…），加日志，业务层只调函数不碰 ORM 细节——这就是下一章 DDD 仓储的前身。
@@trap 查询参数的双下划线语法
`filter(name__contains="张")` 里的 `__contains` 叫**字段查找符**，还有 `__startswith`、`__gt`、`__in`、`__icontains`（不区分大小写）。写错一个下划线（`name_contains`）就会报字段不存在，**两个下划线是 Tortoise 的约定**。

@@point ⑩ 关联关系：1 对 1、1 对多、多对多
@@need 要解决什么
真实业务不是单表：**一个学生一份档案（1:1），一个学生多门成绩（1:多），一个学生选多门课、一门课多个学生（多:多）**。不会建模关联，就只能堆冗余字段，改一处崩一片。
@@idea 核心思路
用"学生-档案-课程-成绩"的学校系统演示三种关系：

```python
from tortoise import fields, models

class Student(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    profile = fields.OneToOneField(                      # 1对1
        "models.StudentProfile", on_delete=fields.CASCADE,
        related_name="student")
    grades = fields.ReverseRelation["Grade"]            # 反向 1对多

    class Meta:
        table = "students"

class StudentProfile(models.Model):                     # 1对1 的"一"
    id = fields.IntField(pk=True)
    address = fields.CharField(max_length=100, null=True)
    phone = fields.CharField(max_length=20, null=True)
    student = fields.OneToOneField(
        "models.Student", on_delete=fields.CASCADE, related_name="profile")

class Course(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    students = fields.ManyToManyField(                   # 多对多，通过 grades 中间表
        "models.Student", through="grades", related_name="courses")

class Grade(models.Model):                               # 中间表：成绩
    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("models.Student", related_name="grades",
                                     on_delete=fields.CASCADE)
    course = fields.ForeignKeyField("models.Course", related_name="grades",
                                    on_delete=fields.CASCADE)
    score = fields.FloatField()

    class Meta:
        table = "grades"
        unique_together = ("student", "course")          # 一人一课一条成绩
```

**三种关系对应三种字段**：

| 关系 | 字段 | 放哪边 | 例子 |
| **1 对 1** | `OneToOneField` | 任意一边 | 学生 - 档案 |
| **1 对 多** | `ForeignKeyField`（"多"那侧） | 多的一方（成绩） | 学生 - 成绩 |
| **多 对 多** | `ManyToManyField` + `through` 中间表 | 任意一边 | 学生 - 课程（经成绩表） |

**`on_delete=CASCADE`**：删学生时级联删掉关联的档案、成绩，避免孤儿数据。**`related_name`**：提供反向访问的名字（`stu.grades`、`stu.profile`）。

**增删查改关联数据**：

```python
# 增：先建主体，再关联
stu1 = await Student.create(name="张飞")
grade1 = await Grade.create(score=100, student=stu1)   # 创建时直接关联

# 查：prefetch_related 一次性带上关联（避免 N+1 查询）
stu = await Student.get(id=1).prefetch_related("grades")
for g in stu.grades:
    print(g.score)

# 改关联：
grade = await Grade.filter(id=1).first()
grade.student = stu                       # 换人
await grade.save()
# 或：await Grade.filter(id=1).update(student=stu)

# 删：删主体，级联带走
await stu.delete()                        # 关联的档案、成绩一起删
```
@@trap 三个关系建模坑
| 现象 | 原因 / 怎么办 |
| 查询越查越慢（N+1 问题） | 循环里逐个取关联。**用 `prefetch_related("grades")` 一次预取** |
| 多对多重复数据 | 中间表没有唯一约束。加 `unique_together` |
| 删了学生剩一堆孤儿 | 外键 `on_delete` 没设置，或设置成了不删除。明确数据归属 |

@@point ⑪ 中间件与 CORS：给所有请求加公共处理
@@need 要解决什么
你想给**每一个请求**都记日志、算耗时、加安全头，难道每个接口写一遍？还有另一个问题：前端跑在 `localhost:8080`，后端在 `8000`，**浏览器直接拦死跨域请求**——这些都要在"所有请求"这一层统一解决。
@@idea 核心思路
**中间件（Middleware）**：夹在"客户端请求"和"路由处理函数"之间的一层，请求进来先过它、响应出去再过它，**所有接口自动生效**：

```python
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()                       # ① 请求进来，先做点什么
    response = await call_next(request)       # ② 放行给路由（或下一个中间件）
    response.headers["X-Process-Time"] = str(time.time() - start)  # ③ 响应出去前加工
    return response
```

**记日志是中间件最经典的用法**——每个请求的方法、路径、状态码全记下来：

```python
import logging
logger = logging.getLogger("api")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response
```

**CORS（跨源资源共享）**——为什么要有它：浏览器有**同源策略**，默认禁止从一个源（协议+域名+端口）的网页去调另一个源的接口，用来防止恶意网站偷数据。但前后端分离开发时，**跨源请求是常态**，于是服务器用 CORS 机制显式声明"我允许谁调我"：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                 # 或 ["http://localhost:8080"]：明确白名单
    allow_credentials=True,              # 允许带 Cookie
    allow_methods=["*"],                 # GET/POST/PUT/DELETE/OPTIONS
    allow_headers=["*"],
)
```

**开发 vs 生产的区别**：开发随便 `*` 图方便；**生产必须列白名单**，否则任何人都能跨域调你的接口，等于把门敞开了。
@@trap CORS 设置后还报跨域
| 现象 | 原因 / 怎么办 |
| 加了这个中间件还报 CORS | ① 检查 `allow_origins` 是否含前端真实源（带端口）② 请求带自定义 header 时确认 `allow_headers` 含它 ③ **中间件顺序**：CORS 要放在最外层（先注册） |
| `allow_origins=["*"]` + `allow_credentials=True` | 浏览器会拒绝这种组合。要么去掉 `*` 用白名单，要么去掉 credentials |

@@point ⑫ APIRouter 与项目结构：服务变大前的必修课
@@need 要解决什么
代码全塞在 `main.py` 一个文件里，第 500 行时你还能找到函数，第 3000 行时**改一个功能要拖动三屏**。业务开始分块（用户、订单、商品）时，你需要把路由按模块拆开。
@@idea 核心思路
**APIRouter = 一个小型的"路由集"**，把一类接口装进一个文件，再挂回主应用：

```python
# routers/user.py
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["用户"])

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

```python
# main.py —— 挂载
from routers import user as user_router

app = FastAPI()
app.include_router(user_router)          # 所有 /users/* 都进来了
```

**`prefix` 一键加前缀**：`APIRouter(prefix="/users")` 后，路由里的路径自动带上 `/users`，前端拿到的完整路径是 `/users/{user_id}`。

**路由也能嵌套**——主路由挂子路由：

```python
main_router = APIRouter()
admin_router = APIRouter(prefix="/admin")
user_router = APIRouter(prefix="/users")

main_router.include_router(admin_router)   # 相当于合并
main_router.include_router(user_router)
app.include_router(main_router)
```

**两种目录结构的取舍**：

```cmd
# A. 按"功能"分（小型项目友好）：config/models/schemas/routers/middleware
# B. 按"业务模块"分（中大型友好）：modules/user/{models,schemas,routers}.py
#                                  modules/item/{models,schemas,routers}.py

# 判断标准：模块之间是否强独立。用户和商品几乎不互相引用 → B 更清爽；
# 都还挤在一起 → A 就够用，别为了架构而架构。
```

**为什么要拆**：职责分离（改用户不动商品）、可读可维护、可扩展（加功能只加目录）、依赖清晰（import 一眼看清谁依赖谁）、**团队并行**（一人改用户路由，另一人改商品路由，互不干扰）、符合企业规范（好接 CI/CD 和代码审查）。
@@trap 拆完找不到路由的两个症状
| 现象 | 原因 / 怎么办 |
| 接口 404 | 忘了 `app.include_router(router)`，或在错误的地方 include |
| 路径多了一层 | `prefix="/users"` 里路由又写了 `@router.get("/users/{id}")` → 变成 `/users/users/{id}`。prefix 只管前缀，路由函数里别重复 |

@@point ⑬ MySQL 基础：数据库长什么样，SQL 怎么说
@@need 要解决什么
ORM 替你写 SQL，但**你总得知道它在替你写什么**：表、行、列、主键、约束、增删改查……不懂这些，你在数据库层查不出 bug，也没法跟 DBA 对话。课程用 24 课时把 MySQL 从零讲到 SQL 函数，这里是压缩版主干。
@@idea 核心思路
**四层概念**（从大到小）：

```cmd
# 数据库(DB) = 数据的仓库
#   └── 表(Table) = 仓库里的货架（二维表：行=记录，列=字段）
#        └── 行(Row) = 一条具体记录  列(Column) = 一个字段
# DBMS（如 MySQL）= 管仓库的软件   DBA = 管软件的人
```

**关系型 vs 非关系型**：关系型用二维表 + SQL，强一致性、适合复杂查询，但海量高并发的读写性能是瓶颈；非关系型（NoSQL）格式灵活（key-value、文档）、速度快、扩展性强，但无事务、复杂查询弱。**业务系统的"账本"用关系型，缓存/海量日志用 NoSQL。**

**MySQL 是什么**：开源的关系型数据库管理系统，属于 Oracle 公司，支持千万级记录、标准 SQL、多平台多语言，社区版免费够用。

**SQL 按功能分五类**（考试常考）：

| 分类 | 全称 | 干什么 | 关键字 |
| **DQL** | 数据查询语言 | 查数据 | `SELECT`（用得最多） |
| **DML** | 数据操纵语言 | 增删改表中的行 | `INSERT`、`UPDATE`、`DELETE` |
| **DDL** | 数据定义语言 | 建/改/删库和表 | `CREATE`、`ALTER`、`DROP` |
| **DCL** | 数据控制语言 | 权限 | `GRANT`、`REVOKE` |
| **TCL** | 事务控制语言 | 提交/回滚 | `COMMIT`、`ROLLBACK` |

**语法约定**：关键字建议大写，语句以分号结尾，可以单行或多行。

**DDL：建库建表**：

```sql
CREATE DATABASE fastapi_db;              -- 建库
USE fastapi_db;                          -- 切库
DROP DATABASE fastapi_db;                -- 删库（慎！）

CREATE TABLE student (
    id INT PRIMARY KEY AUTO_INCREMENT,   -- 主键自增
    name VARCHAR(50) NOT NULL,           -- 非空
    email VARCHAR(100) UNIQUE,           -- 唯一
    age INT DEFAULT 18                   -- 默认值
);
DROP TABLE student;                      -- 删表
```

**约束（CONSTRAINT）**：`PRIMARY KEY` 主键唯一非空、`NOT NULL` 非空、`UNIQUE` 唯一、`DEFAULT` 默认值、`FOREIGN KEY` 外键——**约束是让数据库自己守住规矩，而不是靠业务代码自觉。**

**DML：增删改**：

```sql
INSERT INTO student(name, email) VALUES ('张三', 'z@x.com');   -- 增
UPDATE student SET age = 20 WHERE id = 1;                      -- 改（WHERE 必写！）
DELETE FROM student WHERE id = 1;                              -- 删（WHERE 必写！）
```

**DQL：查询（核心中的核心）**：

```sql
SELECT * FROM student;                            -- 全查
SELECT name, age FROM student WHERE age > 18;     -- 选列 + 行过滤
SELECT * FROM student WHERE name LIKE '张%';      -- 模糊查
SELECT * FROM student ORDER BY age DESC;          -- 排序（DESC 降序 / ASC 升序）
SELECT department, COUNT(*) FROM employee GROUP BY department;   -- 分组统计
SELECT DISTINCT city FROM student;                -- 去重
```

**逻辑条件**：`AND`（且）、`OR`（或）、`NOT`、`BETWEEN ... AND ...`、`IN (...)`。

**SQL 函数**（一行一个小工具）：

| 类别 | 例子 |
| **字符函数** | `CONCAT(a,b)`、`SUBSTR(s,1,3)`、`UPPER(s)`/`LOWER(s)`、`LENGTH(s)` |
| **数字函数** | `ROUND(x,2)`、`ABS(x)`、`MOD(a,b)`（取余）、`CEIL()/FLOOR()` |
| **日期函数** | `NOW()`、`DATE(s)`、`YEAR(d)`、`DATEDIFF(a,b)` |
| **通用/聚合函数** | `IF(条件,a,b)`、`COUNT()`、`SUM()`、`AVG()`、`MAX()`/`MIN()` |

**事务（TCL）**：多个操作要么全成功要么全失败——`START TRANSACTION; ... COMMIT;`（确认）或 `ROLLBACK;`（反悔）。银行转账就是典型：扣款 + 加款必须同一事务。
@@trap 新手必背的三个执行教训
| 教训 | 说明 |
| **UPDATE/DELETE 必须写 WHERE** | 忘了 WHERE = 全表遭殃。先 `SELECT` 验证条件，再执行改/删 |
| **WHERE 在 GROUP BY 前，HAVING 在 GROUP BY 后** | 行过滤用 WHERE，分组后的条件用 HAVING |
| 中文乱码 | 建库建表统一 `utf8mb4`，连接串带 `?charset=utf8mb4` |

@@summary
这一章你实际拿到的是**四样东西**：

| 拿到了什么 | 为什么要紧 |
| **一个能跑的 FastAPI 服务** | 模型有了对外"正门"：路由、参数、文档、校验全通 |
| **一套数据的家** | MySQL + Tortoise-ORM + Aerich 迁移，数据能存能查能演化 |
| **企业化的骨架** | 响应建模、分页封装、中间件、CORS、APIRouter 拆分——不是玩具代码 |
| **数据库的底子** | 看得懂 SQL，知道 ORM 在替你干什么，出 bug 能定位 |

@@quiz
1. FastAPI 说到底是把"函数"变成了什么？它的自动校验和自动文档靠哪两个核心机制？
2. 路径参数、查询参数、请求体分别适合传什么数据？各自怎么声明必填/可选？
3. `Query(1, ge=1)` 里的 `ge` 管什么？校验失败时 FastAPI 返回什么状态码？
4. 为什么 AI 接口要写成 `async def`？在异步函数里调用同步阻塞库会发生什么？
5. `response_model` 解决什么问题？分页列表响应一般封装哪几个字段？
6. ORM 的价值是什么？Tortoise-ORM 和 Aerich 各自负责什么？
7. `filter(name__contains="张")` 的两个下划线叫什么语法？不写它会怎样？
8. 一张"学生-课程"表要表示"一个学生选多门课"，用哪种关系字段？中间表用来干嘛？
9. 中间件和 CORS 分别解决什么问题？生产环境 `allow_origins` 该填 `*` 还是白名单，为什么？
10. SQL 的 WHERE、GROUP BY、HAVING 的执行顺序是什么？DELETE 不写 WHERE 会发生什么？

@@links
讲义|FastAPI 文档|#
讲义|MySQL 讲义|#
资料|后端服务开发 FastAPI 章节资料|#
资料|数据库基础章节资料|#
官网|FastAPI 官方文档|https://fastapi.tiangolo.com/zh/
官网|Tortoise-ORM 文档|https://tortoise.github.io/
官网|MySQL 官方文档|https://dev.mysql.com/doc/