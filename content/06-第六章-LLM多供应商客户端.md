@@h1 第六章　大语言模型多供应商客户端
@@sub 阶段 11 · LegalMind 法律咨询系统　|　|　难度 ★★☆

@@why 这一章在解决什么问题
LegalMind 的所有智能都来自大模型：意图识别、法律问答、文书生成。但大模型有一个现实问题——**供应商会变、模型名会变、价格会变**。把 `openai.ChatCompletion` 写死在代码里，DeepSeek 出个更便宜的就要改全项目；把 prompt 散落在 agent 里，调一次话术要翻五个文件。
本章用一个 `model_client.py` 把"换供应商"这件事收敛成**一个配置文件**：`LLM_PROVIDER` 写 deepseek 就调 DeepSeek，写 openai 就调 OpenAI，底层走 LangChain 统一接口。同时把**所有 prompt 模板**收进 `prompts.py` 单独管理——意图识别、法律问答、文书模板各占一地，改文案不动代码。

@@map 这一章在整个知识库里的位置
上一章（第五章 用户认证）：JWT 已可用，认证不再是问题
**本章** 你在这里：搭 LLM 层——多供应商客户端 + Prompt 模板管理，给 Agent 提供"会说话的大脑"
下一章：文本向量化与向量库——给 RAG 提供"会搜索的耳朵"
再往后：第 8 章 IntentAgent/QAAgent/DocumentAgent 全部 new 一个 get_llm() 就用
阶段终点：同一个代码库，DeepSeek/OpenAI 无缝切换，prompt 改文案不碰代码

@@point ① LangChain 抽象：为什么不能直接用 openai SDK
@@need 要解决什么
直接用 `openai` SDK 写，代码和某一家供应商深度绑定。今天的 DeepSeek 兼容 OpenAI 协议，明天换个不兼容的怎么办？LangChain 提供一层**统一抽象**：`BaseChatModel` 背后是谁，看配置说话。
@@idea 核心思路
本项目依赖里特意同时放 `langchain-openai` 和 `langchain-huggingface`，原因在 `model_client.py`：
```python
# app/llm/model_client.py
from langchain_openai import ChatOpenAI
from langchain_huggingface import ChatHuggingFace
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

def get_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "deepseek":
…（以下省略 7 行，完整代码见仓库对应位置）
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            temperature=0.3,
        )
    if provider == "huggingface":
        return ChatHuggingFace(...)
    raise ValueError(f"未知 LLM 供应商: {provider}")
```
**核心设计**：`get_llm()` 返回 `BaseChatModel`，上游 agent 只认这个抽象类型——"我要一个聊天模型"，不关心它是谁家的。换供应商只改 .env，零代码改动。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| DeepSeek 报 "Invalid URL" | base_url 要写全：`https://api.deepseek.com`（不是带 /v1 的通用 OpenAI 地址也行，但要对齐文档） |
| temperature 参数被忽略 | 部分供应商不支持该参数会被忽略或报错；按供应商裁剪参数 |
| API Key 泄露到 GitHub | `.env` 不进 git；真泄露立刻去控制台吊销重建 |

@@point ② 统一能力：invoke / ainvoke / astream
@@need 要解决什么
对话、问答、流式输出的调用方式不同（同步/异步/流式），如果每个 agent 各写各的调用姿势，会很难维护。LangChain 在 BaseChatModel 上统一了三组调用接口，agent 层只学一次。
@@idea 核心思路
BaseChatModel 提供的三套接口（本项目全部使用异步版本）：
```text
# 1. 同步调用（少用，适合脚本）
llm.invoke(messages)

# 2. 异步调用（API 内首选）
response = await llm.ainvoke(messages)

# 3. 流式调用（聊天/文书生成接口用）
async for chunk in llm.astream(messages):
    yield chunk   # chunk.content 是增量文本
```
定义：**invoke= 完整调用**（输入全部消息，返回完整回复）；**astream= 流式调用**（逐 token 产出，配合 SSE 推给前端）。在 FastAPI 的 async 生态里，`await` 不会阻塞其他请求——这就是为什么整个后端都用 async。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 调 ainvoke 忘了 await，返回 "coroutine was never awaited" | 异步方法不 await 不会执行；在同步上下文（普通 def 路由）里调异步 API，要用 `asyncio.run` 或把路由改成 async def |
| 用 astream 一次收完再处理，流式白做了 | astream 是按 token 逐步 yield；要打字机效果就要在循环里一边收一边发，别先攒成整段 |

@@point ③ Prompt 模板：什么是 ChatPromptTemplate
@@need 要解决什么
直接拼字符串给 LLM，容易注入（用户输入把 system 指令盖了），且不同类型的消息（system/human）混在一起。LangChain 的 ChatPromptTemplate 用结构化方式组织 prompt。
@@idea 核心思路
`ChatPromptTemplate` 是"消息列表模板"，最常见三行式（system + human）：
```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("你是一个法律助手。用户问题：{query}")
```
更正式的做法是"消息元组"式（第 8 章 Agent 里就是这种）：
```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一位专业的法律顾问……"),   # 人设/system
    ("human",  "用户问题：{query}"),          # 用户输入占位
])
```
- `{query}` 是占位符，`.format(query=...)` 或链式调用时填充。
- **一条 chain = prompt | llm | parser**：`chain = prompt | llm | StrOutputParser()`，`await chain.ainvoke({"query": "..."})` 一步完成"填模板→调模型→取文本"。
- system 与 human 分离，让 LLM 明白"系统指令"和"用户内容"的边界，降低 prompt 注入风险。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 模板里写了 `{xxx}` 但传参漏了或拼错变量名，静默填充成空串 | ChatPromptTemplate 缺变量会报错，但变量名写错传了多余的不会报；填充前把模板变量和入参 key 对一遍 |

@@point ④ 意图识别 Prompt：让 LLM 做三分类
@@need 要解决什么
Agent 系统第一步是"判断用户想干嘛"（问答/文书/检索）。这不是硬编码关键词能搞定的——"帮我写份东西"和"我要起诉"都很口语化，得让 LLM 来判，但输出必须**规范**（只能是三个词之一），否则路由没法做。
@@idea 核心思路
`llm/prompts.py` 里的意图识别 Prompt（抑制自由发挥，强制三分类）：
```text
INTENT_RECOGNITION_PROMPT = """你是一个法律咨询意图识别专家。请分析用户的问题，判断其意图属于以下哪一类：

1. qa - 法律问答：用户提出法律问题，需要专业解答
   示例："离婚财产怎么分割？"、"交通事故怎么赔偿？"

2. document - 文书生成：用户需要生成法律文书
   示例："帮我写一份起诉状"、"生成一份租房合同"

3. search - 案例检索：用户需要查找相关案例
   示例："查找类似案例"、"有哪些相关的判例？"

用户问题：{query}

请只返回意图类型（qa/document/search），不要返回其他内容。"""
```
配套的"净化器"（agent 里）：
```text
response = await self.chain.ainvoke({"query": query})
intent = response.strip().lower()
if intent not in ['qa', 'document', 'search']:
    intent = 'qa'    # 输出不规范时的兜底，宁可当问答也别路由崩
```
- **few-shot 示例**（1./2./3. 的示例行）让模型理解"什么话算什么意图"。
- **输出约束**"只返回 qa/document/search" + **代码兜底**双保险——LLM 输出不可控，最后一道防线永远在代码里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 让 LLM"自由分类"，结果冒出个没见过的类别 | 三分类就要在 prompt 里给死白名单并注明"只能从这三类中选"；代码侧再加一道：输出不在白名单就兜底走 default 分支 |
| 把整个聊天历史全塞进意图识别 prompt，爆上下文 | 意图判断通常只需要最新一条用户消息+系统设定，别把文书、引用全带进来 |

@@point ⑤ 法律问答 Prompt：人设 + 原则 + 结构
@@need 要解决什么
问答质量取决于 system prompt 的"人设"和"纪律"。没有约束的模型会编法条、乱给建议、不说风险。写一条**专业法律顾问**人设 + 四条回答原则 + 三段回答结构。
@@idea 核心思路
`QA_SYSTEM_PROMPT` 的三层设计（浓缩版，完整代码见配套代码）：
```text
System: 你是一位专业的法律顾问……你的职责是基于提供的案例资料，为用户提供专业、准确、有法律依据的法律建议。

## 回答原则
1. 基于事实：回答必须基于提供的案例和法律条文，不得编造
2. 专业严谨：使用准确的法律术语，逻辑清晰
3. 引用依据：重要观点需注明出处（案例案号、法律条文）
4. 风险提示：涉及重大利益时，提醒用户咨询专业律师
5. 客观中立：不偏向任何一方，客观分析

## 回答结构
1. 问题分析：简述问题的法律要点
2. 法律依据：引用相关法律条文和案例
3. 解答建议：给出具体、可操作的建议
4. 注意事项：提示可能的风险和注意事项
```
加上 `QA_USER_PROMPT`（每轮动态拼）：
```text
用户问题：{query}
相关案例：{cases}      ← 第 7 章 RAG 检索结果
对话历史：{history}
```
**关键设计**：法律问答"引用依据""风险提示"两条原则，直接决定了回答的**可信度**——这是法律垂直领域和通用 Chat 最大的差异，也是 RAG 存在的意义（第 8 章组织消息时体现）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 让 LLM"自由分类"，结果冒出个没见过的类别 | 三分类就要在 prompt 里给死白名单并注明"只能从这三类中选"；代码侧再加一道：输出不在白名单就兜底走 default 分支 |
| 把整个聊天历史全塞进意图识别 prompt，爆上下文 | 意图判断通常只需要最新一条用户消息+系统设定，别把文书、引用全带进来 |

@@point ⑥ 文书模板：五个可复用的模板骨架
@@need 要解决什么
文书生成不能真让 LLM 完全自由发挥——起诉状有王法格式（原告/被告/诉讼请求/事实与理由/此致）。预置模板骨架，让 LLM **按格式填空**，输出稳定可立案。
@@idea 核心思路
`DOCUMENT_TEMPLATES` 是 dict：文书类型 → 模板字符串。例如民事起诉状：
```text
DOCUMENT_TEMPLATES = {
    "civil_complaint": """民事起诉状

原告：[原告姓名]
被告：[被告姓名]

诉讼请求：
1. [诉讼请求1]
2. [诉讼请求2]

…（以下省略 6 行，完整代码见仓库对应位置）
原告：[签名]
日期：[日期]
""",
    "defense_statement": """民事答辩状 ...""",
    "contract": """...""",
    "lawyer_letter": """...""",
    "appeal_statement": """...""",
}
```
第 8 章 DocumentAgent 的 `_build_user_prompt` 会把模板注入提示词：
```text
prompt_parts.append(f"请严格按照以下格式模板生成，将上述参数与需求填入对应位置，保持结构完整：\n{template.strip()}")
```
- **模板是"骨架"不是"死板"**：LLM 把用户参数（原被告名字、金额、事实）填进 `[...]` 占位处，结构由模板锁死。
- `DocumentAgent.DOCUMENT_TYPES` 做"中文类型名 → 模板 key"映射：用户界面选"起诉状"，代码映射到 `civil_complaint` 模板。

@@point ⑦ 参数调节：temperature 与输出的平衡
@@need 要解决什么
同一个模型，temperature 不同，输出风格天差地别。法律场景要"稳"不要"浪"——文档类和问答类要低温度；但完全 0 又会死板。找到哪个值最适合专业知识输出。
@@idea 核心思路
LegalMind 的默认值 `temperature=0.3`，理由：
- **0.0~0.2**：几乎确定，适合分类/抽取（意图识别其实可以更低）。
- **0.3~0.5**：稳定但保留少量多样性——法律问答、文书生成的主区间。
- **0.7+**：创造性强，适合文案、故事，法律场景**禁止**（会编法条）。
工程上注意：**temperature 是"抽样骰子的随机度"不是"聪明度"**。模型不会因 temperature=0 就变专业——专业靠 prompt + RAG 上下文，temperature 只控制发散程度。生产环境想在"稳定"与"多样"间找平衡，可以跑一组对比测试再定值。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| temperature=0 仍然每次输出不同 | 模型推理本身有不确定性（并行解码/缓存）；不能依赖温度保证稳定 |
| prompt 写一堆但输出还是跑题 | 加强输出约束（"只返回……"）+ few-shot；光写人设不约束输出不够 |
| 上下文太长报 token 超限 | 截断对话历史（本项目只留最近 5 条），案例最多 5 个 |
| 中文乱码 | 所有文件 UTF-8；curl 测试加 `-H 'Content-Type: application/json; charset=utf-8'` |

@@point ⑧ 整条 LLM 层验证
@@need 要解决什么
写完客户端和 prompt，最怕"看起来对，跑起来错"。用一个最小脚本直接调 get_llm()，确认 Key、base_url、模型名全对，再进下一章。
@@idea 核心思路
```python
# scripts/llm_smoke_test.py
import asyncio
from app.llm.model_client import get_llm
from langchain_core.messages import HumanMessage

async def main():
    llm = get_llm()
    resp = await llm.ainvoke([HumanMessage(content="用一句话介绍民法典")])
    print(resp.content)   # 能打印中文回答 = LLM 层可用

asyncio.run(main())
```
逐级排错：
1. `ImportError` → 依赖没装 / .env 没配。
2. APIKey 报 401 → Key 写错或过期。
3. 网络报错 → base_url 错 / 没网 / 代理拦截。
4. 返回但内容怪 → prompt 问题，不进代码改 prompts.py。
这步通过后，第 7 章的向量化和第 8 章的 Agent 就可以放心往上叠。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Prompt 里写了禁止事项，输出还是出现 | 角色/规则类指令要放在 system 消息里且靠前，放在 user 消息尾部最容易被忽略或覆盖；验证时多跑几条边界输入看稳定性 |

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **多供应商客户端** | .env 一改，DeepSeek ↔ OpenAI 无缝切换，代码零改动 |
| **Prompt 集中管理** | 意图识别/问答/文书模板各占一地，改话术不碰逻辑代码 |
| **调用三件套** | invoke/ainvoke/astream 全会，第 8 章 Agent 直接调用 |

@@quiz
1. get_llm() 返回什么类型的对象？换供应商为什么不用改 agent 代码？
2. ainvoke 和 astream 的区别？LegalMind 聊天接口用哪个？
3. ChatPromptTemplate 里 system 和 human 消息分开有什么意义？
4. 意图识别 prompt 为什么要 few-shot 示例？输出兜底逻辑是什么？
5. QA_SYSTEM_PROMPT 里"引用依据""风险提示"两条原则分别解决了什么问题？
6. 文书模板在 prompt 里扮演什么角色？"模板 + {}占位符"的生成方式核心是什么？
7. temperature=0.3 适合什么场景？法律问答为什么不用 0.7+？

@@links
参考|LegalMind 法律咨询系统：大语言模型多供应商客户端|#
官网|LangChain Chat Models 文档|https://python.langchain.com/docs/integrations/chat/
官网|DeepSeek API 文档|https://api-docs.deepseek.com/