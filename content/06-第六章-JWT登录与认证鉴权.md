@@h1 第六章　JWT 登录与认证鉴权
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
平台数据按用户隔离（每个运营看自己的选题与发布记录），如果接口"裸奔"，任何人都能改别人的内容。本章解决：**登录时签发 JWT**（无状态令牌）、**受保护接口校验令牌**（HTTPBearer 依赖注入）、以及**未登录/无权限的优雅报错**。

学完本章，你就能独立回答三个问题：token 是怎么造出来的、怎么验的、前端拿到 token 后怎么用。

@@map 这一章在整个知识库里的位置
上一章：应用启动与测试——服务跑通，无鉴权接口可访问
**本章** ← 你在这里：JWT 登录与认证鉴权——平台加锁
下一章：前端工程连接——Vue3 登录页 + token 存储 + 请求拦截器
再往后：Coze 智能体 → 选题生成 → 文案 → 配图 OSS

@@point ① JWT 原理：三段式令牌
@@need 要解决什么
"无状态认证"为什么能行？JWT 令牌长什么样、谁都能解开验真伪吗？

@@idea 核心思路
JWT（JSON Web Token）= 三段 base64 字符串，用 `.` 分隔：
```
header.payload.signature
```
- **header**：算法声明 `{"alg":"HS256","typ":"JWT"}`。
- **payload**：业务声明，如 `{"sub":"1","iat":1710000000,"exp":1710604800}`——sub=用户id、iat=签发时间、exp=过期时间。
- **signature**：`HMAC-SHA256(header.payload, secret)`——**用服务端 JWT_SECRET 签名**。

两个关键性质：
1. **可验真**：只要 secret 在服务端，任何人都无法伪造签名（篡改 payload 后签名必然对不上）。
2. **无状态**：服务端不存会话，验签通过即放行——所以叫"无状态认证"，适合多实例部署。

本项目用 PyJWT：`jwt.encode(payload, secret, algorithm="HS256")` 签发，`jwt.decode(token, secret, algorithms=["HS256"])` 校验。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| decode 报 "Signature verification failed" | token 被篡改或 secret 不一致（如 .env 被换） |
| decode 报 "Signature has expired" | exp 已过；前端应跳登录页让用户重新登录 |
| 用其它算法（如 RS256）验签 | algorithms 列表必须显式只给 HS256，防算法混淆攻击 |

@@point ② auth.py：登录接口与令牌签发
@@need 要解决什么
用户拿用户名密码来换 token，服务端要"验身份 → 造令牌 → 返回"三步。

@@idea 核心思路
```python
import jwt, time
from fastapi import APIRouter, HTTPException

router = APIRouter()

def _make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_ACCESS_EXPIRE_SECONDS,  # 默认 7 天
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)  # HS256

@router.post("/login")
async def login(username: str, password: str):
    user = await User.filter(username=username).first()
    # 示例实现：密码明文比对
    if not user or user.password != password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = _make_token(user.id)
    return {"code": 200, "message": "登录成功",
            "data": {"token": token, "user": {"id": user.id, "username": user.username}}}
```

要点：
- **payload 用 sub 存用户 id**（JWT 标准字段），iat/exp 用 Unix 时间戳。
- 登录接口是**白名单**——不需要鉴权；其余业务接口统一上锁。
- 这一版为教学清晰用了**明文密码比对**，生产必须换哈希（见下方坑位）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 数据库有用户但登录总失败 | password 比对细节：字段裁剪、空格、转义；或密码字段读的是旧列。先 SELECT 出来对比 |
| 明文密码入库 | 为教学做了显式简化；生产必须 bcrypt/argon2 哈希 + 加盐，密码字段 255 长度就是为此预留 |
| 登录接口也被锁 | 鉴权依赖对 login 例外处理；把鉴权依赖只加在需保护的路由组上，别全局套 |

@@point ③ 校验令牌：HTTPBearer 与依赖注入
@@need 要解决什么
受保护接口怎么"读取并校验"请求里的 token？FastAPI 的依赖注入把这件事做得很干净。

@@idea 核心思路
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

security = HTTPBearer(auto_error=False)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="无效令牌")
```

用法：任何需要登录的接口，把 `user_id: int = Depends(get_current_user_id)` 加进参数列表，FastAPI 自动完成"取 Bearer 头 → 验签 → 取 sub"三步，业务代码直接享受 user_id。

**auto_error=False** 是关键：不自动报错，把"无 token"的判定交给我们的统一 401/403 语义——未登录 401，令牌无效/过期 403（或按团队约定反着用也行，前后端必须一致）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 不带 token 请求报 500 而不是 401 | auto_error=True 时框架直接抛错没走自定义分支；设 False 交给自己处理 |
| Authorization 头格式少写了 "Bearer " | 标准格式 `Authorization: Bearer <token>`；少前缀 HTTPBearer 解析不到 |
| 过期与无效混为一谈 | 先捕 ExpiredSignatureError（401 提示重新登录），再捕 InvalidTokenError（403）——前端体验完全不同 |

@@point ④ 依赖注入的两种挂法：全局 vs 单接口
@@need 要解决什么
鉴权依赖怎么挂？挂全局（整组路由都锁）还是逐个接口挂？本项目的取舍是什么？

@@idea 核心思路
两种挂法各有场景：
1. **单接口挂**（本项目主流）：业务函数签名加 `user_id: int = Depends(get_current_user_id)`。适合"大部分接口要锁、少数白名单"。
2. **整组挂**：`router = APIRouter(dependencies=[Depends(auth)])` 或全局 `app.include_router(x, dependencies=[...])`。适合整个模块都私有。

项目实际节奏：**登录/login 与测试接口不锁，内容生成类接口全锁**——用单接口写法逐个加依赖，清晰且好调。白名单接口（login）绝不能挂 `Depends(get_current_user_id)`，否则自己都登不进来。

@@point ⑤ 401/403 语义约定：谁说"没登录"，谁说"没权限"
@@need 要解决什么
前端要根据不同错误做不同动作（跳登录页 vs 提示无权限），后端语义必须稳定。

@@idea 核心思路
本项目约定（前后端一致）：
- **HTTP 401** = 未登录 / 登录已过期 → 前端清 token 跳登录页。
- **HTTP 403** = 令牌无效 / 无权限 → 前端提示"请重新登录"或"无权访问"。
- 业务参数错误用 **400**，服务端异常用 **500**（都包进 code/message 三件套）。

前端 request.js 拦截器按 HTTP 状态码 + body.code 双信号分支——状态码定"会话层"，业务码定"业务层"，两不混。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 后端抛 401 但前端 axios 拦截器只读 body.code | 401 时响应体可能被代理/网关改写；前后端对"状态码优先还是 code 优先"要达成一致源码级约定 |
| 过期 token 反复请求还 401 | 防抖处理：拿到 401 后清除 token 并只跳一次登录，避免连环请求 |

@@point ⑥ 前端怎么用 token：Bearer 头 + 拦截器（预告）
@@need 要解决什么
本章解决后端签发与校验，但 token 最终要在前端"存下来、带上、过期即登出"。先看全貌，下章细拆。

@@idea 核心思路
前端三板斧：
1. **登录后存 token**：`setCookie('accessToken', token, 7)`——cookie 是前端持久化的落点。
2. **请求自动带**：axios 请求拦截器读 cookie，拼 `Authorization: Bearer ${token}` 头，业务代码无感。
3. **失败自动登出**：响应拦截器遇 401/403，清 cookie、跳 /login。

这套模式让"后端 JWT"与"前端体验"接上：**用户只感知"登录了 / 过期了"，token 的携带与校验收在两端中间件里**。

@@point ⑦ 安全加固清单（生产必看）
@@need 要解决什么
教学版能跑即可，但上线前这些洞必须补——列个清单，逐个说明为什么。

@@idea 核心思路
| 问题 | 现状(示例版) | 生产要求 |
|---|---|---|
| 密码存储 | 明文比对 | bcrypt/argon2 哈希 + 每用户盐 |
| JWT_SECRET | 明文在 .env、示例值 | 32+ 随机字节、环境变量注入，永不入库 |
| 过期时长 | 7 天 | 按产品定（如 2h + refresh token 轮换） |
| CORS 来源 | "*" | 精确到前端域名 |
| 登录接口限流 | 无 | 失败次数锁定/验证码防爆破 |
| token 泄露 | 无吊销机制 | 引入黑名单或缩短过期时间 |

认知：**鉴权是"体系"不是"一个函数"**——从库表设计（密码列宽）到中间件（拦截器）到运维（secret 管理）是一条链，任何一环裸奔都白搭。

@@summary 这一章你学到了什么
- JWT 三段式：header.payload.signature，HS256 + 服务端 secret 保证不可伪造
- 签发：payload 用 sub/iat/exp（Unix 秒），PyJWT encode/decode
- 登录流程：查用户 → 比对密码 → _make_token → 返回 token；登录接口白名单
- 校验：HTTPBearer(auto_error=False) + Depends 注入，业务直接拿 user_id
- 错误分层：401 未登录/过期，403 令牌无效/无权限，前端分动作响应
- 挂法：单接口 Depends 逐个锁为主，白名单（login）绝不挂鉴权
- 生产加固：哈希密码、强 secret、限流、精确 CORS、token 吊销
- 实操拆 token：sub/iat/exp 当场可见；jwt.io 或 pyjwt decode 验证签名与过期

@@quiz
1. JWT 的 signature 用什么保证不可伪造？
   A. 用户密码　　B. 服务端 JWT_SECRET + HS256　　C. 数据库　　D. 前端 cookie
2. JWT payload 中 exp 字段的作用是？
   A. 标识用户　　B. 令牌过期时间（Unix 秒）　　C. 签名算法　　D. 用户头像
3. HTTPBearer 参数 auto_error=False 的意义是？
   A. 关闭校验　　B. 不自动抛错，交给自定义 401/403 逻辑　　C. 允许无 token　　D. 自动生成 token
4. login 接口为什么不能挂鉴权依赖？
   A. 效率低　　B. 它本身就是白名单，挂了无法登录　　C. 语法不支持　　D. 数据库限制
5. 令牌过期时应该返回？
   A. HTTP 200　　B. HTTP 401（登录已过期）　　C. HTTP 403　　D. HTTP 500
6. 示例中密码比对方式是什么？生产建议是？
   A. 明文比对；哈希+加盐　　B. 哈希比对；明文　　C. AES 加密；base64　　D. 不作比对
7. 前端请求如何携带 token？
   A. URL 参数　　B. Authorization: Bearer <token> 头　　C. Cookie 无头　　D. 请求体

@@point ⑧ 实操：现场拆解一个 JWT
@@need 要解决什么
令牌理论背了一堆，不如亲手拆一个——眼见为实，paylaod 长什么样、过期时间在哪、为什么改一个字符就验签失败。

@@idea 核心思路
登录拿到 token 后，最直观的验证姿势是去 **jwt.io**（调试器）或本地 Python 拆解：
```python
import jwt
# token 换成你登录接口实际返回的 JWT
payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
print(payload)   # {'sub': '1', 'iat': 1710..., 'exp': 1710..., ...}
```
- **sub** 就是当前用户 id——后端依赖注入取的就是它；
- **exp** 用 Unix 秒表示，超时时刻转成可读时间就知道"7 天后几点过期"；
- 把 token 随便改一个字符再 decode → 立刻报签名失败——这就是"不可篡改"的直观证据。

实战价值：以后遇到"登录了但请求还是 401"，用这个方法把 token 拆开看 exp 是否已过、sub 是否为当前用户——两分钟定位是"令牌问题"还是"业务问题"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 拆开 payload 看到 sub 是字符串"1" | 后端签发时 str(user_id)；比对/使用时记得 int() 转换 |
| jwt.io 用 secret 验签总是失败 | 有些 JWT 用非对称算法（RS256），需公钥而非 secret；本项目是 HS256 对称密钥 |
| 拆开 token 内容有敏感信息 | JWT payload 只 base64 编码**不加密**——别往 payload 放密码等敏感数据 |

@@links
参考|智能运营平台.pdf|#
官方|PyJWT 文档|https://pyjwt.readthedocs.io/
官方|FastAPI Security 教程|https://fastapi.tiangolo.com/tutorial/security/