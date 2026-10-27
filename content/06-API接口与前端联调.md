@@h1 第六章　API 接口与前端联调
@@sub 阶段 7 · 企业级RAG问答系统　|　实操　|　难度 ★★★

@@why 这一章在解决什么问题
前五章把"入库、检索、生成"都做完了——但这些都是**库函数和类**，用户没法用。企业级系统的最后一棒，是把它变成**浏览器里能点的网页**：上传文档、输入问题、看到答案和出处。这中间隔着两层功夫：一是把能力包成标准的 HTTP 接口（FastAPI），二是写一个前端页面把这些接口调起来。

这一章解决：API 怎么设计（请求/响应模型、健康检查、依赖注入）、上传接口怎么和"仅解析"跟"解析+入库"两种模式兼容、前端怎么接流式输出、以及**联调时最容易踩的跨域（CORS）坑**。

@@map 这一章在整个知识库里的位置
上一章：检索与 LLM 生成——问答链路在代码层闭合（检索→拼上下文→生成）
**本章** ← 你在这里：API 接口与前端联调——把能力包成 HTTP，浏览器可用
阶段终点：企业级 RAG 问答系统——全链路闭合，一个可交付的第一版产品
下一阶段：你可以基于这套骨架扩展多知识库、权限、增量更新等企业能力

@@note info 这一章你要达到什么程度
8 个知识点，收尾实操。学完你能：说清 API 的三个路由各干什么；理解依赖注入为什么让"可替换"延伸到 HTTP 层；知道上传接口的两种模式怎么共存；能独立排查"前端调不通后端"的 CORS 报错。

@@point ① API 层解决什么问题：把"能力"变成"服务"
@@need 要解决什么
检索、生成写得再好，如果只能"在 Python 里 import 后用"，那就只服务了一个程序员。**企业里要服务的是一群浏览器用户**——前端、未来可能的移动端、别的系统，都需要通过标准 HTTP 调用这些能力。API 层就是这扇门。

@@idea 核心思路
项目用 FastAPI（阶段2已验证的选型）提供三个核心路由：

```text
POST /api/chat      用户的提问 → 返回答案 + 来源
POST /api/document  上传文档 → 解析入库（或仅解析）
GET  /api/health    健康检查 → 服务是否活着
```

| 路由 | 方法 | 干什么 | 使用者 |
|---|---|---|---|
| `/api/chat` | POST | 问答主入口 | 前端问答框 |
| `/api/document` | POST | 文档入库入口 | 前端上传区 |
| `/api/health` | GET | 探活/运维 | 部署、负载均衡 |

API 层的设计原则：**内部能力 + HTTP 协议 = 对外服务**。路由很薄——它不做业务，只负责"收请求、调内部服务、回响应"（呼应第2点依赖注入，把内部服务"注入"进来）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由函数越来越胖，把检索、拼提示词、生成全写在里面 | API 层职责应该是"翻译 HTTP"，业务逻辑该在下层服务里。**路由超 30 行就该警觉，业务往 Service 层挪** |
| 以为"API 层 = 写几个函数"，没有请求/响应模型 | 没有契约的接口，前端和后端各猜各的，联调必翻车。**每个接口先定 Pydantic 模型再写逻辑** |

@@point ② 请求/响应模型：用 Pydantic 把"契约"写死
@@need 要解决什么
接口没有明确的"输入输出长什么样"，前后端就会各猜各的：前端传 `question`，后端读 `query`，默默返回空。**接口契约必须显式声明，还能被自动校验。**

@@idea 核心思路
项目用 Pydantic 模型定义契约（自动校验 + 自动文档）：

```python
class ChatRequest(BaseModel):
    question: str                          # 用户问题（必填）
    top_k: int = 5                         # 检索块数（可选，有默认）
    model: str | None = None               # 可选指定模型

class ChatResponse(BaseModel):
    answer: str                            # 生成答案
    sources: list[SourceRef]               # 答案引用的来源
```

```python
class SourceRef(BaseModel):
    doc_id: str      # 哪份文档
    text: str        # 被引用的原文片段
    score: float     # 相似度得分
```

三个要点：**字段必填/可选写清楚**（`question` 必填，`top_k` 有默认）；**响应带 `sources`**——这是企业级 RAG 和玩具的分水岭，答案必须有出处可核；**FastAPI 会自动生成 OpenAPI 文档**，前端照着文档对接，不吵架。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 字段名用前后端各自习惯（`question` vs `query`），静默返回空 | 契约不一致，Pydantic 校验不过会报 422（或静默忽略）。**字段名以模型为准，前后端共用一份 OpenAPI 文档** |
| 响应里直接 `return dict` 而不是定义 `ChatResponse` | 少字段、多字段、类型错都不会被察觉。**定义 response_model，让框架帮你校验出参** |

@@point ③ 设置中心：多提供商配置怎么服务到 API 层
@@need 要解决什么
第1章定了"智谱 + 通义双提供商"，但配置写在哪些模块、怎么被路由读到？**不能每个文件都读一遍 .env、各写各的解析逻辑**——要有唯一的配置中心，一次加载、处处可用。

@@idea 核心思路
项目 `api/config.py` 用 Pydantic `Settings` 统一管理：

```python
class Settings(BaseSettings):
    llm_provider: str = "zhipu"                    # 默认提供商

    # 每个提供商一套连接参数
    llm_providers: dict[str, dict] = {             # zhipu / qwen
        "zhipu": {"base_url": "...", "model": "glm-4", "api_key_env": "ZHIPU_API_KEY"},
        "qwen":  {"base_url": "...", "model": "qwen-plus", "api_key_env": "DASHSCOPE_API_KEY"},
    }
    chroma_path: str = "./chroma_data"
    collection_name: str = "documents"

    class Config:
        env_file = ".env"                           # 从 .env 读，可被环境变量覆盖
```

- **切换提供商**：改 `llm_provider` 一个字段，全局生效（选型承诺兑现）；
- **密钥不落地**：配置里存的是"密钥的环境变量名"，实际 Key 仍在 `.env`/环境变量里，`api_key = os.getenv(cfg.api_key_env)` 时再取；
- **单一真源**：所有模块 `get_settings()` 拿同一个配置实例，不会出现"这模块一个值、那模块一个值"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为"配置在 Settings 里就是安全的"，把真实 Key 写进默认值 | Settings 的默认值也会进代码仓库！**真实 Key 只能从环境变量/`.env` 来，配置类里存的是变量名** |
| 改了 `.env` 但服务不生效 | Settings 通常在进程启动时读一次，**改了要重启服务**（或用热重载）。别以为改文件就立刻生效 |

@@point ④ 依赖注入：让"换实现"延伸到 HTTP 层
@@need 要解决什么
路由函数里如果 `new` 一个具体的 `SearchService` 和 `LLM`，那么：换实现要改路由；测试时想用假服务（Mock）没法注入；多个请求会各自建连接。**依赖注入（DI）解决"路由只管用，不负责造"。**

@@idea 核心思路
FastAPI 的 `Depends` 就是轻量 DI：

```python
# deps.py：集中提供依赖
def get_search_service():
    return SearchService(embedding=get_embedding(),
                         store=get_vector_store(),
                         config=get_settings())

# main.py：路由声明"我要什么"，框架给什么
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest,
               search: SearchService = Depends(get_search_service),
               llm: LLM = Depends(get_llm)):
    ...
```

三个收益：**解耦**（路由不关心 SearchService 怎么构造）；**可测试**（测试时把依赖换成 Mock，不碰真实向量库和 API）；**单例复用**（连接、客户端只建一次）。这是"接口抽象"从类层延伸到 HTTP 层的关键一步——**换实现、换模型、换库，路由代码一行不改**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 以为依赖注入是"花架子"，直接在路由里 `SearchService(...)` new 一个 | 每次请求都新建连接/客户端，且替换实现要改路由。**把所有依赖收敛到 `deps.py`，路由只声明、不创建** |
| 测试时不换 Mock，跑了真实向量库和 API | 单元测试慢、依赖网络、结果不可复现。**依赖注入的正确用法就是测试注入假实现**，见坑率断崖式下降 |

@@point ⑤ /api/chat 主链路：从请求到带出处的答案
@@need 要解决什么
问答接口是整个产品的"门面"，它的内部要把第5章的所有知识串起来，并且把"答案 + 出处"一并返回。**这条链路要诚实：答案多长、依据哪几块，都要可追溯。**

@@idea 核心思路

```text
POST /api/chat  {question: "年假几天"}
   ↓ 依赖注入
SearchService.search(question, config)
   ↓ top_k 块 + min_score 过滤 + format_context 整理
RAG 提示词（严格依据 + 不知道直说）
   ↓ llm.generate
ChatResponse {
  answer: "根据《员工手册》第三章，年休假为 5~15 天……",
  sources: [ {doc_id, text, score}, ... ]   ← 回答的每一步都有依据
}
```

关键设计点：
- **检索和生成都在路由里编排，但业务逻辑全在各服务类里**（路由保持薄）；
- `sources` 不只是展示用——**它是审计依据**：用户能点开原文核对，模型编不了假（编了也对不上出处）；
- 异常分支：检索为空 → 返回"根据现有资料无法确定"（第5章的兜底在 API 层自动生效）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 路由用了 `async def` 却在里面跑同步的重计算 | FastAPI 的 `async` 路由里做阻塞操作会卡住整个事件循环。**重活要么用 `def`（FastAPI 自动放线程池），要么显式异步** |
| 生成答案失败时直接抛 500 | 前端拿到 500 只能干瞪眼。**生成出口要有兜底响应结构"抱歉，暂时无法回答"**，可用性和报错是两回事 |

@@point ⑥ /api/document 上传：一个接口兼容两种模式
@@need 要解决什么
上传接口有个隐藏需求：**有时用户只想"先解析看看效果快不快"，有时要"解析并正式入库"**。如果做两个接口，前端和调用方都要多学一套。更好的方案：一个接口，用参数区分行为。

@@idea 核心思路
`/api/document` 接受文件 + 可选参数：

```python
@app.post("/api/document")
async def upload_document(file: UploadFile,
                          collection_name: str = "default",   # 可选：入库到哪个库
                          store: DocumentStore = Depends(get_document_store)):
    if collection_name:                     # 有 collection → 解析 + 入库
        doc_id = await store.add_document(file)   # 全链路：解析清洗分块嵌入存储
        return {"doc_id": doc_id, "status": "indexed"}
    # 无 collection → 仅解析预览（不落库）
    text = await store.parse_only(file)
    return {"chars": len(text), "status": "parsed"}
```

设计点：**参数即模式**——传 `collection_name` 就走"解析+入库"，不传就走"仅解析"；两个行为一个入口，前端逻辑简单。`DocumentStore` 同时被 API 层和测试复用，符合第4章"装配线总调度"的定位。

@@point ⑦ 健康检查与启动装配：让部署方睡得着觉
@@need 要解决什么
一个服务"看起来活着"和"真的能干活"是两回事。**运维要能一键探活；前端要允许跨域调用**；路由要统一前缀、统一 CORS。这些"装配"不到位，功能再好也上不了线。

@@idea 核心思路
`main.py` 做三类装配：

```python
app = FastAPI(title="企业级RAG问答系统")

# ① CORS：允许前端页面跨域调用（换行续写）
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173"],  # Vue dev server
                   allow_methods=["*"], allow_headers=["*"])

# ② 统一前缀与健康检查
app.include_router(api_router, prefix="/api")
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

| 装配项 | 解决什么 |
|---|---|
| **CORS 中间件** | 浏览器跨域拦截是联调第一坑（见坑位），必须显式放行前端来源 |
| **统一 `/api` 前缀** | 路由分组清晰，未来加版本号（`/api/v1`）方便 |
| **`/api/health`** | 探活用；容器编排和负载均衡都靠它判断服务存活 |

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 前端调后端报 **CORS error**（浏览器控制台红字） | 后端没配 CORS 或 allow_origins 没包含前端地址。**前后端联调第一坑，先查中间件配置** |
| allow_origins 用 `"*"` 图省事 | 生产这样等于允许任何网站调用你的接口（可能被滥用）。**开发用 `*`，生产收窄到真实域名** |
| 端口不对、地址写错，报"连接被拒绝" | FastAPI 默认 8000，Vue 默认 5173。**联调前先 `curl` 一下 health 确认后端真活着**，别让前端背锅 |

@@point ⑧ 前端联调：Vue3 + Element Plus 把链路点亮
@@need 要解决什么
后端接口齐了，但要"用户能点"还差一个壳：**上传区、问答框、答案展示、以及流式打字效果**。前端看着是"界面设计"，实际是"把第5章的流式输出用对"——回答从"等 5 秒全出来"变成"边生成边显示"，体验天差地别。

@@idea 核心思路
前端（frontend/，Vue3 + Element Plus）两个核心页面：

**① 问答页**：输入框 → 调 `POST /api/chat` → 展示 `answer` + 展开 `sources` 卡片（每张显示原文出处，可点击核对）。

**② 流式输出**（要点）：用 `fetch` 读流而非一次拿响应：

```javascript
// 用 fetch 的 ReadableStream 逐段读取后端 /api/chat/stream
const reader = response.body.getReader()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  answerBox.innerText += decoder.decode(value)   // 逐段上屏
}
```

**③ 上传区**：`el-upload` 选择文件 → 调 `POST /api/document` → 显示入库状态（indexed/parsed）。

前端联调三板斧：**先 curl 后端确认活着** → **再配 CORS** → **最后接流式渲染**。任何一步卡住，回第⑦点排查。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 前端"能请求到"但页面一直空白 | 很可能问题在后端响应很慢（同步生成 2-10 秒）且前端没处理 loading。**先确认接口真的返回了，再谈渲染** |
| 把 sources 当可有可无，答案底下不展示来源 | 前端不展示出处，后端精心设计的溯源能力就白做了。**sources 是产品卖点不是技术债**，前端至少要能展开核对 |

@@summary
这一章把整个系统焊成了可交付的产品：
- API 三个路由各司其职：`/api/chat` 问答、`/api/document` 上传、`/api/health` 探活
- Pydantic 把请求/响应契约写死，`sources` 让回答可溯源（企业级分水岭）
- Settings 配置中心实现"智谱/通义一键切换"；依赖注入让换实现不动路由
- 上传接口一个入口两种模式（仅解析 vs 解析+入库）
- 学会了 CORS 的前后端联调排查三板斧
- 前端用流式渲染把"等待"变成"逐字生成"，体验质变

**至此，"企业级 RAG 问答系统"这个阶段的整条链路全部闭合**：文档上传 → 解析 → 清洗分块 → 嵌入 → 入库 → 提问检索 → 拼上下文 → 大模型生成 → 带出处返回 → 浏览器展示。你已经亲手搭完了一个完整的、可交付的企业知识问答系统第一版。

@@quiz
1. /api/chat 响应里的 sources 字段存在的意义是？
   A. 好看　　B. 让答案可溯源、可审计，用户能点开原文核对　　C. 增加数据量　　D. 前端必须用
2. 路由函数用 Depends 注入 SearchService 的好处是？
   A. 代码更少　　B. 路由不负责构造依赖，测试可换 Mock，实现可替换　　C. 运行更快　　D. 必须这样写
3. 前端报 CORS error，第一反应是？
   A. 前端代码写错了　　B. 后端没配 CORS 中间件或 allow_origins 不含前端地址　　C. 换浏览器　　D. 换端口
4. /api/document 的 collection_name 参数作用是？
   A. 给文件改名　　B. 有则"解析+入库"，无则"仅解析"，一个接口两种模式　　C. 指定模型　　D. 加密
5. "双提供商切换"在代码层面最终落在哪？
   A. 改 LLM 类　　B. 改 Settings 里的 llm_provider 一个字段　　C. 改前端　　D. 改 .env 文件名

@@links
参考|章节9_API接口.pdf|#
源码|rag_project/src/api 与 frontend（API 与前端全量源码）|#
官网|FastAPI 依赖注入|https://fastapi.tiangolo.com/tutorial/dependencies/
官网|Pydantic Settings|https://docs.pydantic.dev/latest/concepts/pydantic_settings/
官网|Vue3 官方文档|https://cn.vuejs.org/
官网|Element Plus|https://element-plus.org/
官网|MDN fetch 流式读取|https://developer.mozilla.org/zh-CN/docs/Web/API/ReadableStream