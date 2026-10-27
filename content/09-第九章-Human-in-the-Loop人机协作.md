@@h1 第九章　Human-in-the-Loop：让 Agent 关键时刻等你审批
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
Agent 全自动跑会闯祸：全自动执行危险操作（转账、删库、退款）没人把关；全自动生成重要内容（合同、公告）出错没人发现。**把人类放进循环（Human-in-the-Loop, HITL）**：Agent 该快就快，该停就停——低风险自动执行，高风险人工审批。

本章掌握三个实战场景：**工具执行前审批**（interrupt + Command）、**人类修改 Agent 输出后重新提交**（反馈循环）、**条件式审批**（低风险自动，高风险暂停）。这是生产级 Agent 的必备技能。

@@map 这一章在整个知识库里的位置
上一章：MCP 协议——Agent 能连外部系统了
**本章** ← 你在这里：Human-in-the-Loop——关键动作等人类把关
下一章：Agent 实战与 LangSmith——把前面的能力组合成完整应用并做可观测
再往后：A2A → Skills

@@point ① 为什么要 HITL：全自动 Agent 的三大风险
@@need 要解决什么
先看清问题：全自动 Agent 不是"效率"，可能是"事故"。

@@idea 核心思路
三个典型翻车场景：
1. **危险操作**：转账、退款、删除数据——模型判断失误=真金白银损失
2. **重要内容**：合同、公告、法律文书——生成错误=声誉与合规风险
3. **不可逆动作**：一旦执行无法回滚——没有确认环节=追悔莫及

HITL 的作用：把决策权分层——**模型负责建议，人类负责最终裁决**。低风险环节全自动提速，高风险节点暂停确认。

关键认知：HITL 不是"降低效率"，而是"该快的快、该稳的稳"——风险管理与效率的平衡点。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 给所有工具都加 interrupt，用户被频繁打断 | 最小化人工介入：只在高风险/不可逆动作停，低风险全自动 |
| 审批信息只有一句"是否批准" | 要提供清晰上下文：做什么操作、影响多大，人类才能快速决策 |

@@point ② interrupt：在工具执行前"踩刹车"
@@need 要解决什么
怎么让 Agent 在执行某个动作前停下来，把决定权交给人？需要一种"暂停机制"。

@@idea 核心思路
**interrupt** 是 LangGraph 的暂停原语：在节点/工具内部调用，图立即暂停，返回当前状态等人类处理。

```python
from langgraph.types import interrupt

def process_refund(order_id: str, reason: str) -> str:
    """处理退款。此操作需要人工审批。"""
    # 工具执行前暂停，等待人类审批
    approval = interrupt(
        f"⚠️ 退款审批请求\n"
        f"订单号：{order_id}\n"
        f"退款原因：{reason}\n"
        f"请确认是否批准退款？"
    )
    # 人类 resume 后，从这里继续执行
    if approval == "approve":
        return f"✅ 订单 {order_id} 退款已批准"
    else:
        return f"❌ 订单 {order_id} 退款已拒绝"
```

执行流程：invoke 进入 process_refund → 遇到 interrupt → **图暂停并返回待处理状态** → 人类做出决定 → `Command(resume=...)` 恢复 → 从 interrupt 那行继续。

类比：interrupt = 高速公路上的检查站，先停车接受检查，放行后再继续赶路。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| interrupt 一调用程序就"结束"了 | interrupt 不是报错而是暂停，需要后续用 Command(resume) 恢复执行 |
| 恢复后状态丢失 | resume 必须用同一个 thread_id 对应的 config 调用，否则找不到暂停点 |

@@point ③ Command(resume)：人类审批后恢复执行
@@need 要解决什么
图停下来了，人类审批"通过/拒绝"，怎么把决定传回给图并继续跑？

@@idea 核心思路
用 **Command(resume=审批结果)** 恢复：

```python
# 检查是否被 interrupt 暂停
# invoke 返回当前状态，可检查是否有待处理 interrupt

# 方式1：批准
result = app.invoke(
    Command(resume="approve"),   # 传入 "approve" 批准
    config
)
# 输出：✅ 订单ORD002退款已批准

# 方式2：拒绝
result = app.invoke(
    Command(resume="reject"),    # 传入 "reject" 拒绝
    config
)
# 输出：❌ 订单ORD002退款已拒绝
```

两种"人类审批"形态：
- **方式1 - 简单确认**：`Command(resume="approve")` 传固定值，分支处理
- **方式2 - 修改重提**：`Command(resume="语气太正式了，加上一句感谢王…")` 传自由文本反馈——适合"内容审批"场景（改邮件/文案后重新生成）

Command 是"恢复执行"的通用入口：resume 的值就是 interrupt 的返回值，图从断点继续。

@@point ④ 审批模式实战：工具执行前人工确认
@@need 要解决什么
典型场景：给"危险工具"（退款/发钱/删数据）加审批，套上"执行前确认"的流程。

@@idea 核心思路
完整链路：

```python
from langgraph.prebuilt import ToolNode, tools_condition

# 1. 危险工具内置 interrupt（见第②点 process_refund）
# 2. 正常的 agent + tools 图
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode([process_refund, other_tools]))
graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

# 3. 编译时必须带 checkpointer（interrupt 依赖断点恢复）
memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# 4. 首次调用：触达 interrupt，返回"暂停"状态
result = app.invoke({"messages": [("user", "帮我退款订单ORD002")]}, config)

# 5. 人工审批后恢复
result = app.invoke(Command(resume="approve"), config)
```

⚠️ **interrupt 必须配合 checkpointer**：暂停/恢复的本质是"断点存档+恢复"，没有 checkpointer 无法恢复执行。

类比：审批工具 = 保险柜的钥匙孔，柜员（Agent）只能把申请递到孔前，必须主管（人类）转钥匙（approve）才打得开。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| compile() 忘记传 checkpointer，暂停后状态丢失 | interrupt 依赖断点恢复，没 checkpointer 是最常见错误 |
| resume 时用错 thread_id 找不到暂停点 | 恢复执行必须用同一个 config/thread_id |

@@point ⑤ 反馈循环：人类修改输出并重新提交
@@need 要解决什么
内容类任务（写邮件/文案/合同）不只需要"通过/拒绝"，还要"改一下再生成"。如何实现"不满意→修改意见→重新生成"的循环？

@@idea 核心思路
把人类反馈作为新消息注入，让模型带反馈重写：

```python
# 1. 生成阶段：Agent 产出初稿（如邮件）
# 2. interrupt 暂停，呈现：原始需求 + 初稿 + "请审阅，可直接给出修改意见"

# 3. 人类反馈通过 Command(resume) 传回
result = app.invoke(
    Command(resume="语气太正式了，加上一句感谢王总的长期合作"),
    config
)

# 4. 调试节点处理反馈：把人类反馈作为新的 HumanMessage 注入
#    → 模型看到"初稿 + 修改意见" → 重新生成 → 展示新稿
```

反馈循环的实现要点：
- 人类反馈（resume 值）转成 HumanMessage 注入消息流
- 模型基于"原文+反馈"重写，而非从头生成
- 可循环多次：不满意再次 interrupt，直到通过

类比：写作审批 = 批注式审稿，审稿人（人类）不用重写，只写"这里改一下"，作者（Agent）按批注修订。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 人类反馈后 Agent 直接返回不重新生成 | 反馈要作为新输入交给 LLM 重新生成，循环没闭合 |
| 草稿和修改意见混在一起丢给模型 | 上下文要区分"草稿"与"反馈"，否则模型不知道改哪 |

@@point ⑥ 条件式审批：低风险自动、高风险人工
@@need 要解决什么
所有操作都暂停，Agent 就废了。怎么做到"小额自动、大额审批"这类分级策略？

@@idea 核心思路
**根据条件决定是否 interrupt**——"低风险自动执行、高风险人工审批"设计模式：

```python
def process_payment(amount: float, recipient: str) -> str:
    if amount < 1000:          # 低风险：自动执行
        return transfer(amount, recipient)
    else:                       # 高风险：人工审批
        approval = interrupt(
            f"大额转账审批\n金额：{amount}\n收款方：{recipient}\n请批准？"
        )
        if approval == "approve":
            return transfer(amount, recipient)
        return "已拒绝"
```

设计要点：
- **阈值/条件由业务规则定义**（金额、白名单、时间、频次）
- 条件放工具内部，interrupt 放在高风险分支
- 同样的模式套用到所有"风险分级"场景：删除（垃圾箱✓/永久删除✋）、外发（内部✓/对外✋）、批量（单个✓/批量✋）

类比：小额取款 ATM 直接出钞，大额取款必须柜台核验身份证——风控分级，效率与安全兼得。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 风险判断全写在代码 if-else 里，规则一多就乱 | 把风险分级抽成配置策略（金额/类型/影响范围） |
| 低风险操作也走 interrupt | 违背条件式设计，永远只在高风险时停顿 |

@@point ⑦ HITL 架构总结与最佳实践
@@need 要解决什么
interrupt/Command/条件审批用哪套组合？生产里有哪些经验法则？

@@idea 核心思路
**HITL 架构总结**：

```
用户请求
  └▶ Agent 执行（自动）
       ├▶ 低风险操作 → 直接执行 → 完成
       └▶ 高风险操作 → interrupt 暂停
            └▶ 人类审批（approve/reject/修改意见）
                 └▶ Command(resume) 恢复 → 继续执行
```

最佳实践清单：
1. **interrupt 的消息要说清楚**：要做什么、影响是什么——人类 5 秒内看懂才能果断决定
2. **审批范围宁小勿大**：只对不可逆/高风险/高影响操作加审批，别把每步都拦
3. **默认拒绝**：超时未审批 = 拒绝（安全默认），别默认放行
4. **记录审批日志**：谁、在哪一步、批了什么——审计追溯（合规必备）
5. **给人类提供"修改"而非只有"通过/拒绝"**：自由度更高的审批体验

@@point ⑧ HITL 决策树与生产落地：把"该不该停"变成规则
@@need 要解决什么
三种 HITL 模式都学了，但实战中到底哪些操作要审批、哪些直接放行？需要一条可执行的判断规则。

@@idea 核心思路
决策树判断顺序：
1. 操作**是否不可逆**（删除、转账、发布）？→ 是 → 必须审批
2. 金额 / 影响**是否超过阈值**（如退款 >5000 元）？→ 是 → 审批
3. 内容**是否对外发送**（邮件、公告、合同）？→ 是 → 审核
4. 都不满足 → 自动执行，不打断用户

配套最佳实践：
- **最小化人工介入**：只在真正需要时 interrupt，避免频繁打断失去自动化意义
- **提供清晰上下文**：审批消息说清楚"做什么、影响什么"，人类秒决策
- **风险分级可配置**：金额/类型/影响范围做成策略配置，不写死在代码里
- **记录审批日志**：谁在什么时间批了什么，方便审计追溯

类比：机场安检——危险品必检（不可逆/超阈值），普通行李直接放行（低风险）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 决策规则用 if-else 写死在工具里，改阈值要改代码 | 风险分级抽成配置（金额阈值/危险类型），上线后随时调 |
| 审批行为不留日志 | 审计要求"谁、何时、批了什么"可追溯，审批日志是合规刚需 |

@@summary 这一章你学到了什么
- 理解 HITL 的价值：低风险自动、高风险人工，效率与安全平衡
- 掌握 interrupt：在工具执行前暂停并返回当前状态，等人类处理
- 掌握 Command(resume)：approve/reject 传值或传修改意见，从断点恢复
- 知道 interrupt 必须配合 checkpointer（断点存档）才能恢复
- 会用审批模板：危险工具内置 interrupt + 主流程条件路由 + resume 恢复
- 会构建反馈循环：修改意见作为消息重新注入，模型带反馈重写
- 掌握条件式审批：阈值/白名单分级，低风险绕过 interrupt 直接执行
- 记住最佳实践：消息说清影响、审批宁小勿大、默认拒绝、留审计日志

下一章，把前九章全部组合成完整 Agent 应用，并用 LangSmith 做可观测：Agent 实战与 LangSmith——从工具定义、多 Agent 协作到运行监控、成本追踪。

@@quiz
1. Human-in-the-Loop 的核心价值是？
   A. 让人类接管全部工作　　B. 低风险自动执行、高风险人工审批　　C. 完全去掉人工　　D. 让模型自己审批自己
2. interrupt 的作用是？
   A. 报错中断程序　　B. 在节点/工具内部暂停图执行，等待人类处理　　C. 加速执行　　D. 删除状态
3. 恢复被 interrupt 暂停的图，应该用？
   A. 重新 invoke　　B. Command(resume=审批结果)　　C. 重启电脑　　D. 修改代码再跑
4. interrupt 必须配合什么才能正常暂停恢复？
   A. 数据库　　B. checkpointer（MemorySaver 等）　　C. API Key　　D. 显卡
5. 人类"修改意见"反馈循环的实现方式是？
   A. 人类直接改代码　　B. 反馈作为消息重新注入，模型带反馈重写　　C. 丢弃重新生成　　D. 写死答案
6. 条件式审批的核心设计模式是？
   A. 全部人工　　B. 全部自动　　C. 低风险自动执行、高风险人工审批　　D. 随机决定
7. interrupt 消息的最佳实践是？
   A. 越短越好　　B. 说清楚要做什么、影响是什么　　C. 用英文　　D. 不显示

@@links
参考|09_LLM框架实战_HumanInTheLoop进阶.pdf|#
官网|LangGraph HITL 概念|https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
官网|LangGraph Human in the Loop 教程|https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
官网|interrupt 参考|https://reference.langchain.com/python/langgraph/