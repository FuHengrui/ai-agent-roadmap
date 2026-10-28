@@h1 第九章　Coze API 调用与工作流编排
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
Bot 在扣子平台上"会干活的专家"了，但平台后端还不会使唤它。本章解决两件事：**一是用 Python 官方 SDK（cozepy）调起选题 Bot**（发消息 → 轮询 → 取回复），**二是在扣子平台上编排 HotTopic_Workflow 工作流**——把"搜热点 → 大模型写标题 → JSON 收口"变成可视化流水线，并从扣子应用里调用。

学完你会明白"AI 应用开发"的两种姿势：**SDK 直调 Bot**（简单可靠）与 **工作流编排**（复杂可控），以及为什么本项目两者都要。

@@prep 开始之前
要有第 8 章的 BOT_ID 和扣子个人令牌（pat_ 开头）；cozepy 已在依赖里。

@@goal 学到这儿就够了
能用 SDK 调通 Bot 取回结果、在扣子上编排出热点工作流，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：Coze 选题智能体打造——Bot 人设与输出契约就绪
**本章** ← 你在这里：Coze API 调用与工作流——后端调用层 + 平台编排层
下一章：选题生成 API——/start 接口把 AI 结果落库
再往后：文案 Bot → 配图 → OSS 发布

@@point ① cozepy：官方 Python SDK 的用法骨架
@@need 要解决什么
后端要跟 Coze 通信，最稳的方式是用官方 SDK，而不是自己拼 HTTP。SDK 的核心调用模式是什么？

@@idea 核心思路
```python
from cozepy import Coze, TokenAuth, Message

coze = Coze(auth=TokenAuth(token=COZE_TOKEN), base_url=COZE_CN_BASE_URL)
```
两个关键点：
- **COZE_CN_BASE_URL**：国内环境必须显式指定（`https://api.coze.cn`），不指定默认走海外域名，token 直接无效。
- **TokenAuth**：用 .env 里的 COZE_TOKEN（pat_ 开头个人令牌）做鉴权。

发起对话的核心循环：
```python
chat = coze.chat.create_and_poll(
    bot_id=BOT_ID_TOPIC,
    user_id=USER_ID,
    additional_messages=[Message.build_user_question_text("新能源汽车")],   # 注意不是 messages
)
for message in chat.messages:
    if message.type == "answer":
        return message.content       # Bot 最终回复内容
```
- `create_and_poll`：**一步完成"发起＋轮询到结束"**，不需要自己写 while 循环。
- 回复里 `type == "answer"` 的是最终答案，其余 type（如 function_call、tool_response）是中间过程。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| token 报 401 无效 | 没配 base_url 走了海外域名；或 token 与账号不匹配 |
| 轮询到超时（coze 单轮 90 秒上限） | AI 内部多次调工具+长输出导致；后端超时时间要 >90s，且对超时做可重试处理 |
| 拿到一堆 message 不知道取哪个 | 只取 type=="answer"；其余是 tool 调用等过程消息 |

@@point ② 一次 chat 的完整生命周期
@@need 要解决什么
create_and_poll 内部发生了什么？理解生命周期才能调好超时、幂等与重试。

@@idea 核心思路
时间线：
1. 客户端创建会话 → Coze 平台收到用户问题；
2. Bot 触发插件（联网搜索当前热点）→ 插件返回原始数据；
3. 大模型收到"热点数据 + 人设" → 生成 5 板块 50 标题文本 → JSON 收口；
4. 平台把过程消息与最终 answer 推送回来 → create_and_poll 结束。

耗时预估：搜索 1-3s + 生成（几十秒）→ **单次 chat 常见 15-60 秒**，复杂场景可能逼近 90 秒上限。所以：
- 后端接口超时设 120s+（第 7 章前端 timeout=120000 即为此）；
- 前端要有"生成中"loading 状态（进度条/文案提示）；
- 超时重试要有**幂等设计**（同一主题重复生成允许，但要处理重复板块）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 发起 chat 立刻拿到空 messages | create_and_poll 前的消息构造不对（如 messages 列表为空）；检查 Message.build_user_question_text 是否传了内容 |
| 连续多次调用触发限流 | 并发/频率超配额；接口层做串行或退避，别把短循环打满 |

@@point ③ 消息类型过滤：为什么只信 answer
@@need 要解决什么
chat.messages 里混着多类消息，直接取"第一条"或用错类型会拿到半成品。

@@idea 核心思路
常见的 message.type 值：
| type | 含义 | 要不要 |
|---|---|---|
| question | 用户问题回显 | 否 |
| answer | 最终回复正文 | ✅ 是 |
| function_call | 插件/工具调用请求 | 否 |
| tool_response / tool_output | 工具执行结果（在 function_call 之后） | 否 |
| follow_up / verbose | 追问/过程描述 | 否 |

正确做法：**遍历全部，过滤 type=="answer" 取 content**——不要取第一条、不要按索引。若同轮有多个 answer（罕见），拼或用最后一个。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 拿到的是工具调用 JSON 而不是标题 | 取消息没过滤 type，拿到 function_call 前的 tool_output |
| answer 为空串 | Bot 中途异常或内容被截断；打 message 完整列表排查，别只打印 content |

@@point ④ HotTopic_Workflow：工作流节点编排
@@need 要解决什么
"实时热搜"不能靠 Bot 人设里写"请搜索"（不可控），要在工作流里**显式编排**：先搜、再生成、再收口。HotTopic_Workflow 就是这份编排。

@@idea 核心思路
HotTopic_Workflow 的节点链（实际链路）：
```
开始（接收主题）→ 搜索热点插件（头条/微博/知乎/抖音热点聚合）
→ 大模型节点（人设 + 热点数据 + 主题 → 5 板块 50 标题 JSON）
→ JSON 序列化/收口节点（清洗、补全、规范 JSON）
→ 结束（返回 JSON 给调用方）
```
每个节点的精髓：
- **搜索节点**把"当前热点"变成结构化输入传下去——热点是数据不是提示词；
- **大模型节点**的输入模板里引用上游变量（`{{plugins_output}}`、`{{user_theme}}`）；
- **JSON 收口节点**做后处理：合并重复、校验条数、把文本中的 JSON 段提取出来——**这是"AI 输出不可控"的最后兜底**。

为什么放工作流而不是全塞 Bot：工作流的每个节点的输入输出显式可见，可单独调试（单节点试运行），出问题定位到节点而不是整段黑盒。

@@point ⑤ 扣子应用（Coze App）：把工作流包成可调用单元
@@need 要解决什么
工作流编好了，怎么让"平台后端"调用它？答案是把它发布成扣子应用，拿 API 端点。

@@idea 核心思路
在扣子平台：
1. 创建"应用"（Coze App）→ 关联已建好的 HotTopic_Workflow；
2. 发布应用 → 平台生成应用的调用端点与鉴权信息（API Token / 应用 ID）；
3. 后端或外部系统即通过端点 + token 调用，传入主题参数，拿到工作流结果（JSON）。

与"直接调 Bot"的差异：
| 方式 | 适用 | 优点 |
|---|---|---|
| SDK 直调 Bot（create_and_poll） | 单轮问答、简单生成 | 代码量小、开箱即用 |
| 工作流 + 应用端点 | 多步编排、强结构输出 | 流程可控、节点可调试、输出更规整 |

项目实际形态：**coze_agent.py 里既有直调 Bot 的 hot_topic/content_creation 函数，也编排了 HotTopic_Workflow**——两条路都能出选题，互为印证与兜底。

@@point ⑥ coze_agent.py：AI 调用层收口
@@need 要解决什么
所有 Coze 交互逻辑要集中在一个模块，业务路由只管调它。

@@idea 核心思路
`app/agent/coze_agent.py` 的职责结构：
```python
def _get_coze(token: str) -> Coze:          # 统一构造客户端（含 base_url）
async def hot_topic(theme: str) -> str:      # 调选题 Bot 拿 50 标题 JSON 文本（下游要 await，必须 async）
def content_creation(...) -> str:           # 调文案 Bot 生成本文（第 11 章）
```
- 函数只做"调 AI 取原始文本"，**不做解析**——解析在 create.py 路由层（`_extract_json` 等）。
- 层与层解耦：AI 协议（Coze）变化只改 agent 层，表结构变化只改路由层。

这是第 1 章"agent 层收口 AI"设计的落地：**routers 不 import cozepy，agent 层不 import models**。

@@trap 坑在哪
agent 层只回原始文本、不做 JSON 解析，是刻意为之：一旦 Coze 返回格式变了，你只需要改 create.py 的 `_extract_json` 一处；如果在 agent 层顺手解析了，格式变化就要翻遍所有调用点。分层边界一句话：**协议层不管业务，业务层不碰协议**。

@@point ⑦ 健壮性：超时、重试与降级
@@need 要解决什么
AI 调用是最不可控的环节：超时、限流、偶发空回复。生产级 AI 应用必须有兜底策略。

@@idea 核心思路
| 风险 | 策略 |
|---|---|
| 单轮 90s 超时 | 捕获超时异常 → 提示"生成超时，请重试"，允许用户重发（幂等-允许重复生成） |
| 限流/429 | 指数退避重试 1-2 次；仍失败返回 500 提示稍后再试，不无限重试 |
| 返回空/非 JSON | 路由层 _extract_json 提取失败即报"AI 返回格式异常"，前端给"重新生成"按钮 |
| 网络抖动 | 对"调用 AI"与"落库"两步隔离：AI 成功但落库失败时，数据不丢（可再调 /load 拉回）|

原则：**AI 失败要让用户可感知、可重试，绝不静默吞掉**。日志里记录 Bot ID、主题、耗时、返回摘要，便于复盘。

@@summary 这一章你学到了什么
- cozepy SDK：Coze + TokenAuth + COZE_CN_BASE_URL（国内必配）
- create_and_poll 一步完成发起+轮询；遍历 message 只取 type=="answer"
- chat 生命周期：插件搜热点 → 大模型生成 → 收口返回，单轮 15-90 秒
- HotTopic_Workflow 节点链：开始 → 搜索 → 大模型 → JSON 收口 → 结束
- 扣子应用：把工作流发布成可调用端点，与直调 Bot 是两条互补路线
- coze_agent.py 收口全部 AI 调用，路由层只做解析与落库
- 健壮性四板斧：超时可重试、限流退避、格式异常可感知、AI 与落库隔离
- agent 层日志规范：入参与成果记 info、异常记 error 带堆栈，对外统一 500

@@quiz
1. cozepy 客户端必须显式配置什么才能在国内使用？
   A. 代理　　B. base_url=COZE_CN_BASE_URL　　C. 重试次数　　D. 模型名
2. create_and_poll 的作用是？
   A. 只创建会话　　B. 发起并轮询到对话结束　　C. 直接返回最终结果　　D. 删除会话
3. 从 chat.messages 取最终回复的正确方式是？
   A. messages[0]　　B. 遍历过滤 type=="answer"　　C. messages[-1]　　D. 任意一条
4. HotTopic_Workflow 中"搜索热点"放在哪个环节？
   A. 最后　　B. 大模型之前（先有数据再生成）　　C. 收口节点　　D. 不需要
5. 工作流相比直调 Bot 的核心优势是？
   A. 更快　　B. 节点可单独调试、处理更可控　　C. 不需要 token　　D. 不耗 token
6. AI 调用单轮超时上限大约是？
   A. 10 秒　　B. 90 秒　　C. 5 分钟　　D. 无限制
7. AI 返回非 JSON 时，正确处理是？
   A. 忽略　　B. 路由层提取失败并向用户报"格式异常，可重试"　　C. 强制入库　　D. 重启服务

@@point ⑧ agent 层异常与日志规范：失败要看得见
@@need 要解决什么
AI 调用是最难排查的环节——失败信息若被吞掉，前端只会看到玄学"生成失败"，无从定位。

@@idea 核心思路
coze_agent 层统一异常与日志规范：
```python
import logging
logger = logging.getLogger("coze_agent")

async def hot_topic(theme: str) -> str:
    logger.info("hot_topic start | theme=%s", theme[:50])
    try:
        chat = coze.chat.create_and_poll(...)
        text = 提取 answer
        logger.info("hot_topic ok | chars=%d", len(text or ""))
        return text
    except Exception as e:
        logger.error("hot_topic fail | theme=%s | %s", theme, e, exc_info=True)
        raise HTTPException(500, "AI 生成失败，请稍后重试")
```

规范要点：
- **入参/耗时/成果摘要记 info**，异常记 error 且带堆栈（exc_info=True）；
- 异常向上抛**统一 500**，但详细堆栈留在日志——用户看到的是"可重试"，开发者看到的是"可诊断"；
- 不回传内部错误细节给前端（防信息泄露，也避免把 SDK 报错糊在页面上）。

排查节奏：前端报"生成失败" → 看后端日志的 `hot_topic fail` 行 → 字段（theme/异常类型/堆栈）一次给全。**日志里看不到的失败 = 排查黑洞**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 失败后日志为空 | 异常被 try 吞掉没打日志；log 必须放 except 内第一行 |
| 日志全是堆栈、没有上下文 | 没记入参（theme/bot_id）；排查时无从复现 |
| 把 SDK 原始报错直接回给前端 | 内部细节外泄 + 用户体验差；对外统一 500 提示语 |

@@links
参考|智能运营平台.pdf|#
官方|Coze Python SDK|https://www.coze.cn/open/docs/developer_guides/coze_api_overview
官方|Coze 工作流使用指南|https://www.coze.cn/docs/guides/workflow_overview