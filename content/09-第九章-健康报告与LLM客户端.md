@@h1 第九章　健康报告与 LLM 客户端
@@sub 阶段 10 · 安康智慧健康管理平台（糖尿病AI健康助手）　|　|　难度 ★★★★

@@why 这一章在解决什么问题
血糖分析算出了数字，可患者要看的是"医生怎么说"——**把统计数字变成人话**，这就是 LLM 的工作。本章同时拿下两件事：**一是 LLMClient 封装**（为什么把 LangChain 的 ChatOpenAI 包一层），**二是健康报告生成接口**（周报/月报自动生成：统计 → 摘要 → LLM 建议 → 落库展示）。

关键认知：**LLM 是"文本生成器"，不是"计算器"**——所有数字必须由 health_analyzer 算好、拼进提示词，LLM 只负责"组织语言给建议"。把计算交给模型是新手最常见的错误。

@@map 这一章在整个知识库里的位置
上一章：DietAdvisor 规则引擎
**本章** ← 你在这里：LLM 客户端 + 健康报告——第一次让大模型开口说话
再往后：RAG 医学知识库（给 LLM 装知识）→ LangGraph（把流程串起来）
阶段终点：报告接口从"纯统计"升级为"统计+AI 建议"

@@point ① LLMClient：为什么包一层
@@need 要解决什么
直接用 langchain_openai 的 ChatOpenAI 不就行了？为什么要自定义一层 LLMClient？

@@idea 核心思路
```python
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

class LLMClient:
    def __init__(self):
        api_key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
        base_url = os.getenv("LLM_BASE_URL")
        temperature = os.getenv("LLM_TEMPERATURE")
        max_tokens = os.getenv("LLM_MAX_TOKENS")
        self._llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat(self, system_prompt: str, user_message: str,
             chat_history: Optional[List[Dict]] = None) -> str:
        ...
```

封装的三层价值：
1. **配置集中**：Key/模型/地址全从 .env 读，业务代码不感知"换模型"；
2. **职责收敛**：调用方只传 system_prompt + user_message + 可选历史，不碰消息对象组装；
3. **容错统一**：异常兜底返回友好文案，不会让 50 处调用各写一遍 try/except。

**OpenAI 兼容协议**：`LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` 是关键——阿里云 DashScope 提供 OpenAI 兼容端点，所以 ChatOpenAI 直接可用，模型填 `qwen3.7-max`。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 没设 base_url 报 401/404 | 默认打 OpenAI 官方域名；必须配 DashScope 兼容端点 |
| Key 从代码硬编码 | 必须走 .env；本项目 config.py 用 os.getenv 统一读 |
| 异常直接把堆栈抛给用户 | 工程要求：LLMClient.chat 内部 try/except，返回"暂时无法响应"引导文案 |

@@point ② chat 方法：消息组装的艺术
@@need 要解决什么
大模型对话不只是"发一句话"——系统角色、历史消息、当前提问怎么组合？

@@idea 核心思路
```python
def chat(self, system_prompt: str, user_message: str,
         chat_history: Optional[List[Dict]] = None) -> str:
    # 1. 系统提示词（设定角色）
    messages = [SystemMessage(content=system_prompt)]
    # 2. 对话历史（只取最近10条）
    if chat_history:
        for msg in chat_history[-10:]:
            role = msg.get("role"); content = msg.get("content")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "bot"):
                messages.append(AIMessage(content=content))
    # 3. 当前提问
    messages.append(HumanMessage(content=user_message))
    # 4. 调用模型
    try:
        response = self._llm.invoke(messages)
        return str(response.content)
    except Exception as e:
        return f"抱歉，医学助手暂时无法响应，请稍后再试或咨询医生。错误信息: {e}"
```

三处细节：
- **SystemMessage 开头**：全局设定"你是糖尿病健康管理专家"，约束说话方式；
- **历史截断 10 条**：`chat_history[-10:]` 只取最近，既控 token 又防上下文漂移；
- **角色映射**：历史里 user → HumanMessage、assistant/bot → AIMessage，LangChain 消息类型与角色一一对应。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 历史消息顺序颠倒了 | 必须按时间正序拼接，最后是当前提问；乱序会毁掉上下文理解 |
| 把历史全塞进去 token 爆炸 | 只取最近 10 条；长对话靠截断保命 |
| 角色字段叫别的名字 | 本协议限定 user/assistant；其他角色名要归一化再做映射 |

@@point ③ 健康报告业务流程：五步流水线
@@need 要解决什么
"生成一份周报"背后发生了什么？数据、统计、AI、落库怎么串？

@@idea 核心思路
`POST /reports/generate/{patient_id}?report_type=周报` 的完整流水线：

```python
@router.post("/generate/{patient_id}", response_model=HealthReportResponse)
async def generate_report(patient_id: int, report_type: str = Query(default="周报")):
    patient = await Patient.get_or_none(id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    days = 7 if report_type == "周报" else 30 if report_type == "月报" else 0

    # 第2步：血糖分析（health_analyzer）
    analysis = await health_analyzer.analyze_blood_sugar(patient_id, days)
    # 第3步：生成数值摘要（还是规则逻辑）
    summary = health_analyzer.generate_summary(analysis)
    # 第4步：LLM 生成专家建议
    if analysis.get('error'):
        recommondations = "血糖数据不足，无法生成报告。"
    else:
        prompt = f"请根据以下{report_type}数据生成健康建议：\n{summary}\n\n请给出3-5条具体建议。"
        recommondations = llm_client.chat(
            system_prompt="你是糖尿病健康管理专家，请给出简洁实用的健康建议。",
            user_message=prompt,
        )
    # 第5步：落库
    report = await HealthReport.create(
        patient_id=patient_id, report_type=report_type,
        period_start=date.today() - timedelta(days=days),
        period_end=date.today(),
        avg_blood_sugar=analysis.get('avg', 0),
        blood_sugar_std=analysis.get('std', 0),
        time_in_range=analysis.get('time_in_range', 0),
        summary=summary, recommendations=recommondations,
        risk_level=analysis.get('risk_level') or "低风险",
    )
    ...
```

五步走：**验患者 → 算统计 → 编摘要 → 让 AI 建议 → 报告落库**。注意"数据不足"分支：analysis 有 error 时**不调 LLM**，直接写死文案——无数据时大模型没有输入素材，生成就是空转。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 无血糖数据还硬调 LLM | error 分支必须短路；数据不足生成"无法生成报告"即可 |
| report_type 传"年报" | days=0，周期区间全错；先做枚举校验（周报/月报） |
| summary 与 recommendations 一条空一条有 | 两者分开落库；summary 是统计摘要，recommendations 是 AI 建议 |

@@point ④ generate_summary：把统计字典变成一句话
@@need 要解决什么
analysis 是字典，怎么把它变成"近7天血糖概况：共记录12次…"这种可读摘要？

@@idea 核心思路
```python
def generate_summary(self, analysis: Dict[str, Any]) -> str:
    if analysis.get('error'):
        return str(analysis['error'])
    summary = (
        f"近{analysis['period_days']}天血糖概况：共记录{analysis['record_count']}次，"
        f"平均值{analysis['avg']} mmol/L，范围{analysis['min']}-{analysis['max']} mmol/L。"
        f"达标率{analysis['time_in_range']}%，趋势{analysis['trend']}。"
    )
    if analysis.get('low_count', 0) > 0:
        summary += f"⚠️ 发生{analysis['low_count']}次低血糖，需关注。"
    if analysis.get('high_count', 0) > 0:
        summary += f"⚠️ 发生{analysis['high_count']}次高血糖，注意控制饮食。"
    return summary
```

设计意图：
- **这是"模板文本"，不是 LLM 生成**——保证报告核心数据永远准确、格式稳定；
- **异常条件追加**：低血糖/高血糖次数 >0 才附加警示句，正常时简介利落；
- **给 LLM 当素材**：summary 字符串拼进 prompt，模型基于"确定的事实"展开建议——杜绝幻觉数字。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把统计数值直接交给 LLM 自行引用 | 模型可能算错或编造；必须先由规则生成 summary 再喂给模型 |
| error 分支返回的不是字符串 | str() 包装保证返回值类型统一为 str |
| 警告文案缺标点 | summary 各句以句号结尾，LLM 拼接才不会粘连 |

@@point ⑤ HealthReport 模型落库与查询
@@need 要解决什么
生成的报告存哪？历史报告怎么查？

@@idea 核心思路
HealthReport 模型（第七章 models 之一）核心字段：
- `report_type`：周报/月报；`period_start / period_end`：统计周期；
- `avg_blood_sugar / blood_sugar_std / time_in_range`：**关键指标快照**（生成时固化，历史不随新数据漂移）；
- `summary / recommendations`：摘要与 AI 建议；
- `risk_level`：风险等级快照；`generated_at`：生成时间（auto_now_add）。

历史查询接口：
```python
@router.get("/patient/{patient_id}", response_model=List[HealthReportResponse])
async def get_reports(patient_id: int, limit: int = Query(default=10, le=50)):
    ...
    reports = await HealthReport.filter(patient_id=patient_id) \
        .order_by("-generated_at").limit(limit)
```

**"快照"思维是本例精髓**：报告保存的是生成那一刻的指标值，而不是引用患者血糖表——患者后来新增记录，历史报告不会被"篡改"。这是报告类系统的通用设计。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报告里引用实时血糖表 | 新记录会改变旧报告数据；必须落库快照字段 |
| limit 不设上限 | Query(le=50) 防一次拉爆；列表页分页取 |
| 忘了 order_by 最新在前 | 报告要看"最近的"；-generated_at 倒序 |

@@point ⑥ 响应构造与 fetch_related
@@need 要解决什么
报告生成后怎么返回？外键（patient）怎么在响应里带上？

@@idea 核心思路
```python
await report.fetch_related("patient")   # 预取关联对象（虽然响应只用了 patient_id）
return HealthReportResponse(
    id=report.id,
    patient=patient_id,               # 注意：响应字段叫 patient，值是 ID
    report_type=report.report_type,
    period_start=report.period_start, period_end=report.period_end,
    avg_blood_sugar=report.avg_blood_sugar, blood_sugar_std=report.blood_sugar_std,
    time_in_range=report.time_in_range,
    summary=report.summary, recommendations=report.recommendations,
    risk_level=report.risk_level, generated_at=report.generated_at,
)
```

两点：
- `fetch_related("patient")`：手动预取外键关联，避免后续访问 `report.patient` 时额外的懒加载查询；
- **命名陷阱**：响应 Schema 里 `patient: int`（存的是 ID），与模型的 `patient` 外键对象语义不同——构造时显式传 `patient_id` 进 `patient` 字段，别被名字迷惑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘 fetch_related 报懒加载错误 | 响应构造前先 fetch_related，或在查询时 prefetch_related |
| patient 字段类型不符 | 响应里 patient 是 ID 数字；传 patient_id 而不是外键对象 |

@@point ⑦ 温度与 Token：控制模型"风格"
@@need 要解决什么
LLM 输出太飘或太长？temperature 和 max_tokens 怎么设？

@@idea 核心思路
.env 里的两个参数直接传给 ChatOpenAI：
- `LLM_TEMPERATURE=0.7`：**创造力温度**。0 最稳定（答案固定）、1 最发散。医疗建议场景建议偏低（0.3-0.7），健康类输出求稳；
- `LLM_MAX_TOKENS=4096`：**回答长度上限**。报告建议 3-5 条，4096 足够；对话场景同理控制在合理范围。

理解：**temperature 不改变"知识量"，只改变"表述随机性"**。同样的 prompt，temperature=0.7 每次说的话措辞可能不同但事实一致。诊疗相关建议宁可低温，避免"发挥"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 温度太高建议胡编 | 医疗/事实性输出降到 0.3-0.7；创意场景才拉高 |
| max_tokens 太小被截断 | recommendations 出现半句话；周报建议 2048 起 |
| 参数类型是字符串 | .env 读出来是 str，ChatOpenAI 会自动转换；传错类型可能告警 |

@@point ⑧ 报告模块的架构位置：聚合者
@@need 要解决什么
报告模块在整个系统里扮演什么角色？它和对话模块的分工差异？

@@idea 核心思路
报告模块是**第一个"跨模块聚合"的接口**——它同时消费：
- health_analyzer（统计）
- llm_client（生成建议）
- HealthReport 模型（落库）

对比后面的对话模块（LangGraph）：报告是"一次性成型"（统计→摘要→建议），对话是"多步工作流"（意图→档案→检索→生成→风险）。**报告是串行流水线，对话是状态图**——两者都复用 analyzer + llm_client，但编排复杂度不同。

架构启示：**core 引擎被"报告"和"对话"两条线复用**——这就是为什么统计/摘要/LLM 必须封装在 core 而不是塞进路由的原因：一处实现、多处消费。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报告逻辑直接在路由写死 | 对话模块还要复用 analyzer/llm，不封装就得复制一遍 |
| 把报告当对话的子集 | 报告要落库快照、要周期范围校验；对话要历史上下文；两者编排各自独立 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **LLMClient 封装范式** | 配置集中 + 消息组装 + 容错兜底，业务侧一行调用 |
| **报告五步流水线** | 验患者→统计→摘要→AI 建议→快照落库，规则与模型分工清晰 |
| **快照与聚合思维** | 报告存"生成瞬间的指标"，被报告/对话两线复用的 core 引擎 |

@@quiz
1. LLMClient 封装的三层价值是什么？其中"容错统一"具体指什么？
2. chat 方法里消息拼接顺序为什么必须 system → 历史 → 当前提问？
3. 报告生成流程中，analysis 带 error 时为什么跳过 LLM 调用？
4. generate_summary 为什么不用 LLM 生成？它的输出被谁消费？
5. HealthReport 保存指标快照的现实意义是什么？与"引用实时表"的差别？
6. temperature=0.7 与 max_tokens 各自控制什么？医疗场景推荐怎么设？
7. 报告模块与对话模块（LangGraph）在编排上的本质差异？

@@links
参考|安康智慧健康管理平台：糖尿病AI健康助手|#
官网|LangChain ChatOpenAI 文档|https://python.langchain.com/docs/integrations/chat/openai/
官网|阿里云百炼兼容模式|https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope/