@@h1 第五章　LangGraph 图编排：复杂流程的控制中枢
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
第四章的 LCEL 是一条笔直的管道：A → B → C，一路到底。但真实的 Agent 流程是**一张图**，不是一条线：

- 要**循环**：模型调完工具，可能还要再思考、再调，直到搞定
- 要**分支**：查询结果决定走 A 还是走 B
- 要**人工介入**：转账前停下等人类审批
- 要**记忆**：多轮对话记住上下文、跨会话记住偏好

LCEL 在这些场景下要么做不到、要么写得痛苦。于是有了 LangGraph：**把 Agent 流程描述成"状态 + 节点 + 边"的图，让流程可以循环、分支、暂停、持久化**。这一章从核心概念（State/Node/Edge）到五步构建流程，再到 Reducer、条件边、子图、记忆，全部过一遍。

@@map 这一章在整个知识库里的位置
上一章：LCEL 链式调用——线性管道，适合简单流程
**本章** ← 你在这里：LangGraph 图编排——有状态、可循环、可分支、可人工介入
下一章：LangGraph 工具系统——把"调工具"循环装进图里，组成真正的 Agent
再往后：记忆系统 → MCP → 人机协作 → 实战与 A2A

@@point ① 为什么需要 LangGraph：LCEL 的边界
@@need 要解决什么
LCEL 管道只能"一条道走到黑"。可 Agent 的本质是"干不好就再干一遍、此路不通换条路"——这是**循环和分支**，线性管道表达不了。

@@idea 核心思路
LangGraph 是用于构建**有状态、多步骤应用**的框架，特别适合 Agent 开发。它和 LCEL 的分工：

| 特性 | LCEL | LangGraph |
|---|---|---|
| 适用场景 | 简单线性流程 | 复杂循环/分支流程 |
| 状态管理 | 无 | 有（TypedDict） |
| 循环控制 | ❌ | ✅ |
| 条件分支 | RunnableBranch | 更强大的条件边 |
| 人工介入 | ❌ | ✅ interrupt |
| 持久化 | 需要 | ✅ Checkpointer |
| 可视化 | 弱 | ✅ |

LangGraph 像一个**智能车间**：产品（状态）可以流动到不同工位（节点），工位之间可以来回传送（边），还可以"这个工件回炉重造"（循环）。LCEL 则是传送带——只能往前。

判断标准：**流程有循环/分支/人工介入/持久化需求 → 用 LangGraph；只是线性"取数→处理→回答" → LCEL 够了。**

@@point ② 三大核心概念：State / Node / Edge
@@need 要解决什么
要理解 LangGraph，先理解它的三个基本构件：数据放哪、谁在处理、怎么流转。

@@idea 核心思路
**State（状态）**：Graph 中共享的数据容器。
- 用 TypedDict 定义
- 每个节点可以读取 State，也可以更新 State
- 节点返回的字典会与当前 State **合并（覆盖同名字段）**

**Node（节点）**：处理逻辑单元。
- 就是一个函数：接收 state，返回更新字典 `{"field": new_value}`
- 典型节点：调用 LLM、调用工具、格式化、路由判断

**Edge（边）**：连接节点的路径。
- 普通边：A → B，固定流转
- **条件边**：A → [判断] → B/C，根据 state 内容选择去向

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. 定义 State
class SimpleState(TypedDict):
    input: str
    processed: str
    output: str

# 2. 定义节点：接收 state，返回更新
def process_node(state: SimpleState):
    return {"processed": state["input"].upper()}

def format_node(state: SimpleState):
    return {"output": f"处理结果：{state['processed']}"}

# 3-5. 构建 → 连边 → 编译
graph = StateGraph(SimpleState)
graph.add_node("process", process_node)
graph.add_node("format", format_node)
graph.set_entry_point("process")
graph.add_edge("process", "format")
graph.add_edge("format", END)

app = graph.compile()
result = app.invoke({"input": "简单介绍一下 Python"})
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 节点返回的不是字典/包含未知字段 | 节点返回值会被合并进 State，字段必须在 State 里定义过才合法 |
| 忘记 add_edge 到 END | 节点跑完没出口，图悬空报错或行为异常 |
| 把节点当普通函数直接调用 | 节点必须注册进 graph 再通过 app.invoke 跑，直接调用没有 State 流转 |

@@point ③ 五步构建流程：LangGraph 的标准套路
@@need 要解决什么
LangGraph 项目虽然复杂，"骨架流程"其实固定。记住这个五步模板，任何图都能套。

@@idea 核心思路
1. **定义 State**：TypedDict 声明共享数据字段
2. **定义节点**：写函数（state → 更新字典）
3. **构建 Graph**：`graph = StateGraph(MyState)`
4. **添加边**：`graph.add_edge()`（固定边）/ `graph.add_conditional_edges()`（条件边）/ `graph.set_entry_point()`（入口）
5. **编译运行**：`app = graph.compile()` 然后 `app.invoke(初始state)` 或 `app.stream()`

类比记忆：就像装配一台机器——先画总装图（State），再准备零件（Node），搭框架（StateGraph），连管线（Edge），最后通电试机（compile + invoke）。

**State 传递规则**：初始 State 由 invoke 传入；每个节点返回的字典与当前 State 合并（默认覆盖同名字段）；下一个节点能读到合并后的完整 State。

@@point ④ State Reducer：控制字段怎么"合并"
@@need 要解决什么
默认规则是"节点返回字典覆盖同名字段"。但有些场景要的是**累加而不是覆盖**：比如三个节点各自往消息列表里加一条消息，最后要的是完整的消息列表，而不是最后一条。

@@idea 核心思路
Reducer（状态归约器）决定当多个节点更新同一个 State 字段时，**这些更新如何合并**。

**默认行为**：覆盖——后写的值替换先写的。

**常用 Reducer：`operator.add`（累加）**
```python
from typing import Annotated, TypedDict
import operator

class ChatState(TypedDict):
    messages: Annotated[list, operator.add]  # 多个节点追加，自动拼接

def node_a(state): return {"messages": ["你好"]}
def node_b(state): return {"messages": ["世界"]}
# 两个节点都跑完后 messages == ["你好", "世界"]，而不是只留 ["世界"]
```

**自定义 Reducer**：写一个函数，接收"当前值 + 新值"，返回合并后的值。比如去重合并、按时间排序。

**Reducer 对比**：覆盖（默认）适合"最新状态"（当前页码、最后结果）；累加适合"累积集合"（对话历史、日志列表、工具结果序列）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 期待累加却只留了最后一条 | 忘了给字段配 Annotated[list, operator.add]，默认覆盖了 |
| 自定义 Reducer 忘记处理"首次更新" | Reducer 会被"当前为空"的情况调一次，要兼容初始值 |
| 对数字字段用 operator.add | 累加语义未必是你想要的（比如计数器重跑会翻倍），想清楚再配 |

@@point ⑤ 条件边：让图自己"看情况走路"
@@need 要解决什么
图里经常要做决策：查询结果正常就走"输出"节点，报错就走"重试"节点；用户要翻译就进翻译子流程，要总结就走总结。这种"根据运行数据动态选路径"靠固定边做不到。

@@idea 核心思路
用 `add_conditional_edges` 加一条**条件边**：路由函数读取 State，返回目标节点名。

```python
graph.add_conditional_edges(
    "decide",                # 从哪个节点出发
    route_by_type,           # 路由函数：读 state，返回节点名
    {"content": "process_content", "summary": "process_summary", "unknown": "ask_user"}
)
```

路由函数设计模式：
```python
def route_by_type(state):
    if state["type"] == "content":
        return "process_content"
    elif state["type"] == "summary":
        return "process_summary"
    return "ask_user"
```

类比：**条件边 = 分拣传送带**——扫一下快递地址，国内件走左边的带子，国际件走右边的带子。

条件边还能实现**循环**：路由函数判断"及格了吗？补考次数超了吗？"，没及格就回到"答题"节点再来一轮，超过次数就到"failed"结束。**注意：循环必须有终止条件，否则无限循环。**

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由函数返回的节点名没注册 | add_conditional_edges 时目标映射不完整，或节点名拼错，编译/运行报错 |
| 条件路由没有兜底"unknown" | 模型/数据出现未覆盖分支时图直接崩溃 |
| 循环没有终止条件 | 图永远跑不完，直到超时烧钱，必须用计数器+上限 |

@@point ⑥ SubGraph：把大图拆成可复用模块
@@need 要解决什么
图越画越复杂：几十个节点平铺在一起，没法看、没法复用。如果有一段逻辑（比如"解析→翻译→总结→格式化"）在多处都要用怎么办？

@@idea 核心思路
SubGraph（子图）：把一部分节点和边封装成**独立的图**，再作为节点嵌入主图。就像函数封装：把重复逻辑抽成函数，主函数调用它。

```python
# 1. 建立子图（独立 StateGraph）
sub_builder = StateGraph(SubState)
sub_builder.add_node("classify", classify_node)
sub_builder.add_node("translate", translate_node)
sub_builder.set_entry_point("classify")
sub_builder.add_edge("translate", END)
sub_graph = sub_builder.compile()

# 2. 作为节点嵌入主图
main.add_node("sub_task", sub_graph)   # 子图即节点
main.add_edge("check", "sub_task")
```

**子图关键点**：
- 子图有自己独立的 State；与父图之间通过**State 映射**传递数据（父图把需要的字段传给子图入口，子图把结果映射回父图字段）
- 子图可单独测试、单独复用——同一子图嵌进多个主图分支
- 结构清晰：主图只留"骨架和路由"，细节收进子图

类比：没有子图 = 所有逻辑平铺成一个超长流水线；有了子图 = 工厂里分车间，每个车间负责一段工艺。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 子图与主图 state 字段重名被互相覆盖 | 子图有独立 State 类型，进出子图要显式定义字段映射 |
| 调子图传参报类型错误 | invoke 子图要按子图 State 传字段，不能直接塞主图整包 |

@@point ⑦ 并行节点：扇出-汇聚
@@need 要解决什么
图里有些步骤互不依赖：同一份文档既要打摘要、又要打标签、又要生成标题。按顺序一个个跑浪费时间。LangGraph 能并行吗？

@@idea 核心思路
LangGraph 原生支持并行执行：多个节点可以**同时**从同一上游节点出发（扇出），跑完后汇聚到下游节点（汇聚）。

天然实现方式：一个节点后面接多个节点（多个 add_edge），LangGraph 自动并行调度；以及常用"扇出-汇聚"模式——`parallel_fan_out → (task_a ∥ task_b ∥ task_c) → aggregate`。

```python
graph.add_edge("dispatch", "task_a")
graph.add_edge("dispatch", "task_b")
graph.add_edge("dispatch", "task_c")
# 三个 task 并行跑，都完成后汇聚到 merge
graph.add_edge("task_a", "merge")
graph.add_edge("task_b", "merge")
graph.add_edge("task_c", "merge")
```

类比：一个人洗菜的同时，另一个人切菜，第三个人热锅——三件事并行，最后一起上桌。

注意：并行配 Reducer 才有效——多个节点都往同一字段写，得用 `operator.add` 之类合并，否则最后到的覆盖前面的。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 多个父节点并发写同一 state 字段互相覆盖 | 并发写必须配 reducer 合并，否则后写覆盖先写 |
| 以为并行节点一定同时执行 | 无依赖才并行；共享状态有依赖时实际串行/合并 |

@@point ⑧ MemorySaver 与 Checkpointer：让状态活下来
@@need 要解决什么
默认情况下 app.invoke 跑完，State 就没了。可真实场景要"断点续跑"：多轮对话要记住上下文；人工审批中断后要能从那一步恢复；异常中断要能重入。

@@idea 核心思路
**Checkpointer（检查点）**：LangGraph 的持久化机制，把图的 State 快照存下来，支持：
- 人工介入断点（interrupt 之后 resume）
- 多轮对话记忆（thread_id 隔离会话）
- 崩溃恢复（从上次检查点重跑）

最简单的是 **MemorySaver**（内存版）：
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)
result = app.invoke(initial_state, config={"configurable": {"thread_id": "user-001"}})
```
- 传 thread_id 后，同一线程的多次 invoke 共享 State 累积（这就是 Agent 多轮记忆的基础）
- 换一个 thread_id 就是全新会话，互不干扰

**注意：interrupt() 必须配合 Checkpointer**，否则无法记录暂停点、无法恢复，直接报错。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 多请求并发共用一个 thread_id 状态错乱 | MemorySaver 无锁仅测试用，并发生产换持久化 checkpointer |
| 程序重启后记忆全丢 | MemorySaver 只存内存，重启即失，生产用 PostgresSaver |


@@summary 这一章你学到了什么
- 认清 LangGraph 的定位：LCEL 管线性流程，LangGraph 管"循环/分支/人工介入/持久化"的复杂 Agent 流程
- 建立三大核心概念：State（共享数据容器）、Node（处理函数）、Edge（普通边/条件边）
- 掌握五步构建套路：定 State → 写节点 → 建 StateGraph → 连边 → compile 运行
- 会用 State Reducer 控制合并方式：默认覆盖 vs operator.add 累加 vs 自定义
- 会用 add_conditional_edges 做动态路由和**带终止条件的循环**
- 会用 SubGraph 把复杂图拆成可复用模块
- 会用并行节点实现"扇出-汇聚"
- 会用 MemorySaver + thread_id 实现状态持久化和多轮记忆

下一章，把"工具"装进 LangGraph：ToolNode 自动执行、tools_condition 循环判断——那就是真正的 Agent 了。

@@quiz
1. LangGraph 相比 LCEL 的核心优势是？
   A. 速度快　　B. 支持循环、分支、人工介入、持久化（有状态复杂流程）　　C. 代码更短　　D. 不需要提示词
2. 下列哪个不是 LangGraph 的三大核心概念？
   A. State　　B. Node　　C. Edge　　D. Prompt
3. 多个节点各自追加一条消息到 messages，要得到完整列表而非最后一条，应该？
   A. 什么都不做　　B. 字段配 Annotated[list, operator.add]　　C. 用全局变量　　D. 手动拼接
4. add_conditional_edges 的"路由函数"作用是？
   A. 定义 State　　B. 读取 State 返回目标节点名，实现动态选路与循环　　C. 调用工具　　D. 编译图
5. 条件边实现循环时，最致命的坑是什么？
   A. 节点太多　　B. 没有终止条件导致无限循环　　C. 内存不足　　D. 提示词太长
6. interrupt()（人工介入）不能正常工作的最常见原因是？
   A. 模型不支持　　B. 没配 Checkpointer　　C. 网络慢　　D. 图太小

@@links
讲义|05_LLM框架实战_LangGraph.pdf|#
官网|LangGraph 官方文档|https://langchain-ai.github.io/langgraph/
官网|LangGraph 概念详解|https://langchain-ai.github.io/langgraph/concepts/
官网|LangGraph 快速上手|https://langchain-ai.github.io/langgraph/tutorials/
