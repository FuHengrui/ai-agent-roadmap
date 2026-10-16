@@h1 第十一章　A2A 协议：让不同框架的 Agent 互相协作
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★★

@@why 这一章在解决什么问题
第十章的多 Agent 协作（Supervisor 模式）有个硬伤：**所有 Agent 都在同一个进程里**，无法跨框架、跨服务器协作。但真实企业是异构的——客服 Agent 用 LangGraph 写的、订单 Agent 跑在 Salesforce 上、支付 Agent 是 PayPal 服务……它们之间怎么通信？

A2A（Agent-to-Agent Protocol，Google 于 2025 年 4 月发布）标准化了 Agent 之间的通信——不管用什么框架、部署在哪台服务器，Agent 都能发现彼此、派发任务、传回结果。这是 Agent 生态"互联互通"的协议基础。

@@map 这一章在整个知识库里的位置
上一章：Agent 实战与 LangSmith——单进程内多 Agent 协作（Supervisor）
**本章** ← 你在这里：A2A 协议——跨框架、跨服务器的 Agent 协作
下一章：Agent Skills 技能系统——Agent 的可复用技能包
再往后：无——阶段 8 收尾

@@point ① 为什么需要 A2A：跨进程协作的鸿沟
@@need 要解决什么
Supervisor 模式解决了"进程内分工"，解决不了"跨系统协作"。企业级场景里 Agent 分散在不同平台、不同技术栈——如何编排它们？

@@idea 核心思路
企业级退款场景（真实异构环境）：

```
客服 Agent（LangGraph 开发）→ 接收请求
订单 Agent（Salesforce 平台）→ 查询订单
支付 Agent（PayPal 服务）   → 处理退款
通知 Agent（企业微信）      → 发送通知
```

不同框架、不同服务器上的 Agent 无法直接通信——这就是 A2A 解决的问题：**标准化 Agent 之间的通信**。

与第十章对比：
- LangGraph 内部多 Agent：同进程、同框架，Supervisor 直接路由 ✅
- A2A：跨框架、跨服务器、跨组织，需要一个统一协议才能协作 ❌→✅

类比：Supervisor = 公司内部部门协作（同一栋楼）；A2A = 公司与公司的商务协作（不同楼、不同文化，靠标准合同协议对接）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 A2A 会替代 MCP | 两者互补：MCP 管 Agent↔工具，A2A 管 Agent↔Agent |
| 同进程多 Agent 也用 A2A | 进程内用 LangGraph 编排即可，A2A 专治跨进程/跨框架 |

@@point ② 三大核心对象：Agent Card / Task / Artifact
@@need 要解决什么
Agent 之间通信，最少需要哪几样东西？"你是谁能干什么"、"这次任务是什么"、"干完的结果在哪"。

@@idea 核心思路
A2A 三大核心对象：

| 对象 | 作用 | 类比 |
|---|---|---|
| Agent Card | 描述 Agent 的身份、能力、接口 | 餐厅招牌（菜单+地址） |
| Task | Agent 之间交换的工作单元 | 一笔订单（有状态追踪） |
| Artifact | Task 执行完成后的输出结果 | 外卖食物（最终交付物） |

- **Agent Card**：像"名片+菜单"——name、description、version、capabilities（能力）、skills（技能列表）、supported_interfaces（接口地址）。Client 先读 Card，才知道对方能干什么、怎么调
- **Task**：一个可追踪状态的工作单元（请求派发出去，全程有状态）
- **Artifact**：Task 的产出物（文本、文件、结构化数据）

三者串联：**读 Card 发现能力 → 建 Task 派发工作 → 收 Artifact 拿结果**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 把 Artifact 和 Task 混为一谈 | Task 是执行单元（状态机），Artifact 是执行完的产出对象 |
| Agent Card 描述太简单，对方不会调用 | Card 要写清能力、输入/输出模式，是别的 Agent 认识你的名片 |

@@point ③ Task 生命周期：六种状态走完全程
@@need 要解决什么
Task 不是"发出去就完了"——它要经历创建、进行、成功/失败/取消/拒绝。状态机不搞清楚，客户端无法判断任务结果。

@@idea 核心思路
TaskState 六种状态：

| 状态 | 含义 | 类型 |
|---|---|---|
| TASK_STATE_SUBMITTED (1) | 任务已提交 | 中间态 |
| TASK_STATE_WORKING (2) | 执行中 | 中间态 |
| TASK_STATE_COMPLETED (3) | 成功完成，产出 Artifact | 终态 |
| TASK_STATE_FAILED (4) | 执行失败 | 终态 |
| TASK_STATE_CANCELED (5) | 被客户端取消 | 终态 |
| TASK_STATE_REJECTED (7) | 被服务端拒绝 | 终态 |

提示：TaskState 是 protobuf 枚举，打印显示数字（1、2、3…），用 `TaskState.Name(state)` 转为可读名称。

客户端流程：创建任务 → 轮询/等待状态更新 → 到终态后取 Artifact。A2A 支持 **status_update / artifact_update 事件流**实时通知状态与产出，配合流式调用使用。

类比：快递状态——已下单（SUBMITTED）→ 运输中（WORKING）→ 已签收（COMPLETED）/ 拒收（REJECTED）/ 丢件（FAILED）。

@@point ④ 快速上手：Echo Agent（Server + Client 两端）
@@need 要解决什么
A2A 长什么样？先跑通一个"回声 Agent"（你发什么它回什么），走通发现→建任务→收结果全流程。

@@idea 核心思路
**Server 端**（Starlette + a2a SDK 拼装）：

```python
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentInterface

agent_card = AgentCard(
    name="Echo Agent",
    description="原样返回用户输入",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(protocol_binding="JSONRPC",
                                         url="http://localhost:9999")],
    skills=[AgentSkill(id="echo", name="回声", description="原样返回输入")],
)
# create_agent_card_routes + create_jsonrpc_routes 挂到 Starlette app
# 启动：uvicorn + host=127.0.0.1 port=9999
```

**Client 端**（三步走）：

```python
import httpx
from a2a.client import A2ACardResolver, ClientFactory

async with httpx.AsyncClient() as httpx_client:
    # ① 发现 Agent（读取 Agent Card）
    card = await A2ACardResolver(httpx_client=httpx_client,
                                 base_url="http://localhost:9999").get_agent_card()
    print(f"发现 Agent: {card.name}")

    # ② 创建 Client + 发送消息（构造 SendMessageRequest）
    client = await ClientFactory().create_client(card)
    # ③ 接收结果（非流式：SDK 聚合为单个 task 响应，artifact 在 task.artifacts 里）
```

核心流程：**A2ACardResolver 发现 Agent → ClientFactory 创建客户端 → send_message 派发任务 → 收 task.artifacts**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| Server 地址写 localhost，远程 Client 连不上 | 跨机器部署要暴露可访问的 host 与端口 |
| Client 先行调用但 Server 没启动 | Client 连接依赖 Server 在线，先起服务再调客户端 |

@@point ⑤ 多技能 Agent：退款 + 查询（真实业务版）
@@need 要解决什么
Echo 太玩具。真实 Agent 需要多个技能（退款处理 + 退款查询），还要支持流式和非流式两种调用——怎么做？

@@idea 核心思路
在极简骨架上加三件事：

1. **Server 端加入真实业务逻辑**（退款：关键词匹配模拟退与不退；查询：按订单号返回状态）
2. **Agent Card 定义多个技能**：
```python
skills=[
    AgentSkill(id="refund",  name="退款处理", description="处理退款请求"),
    AgentSkill(id="query",   name="退款查询", description="查询退款状态"),
]
```
3. **Client 端演示两种调用方式**：

| 方式 | 行为 | 适用 |
|---|---|---|
| 非流式 | send_message 聚合，结果统一在 task.artifacts 返回 | 简单同步任务 |
| 流式 | 通过 task/status_update、artifact_update 事件流实时拿中间产出 | 长任务、边算边出 |

要点：**技能（AgentSkill）是 Card 的核心扩展点**——技能越多，Agent 能力越丰富，Client 按技能描述决定"派单给谁"。Server 按请求里的 skill id 路由到对应业务逻辑。

类比：餐厅菜单（Agent Card）列了"招牌菜+家常菜"（多个技能），客人（Client）按菜名点单（skill id），后厨（Server）分灶执行。

@@point ⑥ 集成：LangGraph Agent 调用 A2A Client
@@need 要解决什么
我自己的 Agent 是 LangGraph 写的，怎么让它去"指挥"一个 A2A 退款 Agent？把 A2A 客户端塞进 Agent 的工具里。

@@idea 核心思路
把 A2A 调用封装成普通工具，LangGraph Agent 就能像用本地工具一样调用外部 A2A Agent：

```python
@tool
def call_refund_agent(amount: float, reason: str) -> str:
    """向退款 Agent 发起退款请求"""
    # ① 用 A2ACardResolver 发现退款 Agent
    card = await A2ACardResolver(httpx_client, base_url="http://xxx/").get_agent_card()
    # ② 创建 A2A Client
    client = await ClientFactory().create_client(card)
    # ③ 发送消息 → 收集 Artifact → 解析返回
    return parse_artifacts(await client.send_message(...))
```

集成要点：
- **工具化封装**：A2A 调用 = 一个 @tool，Agent 在需要时自动"派单"给外部 Agent
- 配合 LangGraph 的 Supervisor / ToolNode 机制，形成"进程内编排 + 跨进程协议"的混合架构
- A2A 的"找 Agent"能力放 Agent Card 发现层：A2ACardResolver → 按 URL 发现 → 拿到能力清单

类比：LangGraph Agent = 城市调度中心；外部 A2A Agent = 合作的外包公司。调度中心不直接管理外包员工，而是通过"标准合同"（A2A）发包、收件。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| agent 节点内直接调 A2A client 卡死整个图 | 网络调用必须设超时与重试，避免阻塞执行 |
| 只等 completed 状态 | 任务六态含 failed/canceled 等终态，轮询处理要全 |

@@point ⑦ 反向集成：把 LangGraph Agent 包装成 A2A Server
@@need 要解决什么
反过来：我的 LangGraph Agent 能力很强（有记忆有工具），想把它"发布"出去，让外部 Agent 也能调用我——怎么把 Agent 变成 A2A Server？

@@idea 核心思路
包装四步：

```python
from a2a.server.agent_executor import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentInterface

# 1. 定义执行器：内部调用 LangGraph Agent
class MyExecutor(AgentExecutor):
    async def execute(self, request, request_context, event_queue):
        # 调用 LangGraph app.invoke(...) 获得结果
        # 包装成 A2A Task/Artifact 事件发回
        yield TaskStatusUpdateEvent(...)   # 状态更新
        yield TaskArtifactUpdateEvent(...) # 产出 Artifact

# 2. 声明 Agent Card（把 Agent 的"名片"亮出来）
agent_card = AgentCard(
    name="My LangGraph Agent",
    skills=[AgentSkill(id="customer-service", name="客服", description="...")],
    capabilities=AgentCapabilities(streaming=True),
)
# 3. DefaultRequestHandler 接住 JSONRPC 请求
handler = DefaultRequestHandler(executor=MyExecutor(...))
# 4. create_agent_card_routes + create_jsonrpc_routes 挂到 Starlette
#    对外暴露 Agent Card 与 JSONRPC 端点 → 完成"Agent 服务化"
```

适配器三件套：**AgentExecutor（执行器）+ AgentCard（名片）+ DefaultRequestHandler（协议处理器）**。写完这四项，你的 LangGraph Agent 就是一个标准 A2A Server，任何框架的 Agent 客户端都能调用。

类比：把你的团队（LangGraph Agent）包装成"外包公司"——有营业执照（Agent Card）、有对接人（DefaultRequestHandler）、按行业标准接单交付（JSONRPC + Task/Artifact）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 把 LangGraph 图直接当 A2A 工具用 | 需封装成 A2A Server，实现 send/reply 生命周期 |
| 内存版 TaskStore 重启任务全丢 | 生产用持久化 TaskStore（PostgreSQL/SQLite） |

@@point ⑧ A2A 协议栈全景与选型建议
@@need 要解决什么
学了七招，最后串一遍全景：A2A 和 MCP 是什么关系？什么时候用 A2A？

@@idea 核心思路
**A2A 协议栈全景**：
- 传输层：HTTP（JSON-RPC 2.0 协议绑定），Starlette/uvicorn 承载
- 发现层：Agent Card（URL + 卡片描述能力）
- 任务层：Task 生命周期 + 事件流（status_update / artifact_update）
- SDK：`a2a-sdk`（官方 Python SDK，GitHub: a2aproject/a2a-python，`[http-server]` extra 含 Starlette 依赖）
- 集成层：AgentExecutor / RequestHandler / A2ACardResolver / ClientFactory

**MCP vs A2A（分工不同，不是二选一）**：
- **MCP**：Agent ↔ 工具/数据源 的协议（"手指够到外部系统"）
- **A2A**：Agent ↔ Agent 的协议（"不同 Agent 之间协作"）
- 组合使用：LangGraph Agent 通过 MCP 调数据库，同时通过 A2A 把任务派给退款 Agent——一个系统里两者并行不悖

**选型建议**：需要让 Agent 调用外部工具/数据 → MCP；需要让不同框架的完整 Agent 互相派活 → A2A；两者都涉及（企业多系统编排）→ 混用。

@@summary 这一章你学到了什么
- 理解 A2A 的定位：跨框架、跨服务器的 Agent 通信标准（Google 2025 年 4 月发布）
- 掌握三大核心对象：Agent Card（名片+菜单）/ Task（工作单元）/ Artifact（产出物）
- 掌握 Task 六状态生命周期：SUBMITTED → WORKING → 终态（COMPLETED / FAILED / CANCELED / REJECTED）
- 会跑通 Echo Agent：Server 端拼 Card+routes，Client 端 Resolver 发现 → ClientFactory 建客户端 → send_message 收 Artifact
- 会定义多技能 Agent：AgentSkill 扩展能力，非流式聚合 vs 流式事件更新
- 会双向集成：LangGraph 用 A2A 工具调用外部 Agent；把 LangGraph Agent 包装成 A2A Server（AgentExecutor + Card + Handler）
- 分得清 MCP 与 A2A 分工：工具连接用 MCP，Agent 协作用 A2A，企业多系统编排两者混用

下一章：Agent Skills 技能系统——给 Agent 配"技能包"：SKILL.md 结构、frontmatter 规范、scripts/assets/references 组织，以及"每个人都能开发自己的技能"的实践案例。

@@quiz
1. A2A 协议三大核心对象是？
   A. Agent Card / Task / Artifact　　B. Server / Client / Host　　C. Token / Prompt / Model　　D. 请求 / 响应 / 日志
2. Agent Card 的作用是？
   A. 存储任务结果　　B. 描述 Agent 的身份、能力、接口　　C. 执行计算　　D. 管理数据库
3. Task 的终态不包括哪个？
   A. COMPLETED　　B. WORKING　　C. FAILED　　D. REJECTED
4. A2A 中"客户发现对方 Agent 能力"靠的是？
   A. A2ACardResolver 读取 Agent Card　　B. 随机猜测　　C. 直接调用　　D. 配置文件
5. 非流式调用与流式调用的区别是？
   A. 一个加密一个不加密　　B. 非流式聚合后返回 artifact 在 task.artifacts；流式通过事件流实时拿中间产出　　C. 一个快一个慢　　D. 无区别
6. 想把 LangGraph Agent 变成 A2A Server，需要的适配器三件套是？
   A. AgentExecutor + AgentCard + DefaultRequestHandler　　B. LLM + Tools + Memory　　C. HTTP + JSON + XML　　D. 不需要适配
7. MCP 与 A2A 的分工是？
   A. 完全一样　　B. MCP 连接 Agent与工具/数据，A2A 连接 Agent与Agent　　C. A2A 已取代 MCP　　D. 与工具无关

@@links
讲义|12_LLM框架实战_A2A.pdf|#
官方|A2A 协议文档|https://a2a-protocol.org/
GitHub|a2a-python SDK|https://github.com/a2aproject/a2a-python
教程|A2A 快速上手|https://a2a-protocol.org/latest/quickstart/