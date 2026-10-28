@@h1 第八章　MCP 协议与企业级工具开发
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
前六章的工具都是"自家工具"——用 @tool 写在 Agent 项目内部，跟框架耦合死了。换个应用（比如从 LangGraph 换到 Claude Desktop），工具全废，得重写。这就是"工具与框架耦合，无法跨 Agent 复用"的痛点。

MCP（Model Context Protocol，Anthropic 提出的开放协议）把工具变成**标准的独立服务**：Agent（Client）通过统一协议连接外部工具服务（Server），一套工具到处用。LangGraph、Claude、OpenAI 都能连同一个 MCP Server。

结论先行：**MCP 不是要替代 @tool**。简单工具用 @tool 就够了；需要跨框架共享、独立部署扩展的工具，才上 MCP。这章的判断标准，你学完就能掌握。

@@prep 开始之前
要装 fastmcp 和 MCP 适配器，模型 Key 沿用上一章；Server 和 Client 各起一个进程。

@@goal 学到这儿就够了
能说清 MCP 三端各是什么、三种通信怎么选，能把工具包成 Server 再让 Agent 调通，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：LangGraph 记忆系统——Agent 有记忆了
**本章** ← 你在这里：MCP 协议与企业级工具开发——Agent 连接外部系统
下一章：Human-in-the-Loop——人机协作暂停/恢复
再往后：Agent 实战与 LangSmith → A2A → Skills

@@point ① 为什么要 MCP：工具与框架解耦
@@need 要解决什么
@tool 写死的工具只能在当前 Agent 框架里用：OpenAI Agent 的工具只能在 OpenAI 中用；LangGraph 的工具换平台就废。重复造轮子、无法共享。

@@idea 核心思路
MCP 是**工具界的 USB 标准**：

| 类比 | 现实 |
|---|---|
| MCP Server = USB 设备（键盘、鼠标、U盘） | 工具服务：文件系统、数据库、邮件、GitHub |
| MCP Client = 电脑上的 USB 接口 | 任何支持 MCP 的 Agent/应用 |
| USB 协议 = 设备通用标准 | MCP 协议规范 |

好处：
- **一套工具，处处可用**：LangGraph、Claude、OpenAI 等客户端都可连接同一个 MCP Server
- **生态共享**：社区已有大量现成 Server（文件系统、数据库、GitHub、Slack）
- **独立部署扩展**：工具独立服务，后端升级/扩容不影响 Agent

核心理念："一次编写，到处使用"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 MCP 会替代 @tool，把简单工具全迁移 | 两者互补：简单工具 @tool 更轻量，跨框架共享才上 MCP |
| 本地能跑，部署到云服务器就连不上 | stdio 模式依赖子进程，Web 环境要用 HTTP 模式独立运行 |

@@point ② MCP 架构：Server / Client / Host
@@need 要解决什么
MCP 里 Server、Client、Host 到底谁是谁？搞不清架构，连不上工具，也不知道代码该放哪。

@@idea 核心思路
三层角色分工：

- **MCP Host**：宿主应用——运行 Agent 的应用环境（如 Claude Desktop、LangGraph Agent 所在应用）
- **MCP Client**：连接器——Host 内负责与 Server 通信的组件（如 MultiServerMCPClient）
- **MCP Server**：服务进程——独立运行、对外提供工具/资源/提示的标准服务

```
Host（宿主应用）
 └─ MCP Client（连接器）── 协议 ──▶ MCP Server（工具服务）
       │                              ├─ Tools 工具（可执行操作）
       │                              ├─ Resources 资源（可读数据）
       │                              └─ Prompts 提示（可复用模板）
```

三方关系：Host 里跑 Agent → 通过 Client 发协议请求 → Server 提供"工具/资源/提示"三类能力。Server 是独立进程，Client 是连接它的"插头"。

类比：电脑（Host）→ USB 接口（Client）→ 键盘（Server）。键盘自己供电、自己工作，插到哪台电脑都能用。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 分不清 Host 和 Client，代码不知道放哪 | Host 是宿主应用、Client 是连接器、Server 独立进程，三层各司其职 |
| 以为 MCP Server 是 Agent 代码的一部分 | Server 是独立服务进程，可独立部署独立升级 |

@@point ③ MCP 三种通信机制：stdio / SSE / Streamable HTTP
@@need 要解决什么
进展到什么模式？什么时候用哪种？选错传输模式，本地能跑远程挂、远程能跑本地启动不了。

@@idea 核心思路
三种传输模式对照：

| 模式 | 通信方式 | 适用场景 |
|---|---|---|
| stdio | 标准输入/输出 | 本地开发，Client 启动 Server 子进程 |
| SSE | HTTP 长连接（Server-Sent Events），服务端 text/event-stream 持续推送 | 远程 Server，旧版兼容 |
| Streamable HTTP（推荐） | HTTP 流式传输 | 远程 Server，2025 年推荐方式 |

要点：
- **stdio**：MCP 的 stdio 模式会在调用工具时**启动新的子进程**——在 Web 服务（远程部署）场景下不可用。只适合本地开发
- **SSE**：基于 HTTP 长连接，服务端持续推送，旧版方案，**新项目不推荐**
- **Streamable HTTP（推荐）**：HTTP 流式传输，远程部署主流，`mcp.run(transport="streamable-http")` 一行切到 HTTP 服务，访问地址形如 `http://localhost:8000/mcp`

```python
# 推荐：Streamable HTTP
mcp.run(transport="streamable-http")   # http://localhost:8000/mcp
# 旧版兼容
# mcp.run(transport="sse")
```

类比：stdio = 临时工直接跟你对话（本地）；SSE = 老式传呼机（能用但过时）；Streamable HTTP = 现代电话线（远程主流）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 新项目还在用 SSE 老方案 | SSE 是旧版兼容，新项目推荐 Streamable HTTP |
| 本地 stdio 正常、远程部署就挂 | stdio 调用时启动子进程，远程环境不可用，必须切 HTTP |

@@point ④ FastMCP：3 步创建自己的 MCP Server
@@need 要解决什么
自己写一个 MCP Server 要处理协议、消息格式、序列化……太复杂。有没有"像写普通函数一样"写 MCP 服务的方式？

@@idea 核心思路
**FastMCP** 是基于 Python 的高级框架，用装饰器就能把普通函数变成 MCP 工具：

```python
from fastmcp import FastMCP

# 1. 创建 Server 实例
mcp = FastMCP("my-tools")

# 2. 用 @mcp.tool() 注册工具
@mcp.tool()
def add(a: int, b: int) -> int:
    """两数相加"""          # docstring 自动成为工具描述
    return a + b

# 3. 运行（默认 stdio；远程用 streamable-http）
if __name__ == "__main__":
    mcp.run()
```

**@mcp.tool() 的作用**：把 Python 函数注册为 MCP 工具，函数名和 docstring 自动成为工具的名称与描述，Client 可以发现并调用。也支持 `@mcp.resource()`（数据资源）与 `@mcp.prompt()`（提示模板）。

关键点：写完 Server 代码，`mcp.run()` 之后它就是一个**独立的工具服务进程**，任何支持 MCP 的客户端都能连。

类比：FastMCP = 给普通 Python 函数"插上 USB"，写完即插即用。

@@point ⑤ 开发 MCP 客户端：连接 Server 并调用工具
@@need 要解决什么
Server 有了，客户端怎么连？怎么把 MCP 工具"接回"自己的 Agent？

@@idea 核心思路
通用流程：**创建 Client → 连接 Server → 列出工具 → 调用工具**：

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(command="python", args=["server_chart.py"])
async with stdio_client(server) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()        # 列出 Server 提供的工具
        result = await session.call_tool("add", {"a": 1, "b": 2})  # 调用工具
```

要点：
- `initialize()` 建立会话握手 → `list_tools()` 发现能力 → `call_tool()` 执行
- 学习/实践组合：自己写一个 `server_xxx.py`（服务端）+ 一个客户端脚本（连接调用），先跑通再谈生产

实践案例（企业级三连）：**邮件发送 MCP**（把 send_email 注册为工具）、**数据库查询 MCP**（把 SQL 执行封装成工具）、**面向 Agent 的数据图表工具**（把绘图逻辑封装，Agent 说"画个 8 月销售柱状图"→ 工具出图）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| client 建立连接后不关闭，进程挂起 | 连接是资源，要用 async with 管理生命周期 |
| 工具名凭记忆写，报 tool not found | 先用 list_tools() 核对工具名再调用，别猜 |

@@point ⑥ langchain-mcp-adapters：把 MCP 工具变成 @tool
@@need 要解决什么
LangGraph Agent 不能直接使用 MCP 工具——协议不同，语言不通。还有多个 MCP Server 要同时连，怎么统一管理？

@@idea 核心思路
**langchain-mcp-adapters** 是桥梁：把 MCP Server 的工具**自动转换为 LangChain 的 @tool 格式**，Agent 就能像使用本地工具一样使用 MCP 工具。

```python
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await load_mcp_tools(session)    # MCP 工具 → LangChain @tool 列表
        agent = create_agent(llm, tools)         # 直接给 Agent 用
```

**MultiServerMCPClient**：同时连接多个 Server 的统一入口，按名字区分不同 Server 的工具，自动转换。

类比：MCP Server = 日版电器（110V）；LangGraph Agent = 中国插座（220V）；langchain-mcp-adapters = 电压转换器。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 按旧博客代码写 adapter 报 API 对不上 | langchain-mcp-adapters 随 SDK 迭代，确认与安装版本匹配的示例 |
| 以为 adapter 自动处理鉴权 | MCP Server 的认证仍需自行配置/传递，不是开箱即用 |

@@point ⑦ MCP 在 LangGraph 配置：client 按名注入，tool 递归挂载
@@need 要解决什么
Agent 里工具怎么注入？MCP 的 stdio 子进程、多 Server 命名冲突怎么管理？直接混用会出怪问题。

@@idea 核心思路
标准做法：**Client 按名字注入，tools 递归挂载**：

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "math": {                       # Server 名：math
        "command": "python",
        "args": ["server_math.py"], # stdio 启动配置
        "transport": "stdio",
    },
    "weather": {                    # 第二个 Server
        "url": "http://localhost:8001/mcp",
        "transport": "streamable-http",
    },
})

# ★ MultiServerMCPClient 只支持 async，get_tools() 返回的是**扁平列表**（不是按 server 分的字典）
async def build_agent():
    tools = await client.get_tools()          # 所有 Server 的工具合成一个 list
    # 只要某个 Server 的：await client.get_tools(server_name="math")
    return create_agent(llm, [local_tool, *tools])   # 本地 @tool 可以混用

agent = asyncio.run(build_agent())
```

要点：
- **本地 @tool 与 MCP 工具可以混合使用**——按需挑选，不冲突
- Server 名（math/weather）做命名空间防止工具重名
- 生产注意：**stdio 模式每次调用启动子进程，Web 服务场景换 streamable-http**

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 多个 Server 工具重名互相覆盖 | 多 Server 或与本地 @tool 冲突时，需按工具名去重/重命名 |
| 给 Agent 传了 client 而不是 tool 对象 | tools 参数要传 client 暴露出的工具对象，传 client 本身无效 |

@@point ⑧ 工具选择决策树：@tool 还是 MCP？
@@need 要解决什么
上来就 MCP 会把简单事搞复杂；全用 @tool 又把好架构浪费掉。到底什么时候用哪个？

@@idea 核心思路
决策树：

```
工具逻辑简单，几行代码搞定？ ──是──▶ @tool 本地定义 ✅
        │否
工具需要在多个 Agent/应用间共享？ ──是──▶ MCP Server ✅
        │否
工具有独立的部署和扩展需求？ ──是──▶ MCP Server ✅
        │否
        └──▶ @tool 本地定义
```

判断口诀：
- 工具简单 + 只在本项目用 → **@tool**（快、零成本）
- 跨 Agent/跨框架共享 → **MCP**（一次编写，到处使用）
- 独立部署、独立扩缩容 → **MCP**（工具和 Agent 解耦）

**MCP 的最大优势是生态共享**：需要"现成能力"时优先去社区/官方找现成 MCP Server（文件系统、数据库、GitHub、Slack），比重新实现快得多。

@@summary 这一章你学到了什么
- 理解 MCP 是工具界的 USB 标准：Server/Client/Host 三层架构，工具与框架解耦
- 会对比三种传输：stdio（本地）、SSE（旧版兼容）、Streamable HTTP（远程推荐）
- 会用 FastMCP 三连注册：@mcp.tool() / @mcp.resource() / @mcp.prompt()，docstring 自动成描述
- 会写 MCP 客户端：初始化会话 → list_tools → call_tool 的标准流程
- 会用 langchain-mcp-adapters 把 MCP 工具转换成 LangChain @tool，MultiServerMCPClient 管理多 Server
- 会在 LangGraph 中混合本地 @tool 与 MCP 工具，按 Server 名分组注入
- 掌握决策树：简单内部工具用 @tool，跨框架共享/独立部署用 MCP
- 知道实践三案例：邮件发送、数据库查询、数据图表工具都能封装成 MCP

下一章，把"自动化执行"升级为"人机协作"：Human-in-the-Loop——用 interrupt 让 Agent 在关键时刻暂停等人类审批，用 Command(resume) 恢复执行，构建可靠的审批流。

@@quiz
1. MCP 的三层架构是？
   A. Server/Client/Host　　B. Model/Controller/View　　C. Agent/Tool/API　　D. 前端/后端/数据库
2. 三种传输模式中，2025 年推荐用于远程 Server 的是？
   A. stdio　　B. SSE　　C. Streamable HTTP　　D. WebSocket
3. FastMCP 中 @mcp.tool() 的作用是？
   A. 加速函数执行　　B. 把 Python 函数注册为 MCP 工具，函数名和 docstring 自动成名称描述　　C. 生成测试代码　　D. 加密输出
4. langchain-mcp-adapters 的作用是？
   A. 替代 MCP 协议　　B. 把 MCP 工具自动转换为 LangChain @tool 格式　　C. 加速模型推理　　D. 管理 API 密钥
5. MultiServerMCPClient 的意义是？
   A. 部署多个数据库　　B. 同时连接多个 MCP Server 并按名区分工具　　C. 复制 Agent　　D. 负载均衡
6. 工具简单、只在当前项目内使用的场景，应选？
   A. MCP Server　　B. @tool 本地定义　　C. 两种都强制　　D. 手写 HTTP 接口
7. stdio 传输模式的限制是？
   A. 只能传输文本　　B. 调用工具时会启动新子进程，适合本地不适合 Web 服务　　C. 速度最慢　　D. 不加密

@@links
参考|08_LLM框架实战_MCP.pdf|#
参考|企业级AI模型部署与工具开发实战.pdf|#
官网|MCP 官方文档|https://modelcontextprotocol.io/
中文|FastMCP 教程|https://fastmcp.wiki/zh/getting-started/welcome
官网|langchain-mcp-adapters|https://github.com/langchain-ai/langchain-mcp-adapters