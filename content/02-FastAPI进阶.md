@@h1 第二章　FastAPI 进阶
@@sub 阶段 2 · AI 智能体 Web 系统构建实战　|　DI + DDD 实战　|　难度 ★★★

@@why 这一章在解决什么问题
第一章你学会了"写出能跑的 API"，但**项目一长大就乱**：改一个功能要动十处代码、每个接口各写各的参数检查、数据库代码和业务逻辑糊在一起……这不是你的能力问题，是结构问题。

这一章给你两把武器，专治"长大就乱"：

- **依赖注入（DI）**：让"零件"（数据库、服务、校验逻辑）自己送到需要它的地方，而不是每个接口自己 new。换数据库、换实现，改一行配置就完事
- **领域驱动设计（DDD）**：一套企业级的分层骨架——接口层只管收请求、应用层只管编排、领域层只放业务规则、基础设施层只碰数据库。**业务逻辑不再散落各处**

学完这一章，你交付的不再是"能用的脚本"，而是**结构清晰、能测试、能扩展、能交给别人维护的工程**——这正是 AI 智能体系统后端该有的形态。

@@prep 开始之前
接着上一章就行；要配套代码包 fastapi_code2.7z，装 uv 跑 ddd 工程，数据库用 SQLite。

@@goal 学到这儿就够了
能说清 DI 解决什么、DDD 四层各管什么，并把 ddd 工程跑起来注册用户、查到订单，这一章就算过了。

@@map 这一章在整个知识库里的位置
第一章 后端服务开发 FastAPI：能跑通的 API + 数据库 —— 解决了"有没有"
**本章** ← 你在这里：依赖注入 + DDD 分层 —— 解决"乱不乱、能不能长大"
阶段终点：一个分层清晰、可维护、可扩展的智能体 Web 系统后端 → 可以对接前面的 AI 能力和后面的前端
上一阶段你训练的是"大脑"，这一阶段你给它装上了"身体"和"骨架"，本章就是骨架的最后一环。

@@note info 跟上这章的姿势
本章前半段 DI 通过 6 个独立小文件（DI1~DI6.py）渐进演示，后半段 DDD 用一个完整工程贯穿。建议**边看边改代码**：每看完一个 DI 文件就自己跑一遍 `uvicorn DIx:app --reload`，最后把 ddd 工程 `uv run` 起来、在 `/docs` 里注册一个用户再查订单。代码都配套在 `fastapi_code2.7z` 里。

@@point ① 依赖注入：为什么"别人递给你"胜过"你自己去拿"
@@need 要解决什么
假设每个接口都要用数据库，你可能会在每个路由里写 `db = Database()`。问题来了：

- 十几处 `new`，想换成 Redis / 换连接配置，改到怀疑人生
- 测试时没法换成假数据库，因为每个函数都自己硬造
- 校验逻辑（查权限、验 token）每个接口复制粘贴，改一处漏三处

**依赖注入（Dependency Injection）的核心思想：一个对象需要的"依赖"（数据库、服务、工具），不由它自己创建，而是由 FastAPI 在调用时"注入"给它。你只管声明"我要什么"，框架负责"给什么"。**
@@idea 核心思路
在 FastAPI 里，依赖注入靠两样东西：

| 东西 | 作用 |
| **依赖函数** | 一段可复用的"前置逻辑"，返回你要的东西（token、用户、分页参数、数据库连接） |
| **`Depends()`** | 在路由参数里声明"这个参数的值由依赖函数提供" |

**最简单的依赖**（DI1.py）：一个依赖函数把查询参数转大写后返回：

```python
from fastapi import FastAPI, Depends
from typing import Annotated

app = FastAPI()

def get_query_param(q: str = ""):
    return q.upper()            # 依赖函数：加工参数

async def common_params(q: str = "", skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}   # 返回公共参数包

@app.get("/items/")
async def read_items(common: dict = Depends(common_params)):
    return common               # 路由不再自己解析参数，直接用注入结果

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("DI1:app", host="127.0.0.1", port=8000, reload=True)
```

**产生式依赖（DI2.py）：依赖里做校验，不合格直接拦下** —— token 验证写进依赖，路由自动受保护：

```python
from fastapi import FastAPI, Depends, HTTPException, Header

app = FastAPI()

async def check_user_permission(token: str = Header(...)):
    if token != "secret_token":
        raise HTTPException(status_code=401, detail="未授权")
    return {"user": "admin", "token": token}   # 校验通过，把用户信息交给路由

@app.get("/users/")
async def get_users(user: dict = Depends(check_user_permission)):
    # 能走到这 = 已通过权限校验，路由里再也不用写权限判断
    return {"users": ["admin", "user1"], "current_user": user}   # 别写 [...]，省略号不是数据、无法 JSON 序列化
```

**"装饰器能做的事，Depends 也能做但更干净"**：`Depends` 把校验结果**作为参数传进函数**，而不是像中间件那样笼统拦截——路由能直接拿到"是谁在调用"。

@@trap 三个新手常见误用
| 现象 | 原因 / 怎么办 |
| 依赖一直不执行 | 依赖函数必须用 `Depends(get_xxx)` 声明才会被调用；只 import 不声明 = 白写 |
| 路由参数和依赖参数重名 | FastAPI 按参数名匹配；避免路由签名里出现和依赖函数内部同名但含义不同的参数 |
| 依赖里抛了 `HTTPException` | 这是对的！依赖里抛异常 = 请求被拦在路由之前，返回对应状态码 |

@@point ② 依赖的三种作用域：路径级、路由级、全局级
@@need 要解决什么
上面的依赖只保护一个接口。但业务里常常要保护**一组接口**（用户模块所有接口都要登录）甚至**整个应用**（所有接口都要记日志）。如果每个路由都写一遍 `Depends(...)`，那 DRY 原则就白学了。FastAPI 提供三个"挂载点"，让依赖按作用域生效。
@@idea 核心思路
**三档作用域对比**（越往下覆盖越广）：

| 作用域 | 写法 | 效果 | 典型用途 |
| **路径级**（单接口） | `@app.get("/", dependencies=[Depends(check)])` | 只保护这一个接口 | 登录接口校验 |
| **路由级**（一组接口） | `APIRouter(dependencies=[Depends(check)])` | 该 router 下所有接口生效 | 用户模块统一鉴权 |
| **全局级**（整个应用） | `FastAPI(dependencies=[Depends(check)])` | 所有接口生效 | 全站日志、公共参数 |

**路径级**（DI2.py 变体）—— 单个接口挂依赖：

```python
@app.get("/items/", dependencies=[Depends(check_user_permission)])
async def read_items():
    return {"items": ["item1", "item2"]}
```

**路由级**（DI3.py）—— 一组接口统一挂：

```python
from fastapi import APIRouter, Depends, Header, HTTPException

async def check_auth(x_token: str = Header(...)):
    if x_token != "secret-token":
        raise HTTPException(status_code=403, detail="Invalid token")

router = APIRouter(prefix="/users", tags=["用户"],
                   dependencies=[Depends(check_auth)])   # 一个 router 全保护

@router.get("/")            # 自动继承 check_auth
async def list_users():
    return {"users": ["admin", "user1"]}

@router.get("/{user_id}")   # 也自动继承
async def get_user(user_id: int):
    return {"user_id": user_id}
```

**全局级**（DI4.py）—— 整个应用挂，最适合日志/公共处理：

```python
from fastapi import FastAPI, Depends, Request

async def log_request(request: Request):
    print(f"Request: {request.method} {request.url}")
    return {"logged": True}

app = FastAPI(dependencies=[Depends(log_request)])   # 所有路由自动记日志

@app.get("/items/")
async def list_items():
    return {"items": ["item1", "item2"]}
```

**怎么选？** 记日志/埋点 → 全局级；整组鉴权 → 路由级；个别敏感接口额外校验 → 路径级。三档可以叠加，FastAPI 会按"全局 → 路由 → 路径"逐层执行。
@@trap 挂载位置写错，依赖不生效
`dependencies=[Depends(fn)]` 的位置决定作用域：写在 `@app.get(...)` 里 = 路径级；写在 `APIRouter(...)` 里 = 路由级；写在 `FastAPI(...)` 里 = 全局级。**写错了位置，依赖要么全量生效（性能开销），要么完全不生效（权限漏风）**——鉴权类依赖建议从路由级起步。

@@point ③ 嵌套依赖与类依赖：依赖还能"用依赖"
@@need 要解决什么
现实中校验是分层的：**先验 token 对不对（基础），再根据 token 取当前用户（上层）**。"取用户"这个依赖，自己也需要"验 token"这个依赖——依赖之间互相依赖怎么办？另外，很多服务（如 UserService）需要保存状态、需要构造参数，函数依赖表达不了，怎么办？
@@idea 核心思路
**嵌套依赖（DI5.py）：依赖函数 A 的参数里声明 `Depends(B)`，FastAPI 自动"先执行 B，再把结果传进 A"**：

```python
from fastapi import FastAPI, Depends, HTTPException, Header

app = FastAPI()

async def verify_token(token: str = Header(...)):
    """第一层：先验证 token"""
    if token != "secret_key":
        raise HTTPException(status_code=403, detail="Invalid token")
    return token

async def get_current_user(token: str = Depends(verify_token)):
    """第二层：依赖第一层的结果，再取用户"""
    return {"user": "admin", "token": token}

@app.get("/user/")
async def get_user(user: dict = Depends(get_current_user)):
    return user    # 路由只管用，校验链条由框架自动组装
```

**执行顺序**：请求进来 → `verify_token` 先跑（校验失败 403，后面全不执行）→ `get_current_user` 拿到 token 再取用户 → 路由收到 `user`。**这就是现实中"认证-授权-业务"三层链的标准写法。**

**类依赖（DI6.py）：当依赖需要状态和构造参数时，用类 + 工厂函数**：

```python
from fastapi import FastAPI, Depends

app = FastAPI()

class UserService:
    """带状态的服务类：持有数据库连接等资源"""
    def __init__(self, db_connection: str = "DefaultDBConnection"):
        self.db_connection = db_connection

    def get_user(self, user_id: int):
        return {"user_id": user_id, "name": "John Doe",
                "db_connection": self.db_connection}

def get_user_service():
    """工厂函数（依赖）：负责构造服务实例，可在这里注入配置"""
    return UserService(db_connection="test-db")

@app.get("/users/{user_id}")
async def read_user(user_id: int,
                    user_service: UserService = Depends(get_user_service)):
    return user_service.get_user(user_id)
```

**要点**：`Depends` 里写的是**工厂函数** `get_user_service` 而不是类本身——由工厂决定怎么构造（传什么连接串、要不要单例）。这样换配置/换实现都只改工厂，路由无感知。**这是后文 DDD 里"依赖注入容器"的原型。**
@@trap 依赖链别套太深
嵌套带来便利也带来复杂度：三层以上会让请求链路变难读难测。**超过两层时考虑合并校验**（如把 verify_token 的检查并入 get_current_user 内部），或用独立的鉴权依赖仅做拦路虎，保持业务逻辑在路由里清晰可见。

@@point ④ 为什么要 DDD：从"能跑"到"能长大"
@@need 要解决什么
把第一章的项目继续写下去：用户表、订单表、权限、日志……很快你就会面临熟悉的崩溃：

- `main.py` 三千行，所有路由、逻辑、数据库调用挤在一起
- 业务规则（"用户名不能为空""用户已存在"）散落在各路由里，改一处漏三处
- 数据库字段和业务对象混用，换数据库等于重写业务
- 写测试无从下手

**DDD（Domain-Driven Design，领域驱动设计）就是一套"大型项目不崩溃"的组织方法。** 核心洞察：**让"业务规则"（领域层）独立于"技术实现"（数据库、框架），并且依赖方向永远从外向内。**
@@idea 核心思路
传统写法 vs DDD 的对比：

```cmd
# 传统（贫血模型，业务和技术糊一起）
main.py
├─ 路由 + 参数校验 + 业务规则 + SQL 全在一个文件
└─ 改一个需求 = 动一片代码

# DDD（分层，各司其职）
interface  →  应用入口：收请求、返回响应（只做翻译）
    ↓ 调用
application → 编排：注册、登录、查订单（管流程，不含业务细节）
    ↓ 调用
domain     → 领域：业务规则 + 实体 + 仓储接口（最核心、最稳定）
    ↑ 实现
infrastructure → 技术：ORM 模型、Mapper、仓储实现（可替换）
```

**三个关键规则**：

| 规则 | 含义 |
| **依赖倒置** | domain 定义"仓储接口"，infrastructure 实现它。上层依赖接口不依赖实现 → 换数据库只改 infrastructure |
| **单向依赖** | 只允许 `interface → application → domain ← infrastructure`，禁止反向。domain 绝不 import 框架和 ORM |
| **领域最稳定** | 业务规则写在 domain（实体、值对象、仓储接口），它不依赖任何技术细节，测试最容易 |

**DDD 适用范围**：业务规则复杂、生命周期长、需要长期演进的项目（订单、账号、风控）。简单 CRUD 玩具项目用 DDD 是过度设计——**架构是为"会变大的系统"准备的**。
@@trap DDD 不是银弹
| 误区 | 正解 |
| 所有项目都套 DDD | 3 个接口的 demo 用 DDD = 自找麻烦。**规模上来、业务规则多了再分层** |
| DDD = 目录分层 | 分层只是骨架，灵魂是**领域层独立承载业务规则**、仓储接口隔离技术实现 |
| 任务型小组件（GetOrdersQuery 里模拟数据） | 演示里可先 mock，真正的工程要注入订单仓储，别拿演示当规范 |

@@point ⑤ DDD 工程总览：一个真实项目的骨架
@@need 要解决什么
理论说完了，看落地。配套的 `ddd/` 工程用**用户注册、登录、查订单**三个业务，把完整 DDD 架构跑通。先看整体结构，你才会知道每层文件是干嘛的。
@@idea 核心思路
**工程目录与职责**（对照代码包）：

```cmd
ddd/
├─ main.py                    → 应用入口：组装 FastAPI、注册路由、管理数据库生命周期
├─ config/settngs.py          → 配置：应用名/版本/数据库 URL（pydantic-settings 从 .env 读）
├─ app/
│  ├─ domain/                 ★ 领域层（业务规则，不依赖任何框架）
│  │  ├─ shared/vo.py         → 值对象：UserID（带合法性校验）
│  │  ├─ user/entity.py       → 实体：User（用户名/密码规则 + 验证密码方法）
│  │  └─ user/repository.py   → 仓储接口（抽象，只声明不实现）
│  ├─ application/            ★ 应用层（流程编排：命令/查询 + 处理器）
│  │  ├─ user/commands/       → register_user.py / login_user.py（写操作）
│  │  ├─ user/queries/        → get_orders.py（读操作）
│  │  └─ common/exception.py  → 领域异常体系（AuthError/DuplicateError/...）
│  ├─ infrastructure/         ★ 基础设施层（技术实现，可替换）
│  │  ├─ database/orm_models.py → Tortoise ORM 模型（UserORM）
│  │  ├─ database/mappers.py  → 实体 ⇄ ORM 映射器（UserMapper）
│  │  └─ repository/user_impl.py → 仓储接口的实现（UserRepositoryImpl）
│  └─ interface/              ★ 接口层（HTTP 出入口）
│     ├─ api/v1/auth_router.py  → /auth/register、/auth/login
│     ├─ api/v1/order_router.py → /orders/
│     └─ dependency.py        → 依赖注入容器：把各层"接线"起来
└─ pyproject.toml             → uv 工程声明（fastapi、tortoise-orm、aerich、pydantic-settings）
```

**一次请求的完整旅程（注册用户，务必顺着读一遍）**：

```cmd
浏览器 POST /api/v1/auth/register
  ↓ interface: auth_router 收 JSON → 转成 RegisterUserCommand
  ↓            （handler 由 dependency.py 的 Depends 注入）
  ↓ application: RegisterUserHandler 校验输入 → 查重 → 建 User 实体 → 调用仓储保存
  ↓ domain:      User 实体校验规则（用户名/密码非空）
  ↓              UserRepository 接口（不知道也不关心底层是 MySQL 还是 SQLite）
  ↓ infrastructure: UserMapper 把实体转 UserORM → Tortoise 落库
  ↑ 返回值按层回传：ORM → 实体 → Result → Response → JSON 给前端
```

**读这份工程的方法**：沿着 `main.py → dependency.py → auth_router → register_user.py → entity.py/repository.py → mappers.py/orm_models.py → user_impl.py` 这条线读两遍，第二遍你会发现——**换数据库只需要改 infrastructure 层，其它层一行不动**。
@@trap 入口只有一处，别在别处组装
所有路由在 `main.py` 的 `create_app()` 里统一 `include_router`，依赖在 `interface/dependency.py` 统一声明。**不要在路由文件里直接 import 实现类来 new**（如 `UserRepositoryImpl()`），那样依赖方向就反了——测试时就没法替换了。

@@point ⑥ 领域层：值对象、实体、仓储接口
@@need 要解决什么
领域层是整个架构的"宪法"：业务规则必须集中在这里，且**不依赖 FastAPI、不依赖 Tortoise、不依赖任何框架**。本工程用三样东西承载规则：值对象（校验"是什么"）、实体（校验"能做什么"）、仓储接口（声明"数据怎么存取"）。
@@idea 核心思路
**① 值对象 `UserID`**（`domain/shared/vo.py`）——不可变 + 自带校验：

```python
from dataclasses import dataclass

@dataclass(frozen=True)   # frozen=True: 实例不可变（值对象语义）
class UserID:
    """用户ID值对象"""
    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("用户ID不能小于0")
```

**为什么要有值对象**：ID 不是一个裸 `int`，它自带"不能为负"的业务规则。任何拿它的人（仓储、路由）都自动被这条规则保护，不用各自再判断。

**② 实体 `User`**（`domain/user/entity.py`）——有身份、有行为的业务对象：

```python
from dataclasses import dataclass
from typing import Optional
from ..shared.vo import UserID

@dataclass
class User:
    """用户实体：业务规则和行为都在这里"""
    id: Optional[UserID]
    username: str
    password: str

    def __post_init__(self):
        if not self.username:
            raise ValueError("用户名不能为空")
        if not self.password:
            raise ValueError("密码不能为空")

    def verify_password(self, password: str) -> bool:
        """验证密码是否正确（实体自带行为）"""
        return self.password == password

    def change_password(self, new_password: str) -> None:
        """修改密码（行为封装在实体里，规则不外泄）"""
        if not new_password:
            raise ValueError("密码不能为空")
        self.password = new_password
```

**注意**：`User` 组合了值对象 `UserID`（`id: Optional[UserID]`），密码规则、改名规则全部内聚在实体上——**业务逻辑不再散落在路由里**。

**③ 仓储接口 `UserRepository`**（`domain/user/repository.py`）——只声明"能做什么"，不写"怎么做"：

```python
from abc import ABC, abstractmethod
from typing import Optional
from .entity import User
from ..shared.vo import UserID

class UserRepository(ABC):
    """用户仓储接口：领域层只认接口，实现交给基础设施层"""

    @abstractmethod
    async def save(self, user: User) -> User:
        """保存用户"""
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UserID) -> Optional[User]:
        """通过ID查找用户"""
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        """通过用户名查找用户"""
        pass

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """检查用户名是否存在"""
        pass

    @abstractmethod
    async def delete(self, user_id: UserID) -> bool:
        """删除用户"""
        pass

    @abstractmethod
    async def find_all(self) -> list[User]:
        """查找所有用户"""
        pass
```

**接口的签名值得细看**：入参出参全是**领域类型**（`User`、`UserID`），没有出现 `UserORM`、`select`、`INSERT` 等任何技术词汇——这就是"领域不依赖技术"的落地形态。
@@trap 领域层别 import 框架
`domain/` 里如果出现 `from fastapi import ...` 或 `from tortoise ...` 就是架构违规。检查方法：**领域层只 import dataclasses、abc、typing、以及领域层自己的模块**。一旦破了这条，领域层就失去"可独立测试、可跨技术迁移"的价值。

@@point ⑦ 基础设施层：ORM 模型、映射器、仓储实现
@@need 要解决什么
领域层声明了 `UserRepository` 接口，现在要有人**真的去操作数据库**。基础设施层就是接口的"实现处"：ORM 模型对表、映射器做"实体 ⇄ 数据库行"互转、仓储实现把接口的每个方法落到真实 SQL。
@@idea 核心思路
**① ORM 模型 `UserORM`**（`infrastructure/database/orm_models.py`）——想清楚：这是"数据库视角"的对象，不是业务对象：

```python
from tortoise.models import Model
from tortoise import fields

class UserORM(Model):
    """用户表（ORM模型：只描述表结构，不含业务规则）"""
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
```

**② 映射器 `UserMapper`**（`infrastructure/database/mappers.py`）——"领域对象 ⇄ ORM"双向翻译，隔离两套类型：

```python
from ..database.orm_models import UserORM
from app.domain.user.entity import User
from app.domain.shared.vo import UserID

class UserMapper:
    """实体与ORM映射器：领域对象 ↔ 数据库行"""

    @staticmethod
    def to_entity(orm_model: UserORM) -> User:
        """ORM对象 → 实体对象（出库方向）"""
        return User(
            id=UserID(orm_model.id) if orm_model.id else None,
            username=orm_model.username,
            password=orm_model.password,
        )

    @staticmethod
    def to_orm(user: User) -> UserORM:
        """实体对象 → ORM对象（入库方向）"""
        orm_model = UserORM()
        if user.id:
            orm_model.id = user.id.value
        orm_model.username = user.username
        orm_model.password = user.password
        return orm_model
```

**③ 仓储实现 `UserRepositoryImpl`**（`infrastructure/repository/user_impl.py`）——接口的落地：内部用 ORM 查库，对外仍返回领域对象：

```python
from typing import Optional
from app.domain.user.repository import UserRepository
from app.domain.user.entity import User
from app.domain.shared.vo import UserID
from app.infrastructure.database.mappers import UserMapper
from app.infrastructure.database.orm_models import UserORM

class UserRepositoryImpl(UserRepository):
    """基于ORM的用户仓储实现：接口的数据库版本"""

    async def save(self, user: User) -> User:
        user_orm = UserMapper.to_orm(user)     # 实体 → ORM
        await user_orm.save()
        return UserMapper.to_entity(user_orm)  # 存完转回实体返回

    async def find_by_id(self, user_id: UserID) -> Optional[User]:
        orm_model = await UserORM.get_or_none(id=user_id.value)
        return UserMapper.to_entity(orm_model) if orm_model else None

    async def find_by_username(self, username: str) -> Optional[User]:
        orm_model = await UserORM.get_or_none(username=username)
        return UserMapper.to_entity(orm_model) if orm_model else None

    async def exists_by_username(self, username: str) -> bool:
        return await UserORM.filter(username=username).exists()

    async def delete(self, user_id: UserID) -> bool:
        return await UserORM.filter(id=user_id.value).delete() > 0

    async def find_all(self) -> list[User]:
        orm_models = await UserORM.all()
        return [UserMapper.to_entity(m) for m in orm_models]
```

**这层为什么值得写**：换数据库（SQLite → PostgreSQL）时，**领域层、应用层、接口层一行不改**，只动本层的 ORM 模型和映射器——这就是"依赖倒置"换来的可替换性。
@@trap Mapper 别偷懒省略
有人嫌 Mapper 啰嗦，直接在仓储实现里 `User(id=UserID(orm.id), ...)`。字段少时无所谓，字段一多（几十列）、业务对象和表结构差异变大，**没有 Mapper 的转换逻辑会散落在各处，成为最难维护的死角**。保持 Mapper 单一职责：只做双向翻译。

@@point ⑧ 应用层：命令/查询模式与统一异常
@@need 要解决什么
接口层不该写业务判断（"用户名空没空""用户重没重"），领域层又不该关心 HTTP。**应用层就是中间的"编排者"**：接收"命令/查询"（用户想干什么），指挥领域对象和仓储完成它，返回结果。同时，业务异常要有统一出口，接口层才好统一转成 HTTP 错误。
@@idea 核心思路
**① 统一异常体系**（`application/common/exception.py`）——一个根异常 + 分类子类：

```python
from typing import Optional

class DomainException(Exception):
    """业务异常基类：带业务错误码"""
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)

class AuthError(DomainException):          # 认证失败
    def __init__(self, message="认证失败"):
        super().__init__(message, "AUTH_ERROR")

class DuplicateError(DomainException):     # 数据重复（如用户名已存在）
    def __init__(self, message="数据已存在"):
        super().__init__(message, "DUPLICATE_ERROR")

class NotFoundError(DomainException):      # 数据不存在
    def __init__(self, message="数据不存在"):
        super().__init__(message, "NOT_FOUND_ERROR")

class ValidationError(DomainException):    # 输入校验失败
    def __init__(self, message="数据验证失败"):
        super().__init__(message, "VALIDATION_ERROR")
```

**② 命令 + 处理器**（`commands/register_user.py`）——命令携带输入，处理器编排流程：

```python
from dataclasses import dataclass
from app.domain.user.repository import UserRepository
from app.domain.user.entity import User
from app.application.common.exception import DuplicateError, ValidationError

@dataclass
class RegisterUserCommand:
    """用户注册命令：就是"用户想做的事"的数据包"""
    username: str
    password: str

@dataclass
class RegisterUserResult:
    """注册结果"""
    user_id: int
    username: str

class RegisterUserHandler:
    """注册处理器：编排流程，不含数据库细节"""
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository   # 依赖注入！只认接口

    async def handle(self, command: RegisterUserCommand) -> RegisterUserResult:
        # 1. 校验输入
        if not command.username or not command.username.strip():
            raise ValidationError("用户名不能为空")
        if not command.password or not command.password.strip():
            raise ValidationError("密码不能为空")
        # 2. 查重（用仓储接口，不知道底层是啥）
        if await self.user_repository.exists_by_username(command.username):
            raise DuplicateError("用户名已存在")
        # 3. 构造实体（领域规则自动校验）
        user = User(id=None, username=command.username, password=command.password)
        # 4. 保存（接口调用）
        saved_user = await self.user_repository.save(user)
        return RegisterUserResult(
            user_id=saved_user.id.value if saved_user.id else 0,
            username=saved_user.username,
        )
```

**③ 查询 + 处理器**（`queries/get_orders.py`）——读操作同样走"查询对象 → 处理器"：

```python
@dataclass
class GetOrdersQuery:
    """获取用户订单查询"""
    user_id: int
    limit: Optional[int] = 10
    offset: Optional[int] = 0

@dataclass
class OrderDTO:
    """订单数据传输对象"""
    id: int; order_number: str; total_amount: float
    status: str; created_at: str; updated_at: str

@dataclass
class GetOrdersResult:
    orders: List[OrderDTO]
    total: int

class GetOrdersHandler:
    """订单查询处理器（演示版用模拟数据，工程版应注入订单仓储）"""
    async def handle(self, query: GetOrdersQuery) -> GetOrdersResult:
        if query.user_id <= 0:
            raise ValidationError("用户ID必须大于0")   # 走统一业务异常出口，别抛裸 ValueError
        # ... 校验 limit/offset → 模拟数据 → 分页切片 → 返回
```

**命令/查询模式（CQRS 雏形）的价值**：写操作（Command）与读操作（Query）分开建模，每个业务动作对应一个清晰的数据包 + 处理器，**测试时直接构造 Command 调 Handler，完全不用起 HTTP**。
@@trap 处理器别返回 ORM 对象
Handler 的返回值必须是领域/应用层类型（`RegisterUserResult`、`OrderDTO`），**绝不返回 `UserORM`**——ORM 是基础设施层的东西，泄漏出去你就没法换数据库了。这也是 Mapper 和 DTO 存在的意义。

@@point ⑨ 接口层与组装：依赖注入容器、路由、main.py
@@need 要解决什么
最后一步是"接线"：把接口层和所有下层接起来——路由怎么拿到 Handler？Handler 怎么拿到仓储？应用怎么启动数据库？这些组装工作集中在**依赖注入容器**和 **main.py** 两处，保持"各处只认接口"的干净。
@@idea 核心思路
**① 依赖注入容器**（`interface/dependency.py`）——全部组装在这里：路由只 `Depends` 工厂函数，不碰实现细节：

```python
from fastapi import Depends
from app.domain.user.repository import UserRepository
from app.infrastructure.repository.user_impl import UserRepositoryImpl
from app.application.user.commands.register_user import RegisterUserHandler
from app.application.user.commands.login_user import LoginUserHandler
from app.application.user.queries.get_orders import GetOrdersHandler

def get_user_repository() -> UserRepository:
    """给仓储：目前返回 ORM 实现，换实现只改这里"""
    return UserRepositoryImpl()

def get_register_user_handler(
        user_repository: UserRepository = Depends(get_user_repository),
) -> RegisterUserHandler:
    """给注册处理器：自动注入仓储"""
    return RegisterUserHandler(user_repository)

def get_login_user_handler(
        user_repository: UserRepository = Depends(get_user_repository),
) -> LoginUserHandler:
    return LoginUserHandler(user_repository)

def get_get_orders_handler() -> GetOrdersHandler:
    return GetOrdersHandler()
```

**② 路由**（`interface/api/v1/auth_router.py`）——只做"翻译"：HTTP 请求 ⇄ 命令/结果，异常统一转 HTTP：

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.application.common.exception import DomainException
from app.interface.dependency import get_register_user_handler, get_login_user_handler
from app.application.user.commands.register_user import (
    RegisterUserCommand, RegisterUserHandler)

router = APIRouter(prefix="/auth", tags=["认证"])

class RegisterRequest(BaseModel):
    username: str
    password: str

class RegisterResponse(BaseModel):
    user_id: int
    username: str
    message: str

@router.post("/register", response_model=RegisterResponse,
             status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    handler: RegisterUserHandler = Depends(get_register_user_handler),  # 容器注入
):
    try:
        command = RegisterUserCommand(
            username=request.username, password=request.password)
        result = await handler.handle(command)
        return RegisterResponse(
            user_id=result.user_id, username=result.username,
            message="用户注册成功")
    except DomainException as e:                    # 业务异常统一出口
        raise HTTPException(status_code=400, detail=e.message)
    except Exception:                               # 兜底：不泄露内部细节
        raise HTTPException(status_code=500, detail="服务器内部错误")
```

**③ 应用入口 `main.py`**——生命周期管理 + 组装：

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from tortoise import Tortoise
from config.settngs import settings
from app.interface.api.v1.auth_router import router as auth_router
from app.interface.api.v1.order_router import router as order_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动连库、关闭断连"""
    await Tortoise.init(
        db_url=settings.db_url,
        modules={"models": ["app.infrastructure.database.orm_models"]},
    )
    await Tortoise.generate_schemas()   # 开发期自动建表；生产用 aerich 迁移
    yield
    await Tortoise.close_connections()

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version,
                  description="一个基于FastAPI的DDD示例应用", lifespan=lifespan)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(order_router, prefix="/api/v1")
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=settings.debug)
```

**④ 配置 `config/settngs.py`**——用 pydantic-settings 从 `.env` 读配置（名字虽拼成 settngs，用法就是 Settings）：

```python
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "FastAPI DDD"
    app_version: str = "0.1.0"
    debug: bool = True
    secret_key: str = "your-secret-key"
    db_url: str = "sqlite://./data/test.db"     # 换 PostgreSQL 只改这里+装驱动

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
```

**启动与体验**（工程根目录）：

```cmd
> uv run uvicorn main:app --reload     # 或 python main.py
# 打开 http://127.0.0.1:8000/docs
# 1. POST /api/v1/auth/register 注册一个用户
# 2. POST /api/v1/auth/login 登录
# 3. GET /api/v1/orders/?user_id=1 查订单（演示数据）
```

**整体回看这个工程，你发现了什么？** 从浏览器到数据库，数据形态被 Mapper 转了两次（ORM → 实体 → DTO），每一层只认识自己的邻居——**这就是分层架构的全部秘密：让每一层都有明确的边界和替换的自由。**
@@trap 组装层的三个雷
| 雷 | 后果 / 怎么办 |
| 路由里直接 `UserRepositoryImpl()` | 违反依赖倒置，测试没法替换仓储。一律走 `Depends(get_xxx)` |
| `lifespan` 没注册到 `FastAPI(lifespan=lifespan)` | 数据库永不初始化，接口全报"表不存在"。检查 create_app 里的参数 |
| `.env` 改了不生效 | 用 `python config/settngs.py` 自测读取；确认 `.env` 在启动目录、键名与 Settings 字段一致 |

@@summary
这一章你实际拿到的是**一套完整的工程化方法论 + 一个可运行的样板工程**：

| 拿到了什么 | 为什么要紧 |
| **依赖注入（DI）** | 参数、校验、服务由框架注入而非自己 new——换实现只改一处，测试能替换 |
| **三级作用域** | 路径级/路由级/全局级按需保护接口，日志鉴权不再到处复制粘贴 |
| **嵌套与类依赖** | 多层校验链（token→用户）用 Depends 自动组装；带状态的服务用工厂函数注入 |
| **DDD 四层架构** | 接口层收请求、应用层编排、领域层守规则、基础设施层碰数据库，单向依赖不回头 |
| **依赖倒置 + 仓储模式** | domain 定接口、infrastructure 实现，换数据库零波及 |
| **统一异常体系** | 业务异常（AuthError/DuplicateError/ValidationError）在路由统一转 HTTP，错误不再裸奔 |

**项目形态的质变**：第一章的代码是"能跑的程序"；加上 DI + DDD 之后，是"能长大的工程"——可测试、可替换、可并行开发。**这就是企业级智能体系统后端的标准形态。**

@@quiz
1. 依赖注入解决的核心问题是什么？`Depends()` 在路由参数里扮演什么角色？
2. 路径级、路由级、全局级三种依赖作用域分别挂在哪里？记日志一般用哪级？
3. 嵌套依赖的执行顺序是什么？"取当前用户"为什么需要依赖"验 token"？
4. 类依赖为什么用工厂函数注入而不是直接用类？换数据库连接串要改哪里？
5. DDD 四层分别管什么？依赖方向的铁律是什么（用箭头画出来）？
6. 为什么 domain 层要定义 `UserRepository` 接口而不是直接写实现？换数据库时要改动哪些层？
7. 值对象 `UserID` 和实体 `User` 有什么区别？Mapper 的职责是什么？
8. 命令/查询模式（Command/Query）与路由直写业务逻辑相比，友好在哪里？
9. 浏览一次"接口层 → Handler → 仓储 → Mapper → ORM"的请求全链路：哪一层把 HTTP 请求翻译成命令/查询？"用户名不能为空"这种校验在哪两层各查一次？
10. 从"能跑的脚本"到"能长大的工程"，这一章的两个关键武器是什么？什么情况下 DDD 反而是过度设计？

@@links
参考|FastAPI 进阶|#
代码|DI1~DI6 依赖注入演示代码|#
代码|ddd 分层架构示例工程|#
官网|FastAPI 依赖注入官方文档|https://fastapi.tiangolo.com/zh/tutorial/dependencies/
官网|FastAPI 进阶-全局依赖|https://fastapi.tiangolo.com/zh/tutorial/dependencies/global-dependencies/
