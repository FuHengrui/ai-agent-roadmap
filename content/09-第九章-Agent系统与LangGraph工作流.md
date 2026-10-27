@@h1 第九章　Agent 系统与 LangGraph 工作流
@@sub 阶段 11 · LegalMind 法律咨询系统　|　难度 ★★★

@@why 这一章在解决什么问题
前几章攒了一堆零件：意图识别、案例检索、法律问答、文书生成——但**谁来决定先用哪个、怎么串起来**？写死 if-else 只能处理"能预测的顺序"，可用户的真实请求千变万化：有人问问题（问答）、有人要写诉状（文书）、有人想查判例（检索）。顺序是**运行时由意图决定的**。
正好可以用 LangGraph 来解决：这种"按条件分叉的多步任务"正是有向状态图的强项。LegalMind 用 LangGraph 把所有能力编排成一张图——**总是先走意图识别，再按识别结果条件路由到检索/文书**，工作流完成一次完整协作。学完本章，你的 AI 系统从"单打独斗的工具集合"升级为"会自己排兵布阵的 Agent 系统"。

@@map 这一章在整个知识库里的位置
上一章（第八章 RAG 检索）：RetrievalAgent 已可用，检索质量可调
**本章** 你在这里：把四个 Agent 装进 LangGraph 状态机——分工、路由、记忆，一次编排
下一章：聊天与文书生成 API——工作流实例直接挂在 FastAPI 路由后面，SSE 推流
再往后：前端联调、检索页面
阶段终点：一个"会自动选路"的完整 AI 律师大脑

@@point ① Agent 的拆解：四个单一职责模块
@@need 要解决什么
LLM 调用场景各不相同，全塞一个类会膨胀到没法维护。按职责拆成四个 Agent，各自只干一件事，可单独测试、可替换升级。
@@idea 核心思路
LegalMind 的四枚 Agent 与职责：
| Agent | 输入 | 输出 | 依赖 |
|---|---|---|---|
| IntentAgent | 用户 query | qa / document / search | LLM + 意图 prompt |
| RetrievalAgent | query、filters | 案例列表（已重排） | HybridRetriever + Reranker |
| QAAgent | 案例 + 消息历史 | 流式回答文本 | LLM + QA prompt |
| DocumentAgent | 文书类型 + 参数 | 文书全文 | LLM + 文书模板 |
协作关系一句话：**IntentAgent 决定方向 → RetrievalAgent 找弹药 → QAAgent 组织回答（或 DocumentAgent 生成文书）**。四者互不 import 对方（各自只依赖 rag/llm 层），替换任一 Agent 不影响他人——这就是"单一职责"在 Agent 架构里的落地。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 LLM 调用、检索、写库全塞进一个"万能函数" | 一个函数耦合四件事，改一处全崩；先按职责拆四个模块，图才有清晰的节点边界 |

@@point ② LangGraph 核心概念：State/Node/Edge
@@need 要解决什么
用过的都说 LangGraph 是"给 LLM 应用写流程图"。先搞懂它的三个核心概念，再看 LegalMind 的图就一目了然。
@@idea 核心思路
对比关系（把 Agent 工作流想象成工厂流水线）：
| 概念 | 类比 | 本项目实例 |
|---|---|---|
| **State** | 传送带上的"料盒"（所有节点共用） | AgentState：query / intent / retrieved_cases / response / messages |
| **Node（节点）** | 工位的"工人" | intent_recognition / case_retrieval / qa_generation / document_generation / final_output |
| **Edge（边）** | 工位间的"传送带" | 普通边（顺序）与条件边（按 State 分叉） |
State 定义（TypedDict）：
```python
class AgentState(TypedDict):
    query: str                       # 用户问题
    intent: str                      # 意图（qa/document/search）
    retrieved_cases: list            # 检索结果
    document_type: str               # 文书类型
    document_params: dict            # 文书参数
    response: str                    # 最终回答
    sources: list                    # 引用来源
    messages: Annotated[list[BaseMessage], add_messages]  # 对话历史（自动合并）
```
`add_messages` 是 LangGraph 对 messages 字段的**归约器（reducer）**：多节点往里加消息时自动 append 合并，而不是覆盖。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Node 直接在函数里改入参 State 对象，期望图内共享 | 图节点要返回"要更新的 state 片段"，不是原地改外部变量；否则并发/检查点恢复时状态全乱 |

@@point ③ 建图：五节点 + 三条件边的完整结构
@@need 要解决什么
四个 Agent 怎么编排成图？从"入口在哪、节点叫什么、按什么条件分叉"三个问题入手，把图的结构一次搭对。
@@idea 核心思路
`agents/workflow.py` 的建图代码：
```python
def _build_graph(self) -> StateGraph:
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent_recognition", self._intent_node)
    workflow.add_node("case_retrieval", self._retrieval_node)
    workflow.add_node("qa_generation", self._qa_node)
    workflow.add_node("document_generation", self._document_node)
    workflow.add_node("final_output", self._output_node)

…（以下省略 11 行，完整代码见仓库对应位置）
        "qa": "qa_generation",
        "search": "final_output",
    })
    workflow.add_edge("qa_generation", "final_output")
    workflow.add_edge("document_generation", "final_output")
    workflow.add_edge("final_output", END)

    return workflow.compile(checkpointer=get_checkpointer())
```
图的结构（条件路由示意）：
```text
用户query
   │
   ▼
intent_recognition ──document──► document_generation ──► final_output ──► END
   │  qa/search
   ▼
case_retrieval ──search──► final_output ──► END
   │  qa
   ▼
qa_generation ──► final_output ──► END
```
精华在**条件边（conditional_edges）**：路由函数返回 key，图按映射表跳下一个节点——意图识别结果直接决定工作流走向，这就是"运行时动态编排"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 条件边指向的节点名写错，运行时 KeyError | LangGraph 按字符串匹配节点，建图时节点名和路由返回值逐一核对；先画好图再写代码 |

@@point ④ 各节点实现：如何改 State
@@need 要解决什么
图搭好了，节点函数怎么写？核心纪律：**节点是"状态转换函数"——输入整包 State，输出要更新的字段**，LangGraph 负责合并。
@@idea 核心思路
关键节点实现：
```python
# 意图识别节点：只写 intent 字段
async def _intent_node(self, state: AgentState) -> dict:
    intent = await self.intent_agent.recognize(state.get("query"))
    return {"intent": intent}

# 检索节点：只写 retrieved_cases
async def _retrieval_node(self, state: AgentState) -> dict:
    cases = await self.retrieval_agent.retrieve(query=state.get("query"), top_k=5)
    return {"retrieved_cases": cases}

…（以下省略 14 行，完整代码见仓库对应位置）
async def _document_node(self, state: AgentState) -> dict:
    response = await self.document_agent.generate(
        document_type=state.get("document_type", "起诉状"),
        params=state.get("document_params", {}),
        query=state["query"],
    )
    return {"response": response["content"], "sources": response.get("references", []),
            "messages": [AIMessage(content=response["content"])]}
```
**铁律：节点只返回"增量"，绝不返回整包 State**——否则会把别人的字段覆盖成空。`_qa_node` 里的流式收集展示了异步节点与 LLM 流式输出的结合。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 节点函数忘返回状态片段，下游拿不到新值 | 每个节点必须返回 dict（哪怕空 dict），图才把更新写进 state；只执行不返回 = 状态原地踏步 |

@@point ⑤ 条件路由函数：_router_by_intent 的写法
@@need 要解决什么
条件边需要一个"路由函数"：读 State，返回 key 字符串，LangGraph 拿 key 查映射表决定下一节点。写这个函数要把"默认行为"想清楚。
@@idea 核心思路
```python
def _router_by_intent(self, state: AgentState) -> str:
    intent = state["intent"]
    if intent == "document":
        return "document"
    elif intent == "search":
        return "search"
    return "qa"          # 默认兜底：未知意图一律走问答

def _route_after_retrieval(self, state: AgentState) -> str:
    if state["intent"] == "search":
        return "search"
    return "qa"
```
两个防呆设计：
- **兜底分支**：意图识别输出不在 {qa, document, search} 时，`_router_by_intent` 返回 "qa"——宁可多答，不能路由崩（对应第 6 章 agent 的 output 净化）。
- **search 意图的"双节点接力"**：先走检索拿结果，再到 final_output 把结果 JSON 化直接返回——检索页的接口可以复用这条链路。

@@point ⑥ checkpointer：对话记忆持久化到 Postgres
@@need 要解决什么
聊天要"记得上一轮"。LangGraph 的 checkpointer 可以把状态（含 messages）按 thread_id 存起来；本项目用 **AsyncPostgresSaver** 存进 Postgres——**跨请求、跨进程重启都不丢**。
@@idea 核心思路
`llm/checkpoint.py`：
```python
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None

async def init_checkpointer():
    """lifespan 启动时调用：建连接池 + 幂等建表"""
    global _pool, _checkpointer
…（以下省略 4 行，完整代码见仓库对应位置）
    _checkpointer = AsyncPostgresSaver(conn=_pool)
    await _checkpointer.setup()      # 自动创建 checkpoints 表
    return _checkpointer

def get_checkpointer():
    if _checkpointer is None:
        raise RuntimeError("Checkpointer 尚未初始化，请在应用启动时调用 init_checkpointer()")
    return _checkpointer
```
使用的关键在 workflow：
```python
async def run(self, query: str, thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    init_state = {"query": query, "messages": [HumanMessage(content=query)]}
    return await self.get_graph().ainvoke(init_state, config=config)
```
- **thread_id 决定"对话身份"**：同一 session_id 的多次调用共用一个 thread，LangGraph 自动续接历史。
- **lifespan 顺序**：`init_checkpointer()` 必须在图**首次编译前**调用，否则 `get_checkpointer()` 抛异常（第 3 章已排好顺序）。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `Checkpointer 尚未初始化` | lifespan 没调 init_checkpointer()，或图在 import 时被提前编译 |
| 重启后“记忆”丢了 | 用了 MemorySaver（内存版）；生产必须 AsyncPostgresSaver |
| 多线程同时写同 thread 冲突 | 同一 session 并发请求会乱；前端流式期间禁止重复发送（本项目 isStreaming 锁） |
| checkpoints 表很大 | LangGraph 默认存全量快照；定期清理或调 checkpoint 保留策略 |

@@point ⑦ 懒编译 get_graph：图的加载时机
@@need 要解决什么
图编译是重活（要连接 checkpointer、构建状态机），不能每次请求都编译。项目用**懒加载 + 单例缓存**：第一次调用时编译一次，之后复用。
@@idea 核心思路
```python
class LegalMindWorkflow:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.qa_agent = QAAgent()
        self.document_agent = DocumentAgent()
        self.retrieval_agent = RetrievalAgent()
        self._graph = None

    def get_graph(self):
        """懒加载编译图。首次调用时编译并缓存。"""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph
```
注意：`__init__` 里**只是实例化四个 Agent，不编译图**——这样 import 模块时零副作用（不会触发 `get_checkpointer()`）。图编译推迟到第一次"真实使用时"（lifespan 已完成 checkpointer 初始化），时序天然正确。模块末尾 `workflow = LegalMindWorkflow()` 提供全局单例，API 路由直接 `from app.agents.workflow import workflow`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 每次请求都重新编译整张图，响应慢一截 | 图结构不变就不要每次重建；`get_graph` 缓存复用，只在线程安全的编译一次 |

@@point ⑧ astream 流式：stream_mode="messages"
@@need 要解决什么
聊天体验要"打字机效果"（逐字输出），LangGraph 怎么把内部节点的输出流出来？用 `astream(..., stream_mode="messages")` 只流 LLM 的 token，节点元信息（在哪个节点）一并给出。
@@idea 核心思路
```python
async def astream(self, query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    init_state = {"query": query, "messages": [HumanMessage(content=query)]}
    async for chunk, metadata in self.get_graph().astream(
        init_state, config=config, stream_mode="messages"
    ):
        yield chunk, metadata     # metadata 含 langgraph_node 字段
```
第 10 章 chat API 会用它做 SSE：
```text
async for chunk, metadata in workflow.astream(query=query, thread_id=session_id):
    node = metadata.get("langgraph_node") if metadata else None
    if node == "qa_generation" and chunk.content:
        # 只把问答节点的 token 推给前端
        yield f"data: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"
```
要点：
- `stream_mode="messages"` 流的是 **LLM 层消息 token**（细粒度），不是节点级结果。
- **按节点过滤**：`node == "qa_generation"` 才推流——检索节点没有 token 输出，文书节点走一次性返回。
- 流结束后单独 `graph.aget_state(config)` 读最终 state 取 sources——**流式模式不暴露最终 state**，这是本项目踩过的坑（第 10 章展开）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| stream_mode=messages 和默认模式的事件结构弄混，解析不到内容 | 不同 stream_mode 的 event 结构不同；先用一个回显脚本打印原始事件，再写解析，别猜结构 |

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **可自动路由的 Agent 图** | 意图识别决定走向，问答/检索/文书按需触发，多步协作一次编排 |
| **跨重启的记忆** | Postgres checkpointer 让"记得上一轮"变成持久承诺 |
| **流式工作流** | astream 逐 token 输出，配合第 10 章 SSE 做出打字机对话 |

@@quiz
1. 四个 Agent 各自的职责是什么？为什么它们之间不该互相 import？
2. LangGraph 的 State/Node/Edge 分别对应什么？add_messages reducer 解决什么问题？
3. 画出 LegalMind 的完整状态图（含两条条件边），说明 search 意图的双节点接力。
4. 节点函数为什么只返回"增量字段"？返回整包 State 会有什么灾难？
5. _router_by_intent 的兜底分支是什么？为什么这么设计？
6. checkpointer 用 AsyncPostgresSaver 相比 MemorySaver 强在哪？thread_id 起什么作用？
7. 为什么图要"懒编译"？在模块顶层直接编译会触发什么问题？

@@links
参考|LegalMind 法律咨询系统：Agent 系统与 LangGraph 工作流|#
官网|LangGraph 官方文档|https://langchain-ai.github.io/langgraph/
官网|LangGraph Checkpointer 文档|https://langchain-ai.github.io/langgraph/concepts/persistence/