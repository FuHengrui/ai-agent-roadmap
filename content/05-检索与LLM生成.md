@@h1 第五章　检索与 LLM 生成
@@sub 阶段 7 · 企业级RAG问答系统　|　实操　|　难度 ★★★★

@@why 这一章在解决什么问题
库建好了，用户提问了，真正的"临门一脚"来了：**怎么从几十万块文本里把"最相关的那几块"捞出来，再让大模型"只照着这几块"回答？** 这里有两个大坑等着新手：一是检索边界不设防——捞出来一堆低相关的垃圾，大模型照单全收开始编；二是提示词不会写——上下文和问题糊在一起，模型答得"毛估估"。

这一章把问答半条链焊完：先讲检索服务怎么配（top_k、相似度阈值、metadata 过滤），再讲 LLM 怎么统一封装（同步/流式），最后讲 RAG 提示词模板——**为什么"不知道要直说"、上下文怎么去重截断**。这是整个系统"出活"质量的关键一章。

@@map 这一章在整个知识库里的位置
上一章：嵌入模型与向量存储——小块文本入库成向量，检索有库可查
**本章** ← 你在这里：检索与 LLM 生成——提问时检索相关块，拼提示词让模型照着答
下一章：API 接口与前端联调——把问答能力包成 HTTP 接口，浏览器里可用
阶段终点：企业级 RAG 问答系统——"文档进来、答案出去"全链路闭合

@@note info 这一章你要达到什么程度
8 个知识点，含核心代码。学完你能：独立配置检索参数并解释每个参数为什么存在；能说清 LLM 类为什么只做"统一封装"；能默写出 RAG 提示词模板并讲清"不知道就直说"为什么是防幻觉的关键；明白流式输出的价值。

@@point ① 检索服务：向量库只管"找向量"，检索服务管"找答案材料"
@@need 要解决什么
上一章的向量库只回答"哪些向量离查询近"。但真正给大模型吃的材料，还要过好几道筛：**除非记限制（top_k）、相似度底线（min_score）、范围过滤（只搜某类文档）**。这些决策散落在调用方就会各写各的，检索逻辑没法复用和调优。

@@idea 核心思路
项目把"检索"收敛成一个统一入口 `SearchService`，调用方只传"问题 + 配置"：

```text
用户提问
   ↓
SearchService.search(question, config)
   ↓
① 嵌入问题 → 查询向量
② 按 metadata_filter 过滤范围（如只查某 namespace）
③ 向量库 search → 候选块
④ 按 min_score 砍掉低相关（宁缺毋滥）
⑤ 返回前 top_k 块 + 得分
```

以前散在业务代码里的"检索该怎么做"，现在集中成**一个可测试、可调参的服务**。第6章的 API 层、将来的前端，都只认识这一个入口。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为检索服务就是"把向量库 search 包一层" | 真正值得封装的不是调用，而是**过滤逻辑和调参入口**（top_k/min_score/过滤）。没有这层服务，这些决策就会散落在每个调用方 |
| 把检索配置写死在 SearchService 内部 | 调优时只能改代码。配置通过 `RetrievalConfig` 传入，**不同场景（精确问答 vs 开放闲聊）用不同配置** |

@@point ② 检索配置 RetrievalConfig：三个旋钮各管什么
@@need 要解决什么
"检索得像不像"是个手感活：捞太少答不全，捞太多全是噪音。**配置不参数化，每次调优都要改代码重部署**，可配置的旋钮就是为"不改代码，调效果"准备的。

@@idea 核心思路
项目用 `RetrievalConfig` 数据类统一这几个参数：

```python
@dataclass
class RetrievalConfig:
    top_k: int = 5                # 返回前几块
    min_score: float = 0.3        # 相似度底线，低于此分不返回
    namespace: str | None = None  # 只搜哪个命名空间（可选范围过滤）
    metadata_filter: dict | None = None  # 额外条件，如 {"source_type": "制度"}
```

| 旋钮 | 调大 | 调小 | 影响 |
|---|---|---|---|
| `top_k` | 上下文更全 | 更聚焦 | 生成时看到多少资料 |
| `min_score` | 更严、更干净 | 更宽松、可能有杂音 | 幻觉风险 vs 漏答 |
| `metadata_filter` | 范围更窄 | 范围更广 | 跨知识库 vs 单库 |

实际调优流程：先宽松采样看"命中质量"，再逐步收 `min_score`。**参数的意义在于你可以"试"**，而不是拍一个数永远不动。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| min_score 拍脑袋设个 0.9 | 相似度分数是**模型相对概念**，没有"绝对 0.9 就好"。要拿真实查询跑一遍看分布再定，否则八成空空如也 |
| top_k 定 1 个"更精准" | 1 个块往往覆盖不全答案；**生成阶段宁可给 3-5 块略多一点**，让模型自己权衡 |
| 忘了 metadata_filter 能和 namespace 组合用 | 两个旋钮是**独立叠加**的：既能按 namespace 限库，也能再按来源类型过滤，别只用其一 |

@@point ③ 相似度阈值 min_score：宁可不答，不要瞎答
@@need 要解决什么
最害人的检索结果是"**看起来相关、其实不沾边**"——问"报销流程"，捞到一段聊"绩效考核"的，因为句子结构有点像。向量相似度是个软概念，没到阈值就给它，等于请模型脑补，幻觉的源头。

@@idea 核心思路
`min_score` 就是"相似度底线"，**低于底线的检索结果直接丢弃，返回空也不硬凑**：

```python
candidates = self.store.search(query_vec, top_k=config.top_k*2,
                               metadata_filter=...)
results = [r for r in candidates if r.score >= config.min_score][:config.top_k]
```

注意实现细节：**先取 2 倍候选，再按分数过滤，最后截 top_k**——只取 top_k 个再过滤，剩下的可能不够数。这道"底线"的价值在第5章兜底逻辑处体现：检索为空时模型会回答"根据现有资料无法确定"，**比硬答强一万倍**。

@@point ④ LLM 的统一封装：为什么加一层"壳"
@@need 要解决什么
各家的 chat 接口参数五花八门，模型名、温度、max_tokens 各有各的叫法。**业务代码不该碰这些细节**——它只想要"给我一段回答文字"。另外，返回结果里除了文字，还有**哪个模型答的、花了多少个 token、为什么结束**，这些是成本核算和排障要用的，漏了可惜。

@@idea 核心思路
项目 `LLM` 类把大模型 API 包成"一个方法出答案"：

```python
class LLM:
    def __init__(self, config):
        # config 里带 provider/base_url/api_key/model，第一类选择在配置层做
        self.client = OpenAI(api_key=config.api_key,
                             base_url=config.base_url)

    def generate(self, messages, temperature=0.1) -> LLMResponse:
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature)
        return LLMResponse(content=resp.choices[0].message.content,
                           finish_reason=resp.choices[0].finish_reason,
                           token_used=resp.usage.total_tokens,
                           model=self.model)
```

`LLMResponse` 带 `content / finish_reason / token_used / model` 四件套：文字给产品，**token 给账单，model 给审计**。业务层永远调 `llm.generate(...)`，不知道也不关心底层是智谱还是通义——这又是"一切可替换"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为加一层封装"多此一举"，直接在业务里调 OpenAI 客户端 | 一旦换提供商/加日志/加成本统计，所有调用处都要改。**封装是给"切换"和"观测"买单的**：一次封装，换来按需替换 |
| 生成调用不处理异常（超时/限流/余额不足） | 大模型 API 一定会出岔子，不 try/except 崩溃的是整个请求。**生成出口要有兜底文案，别把 500 抛给用户** |

@@point ⑤ 流式生成：用户不欠你一个"等待的加载圈"
@@need 要解决什么
同步生成一个问题回答要 2-10 秒，**期间用户盯着空白页面**，体验跟"网页卡死"没区别。企业级产品不能让人猜"它是不是死了"。流式输出的价值：**首字即达，边生成边显示**。

@@idea 核心思路
`generate_stream` 用迭代器逐块吐文字：

```python
def generate_stream(self, messages):
    stream = self.client.chat.completions.create(
        model=self.model, messages=messages, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta            # 每来一段就往上抛一段
```

前端拿到流后逐字渲染（第6章会看到），用户 0.5 秒内看到第一个字，**感知速度比实际快得多**。技术要点：`stream=True` + 迭代 `choices[0].delta.content`；生成完上面 `generate` 的 `token_used` 在流式模式下要另行累计（有的实现直接拿不到总用量）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 流式接口通了，但前端"等全部生成完才一次性显示" | 白做了流式——用户看到的还是空白，等于没流。**前端必须逐块渲染**，流式才有意义 |
| 把流式当默认，但统计 token 时拿不到总量 | 流式响应一般不带 `usage`，要自己按 delta 累计或另查。**预算核算时别拿流式当同步用** |

@@point ⑥ RAG 提示词模板：让模型"只信上下文、不懂就直说"
@@need 要解决什么
把检索到的块直接塞进 Prompt 就行了吗？不行——**大模型有个臭毛病：没有答案也要编一个像样的**。所以提示词必须做三件事：告诉它材料是什么、让它"严格依据材料"、**命令它"材料里没有就直说不知道"**。这三句话是 RAG 防幻觉的总开关。

@@idea 核心思路
项目 `build_prompt`（来自源码 rag.py）的模板结构：

```text
【系统指令】
你是公司的知识库问答助手。请严格依据下面提供的资料回答用户问题。
如果资料中没有答案，请直接回答"根据现有资料无法确定"，不要编造。

【资料】
{检索到的 Top-K 块，每条带来源}

【用户问题】
{用户的提问}

【回答】
```

三个关键设计：
- **"严格依据资料"**：斩断模型"自由发挥"的倾向；
- **"没有就直说"**：把"编造"从行为选项里移除，宁缺毋滥；
- **资料在前、问题在后、明确分隔**：让模型先"读材料"再"答题"，而不是凭记忆先答。

同时生成参数 `temperature` 调低（0.1 左右）：**检索回答要的是忠实，不是创意**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 提示词里写"请你尽量回答" | "尽量"是自由发挥的邀请函。**必须用"严格依据+没有就直说"这种强指令** |
| temperature 开 0.7 以上"回答更生动" | RAG 场景生动 ≈ 幻觉。**回答类用低温度**，创意写作才用高温 |
| 不去重、不截断就把资料全塞进去 | 检索到的块可能重复、可能超长（见下一点）——**不处理就塞，模型会懵** |

@@point ⑦ format_context：资料去重 + 截断，别让模型"中毒"
@@need 要解决什么
检索返回的块往往有重复（相似段落）、还可能超长——**一次性塞几千字给模型**，一是成本飙升（按 token 计费），二是上下文越长模型越"抓不住重点"，三是重复信息会带偏回答。拼 Prompt 前必须"整理"。

@@idea 核心思路
`format_context`（源码 rag.py）负责两步：

```python
def format_context(results, max_chars=...):
    # ① 去重：按块文本的规范化结果去重（同一来源重复命中只留一份）
    # ② 截断：超过 max_chars 的块截断/丢弃，控制总长度
    # ③ 每条标注来源：让模型知道这话来自哪份文档
```

它和检索的 `top_k` 形成**双保险**：top_k 管"捞几块"，format 管"拼多长"。企业场景里**引用来源（citation）就是在这一层标注的**——回答时展示"依据：绩效考核管理办法.pdf 第3页"，溯源能力在这里落地。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 去重按"文本完全一样"判断，相似但不相同的块还在 | 同文档重复命中改了几个字的版本去不掉。**用规范化文本（去空白/去标点）作去重键**，效果更好 |
| 截断从头砍，把关键信息砍了 | 块开头往往是核心句。**超长块要么断在句子边界，要么整块丢弃调小 top_k**，而不是硬截头 |

@@point ⑧ generate_answer 兜底：检索为空时，体面地"不知道"
@@need 要解决什么
检索可能真的捞不到相关的（问题超纲、库太小、阈值太严）。**这时系统必须给出"不知道"而不是胡编**——这是第1章就承诺过的"宁缺毋滥"具体落地。

@@idea 核心思路
`generate_answer` 的完整分支（源码 rag.py）：

```text
def generate_answer(question):
    results = search_service.search(question, config)
    if not results:                          # 检索为空
        return "根据现有资料无法确定"         # 直接兜底，不走模型
    context = format_context(results)
    prompt  = build_prompt(context, question)
    return llm.generate(prompt)              # 有资料才走模型
```

两个设计点：
- **"无法确定"是产品文案不是 bug**——它保护了信誉：宁可说不知道，不说错的；
- 空结果**不走模型**：省一次 API 调用（省钱），也避免模型拿到空上下文开始编。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 检索为空时还硬把空上下文塞给模型"猜一下" | 模型为了不冷场会开始编，把"宁缺毋滥"的承诺全毁了。**空结果必须走兜底分支** |
| 兜底文案硬编码在业务代码里，产品想改措辞要发版 | 文案做成常量/配置（如 `NO_RESULT_MESSAGE`），产品改文案不动代码。**产品文案和业务逻辑分离** |

至此，问答链路"提问 → 检索 → 过滤 → 拼上下文 → 生成"完整闭合。剩下的问题只有一个：**怎么把这套能力通过 HTTP 暴露给浏览器**——下一章的事。

@@summary
这一章你掌握了 RAG 系统"出活"的半条链：
- 会用 `SearchService` 统一检索入口，`RetrievalConfig` 的 top_k / min_score / metadata_filter 三个旋钮各管什么、怎么调
- 理解了 min_score 是"宁缺毋滥"的闸门，宁可返回空也不硬凑
- 会讲 `LLM` 统一封装的价值（换厂商不改业务）和 `LLMResponse` 四件套（内容/结束原因/token/模型）
- 知道流式输出为什么是产品体验刚需
- 能写 RAG 提示词模板：严格依据、没有就直说、材料在前问题在后、低温度
- 会拼上下文：先去重截断再标注来源；检索为空时直接兜底"无法确定"

下一章，把这条链路包成 API 接口，让浏览器里的用户真正用起来。

@@quiz
1. min_score（相似度阈值）的主要作用？
   A. 提高检索速度　　B. 过滤低相关结果，宁可返回空也不让模型瞎编　　C. 减少存储　　D. 控制生成长度
2. 检索时为什么要"先取 2 倍候选再过滤"？
   A. 多花点也无妨　　B. 先过滤再取 top_k 可能凑不满，先取足再筛才稳　　C. 2 倍是固定要求　　D. 无所谓
3. RAG 提示词里"根据现有资料无法确定"这句话的作用？
   A. 凑字数　　B. 把"编造"从模型行为里移除，防幻觉　　C. 让回答更长　　D. 只是示例
4. RAG 回答场景的 temperature 应该？
   A. 尽量高，生成更生动　　B. 低（0.1 左右），忠实于资料　　C. 无所谓　　D. 负值
5. format_context 为什么要去重和截断？
   A. 省 token 成本、避免上下文杂乱带偏模型　　B. 显得专业　　C. 去除重复能快一点　　D. 两个都要又省钱又准确
6. 检索结果为空时，系统正确的行为是？
   A. 让大模型自由发挥　　B. 直接返回"根据现有资料无法确定"，省调用且不胡编　　C. 重试 3 次　　D. 报错

@@links
参考|章节7_检索模块.pdf|#
参考|章节8_LLM模块.pdf|#
源码|rag_project/src/retrieval 与 src/llm（SearchService / LLM / rag.py 完整实现）|#
官网|OpenAI Chat Completions 协议（流式参考）|https://platform.openai.com/docs/guides/text-generation
官网|tenacity（重试库，嵌入层使用）|https://github.com/jd/tenacity