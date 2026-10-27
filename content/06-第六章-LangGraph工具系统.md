@@h1 第六章　LangGraph 工具系统：让 Agent 真正"动起来"
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
第五章你建好了图的骨架（State/Node/Edge），但图里装的是"文字处理"——还没有"真动作"。真正的 Agent 必须能查天气、算数学、调数据库。而工具调用的难点不在"写工具"（第二章已经会了），在于**把"思考→调工具→看结果→再思考"这个循环优雅地装进 LangGraph**。

本章是 Agent 技术的核心一环：`@tool` 定义工具 → `ToolNode` 自动执行 → `tools_condition` 判断是否继续——最后用 `create_agent` 一行代码把整个 ReAct 循环封装起来。同时解决工具调用失败的三类错误处理。

学完这一章，你就能写出第一个真正意义上的"会干活"的 Agent 了。

@@map 这一章在整个知识库里的位置
上一章：LangGraph 图编排——State/Node/Edge、条件边、循环的骨架
**本章** ← 你在这里：LangGraph 工具系统——把图变成会调用真实工具的 Agent
下一章：LangGraph 记忆系统——让 Agent 记住上下文与长期知识
再往后：MCP → 人机协作 → 实战与 A2A

@@point ① Tools 的作用：LLM 决策，工具执行
@@need 要解决什么
大模型只有"嘴"，没有"手"。用户问"25*4+10 等于多少"，模型可能算错；问"北京天气"，模型不知道实时数据。必须给模型挂上能执行真实操作的"外挂"。

@@idea 核心思路
**Tool Calling 的工作原理**：LLM 不直接执行工具，而是输出"调用指令"（tool_calls，含工具名+参数），由外部代码执行后把结果返回给 LLM 继续处理。

**工具的三大要素**（LangChain 定义）：
```python
@tool
def search(query: str) -> str:
    """搜索互联网信息"""        # ← 描述：LLM 根据描述决定是否调用
    return f"搜索结果..."      # ← 执行逻辑

# search.name           → "search"          ← 名称：LLM 用它指定调哪个
# search.description    → "搜索互联网信息"    ← 描述：LLM 用它理解用途
# search.args_schema    → {"query": str}     ← 参数：LLM 自动提取参数值
```

类比：顾客（用户）点菜 → 服务员（LLM）不亲自做菜，但知道菜单（工具描述）→ 写好单子（tool_calls）→ 厨房（工具）真实做菜 → 端回给服务员 → 服务员报给顾客。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 模型不调用工具、答案靠胡编 | 工具 description 写得不清楚，模型不知道"什么时候该用它" |
| 调用成功但结果没用上 | ToolMessage 没回传给模型，模型没"看见"工具结果（循环断了） |
| 以为模型"亲手执行"了工具 | 模型只是输出指令 JSON，执行者是 ToolNode/你的代码 |

@@point ② @tool 进阶：Pydantic 参数验证（args_schema）
@@need 要解决什么
简单工具一个 `query: str` 就够。但复杂工具（搜索商品要限价、限定类目）必须有约束——价格范围、数量限制、枚举选项。模型乱填参数怎么办？

@@idea 核心思路
用 **args_schema + Pydantic** 给工具参数上"合同模板"，规定每个字段怎么填：

```python
from pydantic import BaseModel, Field
from typing import Literal

class ProductSearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词")
    category: Literal["手机", "电脑", "家电"] = Field(description="商品类目")
    max_price: float = Field(default=99999, gt=0, description="最高价格")

@tool(args_schema=ProductSearchInput)
def search_product(keyword: str, category: str, max_price: float) -> str:
    """按条件搜索商品"""
    return f"搜索 {category} 中的 {keyword}，价格 <= {max_price}"

# 模型输出参数后，LangGraph 按 args_schema 自动校验：
# 类型错、超范围、缺必填 → 拦截或触发重试
```

**选择标准**：
- 简单工具（一两个无约束参数）→ `@tool` + 类型注解就够
- 复杂工具（参数需要范围/枚举/必填可选）→ `args_schema` + Pydantic

类比：简单工具 = 签字确认，一个签名就行；复杂工具 = 填合同表格，每个格子有规范。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| Pydantic 字段没写 description，模型乱填参数 | JSON Schema 靠 description 指导生成，缺了等于盲填 |
| 只标类型不写约束，非法值漏进业务层 | 范围约束要写 Field(gt=, le=)，光 float/str 不够 |

@@point ③ ToolNode：把 LLM 的"图纸"变成"产品"
@@need 要解决什么
模型输出了 tool_calls（图纸），但图不会自己执行。谁来真正调用工具函数、把结果整理成模型能读的消息？

@@idea 核心思路
**ToolNode** 是 LangGraph 提供的"工具执行器"：接收 LLM 输出的 tool_calls，**自动执行对应工具**，并将结果包装为 **ToolMessage** 追加回消息列表。

```python
from langgraph.prebuilt import ToolNode

# State：消息用 Annotated[Sequence, add] 自动追加（Reducer 累加）
class AgentState(TypedDict):
    messages: Annotated[Sequence, add]

def agent_node(state: AgentState):
    llm_with_tools = llm.bind_tools(tools)   # 把工具清单"绑"给模型
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))    # ← 自动执行工具

graph.add_edge("tools", "agent")            # 结果送回 Agent 继续思考
```

整个循环：
1. **agent**：模型看消息，输出 tool_calls（或直接回答）
2. **tools**：ToolNode 执行 tool_calls，产出 ToolMessage
3. **回 agent**：模型看到工具结果，继续思考——可能再调用或给最终答复

类比：ToolNode = 机器人手臂，按图纸自动加工；ToolMessage = 加工完成的产品，送回设计师（Agent）检查。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| ToolNode 执行报"工具未定义" | ToolNode 接受的是工具列表，传错对象类型或没把工具传进去 |
| 工具结果丢失/模型答非所问 | tools → agent 的边没加，结果没送回模型 |
| messages 被覆盖只留一条 | State 里 messages 没配 Annotated[Sequence, add]，新消息覆盖旧消息 |

@@point ④ Agent 循环详解：完整观察一轮思考-行动
@@need 要解决什么
"agent → tools → agent" 到底是怎么一轮轮跑起来的？手动走一遍流程，才能彻底理解循环。

@@idea 核心思路
以计算器工具为例，完整一轮：

1. **用户**：`messages=[HumanMessage("25*4+10 等于多少？")]`
2. **agent 节点**：模型收到消息 + 工具清单 → 输出 `tool_calls=[calculator("25*4+10")]`, 附在消息里
3. **tools 节点**：ToolNode 执行 `calculator("25*4+10")` → 返回 `ToolMessage(content="110")`
4. **回 agent**：模型现在看到 messages = [用户问题, 我的tool_calls, 工具结果"110"] → 再次思考
5. **模型决定**：不再需要工具 → 输出最终答案 "等于 110"

关键点：**每一轮模型都基于"完整历史 + 最新工具结果"决策**。工具结果就是它的"眼睛"，看着结果才知道下一步怎么走。循环直到模型认为"够了"（不再输出 tool_calls）或达到步数上限。

这个循环就是 ReAct（推理+行动）模式的图化实现。

@@point ⑤ tools_condition：内置的"要不要继续"判断
@@need 要解决什么
循环要有个出口：模型这一轮输出 tool_calls 就进 tools；否则直接结束。手写 `should_continue` 判断函数太重复——标准判断逻辑就那几行。

@@idea 核心思路
**tools_condition** 是 LangGraph 内置的条件路由函数，逻辑等于手写版 but 不用自己写：

```python
# 手写版（等价逻辑）
def should_continue(state):
    if state["messages"][-1].tool_calls:   # 最后一条消息带了工具调用
        return "tools"
    return END

# 内置版
graph.add_conditional_edges(
    "agent",
    tools_condition,           # ← 内置：看最后一条消息有没有 tool_calls
    {"tools": "tools", END: END}   # 有→进 tools；没有→结束
)
```

它的内部逻辑非常简单：**看 messages 最后一条消息有没有 tool_calls**；有就路由到 tools，没有就 END。tools_condition 是 Agent 构建的标准写法——在后面的 `create_agent`/`create_react_agent` 中都内置使用了它。

类比：tools_condition = 直接打开 GPS 导航，自动规划路线，不用自己看地图。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 模型返回了 tool_calls 却没走 tools 节点 | 条件边映射漏写 {"tools": ..., END: END} 或路由函数名拼错 |
| tools_condition 映射里缺 END 分支 | 无工具调用时不知道去哪，运行报错或死循环 |

@@point ⑥ create_agent：一行代码创建标准 Agent
@@need 要解决什么
手动构建 Agent 要写 30 行：定义 State、写 agent 节点、建 ToolNode、配条件边……重复劳动。有没有"开箱即用"的标准 ReAct Agent？

@@idea 核心思路
**create_agent** 一行创建标准 ReAct Agent——内置了 agent 节点、ToolNode、tools_condition、from_messages 状态管理等全部样板：

```python
from langgraph.prebuilt import create_agent

# ⭐ 一行代码
agent = create_agent(llm, tools)

# 使用
result = agent.invoke({"messages": [("user", "25*4+10 等于多少？")]})
print(result["messages"][-1].content)   # "110"
```

- 内部等价于你手动构建的那个图（agent ↔ tools 循环 + tools_condition 出口)
- 支持继续叠加：加 prompt（系统提示词）、加 checkpointer（记忆）、自定义中断
- **手动构建（约 30 行）**：适合完全自定义流程；**create_agent（约 3 行）**：标准 Agent 直接提车

类比：手动构建 = 自己买零件组装一辆车；create_agent = 从 4S 店提一辆现成车，不满意再改装。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| create_agent 后想改内部流程改不动 | 默认 agent 是黑盒，深度定制要回到手动构建或传参覆盖 |
| 忘了传 prompt/系统提示词 | create_agent 接受 system_prompt 参数，不传 Agent 就"没个性" |
| 以为 create_agent 包含记忆 | 默认无记忆，多轮记忆要配 checkpointer（看下一章） |

@@point ⑦ 工具调用错误的三种类型
@@need 要解决什么
工具会失败：参数填错、网络超时、业务规则不允许（余额不足）。不处理错误，Agent 一碰就崩。先分清错误长什么样。

@@idea 核心思路
工具调用失败分三类：

1. **参数错误**：模型填的参数不符合 args_schema（类型错、超范围、缺字段）——发生在执行前的**校验阶段**
2. **执行错误**：工具函数内部抛异常（网络超时、API 5xx、数据库连不上）——发生在**工具执行阶段**
3. **业务错误**：工具"正常返回"但业务上不允许（转账余额不足、股票停牌）——**能返回但结果不可用**

区分意义：三种错误的处理策略完全不同。参数错误 → 重试/让模型重填；执行错误 → 重试或降级；业务错误 → 如实告知用户，绝不自动重试（重试只会更糟，比如重复扣款）。

@@point ⑧ 三种错误处理策略：从工具内部到框架兜底
@@need 要解决什么
知道错误分三类，还要知道"在哪一层拦、怎么拦"。三层防线层层递进，缺一不可。

@@idea 核心思路
**策略 1：工具内部 try-except（第一道防线）**
```python
@tool
def query_database(sql: str) -> str:
    """执行数据库查询"""
    try:
        return run_query(sql)
    except Exception as e:
        return f"查询失败：{e}"   # 把错误变成可读结果返回
```
好处：错误不抛出，Agent 流程继续；问题：错误包装后模型可能"自作聪明"。

**策略 2：ToolNode 自动捕获（第二道防线）**
```python
ToolNode(tools, handle_tool_errors=True)   # 工具抛异常时自动包装为 ToolMessage
```
好处：统一兜底；注意：**create_agent 内部的 ToolNode 默认没有开启 handle_tool_errors**，要显式配置或靠策略 1/3。

**策略 3：Agent 自行决策（最终防线）**
错误信息作为 ToolMessage 返回给 Agent，Agent 根据错误内容自行回复用户、换参数重试或放弃。这是"智能"的体现。

**生产环境组合用法**：工具内部捕获业务逻辑（策略1）+ ToolNode 兜底意外异常（策略2）+ Agent 看到错误信息自主决策（策略3）——三层配合。**工具内部捕获，返回友好错误 → 让 Agent 感知，Agent 不会崩溃。**

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 工具把原始 traceback 抛给模型 | 模型看不懂堆栈只会乱编，要包装成"工具名+原因+建议" |
| 业务错误也自动重试 | 余额不足重试只会再扣一次费；业务错误只能如实返回，让 Agent 上报 |
| 以为 create_agent 默认兜底所有异常 | 其 ToolNode 默认 handle_tool_errors=False，要显式开或工具内部 try-except |

@@summary 这一章你学到了什么
- 理解了工具三要素：名称、描述、参数——描述决定模型"何时用"，参数 Schema 决定"怎么填对"
- 会按复杂度选择工具定义：简单 `@tool` 类型注解 vs 复杂 `args_schema` + Pydantic
- 掌握 ToolNode：自动执行 LLM 的 tool_calls 并包装成 ToolMessage 追加回消息
- 看懂了 Agent 循环：agent → tools_condition → tools → agent，直到模型不再输出 tool_calls
- 会用内置 tools_condition 替代手写 should_continue
- 会用 create_agent 一行创建标准 ReAct Agent，也能理解它与手动构建的对应关系
- 建立三层错误防线：工具内 try-except → ToolNode handle_tool_errors → Agent 自主决策

下一章，给 Agent 装上"笔记本"：LangGraph 记忆系统——短期记忆（checkpointer + thread_id）与长期记忆（Store），让 Agent 既记得"刚才聊了什么"，也记得"你一直喜欢什么"。

@@quiz
1. LangChain 工具三大要素是什么？
   A. 名称、返回值、异常　　B. 名称、描述、参数　　C. 名称、类型、速度　　D. 描述、注释、文档
2. 复杂参数的 @tool 应该如何定义？
   A. 全用字符串　　B. @tool(args_schema=Pydantic模型) 提供约束与校验　　C. 不用定义　　D. 写死参数
3. ToolNode 的核心作用是？
   A. 让模型自己执行工具　　B. 自动执行 LLM 输出的 tool_calls 并返回 ToolMessage　　C. 训练模型　　D. 压缩消息
4. tools_condition 的判断逻辑是？
   A. 看模型心情　　B. messages 最后一条消息是否有 tool_calls，有则进 tools 否则 END　　C. 看时间　　D. 随机
5. create_agent(llm, tools) 内部默认包含哪些？
   A. 只有模型　　B. agent 节点 + ToolNode + tools_condition 条件循环　　C. 训练流程　　D. 向量库
6. 业务性错误（如余额不足）最正确的处理是？
   A. 自动重试直到成功　　B. 包装成可读结果返回，让 Agent 如实告知用户，不自动重试　　C. 忽略　　D. 抛出异常中断

@@links
参考|06_LLM框架实战_Tools.pdf|#
官网|LangGraph 工具调用教程|https://docs.langchain.com/oss/python/langgraph/quickstartworkflows
官网|create_agent 参考|https://reference.langchain.com/python/langgraph/
官网|LangChain 工具概念|https://python.langchain.com/docs/concepts/tools/