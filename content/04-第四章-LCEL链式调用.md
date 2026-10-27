@@h1 第四章　LCEL 链式调用：把 Agent 的步骤连成管道
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★

@@why 这一章在解决什么问题
上一章你会了"模板 → 模型 → 解析器"三步走，但它们是**分开写、手动粘**的。真实 Agent 流程远不止三步：取数据 → 生成初稿 → 改写风格 → 提取要点 → 翻译，每一步之间还要传参。

LangChain 早期用 Chain 对象解决这个问题，但写起来又重又僵。后来官方推出了 **LCEL（LangChain Expression Language）**：用一条条 `|` 管道符，把任意组件优雅地串联起来——就像 Linux 的管道命令一样直观。

本章先带你理解"为什么要链"（旧 Chain 时代的痛点），再重点掌握 LCEL 的三大核心 Runnable（Passthrough / Lambda / Map）和条件路由 Branch，最后用 LCEL 重写旧式链，感受新范式的简洁。

@@map 这一章在整个知识库里的位置
上一章：LangChain 基础——模型、提示词、输出解析的单个积木
**本章** ← 你在这里：LCEL 链式调用——把积木用 `|` 连成流水线
下一章：LangGraph 图编排——当流程需要"循环、分支、人工介入"时，管道就不够了
再往后：工具/记忆/MCP → 实战与 A2A

@@point ① 为什么需要"链"：单步调用的天花板
@@need 要解决什么
直接调模型时，开发者要手动拼接字符串、处理变量替换、管理输出格式——又繁琐又容易错。而且一个任务往往多步：先取数、再生成、再加工，每步之间手动传参，代码迅速变成"面条代码"。

@@idea 核心思路
**链（Chain）是将大语言模型与其他工具、数据源、处理逻辑连接起来，形成完整 AI 应用工作流的机制。**

它的核心价值：
- **封装**：把"输入变量 → 提示模板 → 模型调用"绑定成一个可复用单元
- **编排**：定义步骤之间的数据流，开发者不用再手写中间传参
- **复用**：一条链可以当组件被更大的链拼装

从"手动拼字符串 + 手动传参"升级为"定义数据流，框架自动流转"——这是 LangChain 一切的起点。

@@point ② 传统 Chain 三兄弟：LLMChain / SimpleSequentialChain / SequentialChain
@@need 要解决什么
链概念刚出现时，LangChain 提供了三个经典 Chain 类。理解它们能帮你明白"链解决什么问题"，以及为什么后来被 LCEL 取代。

@@idea 核心思路
**LLMChain（基础链）**：最核心，把 PromptTemplate 和 LLM 绑定为一个单元。
- 输入：变量字典，如 {"question":"什么是量子计算？"}
- 中间：PromptTemplate 组织输入
- 输出：模型调用结果

**SimpleSequentialChain（简单顺序链）**：子链按顺序执行，前一个链的输出**自动**作为后一个链的输入。
- 特点：线性流程、单一输入/输出、自动传递，中间过程对外透明（只能看到最终结果）
- 适用：步骤之间有明确先后、前一步结果直接喂后一步的流水线（如"取数→总结→翻译"）

**SequentialChain（高级顺序链）**：支持多输入/多输出、灵活数据路由、保留中间结果。
- 可以精确指定每个子链的输入来自上一个链的哪个输出键
- 适用：剧本创作（标题+体裁 → 剧本 → 剧评，输出剧本+剧评）、市场分析（产品描述 → 文案 → 翻译 → 语气分析）

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 SimpleSequentialChain 能处理多输入 | 它只有一个输入一个输出，多输入要用 SequentialChain 或 LCEL |
| 中间结果丢了 | Simple 链对外透明，中间产物默认不可见；要保留得用 SequentialChain 的 return_intermediate |
| 新项目还用旧 Chain API | 官方已转向 LCEL，旧 API 在新项目中不推荐 |

@@point ③ 旧 Chain API 的五个痛点：为什么被 LCEL 取代
@@need 要解决什么
旧 Chain API 能用，但工程体验差。理解它的痛点，你就明白 LCEL 的设计动机。

@@idea 核心思路
| 痛点 | 说明 |
|---|---|
| 接口不统一 | 每个 Chain 类方法不同（run/apply/predict），记忆成本高 |
| 传参繁琐 | 多步之间手动管理字典数据，容易传错键 |
| 难以并发 | 并行执行要么手动实现，要么做不到 |
| 配置复杂 | 抽象层多，白盒调试困难 |
| 异步/流式支持弱 | 写异步代码要额外适配，流式输出基本靠手搓 |

而 LCEL 的对应优势：**统一 Runnable 协议（invoke/stream/batch/ainvoke）、管道自动透传数据、RunnableParallel 并行、配置直观、原生异步与流式**。

一句话：LCEL = 声明式 + 统一接口 + 并行 + 异步流式开箱即用。

@@point ④ LCEL 是什么：用 `|` 写 AI 流水线
@@need 要解决什么
流程编排能不能像 Linux 管道 `cat a.txt | grep xx | sort` 一样优雅？LangChain 说能。

@@idea 核心思路
LCEL（LangChain Expression Language）是 LangChain 推出的**声明式链式调用语法**。基本形态极其直观：

```python
chain = prompt | llm | output_parser
result = chain.invoke({"question": "你好吗？"})
```
- `|` 把两个 Runnable 连起来：左输出自动成为右输入
- 末尾 `.invoke()` 触发整条链执行
- 支持 `.stream()`、`.batch()`、`.ainvoke()`（异步）

**核心功臣是 Runnable 接口**：所有组件（Prompt、LLM、Parser、Retriever、工具）都继承自 Runnable，因此统一支持 invoke/stream/batch/ainvoke。就像 USB 接口——不管里面是什么设备，插口都长一样。

RunnableParallel 自动优化并行调用：多条独立的分支管道路径，框架自动并发执行。这是 LCEL 相对旧 Chain 的杀手锏。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 把 `/` 当普通运算符乱用（两端不是 Runnable） | LCEL 管道两侧必须实现 Runnable 协议，普通函数要用 RunnableLambda 包 |
| invoke 拿到的是原始模型输出不是解析结果 | 链末端组件决定返回类型，忘了串 parser 就拿到裸文本 |

@@point ⑤ RunnablePassthrough：原样透传的"数据搬运工"
@@need 要解决什么
管道里常有这种需求：既要保留用户的原始输入（比如订单信息），又要在此基础上追加模型生成的结果。如果直接 `输入 | llm`，原始输入会被模型的输出覆盖掉。

@@idea 核心思路
RunnablePassthrough 的作用：**原样传递输入，不做任何修改**。通常与 `.assign()` 配合——把输入字典保留，并在其上追加新字段。

```python
from langchain_core.runnables import RunnablePassthrough

chain = (
    RunnablePassthrough()
    .assign(answer=lambda x: (prompt | llm).invoke(x))  # 先透传原输入，再算 answer
)
result = chain.invoke({"question": "你好吗？"})
# result = {"question": "你好吗？", "answer": AIMessage("我很好...")}
```
类比：它的角色像"保留原始订单的快递员"，原货不动，额外给你塞一个包裹（新增字段）。在复杂链里它还是绝佳的**占位符与分支点**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 用了 Passthrough 但没 .assign | 它只是透传，不产生任何新字段，单独用等于空转 |
| 以为 Passthrough 能转换类型 | 不转换，只透传——转换交给 RunnableLambda |
| 输入不是字典 | assign 基于字典字段追加，输入结构不是 `{key: ...}` 会出错 |

@@point ⑥ RunnableLambda：把任意 Python 函数"接入管道"
@@need 要解决什么
真实流程中总有"模型管不着"的活：金额格式化、时间转换、调第三方库、清洗数组。这些普通函数怎么进 LCEL 管道？

@@idea 核心思路
RunnableLambda 把任意 Python 函数（或 lambda）包装成**符合 LCEL 规范的 Runnable 对象**，从而无缝融入链式流水线，并获得 invoke/batch/stream 等标准接口。

```python
from langchain_core.runnables import RunnableLambda

def format_price(x: dict) -> dict:
    x["price_display"] = f"¥{x['price']:.2f}"
    return x

chain = prompt | llm | parser | RunnableLambda(format_price) | formatter
```
函数即组件：写业务逻辑时不需要了解 LangChain 内部，一个普通 Python 函数就能成为管道的一环。它是 LCEL 里"自定义逻辑的万能胶水"。

@@point ⑦ RunnableMap：拆开并行，各干各的，再合并
@@need 要解决什么
有些任务的不同部分互相独立：比如同时"提取摘要"和"提取关键词"，完全可以并行处理，显著提速。串行逐个做就慢了。

@@idea 核心思路
RunnableMap（= RunnableParallel 的别名）用于**并行处理输入字典的多个字段**：

```python
from langchain_core.runnables import RunnableMap, RunnableLambda

# 两路独立并行：一路提取摘要，一路提取关键词
parallel = RunnableMap({
    "summary": RunnableLambda(get_summary),
    "keywords": RunnableLambda(get_keywords),
})
result = parallel.invoke(doc)   # {"summary": "...", "keywords": [...]}
```
形象理解：**把输入拆开，各干各的，再合起来**。框架自动调度并行，省时间；输出自动归并成一个字典，下游一次拿到所有结果。

适用：文本分析（摘要+情感+关键词并行）、多路信息聚合、需要同时生成多种输出（文案+翻译）的场景。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 在非独立任务上强行并行 | 某一路依赖另一路结果就不是 RunnableMap 的场景，要先串行再并行 |
| 各分支返回结构不一致 | 合并后字段层级混乱，下游解析时容易踩 KeyError |
| 认为 RunnableMap 是"路由" | 路由（按条件选一条路走）是 RunnableBranch 的活，Map 是全走 |

@@point ⑧ RunnableBranch：根据输入走不同路
@@need 要解决什么
Agent 要"看情况行事"：用户问数学题走解题分支，问天气就调工具。这类似于代码里的 if-elif-else——LCEL 里怎么表达条件路由？

@@idea 核心思路
RunnableBranch 根据输入内容**动态选择执行哪个分支**的 Runnable，是构建智能、自适应应用的关键组件。

```python
from langchain_core.runnables import RunnableBranch, RunnableLambda

chain = RunnableBranch(
    (lambda x: "紧急" in x["msg"], urgent_handler),   # if: 条件1 -> 分支1
    (lambda x: len(x["msg"]) > 100, long_handler),    # elif: 条件2 -> 分支2
    default_handler,                                   # else: 兜底
)
```
每个 condition 是可调用对象（callable），真则走对应分支，全不满足则走 default。合用场景：按用户意图分流（咨询/投诉/下单）、按数据类型分流、按上下文状态分流。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由条件用硬编码字符串，改一处忘另一处 | 条件分散难维护，把判断逻辑集中成函数 |
| 以为分支会逐个尝试直到命中 | RunnableBranch 只匹配第一个条件，无兜底分支会报错 |

@@point ⑨ 用 LCEL 重写传统链：感受新范式的力量
@@need 要解决什么
旧 Chain 五痛点讲了一堆，不见真章。把 LLMChain / SimpleSequentialChain / SequentialChain 用 LCEL 各重写一遍，眼见为实。

@@idea 核心思路
**重写 LLMChain（问答）：**
```python
chain = RunnablePassthrough().assign(answer=lambda x: (prompt | llm).invoke(x))
```
**重写 SimpleSequentialChain（问答→改写）：**
```python
from langchain_core.runnables import RunnablePassthrough
chain = RunnablePassthrough().assign(
    title=lambda x: title_gen.invoke({"topic": x["topic"]})
)
```
**重写 SequentialChain（多路输出 + 并行）：**
```python
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
chain = RunnablePassthrough().assign(
    review=lambda x: (generator | critic).invoke(x),   # 串行子流程
    tags=RunnableParallel({"a": tag_a, "b": tag_b}),   # 并行子流程
)
```
对比结论：写在纸上就赢——**同样的功能，LCEL 行数减半、数据流一目了然、并行/异步/流式全免费**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 抄旧版文档代码在新版本 ImportError | LangChain 0.1+ 大量旧类被移除/重命名，以当前稳定版文档为准 |
| 重写后行为不一致（字段名对不上） | 传统链隐式映射字段，LCEL 显式传递，需核对输入 key |

@@point ⑩ LCEL-RouterChain：路由选择链的前世今生
@@need 要解决什么
最后一问：老教程里的 RouterChain / LLMRouterChain（路由选择链）还要学吗？它和 RunnableBranch 什么关系？

@@idea 核心思路
旧版路由能力：LLMRouterChain 用**模型自己判断**"这个问题该走哪条子链"，返回目标链名再分发。问题是：模型判断有延迟、有误判率、还需维护路由提示词。

LCEL 时代的替代：**RunnableBranch 用确定性的 Python 条件做路由**——快速、稳定、零 token 消耗；如果要"模型智能路由"，也是先让模型输出分类结果（结构化输出），再把这个结果送入 RunnableBranch 选分支。

实践建议：
- 条件明确（关键词、长度、来源）→ RunnableBranch 无条件优先
- 语义复杂无法用规则表达 → 让模型结构化输出路由意图，再 Branch
- 新项目一律不再用 LLMRouterChain 旧 API

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由函数返回值与映射表 key 不一致直接报错 | 映射表必须覆盖所有可能返回值，加默认分支兜底 |


@@summary 这一章你学到了什么
- 理解了"链"解决的核心问题：把模型调用与提示词、工具、处理逻辑编排成完整工作流
- 认识旧 Chain 三兄弟（LLMChain / Simple / Sequential）的用法与演进逻辑，以及它们的五个痛点（接口不统一、传参繁琐、难并发、配置复杂、异步流式弱）
- 掌握 LCEL：`prompt | llm | parser` 管道语法与统一 Runnable 接口（invoke/stream/batch/ainvoke）
- 会用四大核心 Runnable：
  - RunnablePassthrough：透传原始输入 + assign 追加字段
  - RunnableLambda：把任意 Python 函数包装成管道组件
  - RunnableMap（别名 RunnableParallel）：多路并行处理再合并
  - RunnableBranch：按条件动态路由，替代旧 RouterChain
- 亲自用 LCEL 重写了三类传统链，直观感受声明式管道的简洁

下一章，当流程需要"循环、分支、记忆、人工介入"时，线性的管道就不够用了——进入 LangGraph 图编排。

@@quiz
1. LLMChain 的核心作用是？
   A. 训练模型　　B. 把 PromptTemplate 与 LLM 绑定成可复用单元　　C. 向量检索　　D. 数据清洗
2. SimpleSequentialChain 与 SequentialChain 的主要区别是？
   A. 速度　　B. Simple 仅单输入单输出自动传递；Sequential 支持多输入输出、灵活路由、保留中间结果　　C. Simple 更高级　　D. 无区别
3. LCEL 中 `chain = prompt | llm | parser` 的含义是？
   A. 三选一　　B. 前一个的输出自动作为后一个的输入，串联执行　　C. 并行执行　　D. 循环执行
4. RunnablePassthrough 配 `.assign(...)` 的典型用途是？
   A. 转换数据类型　　B. 保留原始输入并追加模型生成的新字段　　C. 删除字段　　D. 调外部 API
5. RunnableMap（RunnableParallel）适合什么场景？
   A. 步骤强依赖　　B. 多个互相独立的任务并行处理、结果合并　　C. 按条件路由　　D. 兜底分支
6. 新项目中要"按用户意图走不同分支"，推荐的做法是？
   A. 用旧 LLMRouterChain　　B. 用 RunnableBranch（条件明确）或先结构化输出路由意图再 Branch　　C. 写多个独立链硬编码　　D. 让用户自己选

@@links
参考|04_LLM框架实战_中级.pdf|#
官网|LangChain LCEL 教程|https://python.langchain.com/docs/concepts/lcel/
官网|LangChain Runnable 接口|https://python.langchain.com/docs/concepts/runnables/
官网|LCEL 各组件参考|https://python.langchain.com/docs/how_to/#langchain-expression-language-lcel
