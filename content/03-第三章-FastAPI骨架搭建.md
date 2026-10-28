@@h1 第三章　FastAPI 应用骨架搭建
@@sub 阶段 11 · LegalMind 法律咨询系统　|　难度 ★★☆

@@why 这一章在解决什么问题
上一章数据库活了，但代码入口还是空的。国外教程最爱讲"Hello World"，可真实的 FastAPI 应用不止一个路由文件——它要处理**启动时连数据库、挂向量库、初始化记忆系统**，要解决 **Windows 上 asyncio 事件的兼容坑**，要配置跨域让前端能访问，还要按模块挂载四组路由。
本章把这套"骨架"一次搭好。学完这章，你的 `uvicorn app.main:app` 一跑，就是一个**带完整生命周期的真实应用**：启动即建表、即连向量库、即有健康检查，为第 4 章起的每个模块提供挂载点。

@@prep 开始之前
第 2 章的容器起来、依赖装好了就能开始，这章不用装新东西，只写骨架。

@@goal 学到这儿就够了
能跑起带 lifespan 和 CORS 的应用、四组路由挂上、健康检查能返回，就算过了。

@@map 这一章在整个知识库里的位置
上一章（第二章 开发环境）：Postgres/Redis 容器已起，依赖已装，.env 已配置
**本章** 你在这里：搭 FastAPI 骨架——main.py 入口 + Settings 配置 + lifespan 生命周期 + CORS + 路由注册
下一章：数据库模型与 ORM——四个 Model 类，靠本章的 init_db() 自动建表
再往后：认证（dependencies.py）→ LLM 客户端 → RAG → Agent → 各 API 路由，全部挂到本章的 router 上
阶段终点：应用有"骨架、生命周期、出入口"，业务代码往里填

@@point ① main.py：应用入口的整体结构
@@need 要解决什么
一个 FastAPI 应用的文件比想象的多：路由、模型、配置、依赖。入口文件要把它们"组装"起来，并处理好启动/关闭时的一次性资源，否则就会出现"路由找不到""数据库没连上"等连环问题。
@@idea 核心思路
LegalMind 的 `app/main.py` 承担四件事：**创建 app、注册路由、定义 lifespan（启动/关闭钩子）、CORS 中间件**。
```python
# app/main.py
import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db, close_db
…（以下省略 33 行，完整代码见仓库对应位置）
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}
```
代码结构的三条纪律：
- **lifespan 是一切初始化的唯一地点**：不写模块顶层 `init_xxx()`（那会在 import 时就执行，顺序不可控）。
- **路由统一带前缀**：`/api/auth`、`/api/chat` 等，前端 axios baseURL 正好是 `/api`，天然对齐。
- **健康检查 `/health`**：部署后探活、本地排错都靠它，返回版本号能快速判断是旧代码还是新代码。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 所有路由、中间件、数据库初始化全堆在一个 main.py | 启动快了，但加功能时处处改入口、循环 import 满天飞；main.py 只做组装，业务逻辑按模块拆出去 |

@@point ② lifespan：启动即初始化，关闭即清理
@@need 要解决什么
数据库连接、向量库、checkpointer 都是"进程级资源"——启动时必须建立，进程退出时必须释放。如果放在路由里懒初始化，第一次请求就会慢半拍或崩掉。
@@idea 核心思路
`@asynccontextmanager` 是 FastAPI 的生命周期机制：`yield` 之前是启动逻辑，之后是关闭逻辑。
- **启动**：`init_db()` 建表 → `init_vector_store()` 连接 Chroma → `init_checkpointer()` 建 LangGraph 记忆表（Postgres 里自动建 `checkpoints` 表）。
- **关闭**：三个 close 对称释放，避免端口、连接池泄漏。
一个重要特性：**startup 与 shutdown 的顺序必须对称**——**后建的先关**（与 init 顺序逆序），否则会出现"关库时还有连接还在用"的报错。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 启动时 `init_db` 报连接失败 | Postgres 容器没起来或 .env 的 DATABASE_URL 不对；先 `docker compose ps` 确认 healthy |
| lifespan 里 await 全部塞一起 | 三个 init 无依赖可以并行：`await asyncio.gather(init_db(), init_vector_store(), init_checkpointer())` 加速启动 |
| 关闭时报 "connection already closed" | close 顺序和 init 顺序不一致；严格逆序关闭 |

@@point ③ Tortoise 配置与 init_db：建表藏在启动里
@@need 要解决什么
第 4 章我们定义 Model 类，但"表什么时候建"？SQLAlchemy 要 migrate，Tortoise 有 aerich 迁移，但**开发期最省事的是启动时自动建表**——表结构变了重启就行，不用记迁移命令。
@@idea 核心思路
`app/db/database.py` 集中管理 Tortoise 的连接与建表：
```python
# app/db/database.py
from tortoise import Tortoise
from app.config import settings

DB_MODELS = [
    "app.models.user",
    "app.models.case",
    "app.models.chat",
    "app.models.document",
]
…（以下省略 3 行，完整代码见仓库对应位置）
        db_url=settings.DATABASE_URL,
        modules={"models": DB_MODELS},
    )
    # 开发期自动建表（生产环境应改用 aerich 迁移）
    await Tortoise.generate_schemas(safe=True)

async def close_db():
    await Tortoise.close_connections()
```
关键点：
- `modules={"models": [...]}` 是 Tortoise 的必填写法（`db_url` + `modules`），**漏了任一模块，该模型的表就不会建**。
- `generate_schemas(safe=True)`：`safe=True` 表示"已存在的表跳过"，重启应用不会报 already exists。
- 生产环境的多表变更应切换为 **aerich 迁移**（`aerich init` / `migrate` / `upgrade`），开发期自动建表只适合"表还没上生产"的阶段。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 启动成功但一查表就报 "table not found" | `generate_schemas` 在 lifespan 里没执行或执行失败被吞了；init_db 里先 `Tortoise.init` 再 `generate_schemas(safe=True)`，启动日志确认建表完成 |
| 报 "Unknown model" 或模型没生效 | `TORTOISE_ORM` 的 `apps.models` 里漏了 `app.models.xxx` 模块名；每个新增模型都要登记进 models 列表 |

@@point ④ CORS：为什么前端访问不了后端
@@need 要解决什么
前端在 5173 端口，后端在 8000 端口，浏览器会拦截跨域请求——报错长这样：`Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:5173' has been blocked by CORS policy`。这不是后端拒绝了，是浏览器安全策略不允许。
@@idea 核心思路
浏览器同源策略：协议+域名+端口任一不同就是"跨源"。开发期前后端端口不同，必须由**后端**声明"允许谁访问我"：
```text
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
注意区别于"请求头里的 CORS 配置"——这个 CORS 是在**响应头**加 `Access-Control-Allow-Origin`，由 FastAPI 中间件统一注入，你不需要在每个路由手写。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 换了前端端口后请求还是被拦 | `allow_origins` 写死了 5173；改成读环境变量，或开发期写 `allow_origins=["*"]`（此时必须 `allow_credentials=False`） |
| 用 `allow_origins=["*"]` 却带 cookie 失败 | `*` 与 `allow_credentials=True` 互斥；必须列具体 origin |
| 内网 IP 访问被拦 | 前端用 IP 时把该 IP 也加进 allow_origins |
| 加了 CORS 还是报错 | 确认是不是浏览器缓存了旧响应；强刷 + 关插件再试 |

@@point ⑤ include_router：按模块挂载，目录即路由
@@need 要解决什么
把所有路由写在一个文件里，几百行之后没人能从`@app.get` 大海捞针。按业务模块拆 router 文件，再统一挂载，是 FastAPI 的官方推荐组织方式。
@@idea 核心思路
每个业务模块是一个 `APIRouter`，在各自文件里定义，最后在 main.py 统一挂载：
```python
# app/api/chat.py（示例，骨架）
from fastapi import APIRouter, Depends
router = APIRouter()

@router.post("/stream")
async def stream_message(...):
    ...
```
main.py 里：
```text
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
```
效果：chat.py 里 `@router.post("/stream")` 最终对外是 `POST /api/chat/stream`。**prefix 加在挂载处而非路由定义处**，好处是：想看全路径要查 main.py；想批量改前缀只改一处。

@@point ⑥ Windows 事件循环兼容（SelectorEventLoop）
@@need 要解决什么
代码在 macOS/Linux 跑得好好的，Windows 上一跑 LangGraph 就报错或行为诡异——这是老牌坑：**Windows 的默认事件循环（ProactorEventLoop）与某些库（如 psycopg 异步、LangGraph 的 asyncio）不兼容**。
@@idea 核心思路
项目代码在 `main.py` 顶部做了针对性处理：
```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
原因拆解：
- Windows 有两种事件循环策略：`WindowsSelectorEventLoopPolicy`（基于 select，兼容性好）和 `WindowsProactorEventLoopPolicy`（默认，性能好但对 subprocess/部分 socket 支持差）。
- **uvicorn 在新版本默认通过 loop_factory 使用 asyncio.Runner**，仅设全局 policy 可能不生效，所以要在**模块顶层、且早于 uvicorn 启动**的地方设置（本项目放在 import 区的最前面 + 入口脚本层级，确保先于 Server.run() 生效）。
这个坑很隐蔽，报错往往不是明说"循环不兼容"，而是 `RuntimeError: Event loop is closed` 或在 `asyncio.run()` 里莫名卡死。**Windows 上跑任何 asyncio + 数据库的项目，第一步就加这行**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Windows 上偶发 "Event loop is closed" / 协程卡死 | Windows 默认 ProactorEventLoop 与部分异步库不兼容；入口处 `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` 强制 Selector 模式 |

@@point ⑦ app 打包：工程里为什么处处是 `from app.xxx`
@@need 要解决什么
代码写成 `from app.config import settings` 而不是 `from config import settings`，不是强迫症——它让项目以"包"的方式运行，模块路径清晰、避免命名冲突。
@@idea 核心思路
`app/` 目录本身就是 Python 包（有 `__init__.py`）。所有代码统一用 `from app.xxx import yyy` 的绝对导入，收益：
- 无歧义：`models/chat.py` 里的 `chat` 不会与标准库或其他模块撞名。
- 可复用：其他地方 import 同一模块只要一条路径。
- uvicorn 启动命令也统一为 `uvicorn app.main:app --reload --port 8000`，`app.main` 正是"包.模块:变量"，与代码里的导入格式完全一致。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 本地 `python xxx.py` 能跑，`uvicorn app.main:app` 就 ImportError | 直接执行脚本时 sys.path 是脚本目录，不是项目根；统一以模块方式运行（`python -m app.xxx`），别用 `python xxx.py` 调试 |

@@point ⑧ 路由分发前的一次性脚本 start.sh / 启动命令
@@need 要解决什么
每次手动敲一长串 `uvicorn app.main:app --reload` 容易漏参数。把启动命令固化成一个脚本/README 片段，团队协作零门槛。
@@idea 核心思路
后端启动的标准姿势（写入 README）：
```bash
cd backend
source .venv/Scripts/activate   # git-bash on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- `--reload` 开发专用：改代码自动重启。
- `--host 0.0.0.0`：允许局域网设备访问（手机联调前端时用），默认 127.0.0.1 只本机。
- 验证：浏览器开 `http://localhost:8000/health`，应返回 `{"status":"healthy","version":"1.0.0"}`。
- **FastAPI 自动文档**：`http://localhost:8000/docs` 是 Swagger UI——所有已注册路由都列在上面，调试阶段先看这里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `--reload` 下改代码不生效 | reload 只监听 Python 文件，改了 `.env`、新建目录/文件不会自动重载；重启进程或按文档加 `--reload-dir` / `--reload-include` |

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **完整应用骨架** | main.py + lifespan + CORS + 路由挂载，业务代码天天往里填 |
| **Windows 兼容修复** | SelectorEventLoop 一行代码，避开 asyncio+DB 在 Win 上的隐形崩溃 |
| **生命周期规范** | 数据库/向量库/checkpointer 启动建、关闭清，资源永不泄漏 |

@@quiz
1. lifespan 里 yield 之前和之后的代码分别做什么？为什么初始化都放这里而非模块顶层？
2. init_db 里 `modules={"models": [...]}` 漏了某个模型模块会发生什么？
3. CORS 报错是前端还是后端的问题？修在哪一端？
4. include_router 的 prefix 加在哪里？chat.py 里 `@router.post("/stream")` 对外路径是什么？
5. Windows 上为什么需要 `WindowsSelectorEventLoopPolicy`？只设 policy 在 uvicorn 新版够吗？
6. `generate_schemas(safe=True)` 的 safe 参数解决了什么问题？
7. 如何用一条命令验证后端真的起来了？自动化文档地址是多少？

@@links
参考|LegalMind 法律咨询系统：FastAPI 应用骨架|#
官网|FastAPI Lifespan 文档|https://fastapi.tiangolo.com/advanced/events/
官网|FastAPI CORS 文档|https://fastapi.tiangolo.com/tutorial/cors/
官网|Tortoise ORM 文档|https://tortoise.github.io/