@@h1 第七章　LangGraph 记忆系统：让 Agent 记住你
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
上一章 Agent 会"干活"了，但它是"金鱼脑"——每次对话都是全新的它，什么都记不住。你 10 分钟前告诉它"我叫张三、暗色模式"，10 分钟后它一脸茫然。多轮对话上下文、用户长期偏好，这些数据不保存，Agent 永远只能是"一次性工具"。

本章解决两条记忆线：
- **短期记忆（Checkpointer）**：记录"当前这轮对话聊了什么"——会话隔离、多轮上下文
- **长期记忆（Store）**：记录"你一直以来的信息"——用户画像、偏好，跨会话不丢

再看懂新旧 API 差异，最后升级到 PostgreSQL 生产持久化。

@@prep 开始之前
沿用上一章的 LangGraph 环境；内存版不用额外服务，Postgres 那节再准备 Docker 和数据库。

@@goal 学到这儿就够了
能说清短期记忆和长期记忆各存什么、靠什么隔离，能给 Agent 接上这两种记忆并跨轮记住你，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：LangGraph 工具系统——Agent 会干活了
**本章** ← 你在这里：LangGraph 记忆系统——Agent 能记住了
下一章：MCP 协议——Agent 连外部系统
再往后：人机协作 → 实战与 A2A → Skills

@@point ① 两种记忆类型：Checkpointer vs Store
@@need 要解决什么
"记忆"是个大词，实际场景有两种完全不同的需求：记住这一轮聊到哪了（短会话），和记住你这个人（跨会话）。方案如果选错，要么记不住、要么过度存储。

@@idea 核心思路
LangGraph 用**两套机制**分治：

| 维度 | 短期记忆 Checkpointer | 长期记忆 Store |
|---|---|---|
| 保存内容 | Graph 的完整 State（messages 列表） | 结构化键值对（JSON） |
| 生命周期 | 会话内，结束可清理 | 跨会话持久化 |
| 典型实现 | MemorySaver / PostgresSaver | InMemoryStore / PostgresStore |
| 隔离方式 | thread_id | namespace |
| 适合场景 | 多轮对话上下文 | 用户画像、偏好设置 |

实现类有两档：**内存版**（MemorySaver / InMemoryStore，开发测试用）和 **数据库版**（PostgresSaver / PostgresStore，生产用）。

类比：短期记忆 = 笔记本，记今天的对话，合上就翻篇；长期记忆 = 档案柜，按标签存放关键信息（姓名、地址、偏好），随时可查。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 把 Checkpointer 当长期记忆用 | Checkpointer 保存的是会话图状态快照，跨会话要用 Store |
| 以为加了 checkpointer 就自动"记住所有" | 它只保存 state，不等于自动语义记忆，需自行读写 |

@@point ② 新旧 API 差异：别再学旧版的 RunnableWithMessageHistory
@@need 要解决什么
网上大量旧教程还在教 RunnableWithMessageHistory、ConversationBufferMemory、ConversationSummaryMemory。新手照抄老教程，一步一个坑——这些 API 正在被弃用。

@@idea 核心思路
新旧 API 对照：

| 特性 | 旧版（已弃用） | 新版（推荐） |
|---|---|---|
| 短期记忆 | RunnableWithMessageHistory / ConversationBufferMemory / ConversationSummaryMemory | MemorySaver (Checkpointer) |
| 长期记忆 | 无官方方案 | InMemoryStore / PostgresStore |
| 会话隔离 | session_id | thread_id |
| 依赖 | langchain-core | langgraph |
| 生产持久化 | 需自己实现 | PostgresSaver / PostgresStore |

**新项目一律用 LangGraph 的 Checkpointer + Store**。旧类（RunnableWithMessageHistory、ConversationBufferMemory、ConversationSummaryMemory 等）已逐步弃用。

类比：旧 API = 手动翻本子的老秘书；新 API = 带索引和档案库的现代化系统，一条命令全搞定。

@@point ③ 短期记忆（MemorySaver）：三步接入 Checkpointer
@@need 要解决什么
多轮对话中，第二句就必须"知道"第一句。没有 Checkpointer，每次 invoke 都是独立回合。怎么让图记住对话历史？

@@idea 核心思路
三步配置：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(AgentState)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

# 第一步：创建
memory = MemorySaver()
# 第二步：编译时挂上
app = builder.compile(checkpointer=memory)
# 第三步：每次调用传 thread_id（必传，否则报错）
result = app.invoke({"messages": [("user", "我是张三")]},
                    config={"configurable": {"thread_id": "user-alice"}})
result2 = app.invoke({"messages": [("user", "我叫什么？")]},
                     config={"configurable": {"thread_id": "user-alice"}})
# result2 → AI："张三"
```

**工作原理**：每次 Graph 执行后自动保存完整 State，下次通过相同 thread_id 恢复。**thread_id = 不同的笔记本，互不干扰**——user-alice 和 user-bob 各聊各的。

注意：**MemorySaver 数据在内存，程序重启即丢，仅用于开发测试，生产用 PostgresSaver**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 编译时报错"checkpointer 必须提供" | create_agent/compile 配了记忆回放、没有 checkpointer 直接报错 |
| 不传 thread_id 调用失败 | 挂了 checkpointer 后每次 invoke 必须带 config thread_id |
| 重启后记忆全没了 | MemorySaver 纯内存，生产必须换 PostgresSaver |
| 两个用户串台了 | thread_id 没用"用户维度"区分，要按 user-id 建隔离 |

@@point ④ Checkpointer 保存了什么：完整 State 快照
@@need 要解决什么
MemorySaver 到底存了什么？是只存最后一句，还是全部？搞清楚存储粒度，才能预估成本、判断会话恢复能力。

@@idea 核心思路
**Checkpointer 保存的是完整的 Graph State（messages 列表）**——不只是最后一句，而是这一轮会话所有历史消息。每次执行结束，整个状态快照落盘（内存版落内存）。

```python
# State
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # 累积的完整对话，用官方 reducer 归并

# Checkpointer 保存：完整的 messages（含每一轮的 Human/AI/Tool 消息）
app.get_state(config)          # 查看某个 thread 的完整状态
app.get_state_history(config)  # 查看状态历史（可回放）
```

所以：恢复会话 = 从 Checkpointer 取回完整 messages，重新喂给模型 → 模型"记得"所有前文。工具调用的中间结果（ToolMessage）也在其中，多轮工具协作也能完整还原。

@@point ⑤ Agent + 短期记忆：工具调用也一起记
@@need 要解决什么
上一节是纯对话记忆，但实际 Agent 带工具——工具调用记录（调了什么、结果多少）也是对话的一部分，必须一起保存，否则恢复上下文时工具结果丢了，模型会"失忆"。

@@idea 核心思路
**create_agent 同样支持 checkpointer 参数**，一行接入：

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_agent(llm, tools, checkpointer=MemorySaver())

result = agent.invoke({"messages": [("user", "帮我算出 25*4+10")]},
                      config={"configurable": {"thread_id": "calc-001"}})
# Agent 内部：agent→tools→agent 的每一轮消息都被 Checkpointer 保存
# 下一轮继续问"那再加 5 呢?" → 恢复完整上下文（含工具结果）→ 正确回答 115
```

记忆与工具调用协作：HumanMessage、AIMessage（含 tool_calls）、ToolMessage 全部按顺序保存，恢复时完整重放——这就是"多轮工具对话"能被记住的底层原因。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| create_agent 加了 checkpointer 却没传 thread_id | 缺 thread_id 每条消息仍是独立会话，记忆不生效 |
| 工具调用记录没回传，模型看不到历史 | ToolMessage 必须回流，Checkpointer 才保存完整对话 |

@@point ⑥ 长期记忆（InMemoryStore）：put / get / search
@@need 要解决什么
短期记忆会话结束就没了。但用户姓名、偏好设置、历史订单要长期保留，下次新会话也必须知道。谁来存"跨会话"的数据？

@@idea 核心思路
**InMemoryStore** 以命名空间 + 键值对存储结构化数据：

```python
# 1. 创建 Store
store = InMemoryStore()

# 2. 写入（put）
store.put(
    ("users", "user-001"),        # namespace：用户 user-001
    "profile",                    # key：数据类型
    {"name": "张三", "age": 25, "city": "北京", "theme": "dark"}   # value
)

# 3. 读取（get）
profile = store.get(("users", "user-001"), "profile")

# 4. 搜索（search）：枚举某命名空间下的所有数据
all_profiles = store.search(("users",))
```

**命名空间（namespace）**是 Store 的隔离维度：`("users", user_id)` 把每个用户的数据隔开，互不污染。API 速查：**put 写入 / get 读取 / search 搜索命名空间下所有 / delete 删除**。

类比：长期记忆 = 身份证 + 档案柜——namespace 是柜子格子（用户分区），key 是档案袋标签，value 是袋子里的事实。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| namespace 写了字符串而不是元组报错 | namespace 是元组，如 ("users","u1")，传 str 会类型错误 |
| put 完了 search 搜不到 | search 依赖索引/精确路径，忘了配置就查不到 |

@@point ⑦ Agent + 长期记忆：自动提取并存储用户信息
@@need 要解决什么
手动 put 用户信息太蠢——对话里说"我叫张三、喜欢深色"就得开发去写代码存。能不能让 Agent 自己在对话中识别关键信息并自动存下来？

@@idea 核心思路
在 Agent 里同时配 **Checkpointer（短期） + Store（长期）**，两条记忆并行：

```python
from langgraph.store.memory import InMemoryStore
from langchain.agents import create_agent

# 同时挂 Store（长期）
store = InMemoryStore()
agent = create_agent(llm, tools, checkpointer=MemorySaver(), store=store)
```

- 短期记忆保持当前对话上下文，长期记忆保存跨会话关键信息
- **自动提取存储**：通过工具（如 save_user_info 工具）或模型指令，从对话中提取"姓名/偏好/订单"写入 `namespace=("users", user_id)`
- 下次任何新会话（新 thread_id）→ Agent 先 search Store → 直接说出"张三你好，还是深色模式吗？"

实践要点：写"用户信息提取"工具 + 提示词要求"识别到新用户信息时调用该工具"—两条线分清：日常对话走 Checkpointer，身份偏好走 Store。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| "记住用户"没写进 system prompt | Agent 必须被显式告知"先查记忆再用"，否则存了也不查 |
| 只写入不检索，记忆变摆设 | 长期记忆要成对：先检索后使用，再决定写入 |

@@point ⑧ 生产持久化：PostgresSaver + PostgresStore
@@need 要解决什么
MemorySaver / InMemoryStore 都在内存，服务一重启全部丢失——生产环境不能用。需要真正落盘的记忆后端：PostgreSQL。

@@idea 核心思路
只用改两行，Agent 代码完全不用动：

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://user:pass@localhost:5432/mydb"

# 1. ⚠️ from_conn_string() 返回的是**上下文管理器**，不能直接赋值
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:      # 原来是 MemorySaver
    checkpointer.setup()                                          # 首次跑要建表
    with PostgresStore.from_conn_string(DB_URI) as store:         # 原来是 InMemoryStore
        store.setup()

        # 2. 挂载方式与内存版完全一致
        agent = create_agent(llm, tools, checkpointer=checkpointer, store=store)
        # 注意：with 块退出后连接就关了，实际项目里在应用启动时打开、常驻到进程结束
```

关键点：
- `from_conn_string` 一行连接；`setup()` 自动创建所需数据表（必调，否则报错）
- **Agent 代码完全不变**：MemorySaver → PostgresSaver、InMemoryStore → PostgresStore 无缝替换
- namespace、thread_id 用法不变——生产持久化=换后端，不是改逻辑

类比：内存版 = 随手记在脑门上，重启就忘；Postgres 版 = 记进正式档案柜，关机也不丢。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 换 Postgres 后报"表不存在" | 忘了调 setup()，表没建 |
| 以为 Production 也能用 MemorySaver | 纯内存丢失数据，生产必须 PostgresSaver/PostgresStore |
| 长期记忆写了但新会话读不到 | 读写 namespace 不一致：入账时 ("users", uid)，读时也得同款 namespace |
| 短期长期搞混 | 名字（有序消息）用 Checkpointer；画像/偏好（结构化）用 Store |

@@summary 这一章你学到了什么
- 区分两类记忆：Checkpointer 短期页会话 State、Store 长期跨会话键值
- 会新旧 API 对照，新项目拒绝旧版 RunnableWithMessageHistory 系列
- 三步接入 MemorySaver：创建 → compile(checkpointer=) → 每次调用带 thread_id
- 理解 Checkpointer 保存完整 State（messages 含工具记录），可恢复可回放
- create_agent 一键加 checkpointer，工具协作上下文完整记忆
- 掌握 InMemoryStore 的 put / get / search 与 namespace 隔离设计
- 会业务组合：Checkpointer 保对话 + Store 保画像，Agent 自动提取用户信息
- 生产化：PostgresSaver / PostgresStore 换后端，setup() 建表，Agent 代码不变

下一章，把 Agent 从"内部工具"解放到"外部系统"：MCP 协议——如何让 Agent 以标准化方式接入邮件、数据库、企业系统，以及如何用 FastMCP 3 分钟发布你自己的工具服务。

@@quiz
1. LangGraph 中短期记忆与长期记忆分别对应？
   A. Checkpointer / Store　　B. Store / Checkpointer　　C. 都是 List　　D. 没有区别
2. 新项目做多轮对话记忆，推荐用哪个 API？
   A. ConversationBufferMemory　　B. RunnableWithMessageHistory　　C. MemorySaver (Checkpointer)　　D. 手写数组
3. 挂上 checkpointer 后，每次 invoke 必须传什么？
   A. api_key　　B. thread_id　　C. timezone　　D. 什么都不用
4. MemorySaver 适合哪些用途？
   A. 生产环境持久化　　B. 仅开发测试，重启即丢　　C. 跨设备同步　　D. 大模型训练
5. InMemoryStore 的四个基础操作是？
   A. add/remove/update/query　　B. put/get/search/delete　　C. save/load/merge/flush　　D. insert/select/join/drop
6. 使用 PostgresSaver / PostgresStore 时，必须先做什么？
   A. 建索引　　B. 调用 setup() 建表　　C. 写触发器　　D. 改 thread_id
7. 用户画像（姓名、偏好、历史订单）应该存哪？
   A. 短期 Checkpointer　　B. 长期 Store（带 namespace）　　C. 系统日志　　D. 提示词里

@@links
参考|07_LLM框架实战_Memory.pdf|#
官网|LangGraph 记忆概念|https://docs.langchain.com/oss/python/langgraph/overview
官网|MemorySaver 参考|https://reference.langchain.com/python/langgraph/
官网|LangGraph Store 参考|https://reference.langchain.com/python/langgraph/