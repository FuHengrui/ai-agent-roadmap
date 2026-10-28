@@h1 第十章　Agent 实战与 LangSmith 可观测
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
前面九章学了一堆"零件"：工具、记忆、图、MCP、审批流……但零件不等于产品。这一章做两件事：

1. **组装**：把 Tools + Memory + Graph 组合成三个完整应用——个人助手 Agent、多 Agent 协作（Supervisor 主管模式）、RAG Agent
2. **装仪表盘**：用 LangSmith 解决"看不到 Agent 内部在干什么"的问题——Chain / LangGraph 是黑盒，报错靠 print、Token 消耗是个谜

生产级 Agent = 能干活（组装）+ 能观测（LangSmith）。

@@prep 开始之前
要注册 LangSmith 账号、建 Key 填进 .env；LangGraph 环境沿用上一章，三个实战都要跑。

@@goal 学到这儿就够了
能说清工具、记忆、图为什么缺一不可、Trace 看什么，能组装一个带追踪的 Agent，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：Human-in-the-Loop——关键动作等人类把关
**本章** ← 你在这里：Agent 实战与 LangSmith——组合全部能力 + 可观测
下一章：A2A 跨 Agent 协作协议
再往后：Agent Skills 技能系统

@@point ① 核心问题：单一能力不够，需要三者组合
@@need 要解决什么
只用 Tools / 只用 Memory / 只用 Graph，都不完整。缺一个，Agent 就是"残疾人"。

@@idea 核心思路
三缺一演示：

| 组合 | 结果 |
|---|---|
| 只用 Tools | 能做事，但没记忆："帮你查了天气…但不记得你叫什么" ❌ |
| 只用 Memory | 有记忆，但不能做事："记得你叫张三…但帮你算不了数" ❌ |
| Tools + Memory + Graph | 完整 Agent："记得你叫张三，帮你查了北京的天气，晴天适合出门" ✅ |

**组合原则**：Tools 赋予能力、Memory 赋予连续性、Graph 赋予流程控制。缺一不可。

类比：只给厨师刀（Tools）没有菜谱记忆（Memory）断片；只有菜谱没有刀做不了菜；Tools+Memory+Graph 才是完整"大厨"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 学了 Tools/Memory/Graph 就以为能直接组合出生产级 Agent | 组合还要系统提示词、状态设计、错误处理，缺一不可 |
| 三者各自为政互不联通 | 必须放进同一个图共享 state，才能协同工作 |

@@point ② 实战案例：个人助手 Agent 完整组装
@@need 要解决什么
把"三合一"落到代码：一个既能聊天记住你、又能查询工具、还走了图流程的 Agent 长什么样？

@@idea 核心思路
三步组装（对应前四章能力）：

```python
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# 1. 定义工具（第二章能力）
@tool
def get_weather(city: str) -> str:
    """查询城市天气"""
    return f"{city} 今天晴天，适合出门"

# 2. 初始化带记忆的 Agent（第五/七章能力）
memory = MemorySaver()
agent = create_agent(
    llm,
    tools=[get_weather],
    system_prompt="你是一位贴心的个人助手，记住用户信息并主动提供帮助",
    checkpointer=memory,
)

# 3. 多轮对话：又能记住、又能查工具（第八章能力：可挂 MCP 工具）
agent.invoke({"messages": [("user", "我叫张三")]}, config)
agent.invoke({"messages": [("user", "帮我查北京天气")]}, config)
agent.invoke({"messages": [("user", "我叫什么？" )]}, config)
# → 张三 + 北京晴天，完整 Agent ✅
```

要点：tools（能力）+ checkpointer（记忆）+ system_prompt（角色）+ invoke 配置，四个零件拼一个完整 Agent。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 伪造/编造工具返回结果 | 工具返回必须是真实调用结果，否则模型学到错误映射 |
| 系统提示词没说明工具用法和记忆规则 | Agent 不知道何时用工具、何时查记忆 |

@@point ③ 为什么需要多 Agent：单一 Agent 的局限
@@need 要解决什么
任务越复杂，单一 Agent 越崩溃。看清"全能 Agent"的困境，才能理解为什么要拆。

@@idea 核心思路
单 Agent 局限：工具越来越多、提示词越来越长、互相干扰。

```
用户：帮我分析苹果公司的股票，然后翻译成英文，最后发邮件给老板
单Agent：
  → 调用股票查询工具 ✅
  → 翻译？没有翻译工具 ❌
  → 发邮件？没有邮件工具 ❌
  → 需要一个"全能"Agent，工具越来越多，提示词越来越长
```

多 Agent 分工：**Agent1 → Agent2 → Agent3**，各司其职。

类比：单 Agent = 一个人同时做产品、开发、测试、运维（累死）；多 Agent = 产品经理提需求、开发写代码、测试找 bug、运维部署（各司其职）。

@@point ④ Supervisor 主管模式：多 Agent 的大脑
@@need 要解决什么
多 Agent 各自干活，谁来分配任务？谁汇总结果？需要一个"调度者"。

@@idea 核心思路
**Supervisor（主管）模式**：主管 Agent 只做两件事——**分析用户意图、路由到最合适的专业 Agent**，它自己不执行具体操作；专业 Agent 干活后回传结果，Supervisor 汇总。

```
用户请求
  └▶ Supervisor（主管：分析意图 → 路由）
       ├▶ 金融Agent：分析股票
       ├▶ 翻译Agent：翻译成英文
       └▶ 邮件Agent：发邮件给老板
            └▶ Supervisor 汇总结果 ✅
```

客服中心案例：一个 Supervisor + 多个专业 Agent（退款/售后/咨询），天然适合用 LangGraph 的状态图表达——Supervisor 是中心节点，专业 Agent 是子节点，条件边路由。

类比：Supervisor = 项目经理，决定每个任务交给谁，自己不做具体活；专业 Agent = 各岗位员工。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 子 Agent 上下文互相污染 | 每个子 Agent 要有专属 system prompt 和工具集 |
| Supervisor 输出不在这选项里还硬路由 | 路由 prompt 要限定枚举输出并加 default 兜底 |

@@point ⑤ RAG Agent：从"固定流程"到"自主决策"
@@need 要解决什么
传统 RAG Pipeline 有个大毛病：**不管用户问什么，都去检索**，浪费 Token；检索结果不相关，也无法自我修正。怎么让 Agent 自己判断"要不要检索"？

@@idea 核心思路
**RAG + Agent 组合**——检索变成工具，要不要用由 Agent 决定：

```
传统RAG Pipeline（固定流程）：
用户提问 → 必须检索文档 → 生成回答
  问题1：不管问什么都会检索，浪费Token ❌
  问题2：检索结果不相关，无法自我修正 ❌

RAG Agent（自主决策）：
用户：你好 → Agent 判断不需要检索 → 直接回答 ✅
用户：公司的请假制度是什么？ → Agent 判断需要检索 → 调用检索工具 ✅
  检索结果不理想 → Agent 换关键词重新检索 → 自我修正 ✅
```

**RAG Agent 让 LLM 自主决定是否检索、用什么关键词检索、是否重试**——检索从"流程步骤"变成"待调用的工具"。

类比：传统 RAG = 每次出门都背百科全书（不管用不用）；RAG Agent = 需要时再查（手机查资料），还懂得换关键词再搜。

@@summary 这一章你学到了什么
- 理解 Agent 三合一：Tools（能力）+ Memory（记忆）+ Graph（流程）缺一不可
- 会用 create_agent + checkpointer + system_prompt 组装个人助手 Agent
- 看清单一 Agent 局限：工具堆积、提示词膨胀、无法支撑复杂多领域任务
- 掌握 Supervisor 主管模式：主管只做意图分析与任务路由，专业 Agent 执行，主管汇总
- 会用 LangGraph 状态图表达多 Agent 协作（Supervisor 中心节点 + 条件边路由）
- 掌握 RAG Agent：检索即工具，Agent 自主判断是否检索、换关键词、自我修正
- 对比传统 RAG 与 RAG Agent：减少无效检索、支持检索修正

下一部分：LangSmith 可观测——把黑盒 Agent 变成可视化流程，Token 消耗不再是个谜。

---

@@h1 附：LangSmith 调试与可观测性

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 不管用户问什么都先检索，Token 白白烧 | RAG Agent 要自主判断"是否需要检索"，不是固定流程 |
| 检索结果不相关也不修正 | Agent 应根据检索质量决定重检索或直接作答 |

@@point ① 为什么需要 LangSmith：黑盒三问
@@need 要解决什么
链式调用和 LangGraph 是黑盒：prompt 真正发给模型的内容是什么？哪一步耗时最长？今天跑 50 次花了多少 Token？没有工具，只能 print 调试。

@@idea 核心思路
LangSmith 解决的三个问题场景：

1. **LCEL 链式调用是黑盒**：chain.invoke 出了结果，但——prompt 发送给 LLM 的完整内容？LLM 返回了什么原始内容？parser 解析正确吗？哪一步耗时最长？全不知道
2. **LangGraph 执行流程不可见**：节点怎么走的、走了哪个分支、哪步报错，看不到
3. **Token 消耗是个谜**：跑了 50 次调用花了多少 Token？哪个 prompt 最耗？如何优化？没数据

**有 LangSmith**：每次调用自动记录完整链路（Trace）——输入输出、耗时、Token 一目了然；可视化展示执行流程和分支；错误直接定位到出错步骤；支持评估（Eval）对比不同 prompt 效果。

类比：没有仪表盘开车，只能凭感觉；LangSmith = 给代码装了个行车记录仪 + 仪表盘。

@@point ② LangSmith 快速上手：三步接入
@@need 要解决什么
怎么注册、怎么配置、怎么看到第一个 Trace？三步走。

@@idea 核心思路
**第一步：注册和获取 API Key**
1. 访问 https://smith.langchain.com
2. 注册账号（支持 GitHub / Google 登录）
3. 进入 Settings → API Keys → Create API Key
4. 复制 API Key（格式：lsv2_pt_xxx...）

**第二步：配置环境变量（推荐 .env）**
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your-key-here
LANGCHAIN_PROJECT=my-first-project
```
- `LANGCHAIN_TRACING_V2=true` 是开启追踪的开关：设置后**所有 LangChain 调用自动上报**
- API Key 是敏感信息，**不要提交到 Git 仓库**，确保 .env 在 .gitignore 中
- 代码里 os.environ 设置仅用于测试，不推荐

**第三步：跑通第一个 Trace**
```python
chain.invoke({"input": "你好"})
# → 打开 LangSmith 网页面板
# → 看到完整的调用链：prompt → llm → parser
```

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 面板里没有数据 | LANGCHAIN_TRACING_V2 没设成 "true" 或 API Key 配错 |
| API Key 泄漏到仓库 | .env 没进 .gitignore，Key 是敏感信息必须脱敏 |
| 不知道哪个项目的数据 | LANGCHAIN_PROJECT 没设，默认项目堆一起 |

@@point ③ Trace 面板解读
@@need 要解决什么
Trace 有了，怎么看？面板上那些层级、耗时、token 数字怎么读？Debug 时看哪里？

@@idea 核心思路
**Trace**：一次完整调用的链路记录，树形展开每一步：

```
Trace: ChatPromptTemplate | ChatOpenAI | ...
  ├─ ChatPromptTemplate：输入 → 渲染后 prompt（看模型实际收到什么）
  ├─ ChatOpenAI：模型调用（耗时、token、原始输出）
  └─ 解析/后处理（错误时直接定位到出错的步骤）
```

解读要点：
- **每层看三件事**：输入是什么、输出是什么、耗时多长
- **模型层重点看 token**：prompt_tokens / completion_tokens / total_tokens（成本核算依据）
- **报错场景**：Trace 直接标记出错节点——不再靠 print 猜

调试 LangGraph 同理：每个节点、每次工具调用、每次 interrupt 暂停点都有独立 span，整个图执行路径可视化。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 找不到 trace 或面板空白 | 检查 LANGCHAIN_API_KEY/环境变量，或模型后端是否支持 tracing |
| 只盯 LLM 调用不看工具链 | Trace 要看完整链路：prompt→LLM→工具→结果，瓶颈常藏在工具 |

@@point ④ LangSmith 在生产中的价值
@@need 要解决什么
"能跑"和"能上线"之间隔着观测与评估。LangSmith 在生产里到底提供什么？

@@idea 核心思路
生产可观测四件套：
1. **成本追踪**：每次调用的 token/费用，按 project 汇总——"今天 50 次调用花了多少""哪个 prompt 最耗 Token"有数据支撑
2. **性能监控**：延迟、错误率、失败定位——问题出现 5 分钟内发现
3. **评估（Eval）**：用数据集（如问答对）批量评测不同 prompt/模型效果，量化对比，"对比不同 prompt 的效果"不再是感觉
4. **协作与复现**：Trace 可分享、可回放，团队排查同一个 bug 时有共同视图

上线检查清单：TRACING 开启 ✅ → 项目命名规范 ✅ → 关键毒点（失败率/成本）设预警 ✅ → 定期跑 Eval 回归 ✅。

@@summary 附章你学到了什么
- 理解 LangSmith 的价值：链式黑盒 → 可视化 Trace，Token/耗时/错误全部可观测
- 三步接入：注册 → 配 LANGCHAIN_TRACING_V2 + API_KEY + PROJECT → 跑第一个 Trace
- API Key 安全：不提交 Git、.env 进 .gitignore
- 读懂 Trace 面板：树形展开、逐层看输入输出、模型层看 token、报错节点精准定位
- 掌握生产四件套：成本追踪、性能监控、Eval 评估、协作复现

下一章，从"单机 Agent"走向"Agent 互联"：A2A 跨 Agent 协作协议——Agent 之间如何发现彼此、派发任务、传递结果。

@@quiz
1. 完整 Agent 的三大组合要素是？
   A. Tools + Memory + Graph　　B. 数据库 + 前端 + 后端　　C. API + SDK + CLI　　D. 提示词 + 模型 + 温度
2. Supervisor（主管）模式中，主管 Agent 的职责是？
   A. 执行所有具体操作　　B. 分析用户意图并把任务路由给最合适的专业 Agent　　C. 管理数据库连接　　D. 训练模型
3. 传统 RAG Pipeline 的两个问题是？
   A. 无检索可用　　B. 不管问什么都会检索浪费 Token、检索结果不相关无法自我修正　　C. 回答太长　　D. 不能联网
4. RAG Agent 与传统的区别核心是？
   A. 检索变成工具，Agent 自主决定是否检索/换关键词/重试　　B. 提示词更长　　C. 模型更大　　D. 无区别
5. 开启 LangChain 调用自动上报 LangSmith 的开关是？
   A. LANGCHAIN_TRACING_V2=true　　B. DEBUG=true　　C. LOG_LEVEL=info　　D. USE_CACHE=true
6. LangSmith API Key 的正确处理方式是？
   A. 提交到 Git 方便共享　　B. 放在 .env 并确保 .gitignore 排除　　C. 写在代码注释里　　D. 输出到日志
7. 想量化对比不同 prompt 的效果，LangSmith 提供的功能是？
   A. 自动改写　　B. 评估（Eval）　　C. 代码生成　　D. 模型训练

@@links
参考|10_LLM框架实战_Agent实战.pdf|#
参考|11_LLM框架实战_LangSmith.pdf|#
官网|LangSmith 官方|https://smith.langchain.com/
教程|LangGraph 多 Agent 教程|#