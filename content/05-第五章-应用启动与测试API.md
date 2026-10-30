@@h1 第五章　应用启动与测试 API
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★

@@why 这一章在解决什么问题
模型、配置都就绪了，现在要把服务真正"跑起来"。本章解决三个问题：**main.py 如何组装 FastAPI 应用**（CORS、路由注册、启动/关闭生命周期），**uvicorn 怎么启动**，以及**第一轮 API 实测**（用浏览器/Postman/curl 验证 GET /styles 等接口真的返回数据）。

这也是一道"体检关"：前四章的任何配置错误（数据库连不上、模型没注册、CORS 拦截）都会在这一章集中爆发。学会读报错、按"链路排查法"定位，比背代码更重要。

@@prep 开始之前
第 4 章的模型和迁移跑通了就能开始，这章不用装新东西，一条 uvicorn 命令就起服务。

@@goal 学到这儿就够了
能跑起服务、在 /docs 里调通 GET /styles，报错时会按链路排查，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：数据模型与迁移——8 张表模型就绪
**本章** ← 你在这里：应用启动与测试——main.py 组装、生命周期、跑通第一个 API
下一章：JWT 登录与认证鉴权——给平台加登录与用户体系
再往后：前端工程 → Coze 智能体 → 配图与发布

@@point ① main.py：FastAPI 应用入口的三件事
@@need 要解决什么
一个 FastAPI 应用入口要做三件事：创建实例、挂中间件（CORS）、注册路由与生命周期。main.py 的职责边界要清晰。

@@idea 核心思路
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# auth 在第 6 章、create 在第 10 章才写。**本章先只 import test**，
# 或者先把这两个文件建出来当空壳（各自一行 router = APIRouter()），否则现在跑必 ModuleNotFoundError
from app.routers import test
from app.database import register_db

app = FastAPI(title="智能运营平台", version="1.0.0")

# 1) CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 通配写法；生产必须收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) 路由注册
app.include_router(test.router, prefix="/v1/test", tags=["测试"])
# 第 6 章写完 auth 再把这两行放开
# app.include_router(auth.router, prefix="/v1/auth", tags=["认证"])
# app.include_router(create.router, prefix="/v1/create", tags=["内容生成"])

# 3) 数据库生命周期
register_db(app)   # 挂载 startup/shutdown 钩子

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

模块化要点：**路由全部用 APIRouter 分离**（test/auth/create 各自文件），main.py 只做"组装与暴露"；真实的业务逻辑全在各自 router 里——这是 FastAPI 工程的基本礼仪。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由 404 | 注册时 prefix 与路由内部路径拼接错误；/v1/test + Router 里的 /styles = /v1/test/styles |
| 前端能加载但请求全挂 | CORS 拦截（见下一点）或代理没配上 |

@@point ② CORS：谁允许访问我
@@need 要解决什么
前端跑在 5173，后端在 8000，浏览器会拦截跨域请求。CORS 中间件就是"允许名单"。

@@idea 核心思路
浏览器同源策略下，**跨域请求前先发 OPTIONS 预检**，后端要回复允许的源/方法/头。CORSMiddleware 参数对应：

| 参数 | 含义 | 本项目 |
|---|---|---|
| allow_origins | 允许的来源列表 | 练习环境用 ["*"]；联调建议写 ["http://127.0.0.1:5173"] |
| allow_credentials | 是否允许携带 Cookie/Authorization | True（JWT 走 Authorization 头） |
| allow_methods | 允许的 HTTP 方法 | ["*"] 即 GET/POST/PUT/DELETE/OPTIONS |
| allow_headers | 允许的请求头 | ["*"] 含自定义头如 Authorization |

⚠️ 金牌规则：**allow_origins=["*"] 与 allow_credentials=True 别一起用**。Starlette 遇到这种组合会把请求的真实 Origin 回显，所以技术上能跑通；但生产环境务必把 "*" 换成真实域名，别依赖这个回显。前端走后端代理时后端其实收不到跨域问题（同源），但若直连 8000，CORS 配置必须精确。生产环境务必把 "*" 换成真实域名。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 前端直连 8000 报 CORS error | 后端没配这个来源；联调期把 127.0.0.1:5173 加进 allow_origins |
| 配了 "*" 且 credentials=True 仍报错 | 通配源与凭据互斥；要么精确源 + True，要么 "*" + False |
| 预检 405 Method Not Allowed | OPTIONS 没被放行——allow_methods 别忘了 OPTIONS |

@@point ③ database.py：连接生命周期的正确挂法
@@need 要解决什么
Tortoise 的连接要在**应用启动时建立、关闭时销毁**，否则每个请求都手动连、关会出现连接泄漏。

@@idea 核心思路
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from tortoise.contrib.fastapi import RegisterTortoise   # 注意是大写 R 的那个
from app.config import TORTOISE_ORM

@asynccontextmanager
async def lifespan(app: FastAPI):
    # RegisterTortoise 是**异步上下文管理器**：进入 with 时连库、退出时关库
    # 别写成「import RegisterTortoise，却调 register_tortoise()」——那是两个不同的东西
    async with RegisterTortoise(
        app,
        config=TORTOISE_ORM,
        add_exception_handlers=True,   # 数据库异常自动转成友好的 HTTP 错误
        generate_schemas=False,        # 不自动建表：表交给 SQL / Aerich 管
    ):
        yield

app = FastAPI(title="智能运营平台", lifespan=lifespan)
```

- RegisterTortoise 自动注册 startup（连库）与 shutdown（关库）事件。
- `generate_schemas=False`：**不自动建表**——表由 SQL/Aerich 管理，这里只连接不建表，避免"自动建的表和设计不一致"。
- `add_exception_handlers=True`：数据库异常自动转成友好 HTTP 错误。

启动时若报"ConnectionError: Can't connect to MySQL"，先查：MySQL 启动没？密码对不对？quote_plus 处理了没？host/port 通不通？

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 请求一执行就报 ConnectionError | startup 建连失败——uwsgi/uvicorn 可能没触发启动事件，或 MySQL 没起 |
| 程序退出时"数据库连接未关闭" | shutdown 事件没注册；用 RegisterTortoise 自动管理即可 |

@@point ④ 启动 uvicorn：三种姿势与热重载
@@need 要解决什么
服务怎么启动？开发期与生产期姿势不同。

@@idea 核心思路
```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
- `main:app`：模块:实例，命令在工程根目录执行时自动找 main.py。
- `--reload`：改代码自动重启——**开发必备**（.env 改动不触发 reload，需手动重启）。
- 或 `python main.py`（main.py 里有 uvicorn.run 兜底）。

启动成功标志：日志出现 `Uvicorn running on http://127.0.0.1:8000` + 无重试报错；访问 `http://127.0.0.1:8000/docs` 能看到 Swagger 交互文档——FastAPI 白送的 API 测试面板。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 8000 端口被占用 | 杀占用进程或改端口；`netstat -ano \| findstr 8000` 定位 PID |
| 改 .env 后 --reload 不重启 | reload 只监听 .py；改配置需手动重启进程 |

@@point ⑤ 第一个接口：GET /v1/test/styles
@@need 要解决什么
不接任何 AI、不写复杂逻辑，先验证"数据库→后端→响应"整条链路通不通。test router 就是干这个的。

@@idea 核心思路
```python
from fastapi import APIRouter
from app.models.style import Style

router = APIRouter()

@router.get("/styles")
async def get_styles():
    styles = await Style.all()
    return {"code": 200, "message": "success",
            "data": [{"id": s.id, "name": s.name, "fengge": s.fengge} for s in styles]}
```

`await Style.all()` —— **Tortoise 是异步 ORM，任何查询都要 await**！忘了 await 会拿到协程对象而不是数据。

响应约定（全平台统一）：`{"code": 200, "message": "success", "data": ...}`——前端 axios 拦截器就靠 code 判断成败。

测试方法：
1. 浏览器直接开 `http://127.0.0.1:8000/v1/test/styles`
2. 或 Postman GET 同 URL
3. 或 curl：`curl http://127.0.0.1:8000/v1/test/styles`

看到 JSON 里返回种子的风格列表 = 数据库链路全通。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 返回 {"detail": "Not Found"} 405/404 | 路径拼错：路由前缀 /v1/test + 内部路径必须拼对；最稳的是看 Swagger 文档里的实际路径 |
| 报 TypeError coroutine 对象 | 异步查询没 await；`Style.all()` 返回协程，必须 await |
| 返回空 data | 表里没种子数据：回到第 2 章重新导入 ai_operation.sql |

@@point ⑥ 响应格式约定：code/message/data 三件套
@@need 要解决什么
后端接口很多（几十个），如果每个返回结构不统一，前端解析代码会写疯。先钉死全局响应契约。

@@idea 核心思路
统一格式：
```json
{
  "code": 200,          // 业务码：200 成功，400 参数错误，401 未登录，403 无权限，500 服务异常
  "message": "success", // 人读的说明
  "data": { ... }       // 业务数据，可空
}
```
前端 request.js 拦截器：code===200 才 resolve（进入业务分支），否则 reject 并全局提示 message。**code 与 HTTP 状态码可能不同**（如 401 未登录用 HTTP 200 返回也是约定之一，前后端要一致）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 后端某接口忘包 code/message/data | 前端拦截器拿到 undefined 直接崩；写接口前先复制标准返回模板 |
| 前端判断 code===200 但后端返回 HTTP 200 + code 500 | code 是业务码，与 HTTP 状态码独立；后端异常分支也要统一包进 JSON |

@@point ⑦ 用 Swagger /docs 调试接口
@@need 要解决什么
Postman 之前，FastAPI 自带交互文档是最快的调试入口——自动列出所有路由、参数、试跑。

@@idea 核心思路
访问 `http://127.0.0.1:8000/docs`：
- 左侧列出全部注册路由（test/auth/create 分组可见）；
- 点开 GET /v1/test/styles → Try it out → Execute → 立刻返回 JSON；
- 页顶还能看到每个接口的请求/响应结构，等于一份自动生成的 API 文档。

**先 /docs 后 Postman**：/docs 能证明"服务与路由本身正常"，之后再用 Postman 专门测鉴权、头信息、异常分支等 /docs 不擅长模拟的场景。

@@point ⑧ 启动失败的"三板斧"排查法
@@need 要解决什么
服务起不来时最常见的三句话："ImportError 找不到模块""端口被占""连不上数据库"。与其盲试，按序三板斧。

@@idea 核心思路
第一板斧：**看启动日志的第一条异常**——报错行号会直接指到文件与代码行，90% 的问题到此结束。
第二板斧：**分三段验证 import 链**：
```
python -c "from app.config import TORTOISE_ORM"      # 配置层
python -c "from app.models import Title"              # 模型层
python -c "from main import app"                      # 应用层
```
哪段报错就修哪段——把"一条大报错"拆成三个小验证，定位瞬间清晰。
第三板斧：**检查运行位置与依赖**：uv run 是否在工程根目录执行（import main 靠 cwd）；uv sync 是否装齐（缺包报 ModuleNotFoundError: xxx）。

常见启动报错对照表：
| 报错 | 原因 |
|---|---|
| ModuleNotFoundError: app | 命令没在工程根目录跑 |
| ModuleNotFoundError: xxx包 | 依赖没装（uv add 或 uv sync） |
| Can't connect to MySQL | MySQL 没起/密码错/端口错（第 2 章五要素） |
| Address already in use | 8000 端口占用，换端口或杀进程 |

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 报错一闪而过看不清 | uvicorn 用 --reload 时崩溃会重启刷屏；先不带 --reload 跑一次看完整堆栈 |
| 改了代码却还是旧报错 | reload 节点没监听到该文件（新加的文件）；重启进程最稳 |


@@summary 这一章你学到了什么
- main.py 三件事：CORS 中间件、APIRouter 路由注册（prefix 前缀）、RegisterTortoise 生命周期
- CORS 参数语义：allow_origins/credentials/methods/headers；"*" 与 credentials=True 互斥
- RegisterTortoise：startup 建连 + shutdown 关连 + generate_schemas=False 不自动建表
- uvicorn 启动：uv run uvicorn main:app --reload；/docs Swagger 面板
- 第一个接口 GET /v1/test/styles：await Style.all() + code/message/data 三件套
- 全局响应契约：code 业务码 ≠ HTTP 状态码，前端靠 code 分支
- 调试顺序：/docs 验路由 → Postman 验头与异常
- 启动三板斧：看首条异常 → 分三段验证 import → 查位置与依赖

@@quiz
1. 以下哪项不属于 main.py 的职责？
   A. 注册 CORS 中间件　　B. include_router 挂路由　　C. 写业务 SQL　　D. 注册数据库生命周期
2. allow_origins=["*"] 与 allow_credentials=True 同时配置会？
   A. 正常工作　　B. 浏览器拒绝通配源带凭据　　C. 后端崩溃　　D. 数据库断开
3. RegisterTortoise 中 generate_schemas=False 表示？
   A. 关闭建表，只连接　　B. 自动建表　　C. 生成迁移文件　　D. 生成表结构文档
4. 异步 ORM 查询 Style.all() 必须？
   A. 加 .all_now　　B. await　　C. 用同步模式　　D. 不需要特殊处理
5. 前端判断业务成功的依据是？
   A. HTTP 200　　B. data.code === 200　　C. data.message　　D. 响应头
6. 开发期改代码自动重启用哪个参数？
   A. --host　　B. --reload　　C. --debug　　D. --workers
7. 路由注册为 /v1/test + 内部 /styles，最终路径是？
   A. /v1/styles　　B. /v1/test/styles　　C. /styles　　D. /test/styles

@@links
参考|智能运营平台.pdf|#
官方|FastAPI CORS 文档|https://fastapi.tiangolo.com/tutorial/cors/
官方|Tortoise FastAPI 集成|https://tortoise.github.io/contrib/fastapi.html
