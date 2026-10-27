@@h1 第十二章　LangGraph 工作流与 AI 对话
@@sub 阶段 10 · 安康智慧健康管理平台（糖尿病AI健康助手）　|　难度 ★★★★★

@@why 这一章在解决什么问题
前面所有模块都在造零件，本章把它们**装成一台会对话的机器**：患者发一句"最近血糖高了怎么办"，系统要识别意图 → 调取患者档案 → 检索医学知识 → 生成建议 → 评估风险。五个步骤有先后、有分支，用 LangGraph 状态图表达。本章解决三件事：**一是 LangGraph 状态图的基本概念**（State/TypedDict/节点/边/编译），**二是五节点工作流的设计**（每个节点干什么、状态怎么流转），**三是 chat 路由如何接住工作流**（对话持久化与响应构造）。

关键认知：**LangGraph 把"流程"变成了"可编排的状态图"**——每一步都显式声明输入输出，比在一段函数里写 if 金字塔清晰得多，也方便后续加分支、加人工确认。

@@map 这一章在整个知识库里的位置
上一章：RAG 医学知识库（资料库就绪）
**本章** ← 你在这里：LangGraph 工作流——把档案/统计/RAG/LLM/风险全部编排成对话
阶段终点：全平台闭环——患者数据 → 意图理解 → 知识检索 → 个性化回答

@@point ① LangGraph 是什么：状态图思维
@@need 要解决什么
多步 AI 流程用普通函数写会怎样？——耦合、难调试、加一步要改全链路。怎么办？

@@idea 核心思路
LangGraph 是 LangChain 官方的**图编排框架**，核心模型：

- **State（状态）**：全程共享的数据结构（患者ID、意图、检索结果、回复……全程累积传递）；
- **Node（节点）**：一个处理步骤（async 函数），读 State、改 State；
- **Edge（边）**：节点间的流转关系（从 A 到 B，或条件分支）；
- **Graph（图）**：把节点和边组装成可执行的工作流，`compile()` 后 `ainvoke()` 运行。

```
┌─────────┐    ┌────────────┐    ┌─────────┐    ┌────────┐    ┌───────────┐
│ classify │ → │ load_context│ → │ retrieve│ → │ generate│ → │ assess_risk│ → END
│ 意图识别 │    │ 患者档案    │    │ 知识检索 │    │ AI生成  │    │ 风险评估  │
└─────────┘    └────────────┘    └─────────┘    └────────┘    └───────────┘
```

类比记忆：**State 是"会上共用的笔记本"**——每个节点往上面记几笔，下一个节点接着读接着写。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把流程写成一个大函数 | 每一步耦合、无法单独测；图编排让节点可独立调试 |
| 节点想"返回数据"给下一步 | 节点只改 State，不直接 return 数据给下一个节点；数据全走 State |

@@point ② AgentState：用 TypedDict 定义状态结构
@@need 要解决什么
全程共享的"笔记本"长什么样？每个字段是干什么的？

@@idea 核心思路
```python
from typing import TypedDict

class AgentState(TypedDict, total=False):
    patient_id: int          # 患者ID
    input_type: str          # 意图分类结果
    user_message: str        # 用户原始消息
    patient_context: str     # 患者档案文本
    blood_sugar_data: Optional[Dict]  # 血糖统计数据（结构化）
    rag_context: str         # RAG检索结果
    recommendations: str     # LLM生成的建议
    risk_level: str          # 风险等级
    response: str            # 最终回复（建议+警告）
```

三个要点：
- **TypedDict**：类型声明，IDE 自动补全、写错字段名立刻报错；
- **total=False**：字段不必全部填充，未赋值的默认 None/空——节点可以只写自己负责的字段；
- **全程累积**：classify 写 input_type，load_context 写 patient_context……到最后 response 组装完成，**每个节点的产物既服务下一节点，也是最终输出的组成部分**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘写 total=False | 所有字段强制必填，开局构造 State 就报错 |
| State 字段命名漂移 | 节点间靠字段名传值；大小写/下划线不一致直接断链 |

@@point ③ 节点一：classify_input 意图识别
@@need 要解决什么
"我想知道能吃什么"和"最近血糖怎么样"要用不同的知识库分类与流程——第一步先听懂用户关心什么。

@@idea 核心思路
```python
async def classify_input(state: AgentState) -> AgentState:
    message = state['user_message'].lower().strip()
    if any(keyword in message for keyword in ['血糖', 'mmol', '测量', '记录血糖']):
        input_type = 'blood_sugar'
    elif any(keyword in message for keyword in ['饮食', '吃', '食物', '食谱', '营养', '能吃什么']):
        input_type = 'diet_query'
    elif any(keyword in message for keyword in ['用药', '药', '胰岛素', '打针', '二甲双胍']):
        input_type = 'medication_query'
    else:
        input_type = 'health_query'
    state['input_type'] = input_type
    return state
```

四类意图与关键词清单：
| 意图 | 关键词 | 后续影响 |
|---|---|---|
| blood_sugar | 血糖/mmol/测量/记录血糖 | RAG 查"血糖管理"分类 |
| diet_query | 饮食/吃/食物/食谱/营养/能吃什么 | RAG 查"饮食管理"分类 |
| medication_query | 用药/药/胰岛素/打针/二甲双胍 | RAG 查"用药管理"分类 |
| health_query | 兜底 | RAG 全库检索 |

**规则关键词识别**是"轻量意图分类"——本项目刻意不用模型做分类（快、稳定、零成本）；复杂场景才升级为 LLM 分类器。分支的"分岔点"在 retrieve 节点消费 input_type。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 关键词没覆盖口语 | "能吃点啥"也要能命中；关键词清单按用户真实问法扩充 |
| 意图与分类映射写错 | _INTENT_CATEGORY_MAP 里 blood_sugar→"血糖管理"；映射错 RAG 查空 |
| 想用 LLM 做意图 | 量小用规则即可；规则足够稳定就不要引入模型调用 |

@@point ④ 节点二：load_patient_context 患者档案装配
@@need 要解决什么
AI 回答要"懂这个人"——姓名、BMI、病史、近7天血糖，都从哪来？怎么拼成一段话？

@@idea 核心思路
```python
async def load_patient_context(state: AgentState) -> AgentState:
    patient = await Patient.get_or_none(id=state['patient_id'])
    if patient:
        bg_analysis = await health_analyzer.analyze_blood_sugar(patient.id, days=7)
        bg_summary = health_analyzer.generate_summary(bg_analysis)
        context = f"""患者信息：
        - 姓名：{patient.name}，年龄：{patient.age}岁，性别：{patient.gender}
        - 糖尿病类型：{patient.diabetes_type}
        - BMI：{patient.bmi}（{patient.bmi_category}）
        - 病史：{patient.medical_history or '无特殊'}
        - 过敏：{patient.allergies or '无'}
        - 近7天血糖概况：{bg_summary}"""
        state['patient_context'] = context
        state['blood_sugar_data'] = bg_analysis   # 结构化数据给风险评估用
    else:
        state['patient_context'] = "(未找到患者档案)"
    return state
```

本节点演示"**把诉求转成语义文本**"：
- **档案模板化**：姓名/年龄/BMI（计算属性！）/病史/过敏 + 血糖概况，全部拼进一段上下文；
- **一份统计两处使用**：`bg_summary` 进档案文本（给 LLM），`bg_analysis` 单独存（给 risk 节点算风险等级）——**同一数据，文本给生成、结构化给判定**；
- **查无此人的兜底**：患者不存在时档案写"(未找到患者档案)"，不中断流程。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| blood_sugar_data 不单独存 | risk 节点还要重算一遍统计；状态里存结构化副本避免重复查询 |
| 患者档案包含敏感信息 | 姓名/病史/过敏会进 LLM 提示词——本项目为教学单机场景，生产须经授权与脱敏 |
| medical_history 为空直接拼 None | `or '无特殊'` 兜底，模板永不留白 |

@@point ⑤ 节点三：retrieve_knowledge 知识分流检索
@@need 要解决什么
意图已定，怎么按意图挑知识库分类去检索？

@@idea 核心思路
```python
async def retrieve_knowledge(state: AgentState) -> AgentState:
    input_type = state.get("input_type", "")
    if input_type == "health_query":
        # 通用问题：不限分类，全库检索
        state['rag_context'] = rag_engine.retrieve(query=state['user_message'], category=None)
    else:
        _INTENT_CATEGORY_MAP = {
            "blood_sugar": "血糖管理",
            "diet_query": "饮食管理",
            "medication_query": "用药管理",
        }
        category = _INTENT_CATEGORY_MAP.get(input_type, "")
        state['rag_context'] = rag_engine.retrieve(
            query=state['user_message'], category=category)
    return state
```

分流逻辑：
- **health_query（兜底类）**：不限定分类，全库语义检索——如"糖尿病并发症有哪些"跨 3 个分类，全库才能覆盖；
- **三类明确意图**：映射到对应分类，只在"饮食管理"里找，精准且快；
- 输出 `rag_context`（带编号引用的文本）给 generate 节点。

**这是第十一章 category 设计的直接消费点**——分类结构服务意图分流，环环相扣。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| health_query 也按分类查 | 跨类问题会漏知识；兜底意图必须全库检索 |
| 映射表里意图名拼错 | category 为空 → 检索退化待查空；核对四键值 |
| 忘把检索结果写进 state | generate 节点拿不到 rag_context，回答就没了"资料" |

@@point ⑥ 节点四：analyze_and_generate 提示词组装与生成
@@need 要解决什么
患者档案 + 医学知识 + 用户问题，怎么组装成一段高质量的 system prompt 让模型回答？

@@idea 核心思路
```python
async def analyze_and_generate(state: AgentState) -> AgentState:
    system_prompt = f"""你是糖尿病健康管理AI助手。请根据以下信息为患者提供个性化建议。
    {state.get('patient_context', '')}

    相关医学知识：
    {state.get('rag_context', '')}
    请提供：
    1. 对患者当前状况的分析
    2. 具体可执行的建议
    3. 需要注意的事项

    请用温和关怀的语气，给出简洁实用的建议。"""
    response = llm_client.chat(system_prompt=system_prompt,
                               user_message=state['user_message'])
    state['recommendations'] = response
    return state
```

提示词三段式（写 AI 助手的黄金模板）：
1. **角色设定**："你是糖尿病健康管理AI助手"——定身份与边界；
2. **信息供给**：患者档案 + 相关医学知识（RAG 结果）——**给足上下文，模型才有依据**；
3. **输出约束**：分析/建议/注意事项三件套 + "温和关怀语气"——定结构与语气。

**注意用户消息绝不拼进 system_prompt**：`user_message` 原样作为 user 消息传给 chat 方法，身份（system）与提问（user）分离是规范。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把用户消息拼进 system | 身份与提问混淆，模型分不清"你是谁"；保持 system/user 分离 |
| 没给 RAG 上下文就直接问 | 回答失去"资料依赖"，回到记忆力幻觉模式 |
| 提示词没有输出约束 | 模型自由发挥结构混乱；三件套约束稳定输出 |

@@point ⑦ 节点五：risk_assessment 风险兜底
@@need 要解决什么
LLM 说了一堆好话，但患者血糖其实很危险——风险评估怎么成为"安全刹车"？

@@idea 核心思路
```python
async def risk_assessment(state: AgentState) -> AgentState:
    bg_data = state.get('blood_sugar_data', {})
    risk_level = bg_data.get('risk_level') or "低风险"
    state['risk_level'] = risk_level
    warning = ""
    if risk_level == "高风险":
        warning = "\n\n⚠️ **高风险警告**：您的血糖控制不理想，建议尽快联系主治医生调整治疗方案。"
    elif risk_level == "中风险":
        warning = "\n\n⚡ **提醒**：近期血糖波动较大，请注意饮食和用药规律。"
    state["response"] = state.get('recommendations', '') + warning
    return state
```

设计精髓：
- **规则补刀不靠模型**：风险等级由 health_analyzer 用医学规则算（非 LLM）——**急救信息绝不让模型"自由发挥"**；
- **高/中/低三档警告文案**：高风险直接建议就医（语气最重），中风险提醒规律，低风险不加警告；
- **response = 建议 + 警告**：LLM 答案保留，规则警告**追加**在末尾——两套系统各司其职、互不覆盖。

这是全工程的安全设计制高点：**生成靠 AI，安全兜底靠规则**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把风险判定交给 LLM | 医疗安全红线：判定必须规则化、确定性、可审计 |
| 高风险患者没收到就医提示 | 高风险分支必须存在；warning 文案按等级分级 |
| 警告覆盖了模型建议 | 用 `+` 拼接追加而非替换；两条信息都要到达用户 |

@@point ⑧ 工作流编译与 chat 路由接线
@@need 要解决什么
五个节点怎么编译成图？对话接口怎么调用它、怎么落库？

@@idea 核心思路
编译：
```python
def create_agent_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("classify", classify_input)
    workflow.add_node("load_context", load_patient_context)
    workflow.add_node("retrieve", retrieve_knowledge)
    workflow.add_node("generate", analyze_and_generate)
    workflow.add_node("assess_risk", risk_assessment)
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "load_context")
    workflow.add_edge("load_context", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "assess_risk")
    workflow.add_edge("assess_risk", END)
    return workflow.compile()

agent_app = create_agent_workflow()        # 模块级编译一次

async def run_agent(patient_id, user_message) -> Dict:
    initial_state = { "patient_id": patient_id, "user_message": user_message, ... }  # 完整初始状态
    result = await agent_app.ainvoke(initial_state)
    return {"response": result['response'], "risk_level": result['risk_level'],
            "input_type": result['input_type'], "blood_sugar_data": result['blood_sugar_data']}
```

chat 路由（第五章已见雏形）：
```python
@router.post("/message", response_model=ChatResponse)
async def send_message(data: ChatMessage):
    user_msg = await ChatHistory.create(patient_id=data.patient_id, role="user", content=data.message)
    result = await run_agent(data.patient_id, data.message)     # 触发工作流
    ai_msg = await ChatHistory.create(patient_id=data.patient_id, role="assistant", content=result["response"])
    return ChatResponse(...)
```

闭环总结：**消息持久化（user）→ 工作流执行 → 回复持久化（assistant）→ 响应返回**。历史接口再按 patient_id 倒序取对话记录——AI 对话的"记忆"由此而来（本流程未回填历史给 LLM，属简化设计）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 节点加了忘加边 | 图只有孤立节点，流程走不通；每个 add_node 都要配 set_entry_point/add_edge |
| 初始 state 字段不齐 | ainvoke 时缺字段节点取不到；按 AgentState 全字段初始化 |
| 对话历史未回填 | 本项目每轮独立调用 LLM（无多轮上下文）；生产可把历史传入 chat 的 chat_history 参数 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **LangGraph 状态图范式** | TypedDict 定义 State + 节点改状态 + 边定流向，多步 AI 流程可编排可调试 |
| **五节点智能体设计** | 意图识别→档案→RAG→生成→风险，每个节点单一职责、前后数据靠 State 传递 |
| **生成与安全双轨制** | LLM 负责表达，规则负责医疗安全判定；高风险警告绝不出自模型之口 |

@@quiz
1. LangGraph 中 State、Node、Edge 各自是什么？"共用笔记本"比喻对应哪个概念？
2. total=False 的作用？忘记它会发生什么？
3. 四个意图（blood_sugar/diet_query/medication_query/health_query）分别命中什么关键词？RAG 检索差异在哪？
4. load_patient_context 为什么把同一份血糖统计存两份（summary 文本 + 结构化 dict）？
5. generate 节点组装提示词要注意哪两条纪律（身份/提问分离、上下文必须给）？
6. 为什么风险警告必须由规则引擎而非 LLM 生成？三档警告文案分别怎么处理？
7. 整个 AI 对话闭环的数据流是怎样的（从用户发消息到最后响应落库）？

@@links
参考|安康智慧健康管理平台：糖尿病AI健康助手|#
官网|LangGraph 官方文档|https://docs.langchain.com/oss/python/langgraph/overview
官网|LangGraph StateGraph 指南|https://docs.langchain.com/oss/python/langgraph/overview