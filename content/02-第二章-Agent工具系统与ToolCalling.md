@@h1 第二章　Agent 工具系统与 Tool Calling
@@sub 阶段 8 · AI Agent 智能体与多模态应用　|　理论+实践　|　难度 ★★★

@@why 这一章在解决什么问题
上一章说了 Agent 要有"手脚"，可问题来了：**模型是个"只会输出文字"的程序，它怎么才能真的去查天气、下单、转账？** 答案是模型并不会"亲手"执行任何代码——它只能**输出一段 JSON 告诉系统"我想调用 XX 工具，参数是 YYY"**，真正干活的是你的程序。这个"模型表达意愿 → 系统代为执行"的机制，就是 Tool Calling。

本章解决三件事：
1. Tool Calling 到底是怎么工作的（API 长什么样、流程怎么走）
2. 工具的参数怎么定义才能让模型准确填写（JSON Schema / Pydantic）
3. 参数错了怎么办、工具执行失败怎么办（验证策略 / ToolException）

这是后面所有 Agent 工程的地基：LangGraph 的 ToolNode、MCP、A2A，最终都是围绕"模型选工具→填参数→执行→返回"这同一套心智模型运转的。

@@map 这一章在整个知识库里的位置
上一章：Agent 智能体理论基础——概念模型（大脑/手脚/笔记本）
**本章** ← 你在这里：Agent 工具系统与 Tool Calling——把"手脚"真正做出来
下一章：LangChain 基础——用框架把这些能力工程化、可复用
再往后：LCEL → LangGraph → 工具/记忆/MCP → 实战与 A2A

@@point ① Tool Calling 是什么：模型只"表达"，不"执行"
@@need 要解决什么
用户说"帮我查杭州明天天气"，模型知道该查天气，但它**没有办法真的访问天气 API**——它只是个文本生成器。必须有个机制让"模型的想法"变成"真实世界的动作"。

@@idea 核心思路
Tool Calling（原名 Function Calling）指：**LLM 将用户的自然语言请求，结构化地映射为对预定义工具函数的调用**。

工作流程（五步）：
1. 你定义工具列表（每个工具= 名称 + 描述 + 参数 Schema），随请求一起发给模型
2. 模型判断"这个问题该用哪个工具"，输出一段**工具调用请求**（含工具名 + 参数 JSON）
3. 你的代码**解析这段 JSON，自己去执行**真实的函数/API
4. 把执行结果以"工具消息"回传给模型
5. 模型基于结果组织最终回答（或继续下一步调用）

核心特点：
- **模型不执行代码**，只做"决策与参数生成"；执行权始终在宿主程序手里
- 一次请求里模型可能输出**多个工具调用**（并行调用）
- 模型也可能先不调用、直接回答（当问题用不到工具时）

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为模型"自己调用"了 API | 模型只输出 JSON 意图，真实调用必须由你的代码执行，忘了执行就永远是"纸面调用" |
| 把工具结果直接拼进 prompt 不回传 | 必须作为 tool 消息回传，模型才能"看到"结果并续答 |
| 忽略"模型可以只回答不调工具" | 强行期待每次都有 tool_calls 会导致流程误判，要处理"无调用"分支 |

@@point ② 核心 API 组件：工具怎么"长在"请求里
@@need 要解决什么
要让模型知道有哪些工具可选、每个工具长什么样，需要一套**标准化的描述方式**随请求发送。这套描述方式就是 API 层面的"工具注册表"。

@@idea 核心思路
主流 LLM 的 Tool Calling API 通常包含三大核心组件：

1. **Tools（工具定义列表）**：发给模型的一组"工具说明书"，每个包含 type（通常 function）、function.name（工具名）、function.description（何时用）、function.parameters（参数 JSON Schema）
2. **Tool Calls（模型的响应）**：模型返回的调用意图，含 id、function.name（选中的工具）、function.arguments（参数 JSON 字符串）
3. **Tool Message（工具结果回传）**：你把执行后的结果以 tool 角色消息传回，与模型发出的调用 id 对应

一次完整对话的消息序列大致是：
```
user: 杭州明天天气怎么样？
assistant: tool_calls=[get_weather(city="杭州", date="明天")]
tool: 晴，25℃
assistant: 杭州明天晴天，25℃……
```
API 兼容性提示：OpenAI 系（含通义、智谱、DeepSeek 等国产模型）基本都兼容这套形态，切换模型时工具代码改动很小。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 工具 description/参数说明写得太简略 | 模型全靠 description 决定"何时调用、怎么填参"，缺了等于盲填 |
| 把所有逻辑塞进一个大函数、参数大而全 | 违背单一职责，字段越多模型越容易填错 |

@@point ③ JSON Schema 设计基础：让模型"会填参数"
@@need 要解决什么
模型要"看懂一个工具怎么用"，靠的是参数的结构化描述。描述得模糊，模型就乱填；描述得精确，模型一把填对。

@@idea 核心思路
JSON Schema 是**定义 JSON 数据结构的规范**，用于描述工具参数的字段、类型、必填性、取值范围。

设计原则：
- **type**：string / number / integer / boolean / array / object
- **properties**：列出每个字段及其类型
- **required**：标记必填字段（模型漏填会直接校验失败）
- **description**：每个字段写清楚含义、格式（"YYYY-MM-DD"比"日期"强 100 倍）
- **enum / minimum / maximum / pattern**：约束取值，把"模型自由发挥"的空间压缩到最小

示例（电商搜索工具）：
```json
{
  "type": "object",
  "properties": {
    "keyword": { "type": "string", "description": "搜索关键词" },
    "category": { "type": "string", "enum": ["手机", "电脑", "家电"], "description": "商品类目" },
    "page": { "type": "integer", "minimum": 1, "description": "页码，从1开始" }
  },
  "required": ["keyword"]
}
```

规则：**描述越具体，模型填对率越高**。给格式示例、给取值范围、给默认行为——把歧义消灭在定义阶段。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 字段 description 写"一些数据"之类空话 | 模型无从判断格式，只能猜，填错率飙升 |
| 忘记 required | 关键字段缺失时模型还浑然不觉，下游直接炸 |
| enum/format 不用 | 自由文本框模型容易填"灰色地带"值，校验失败还不知怎么改 |

@@point ④ JSON Schema 现代化生成：Pydantic 自动产出
@@need 要解决什么
手写 JSON Schema 又长又容易出错，而且代码里已经定义了 Python 数据结构，两边要保持同步——改一处漏一处。

@@idea 核心思路
用 **Pydantic**（Python 类型驱动的数据校验库）定义参数模型，然后**自动生成 JSON Schema**，实现"类型驱动开发"：

```python
from pydantic import BaseModel, Field
from typing import Literal

class SearchProductsArgs(BaseModel):
    keyword: str = Field(description="搜索关键词")
    category: Literal["手机", "电脑", "家电"] = Field(description="商品类目")
    page: int = Field(default=1, ge=1, description="页码，从1开始")

# 自动生成 JSON Schema
schema = SearchProductsArgs.model_json_schema()
```

Pydantic 核心特性：
- **自动 JSON Schema 生成**：BaseModel 定义即 Schema，零维护
- **类型声明即是文档**：字段类型、默认值、约束（gt/ge/lt/le/Literal）就是参数说明书
- **验证一体化**：同一个模型既能生成 Schema，又能拿来校验模型填的参数、解析工具结果
- **与 LangChain/LangGraph 深度集成**：agent 工具的参数模型直接写 Pydantic 类

一句话：**写代码时定义一次类型，Schema、校验、解析全自动**。这是现代 Agent 工具开发的标配姿势。

@@point ⑤ 参数验证：模型也会填错，必须有防线
@@need 要解决什么
即使 Schema 写得再好，模型也可能填错参数（漏字段、类型错、越界）。如果直接拿错误参数执行工具，轻则返回垃圾结果，重则把脏数据写进系统。

@@idea 核心思路
验证发生在**模型输出之后、真实执行之前**，是 Agent 可靠性的第一道保险。

验证策略选择：
- **强制失败（Fail Fast）**：参数不符合 Schema 就直接报错，让模型重新生成。适合"参数错了会产生副作用"的场景（转账、下单）
- **自动修复（Auto-fix）**：类型能转就转（"5"→5）、缺省值用默认补齐。适合字段价值低、容错高的场景（搜索分页）
- **重试机制（Retry）**：校验失败后带着错误信息回给模型，让它修正后重试 1-2 次——这是 Agent 实战中最常用的兜底

AI 平台的角色：现在主流平台（OpenAI/通义/智谱）在服务端也会做一层参数校验，模型生成不符合 Schema 时自动重试或返回错误。但**不要把平台校验当唯一防线**——你的 Agent 系统同样要校验。

工具层集成（以 LangChain 为例）：用 Pydantic 作为 args_schema，LangChain 在调用工具前自动校验参数，不符合直接抛 ValidationError，由上层捕获重试。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 完全信任模型参数直接执行 | 模型偶发填错是常态，不校验等于把脏数据直接写进业务系统 |
| 校验失败不重试就放弃 | 错一次不代表永远错，带错误信息重试一次成功率大幅提升 |
| 只靠平台侧校验 | 平台校验覆盖不到你的业务规则（如余额是否足够），必须在自己侧也校验 |

@@point ⑥ ToolException：工具执行失败后的"体面"
@@need 要解决什么
参数对了，工具执行也可能失败（网络超时、API 限流、业务报错）。如果执行层直接把异常抛穿整个 Agent 流程，一次失败就全盘崩溃。

@@idea 核心思路
用 **ToolException**（工具异常）把"工具内部错误"包装成**可回传给模型的结构化错误信息**，让 Agent 有机会自救。

要点：
- 工具内部 try/except 捕获真实异常，转成 ToolException("查天气失败：上游 API 超时（5xx）") 抛出
- Agent 框架捕获 ToolException 后，把**可读的错误信息**作为工具结果回传给模型
- 模型看到错误信息后自行决策：重试 / 换工具 / 换参数 / 放弃并如实告知用户

好处：
1. 工具失败不再中断整个 Agent 流程（异常被"降级"成一次普通工具结果）
2. 错误信息成为模型决策的依据（"超时了我就稍后重试"）
3. 对用户透明——最终回答里能解释"刚才查失败了，原因是什么"

设计建议：错误信息要**结构化、可读、可行动**（"哪个工具、失败原因、建议怎么做"），而不是堆一屏 traceback。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 把原始 traceback 原样抛给模型 | 模型看不懂堆栈，只会胡编原因；要包装成"工具名+原因+建议" |
| 工具吞掉异常返回 None | 模型拿"空结果"当"查无数据"，可能给出错误结论；失败必须显式标记 |
| 所有工具异常都重试 | 业务性失败（余额不足）重试只会更糟，要区分"可重试"与"不可重试" |

@@point ⑦ 案例拆解：三个真实工具
@@need 要解决什么
前面都是概念，看看真实 Agent 项目里工具到底长什么样，把 Schema + 校验 + 异常串成一条线。

@@idea 核心思路
**案例 1：电商搜索工具**（查询类，低风险）
- 参数：keyword（必填）、category（枚举）、page（默认1）
- 返回：商品列表 + 总数
- 校验：Fail Fast + 重试，参数错就让模型重填
- 异常：搜索服务超时 → ToolException 提示降级为"返回热销推荐"

**案例 2：金融交易工具**（写操作，高风险）
- 参数：股票代码、方向（买/卖）、数量（正整数）、限价
- 校验：强制失败 + 二次人工确认（结合 HITL，后面章节讲）
- 异常：余额不足、停牌等业务错误 → 结构化错误回传，模型如实告知用户，禁止自动重试下单

**案例 3：API 代理工具**（通用，中风险）
- 参数：端点、方法、请求体
- 设计：白名单限制端点，避免模型"乱打 API"
- 校验：端点白名单 + 方法白名单 + 参数 Schema
- 异常：鉴权失败/限流 → 区分可重试（429 限流可稍后）与不可重试（401 换凭证）

案例共性的三个结论：**查询型容错高、写操作必须严格校验甚至人工确认、错误信息决定 Agent 能否自救。**

@@point ⑧ 工具设计最佳实践：让工具"好用"而不是"能用"
@@need 要解决什么
工具写出来还要能被模型稳定、正确地调用。设计不当，工具就是"没人用的摆设"——模型要么不调，要么乱填参数。

@@idea 核心思路
四条硬规则：
1. **用具体的类型而不是 Any**——模型不知道 Any 该填什么，给出 str / int / 枚举
2. **为所有字段添加 description**——description 是模型填参数的说明书，缺失=盲填
3. **合理使用约束条件**——`Field(gt=0)`、`Literal[...]` 把取值范围写死，减少非法参数
4. **保持工具的单一职责**——一个工具只干一件事，字段越聚焦，模型越不容易填错

```python
class SearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词，必填")
    limit: int = Field(default=10, ge=1, le=50, description="返回条数，1-50")
    category: Literal["手机", "电脑"] = Field(description="商品类目")

@tool(args_schema=SearchInput)
def search_product(keyword: str, limit: int = 10, category: str = "") -> str:
    """搜索商品，返回符合条件的结果列表"""
    ...
```

一句话：**模型拿不到的信息就不会用它——把可选项、边界和含义都写进 description 与约束里**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 字段用 Any/裸 dict，模型不知道填什么 | 类型越具体模型越容易生成合法参数，Any 等于没约束 |
| 只标类型不写 description | 模型不理解字段含义，会跳过或填错，description 就是说明书 |

@@summary 这一章你学到了什么
- 理解了 Tool Calling 的本质：模型只输出"调用意图 JSON"，宿主程序负责真实执行，结果以 tool 消息回传
- 掌握了工具的 API 三件套：tools 定义 → tool_calls 响应 → tool message 结果
- 会用 JSON Schema 结构化参数，并总结出"描述越具体、类型枚举约束越多，模型填对率越高"
- 会优雅升级：用 Pydantic 类型定义自动生成 Schema，实现"定义一次、Schema/校验/解析全自动"
- 建立了双层防线：参数校验（Fail Fast / Auto-fix / Retry）+ 执行异常（ToolException 包装、结构化回传、模型自救）
- 通过三个案例看清了不同风险等级工具的差异化设计

下一章进入框架层：LangChain 基础，把"模型调用、提示词、输出解析"这些重复劳动交给框架，让 Agent 开发提速。

@@quiz
1. Tool Calling 中，模型实际执行 API 调用吗？
   A. 执行，模型直接调 API　　B. 不执行，模型只输出调用意图，宿主代码执行　　C. 执行一半　　D. 视模型而定
2. 下面哪项最能提高模型填参数的准确率？
   A. 字段描述写详细+用枚举约束取值　　B. 参数越多越好　　C. 不写 description　　D. 全靠模型自觉
3. Pydantic 相比手写 JSON Schema 的核心优势是？
   A. 运行更快　　B. 定义一次自动生成 Schema、顺带校验和解析　　C. 能训练模型　　D. 不需要类型声明
4. 工具执行失败后，ToolException 的正确处理方式是？
   A. 直接中断 Agent　　B. 包装成结构化错误信息回传，让模型决策重试/换策略　　C. 吞掉异常返回 None　　D. 记录日志继续当成功
5. 金融交易类工具与搜索类工具的设计差异，最正确的是？
   A. 没差异　　B. 交易工具校验更严格、失败更谨慎（可加人工确认），搜索工具容错更高　　C. 搜索工具更严格　　D. 交易工具不校验
6. 模型"该调工具却直接回答"或"不该调却调了"，常见根因是？
   A. 模型太笨　　B. 工具 description 写得含混，边界不清　　C. 参数太多　　D. 网络慢

@@links
参考|02Agent工具系统.pdf|#
官网|OpenAI Function Calling 文档|https://platform.openai.com/docs/guides/function-calling
官网|Pydantic 官方文档|https://docs.pydantic.dev/
官网|LangChain 工具概念|https://python.langchain.com/docs/concepts/tools