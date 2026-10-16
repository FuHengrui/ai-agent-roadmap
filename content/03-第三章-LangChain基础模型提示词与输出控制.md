@@h1 第三章　LangChain 基础：模型、提示词与输出控制
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　实践　|　难度 ★★☆

@@why 这一章在解决什么问题
前两章你理解了 Agent 的"手脚"和"大脑"。但如果每个 Agent 项目都要自己封装 API 请求、手写提示词拼接、正则在回复里抠 JSON——那开发效率会低到劝退。

LangChain 把这三件高频重复的脏活封装成了统一 API：**接大模型、写提示词模板、解析模型输出**。本章是 LangChain 的入门实战：把"调一个通用对话大模型"这件事，从零到一地跑通，并学会让模型输出"你说了算的结构化数据"。

读完之后你能回答三个问题：模型有哪些接法（云 API/本地）、提示词模板怎么管理变量和多角色对话、怎么让模型稳定吐 JSON 而不是散文。

@@map 这一章在整个知识库里的位置
上一章：Agent 工具系统与 Tool Calling——工具的定义与校验
**本章** ← 你在这里：LangChain 基础——模型、提示词、输出控制三件套
下一章：LCEL 链式调用——把"取数→处理→回答"连成管道
再往后：LangGraph 编排 → 工具/记忆/MCP → 实战与 A2A

@@point ① LangChain 是什么：Agent 的"万能工具箱"
@@need 要解决什么
直接调大模型 API 很痛苦：每个厂商的接口不一样（OpenAI、通义、智谱、国产本地模型），换个模型就要重写调用代码；提示词、输出解析、工具调用全是手写样板代码。

@@idea 核心思路
LangChain 是一个开源框架，帮你更方便地构建 LLM 应用。它提供的核心能力：

- **统一模型接口**：`langchain-openai` 兼容 OpenAI 协议的模型（通义、智谱、DeepSeek、OpenAI 都能用同一套代码）；`langchain-ollama` 接本地模型
- **提示词模板**：PromptTemplate / ChatPromptTemplate / FewShotPromptTemplate 三类模板
- **输出解析器**：强制模型输出 JSON / XML / Pydantic 结构化数据
- **链式调用（LCEL）**：把多个组件用 `|` 管道符连成一条处理流水线

一句话：**LangChain 让"接模型、写提示、收结果"变成可组合的积木**，把精力留给业务本身。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为 LangChain 是"补全万能的 AI" | 它只是编排框架，模型能力是模型给的，框架不提升模型智商 |
| 只装 langchain 包 | 模型供应商各自有独立包（langchain-openai / langchain-ollama），要按需安装 |
| 版本混乱（旧版 v0.1 教程满天飞） | 先确认用 v0.3+（Pydantic v2 原生支持），很多老教程 API 已废弃 |

@@point ② 环境搭建：3 条路线通通义 / 智谱 / 本地
@@need 要解决什么
要让代码真正跑起来，需要模型服务。三种主流选择：通义（DashScope）、智谱（BigModel）、本地模型（Ollama）。它们的接法大同小异，但配置细节有坑。

@@idea 核心思路
**通义（DashScope）路线：**
```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="qwen-plus",            # 通义模型名
    api_key=os.getenv("DASHSCOPE_API_KEY"),  # 环境变量，不硬编码
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```
**智谱（BigModel）路线：** 同样走 OpenAI 兼容协议，`base_url="https://open.bigmodel.cn/api/paas/v4"`、model 用 `glm-4-plus` 之类；API_KEY 在 https://bigmodel.cn/usercenter/proj-mgmt/apikeys 申请。
**本地模型（Ollama）路线：**
```python
from langchain_ollama import ChatOllama
llm = ChatOllama(model="qwen2.5")  # 本机已装 Ollama 并 pull 模型
```

共同要诀：
1. **API Key 一律放环境变量**（`.env` + `dotenv`），绝不硬编码进代码
2. 尽量选**兼容 OpenAI 协议**的模型服务——换模型只改 base_url 和 model 名
3. 本地模型先确认已 `ollama pull` 对应模型，否则报模型找不到

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 报 401/鉴权失败 | API Key 没设、设错环境变量名，或 Key 在代码里没被读到 |
| 报 model not found | base_url 与 model 名不匹配（把通义模型名用在智谱地址上） |
| 本地模型迟迟不响应 | 未先 pull 模型 / 内存不够 / 模型名拼错，先 `ollama list` 确认 |

@@point ③ 模型分类与调用模型的两种方式
@@need 要解决什么
"大模型"不止一种：有纯文本生成模型、有对话模型、有带工具调用的模型。调用方式也分"问一句等答复"和"流式逐字返回"。选错方式体验和功能都打折。

@@idea 核心思路
**模型分类：**
- **纯补全模型（LLM）**：输入文本续写文本，多用于古典场景
- **对话模型（ChatModel）**：按 System/User/Assistant 角色消息交互——现在的主流，ChatOpenAI/ChatOllama 都属于这一类
- 对话模型进一步支持**流式输出**和**工具调用**（Tool Calling，上章的机制）

**两种调用方式：**
```python
# 方式1：非流式——一次调用等完整结果
resp = llm.invoke("杭州天气怎么样？")
print(resp.content)               # 完整回答

# 方式2：流式——逐块吐出，边生成边显示
for chunk in llm.stream("讲个笑话"):
    print(chunk.content, end="")
```
流式的价值：用户感知延迟大幅下降（首字秒出），适合聊天 UI；非流式适合后台批处理、需要完整结果再加工的场景。

@@point ④ 提示词模板：把"千变万化的输入"装进"固定的框架"
@@need 要解决什么
直接拼字符串造 prompt 又乱又容易出错：用户输入里嵌着引号怎么办？角色设定和问题混在一起？每次都要重写冗长提示词？

@@idea 核心思路
**PromptTemplate 类**：用 `{变量}` 占位符定义模板，运行时填充，自动处理转义与组装。

```python
from langchain_core.prompts import PromptTemplate

template = '你是一个{role}，请用{style}风格回答问题：{question}'
prompt = PromptTemplate.from_template(template)
filled = prompt.format(role='数学老师', style='通俗易懂', question='勾股定理是什么？')
```

作用：**把"角色 / 风格 / 问题"这种常变化的输入变量化**，提示词主体只写一次、处处复用；更换角色或风格不用改模板，只换参数。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 模板里有 `{}` 花括号但不是变量 | 例如写 JSON 示例 `{"a":1}` 会被误判为变量，需要在模板里转义 `\{` 或用 `.partial` |
| format 时漏传变量 | 模板声明的变量必须全部提供，否则直接抛 KeyError |
| 凭空拼接长 prompt | 该用模板却手工 + 字符串，注入风险与维护成本双高 |

@@point ⑤ ChatPromptTemplate：多轮对话的正确姿势
@@need 要解决什么
单段模板适合"一问一答"。但真实 Agent 是**多角色对话**：系统设定(System)、用户提问(Human)、AI 历史回答(Assistant)。把它们混在一个字符串模板里很别扭，模型也分不清边界。

@@idea 核心思路
**ChatPromptTemplate.from_messages**：按 `(角色, 模板)` 列表定义消息序列。

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是数学老师，请以{style}的风格回答问题"),
    ("human", "请用简单易懂的方式解释：{question}"),
])
```
填充时用 `invoke({"style": "...", "question": "..."})`，得到的就是一段**标准角色消息列表**，直接进模型。

好处：
- 角色边界清晰，模型行为更稳（系统提示词不被用户内容"污染"）
- 天然支持多轮：把历史消息追加进列表即可
- 后面 LCEL / LangGraph 里，ChatPromptTemplate 是消息流的标准入口

@@point ⑥ FewShotPromptTemplate：给模型"抄作业"的样例
@@need 要解决什么
有时光靠"你是一个 XX"不够——模型不知道你要的**具体格式**长什么样。给它几个"输入→输出"的黄金样例，它就能照着格式走。典型场景：从一句话里提取城市名。

@@idea 核心思路
**FewShotPromptTemplate** = 示例列表 + 示例模板 + 后缀模板。

```python
from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate

examples = [
    {"input": "北京天气怎么样", "output": "北京市"},
    {"input": "南京下雨吗",     "output": "南京市"},
]
example_prompt = PromptTemplate.from_template("输入：{input}\n输出：{output}")
prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    suffix="输入：{input}\n输出：",   # 留白让模型续写
    input_variables=["input"],
)
```
模型看到示例后，会按"输出城市名"的范式推理——**用类比提升在特定任务上的表现**。可扩展 example_selector 动态挑选与当前输入最相关的示例（本地化、多语言场景尤其有用）。

**模板策略选择表：** 结构固定/参数明确 → PromptTemplate；多轮对话/角色扮演 → ChatPromptTemplate；示例驱动/类比推理 → FewShotPromptTemplate。

@@point ⑦ 输出解析器总览：让模型吐"程序能用的数据"
@@need 要解决什么
模型默认输出散文："我叫李明，今年28岁，喜欢爬山和摄影。" 程序要的是结构化数据：`{"name":"李明","age":28,"hobbies":[...]}`。从散文里用正则抠数据，又慢又脆。

@@idea 核心思路
**输出解析器（Output Parser）**：在 prompt 注入格式指令 + 解析模型返回，双管齐下。分类与选型：

| 解析器 | 优势 | 适用场景 |
|---|---|---|
| PydanticOutputParser | 类型安全、验证严格、IDE 支持好 | 生产环境、复杂结构、强验证 |
| JsonOutputParser | 灵活、兼容好、支持流式 | Web API、前后端交互、动态结构 |
| XMLOutputParser | 层级清晰、兼容旧系统 | 企业集成、文档处理、配置管理 |
| CommaSeparatedListOutputParser | 简单高效、占用小 | 标签提取、简单列表 |
| StructuredOutputParser | 完全自定义、灵活度最高 | 特殊格式、原型开发 |

**选择建议**：新项目优先 PydanticOutputParser 或 JsonOutputParser；企业集成用 XML；简单任务用逗号列表；流式需求选 Json；强验证选 Pydantic。

常见问题：模型仍可能不遵守格式 → 结合 retry 机制；中文模型对英文字段名混淆 → 字段描述用中文；流式注意解析器是否支持。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 手写 split/json.loads 硬解析模型输出 | LLM 输出不稳定，手写解析脆弱，格式一变就崩 |
| 以为解析器全万能 | 不同解析器对格式约束力不同，结构化输出才最稳 |

@@point ⑧ JsonOutputParser：最快拿到 JSON
@@need 要解决什么
前后端联调、Agent 工具参数传递，最常要的就是"模型输出合法 JSON"。手写解析兜底逻辑太繁琐。

@@idea 核心思路
JsonOutputParser 把"请输出 JSON"的指令自动写进 prompt，并解析模型回复为 Python 对象。

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser()
resp = parser.parse('{"answer": "42"}')
# -> {'answer': '42'}
```
它灵活、兼容性广，同样内容还能放在 LCEL 链里与提示词拼装：`prompt | llm | parser`。适合结果的**字段结构动态**、只需要合法 JSON 不需要强类型校验的场景。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 模型输出带 ```json 代码块标记，json.loads 直接报错 | 默认解析器不会剥离代码块标记，需先清洗 |
| 字段名/顺序漂移导致解析失败 | 纯靠提示词约束格式不稳，应配合 format_instructions 或结构化输出 |

@@point ⑨ PydanticOutputParser：强类型 + 自动校验
@@need 要解决什么
JsonOutputParser 只能保证"是 JSON"，不能保证"字段对、类型对"。生产环境里 `age` 传成字符串"28"就等着崩。需要"模型输出 -> 强类型对象 + 验证"一步到位。

@@idea 核心思路
PydanticOutputParser（基于 Pydantic v2）：定义 BaseModel，解析器自动生成格式指令并校验结果。

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class UserProfile(BaseModel):
    name: str = Field(description="用户名")
    age: int = Field(description="年龄")
    is_student: bool = Field(description="是否学生")

parser = PydanticOutputParser(pydantic_object=UserProfile)
data = parser.parse('{"name": "李明", "age": 28, "is_student": false}')
print(data.age + 1)   # 29，类型已经是 int
```
解析失败（格式错/类型错）抛异常 → 配 retry 实现"错了就带着报错信息让模型重出"。**生产环境复杂数据的首选。**

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 数字字段模型给了字符串，校验失败 | Pydantic 校验不通过，需设计"修正提示"让模型重试 |
| Pydantic 模型嵌套又复杂，模型频繁出错 | 字段越扁平模型越容易填对，复杂结构拆开解析 |

@@point ⑩ StructuredOutputParser：完全自定义格式
@@need 要解决什么
有些场景输出不止 JSON：可能要多字段混合、特殊排版、或原型阶段还没定死结构。需要一种"我定义字段，模型照着出"的灵活方案。

@@idea 核心思路
StructuredOutputParser 用 ResponseSchema 声明字段（名称+类型+描述），自动生成格式指令。

```python
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.prompts import PromptTemplate

schemas = [
    ResponseSchema(name="answer", description="问题的答案", type="string"),
    ResponseSchema(name="confidence", description="答案的置信度", type="float"),
]
parser = StructuredOutputParser.from_response_schemas(schemas)
prompt = PromptTemplate(
    template="回答以下问题，并以 JSON 格式返回答案和置信度：\n{question}\n{format_instructions}",
    partial_variables={"format_instructions": parser.get_format_instructions()},
    input_variables=["question"],
)
```
适合特殊格式需求与原型开发；灵活性最高，但解析与验证靠自定义，生产里不如 Pydantic 稳。

@@point ⑪ 声明式模型：with_structured_output 的现代范式
@@need 要解决什么
前面每种解析器都要"手动把格式指令塞进 prompt"，模型还可能不听话。2025 年起 LangChain 主推更优雅的范式：**让模型服务端原生支持结构化输出**（Structured Output / JSON Mode），你只声明"我要这个 Pydantic 模型"。

@@idea 核心思路
`model.with_structured_output(PydanticModel)` —— 告诉模型"你的输出必须是这个结构"，框架内部自动完成格式指令、参数序列化、结果校验，一步到位：

```python
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    name: str = Field(description="用户名")
    age: int = Field(description="年龄")
    is_student: bool = Field(description="是否学生")

llm = ChatOpenAI(model="qwen-plus")  # 需支持 structured output
structured_llm = llm.with_structured_output(UserProfile)

profile = structured_llm.invoke("李明 28 岁，在读学生")
print(profile.name, profile.age, profile.is_student)  # 直接是 Pydantic 对象
```
要点：
- 模型原生"承诺"输出合规结构，比"prompt 里塞格式指令"可靠得多
- 声明式 = 聚焦"结果长什么样"，把生成细节交给框架
- **注意：不是所有模型都支持**（尤其部分本地模型），使用前先实测

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 换模型供应商后结构化输出失效 | 部分模型/接口不支持 tool_use 强制约束，声明式依赖后端能力 |
| 以为结构化输出=永远正确 | 结构化只约束格式不保证内容正确，业务校验仍要做 |


@@summary 这一章你学到了什么
- 认识 LangChain 的定位：统一模型接口 + 提示词模板 + 输出解析的编排框架
- 会走三条接入路线（通义 / 智谱 / 本地 Ollama），并坚持 API Key 进环境变量
- 分清非流式与流式两种调用方式
- 掌握三类提示词模板的适用场景：PromptTemplate（结构固定）、ChatPromptTemplate（多轮角色对话）、FewShotPromptTemplate（示例驱动）
- 会用五类输出解析器，并能按场景选型：生产强验证用 Pydantic、要 JSON 用 Json、企业集成用 XML、简单列表用逗号、自定义用 Structured
- 会用声明式 `with_structured_output()` 一步拿到类型安全的结构化结果

下一章：LCEL 链式调用——把"模板 → 模型 → 解析器"以及更复杂的多步逻辑，用 `|` 管道优雅地连起来，为 LangGraph 的图编排打基础。

@@quiz
1. 切换模型供应商（通义↔智谱）时，LangChain 最常见的做法是？
   A. 重写全部代码　　B. 只改 base_url 和 model 名，代码结构不变　　C. 换框架　　D. 换语言
2. ChatPromptTemplate 相比 PromptTemplate 的核心优势是？
   A. 速度更快　　B. 支持多角色（system/human/assistant）消息序列，适合多轮对话　　C. 支持图片　　D. 不需要变量
3. FewShotPromptTemplate 解决什么问题？
   A. 模型太慢　　B. 光靠口头描述模型不知道具体格式，给样例让它照着输出　　C. 内存不足　　D. 无法联网
4. 生产环境、复杂结构、需要强验证时，首选哪个输出解析器？
   A. JsonOutputParser　　B. PydanticOutputParser（类型安全+验证严格）　　C. CommaSeparatedListOutputParser　　D. 手写正则
5. with_structured_output() 相比手动塞 format_instructions 的优势是？
   A. 模型更聪明　　B. 由模型服务端原生保证输出结构，声明式一步到位　　C. 更省钱　　D. 不需要 API Key
6. 本地模型接 LangChain 报"模型找不到"，最可能的排查顺序是？
   A. 重装 Python　　B. 确认 ollama pull 过该模型、模型名拼写、是否走对 langchain_ollama　　C. 换电脑　　D. 升级内存

@@links
讲义|LLM框架实战_基础.pdf|#
官网|LangChain 官方文档|https://python.langchain.com/docs/introduction/
官网|LangChain 提示词模板|https://python.langchain.com/docs/how_to/#prompt-templates
官网|LangChain 输出解析器|https://python.langchain.com/docs/how_to/#output-parsers
官网|Ollama 官方|https://ollama.com/
