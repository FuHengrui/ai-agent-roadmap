@@h1 第一章　项目全景与技术选型
@@sub 阶段 11 · LegalMind 法律咨询系统（RAG + 多 Agent）　|　2 课时　|　难度 ★★☆

@@why 这一章在解决什么问题
普通人遇到法律问题，第一反应是"问朋友"或"上网搜"。网上搜到的答案是**通稿**，不针对你的案情；问朋友最多给你一句"这事得打官司"。真正有用的回答要命中两样东西：**具体的法条**和**类似的判例**——"你这案子和某法院 2023 年那个判例很像，按那个逻辑你大概能赢"。

但法律条文和裁判文书动辄上千万条，不可能全塞进提示词。LegalMind 要做的，就是用 **RAG（检索增强生成）** 先把相关案例和法律依据"捞"出来，再交给 **多 Agent 系统（意图识别 → 案例检索 → 问答/文书生成）** 组织成专业回答——你问"离婚财产怎么分"，它先判断这是"问答"意图，检索离婚判例，再给你有法条有案例的回答；你说"帮我写起诉状"，它自动切换成文书生成通道。

学完这一章，你手里有一张**完整系统蓝图**：这个"AI 律师"由哪些模块组成、每个模块用什么技术、请求从浏览器到 Postgres 再到 LLM 怎么走通。后面每一章都是这张图的一块拼图。

@@map 这一章在整个知识库里的位置
上一章（阶段 10 · 安康智慧健康管理平台）：LangGraph 五节点工作流 + RAG 医学知识库——你已经跑通过"检索-生成"链路
**本章** ← 你在这里：为"法律咨询系统"画全景图——痛点、功能模块、技术栈、架构分层与数据流
下一章：开发环境与基础设施——Python 3.14、Postgres/Redis 容器、.env 配置怎么一次搭好
再往后：FastAPI 骨架 → ORM 建模（用户/案例/会话/文书四张表）→ JWT 认证 → LLM 客户端 → 向量库 → RAG → Agent 工作流 → API 组装 → Vue3 前端
阶段终点：交付一个能跑通"咨询-检索-问答/文书生成"全流程的 AI 法律顾问 Web 应用

@@point ① 这个项目解决的真实痛点
@@need 要解决什么
先搞清楚"为什么非做这个系统不可"，后面的技术选型才有落点——技术永远为痛点服务。法律咨询行业有四件"传统方案干不了"的事：

@@idea 核心思路
| 痛点 | 具体表现 | 传统方案为什么不行 |
|---|---|---|
| 信息过载 | 法条几十万条、裁判文书几千万份 | 人力翻不完，搜索引擎只给你链接不给结论 |
| 回答不精准 | 同样问"欠钱不还怎么办"，民间借贷和工程款纠纷答法完全不同 | 通用大模型没喂你的案情细节，只能讲"正确废话" |
| 文书门槛高 | 起诉状、答辩状有固定格式和必备要素，写错一处立案就被退 | 普通人不知道"诉讼请求要列明金额""管辖法院不能随便写" |
| 案例依据难找 | 回答要有"哪个法院哪个案号判过类似案子"才有说服力 | 判例检索是专业法律数据库的活，普通用户够不着 |

LegalMind 的解法一句话：**用向量检索+关键词检索双路召回把相关案例捞出来 → 重排序挑最相关的 3-5 个 → 连同对话历史和用户问题一起交给 LLM → LLM 按法律人设组织成有案号、有法条的专业回答**。用户要的是"结论+依据"，不是"链接列表"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"把几千条法条全塞进 prompt 让模型背"就行 | prompt 有 token 上限，法条 + 文书动辄几千万份；RAG 的价值是**只取相关的几条**，不是全喂 |
| 以为"通用大模型就是法律顾问，直接问就行" | 通用模型没检索能力，答法律问题全靠训练记忆，容易一本正经引用不存在的法条——没有"案例+案号"背书，回答不可信 |

@@point ② 八大功能模块拆解
@@need 要解决什么
一个完整产品不可能一把梭，先把"这系统到底有哪些能力"列成清单，后面开发才有交付物清单。

@@idea 核心思路
讲义给出的功能模块，就是 LegalMind 的需求地图：

| 模块 | 职责 | 技术落点 |
|---|---|---|
| 🔐 用户注册登录 | 账号体系、JWT 令牌、会话归属 | User 模型 + JWT 认证 |
| 💬 AI 法律咨询 | 基于案例的问答、带引用来源 | QAAgent + RAG |
| 📋 法律文书生成 | 起诉状/答辩状/合同/律师函/上诉状 | DocumentAgent + 模板 |
| 🔎 案例检索 | 关键词/法条检索、按法院案件类型过滤 | RetrievalAgent + HybridRetriever |
| 🧭 意图识别 | 判断问题属于 问答/文书/检索 哪一类 | IntentAgent + LLM |
| 🗂️ 会话管理 | 多轮对话、会话列表、历史消息 | ChatSession/ChatMessage 表 |
| 🚀 流式输出 | 答案逐字显示，不等整段生成完 | SSE + StreamingResponse |
| 🧠 向量知识库 | 裁判文书切片向量化、相似度召回 | BGE 嵌入 + ChromaDB |

记住这张表：**前 3 个偏业务，中间 3 个是 AI 核心，后 2 个是工程支撑**——第 5、6 章解决后面两个，第 7~9 章解决中间三个。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"模块越多越高级，先全做上" | 这 8 个模块有依赖关系：没有认证（第 5 章）、没有案例数据（第 4/7 章），聊天根本没法闭环。按依赖顺序做，不是按表里的顺序做 |
| 以为"案例检索 = 聊天里的搜索" | 聊天里的 RAG 检索是**内部步骤**（给 LLM 找依据），案例检索页是**面向用户的独立界面**——同一套 RetrievalAgent，两个消费场景，别混为一谈 |

@@point ③ 技术选型：全套技术栈
@@need 要解决什么
项目用什么语言、什么框架、什么数据库，必须动手前一次性定清楚，避免中途换栈返工。这个项目是全栈 AI 应用，选型要同时照顾"AI 生态"和"Web 工程"两边。

@@idea 核心思路
讲义交付的技术栈清单（13 项），每项选它都有明确理由：

| # | 技术 | 用途 | 为什么选它 |
|---|---|---|---|
| 1 | Python ≥ 3.14 | 后端语言 | AI 生态（LangChain/LangGraph）只认 Python |
| 2 | FastAPI ≥ 0.136 | Web 框架 | 原生 async + Pydantic 校验 + 自带 SSE 支持 |
| 3 | Tortoise ORM ≥ 0.24 | 数据库操作 | 与 FastAPI async 生态契合、免写 SQL |
| 4 | PostgreSQL 16 | 业务数据库 | 存用户/案例/会话/文书，JSON 字段支持数组 |
| 5 | Redis 7 | 缓存/队列 | 与 LangGraph checkpointer 搭配（本项目实际用 PG 存状态） |
| 6 | LangChain ≥ 1.3 | LLM 调用封装 | Prompt/输出解析/多供应商统一接口 |
| 7 | LangGraph ≥ 1.2 | Agent 编排 | 有向状态图，多 Agent 协作天然合适 |
| 8 | sentence-transformers | 文本向量化 | 本地跑 BGE-small-zh，不依赖外部 API |
| 9 | ChromaDB | 向量数据库 | 轻量、支持过滤、与 LangChain 集成好 |
| 10 | rank-bm25 | 关键词召回 | 与向量检索互补，专治专有名词（案号、法条） |
| 11 | python-jose | JWT 签发校验 | 标准 JWT 实现，配合 OAuth2 Bearer |
| 12 | Vue3 + Vite + Tailwind | 前端 | 组合式 API + 秒级热更新 + 原子类快速出 UI |
| 13 | Pinia + vue-router | 状态与路由 | 官方生态，auth/chat 两 store 管理全局状态 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"版本号写得越高越安全，直接装最新版" | 表中版本是**下限**（≥），不是推荐最新。LangChain/LangGraph 迭代快、breaking change 多，教程代码往往是旧接口，直接装最新可能 API 对不上。先装下限版本验证跑通，再决定升不升 |
| 以为"Redis 是必须的，没有就不算正规项目" | 本项目的业务数据全在 Postgres，Redis 只是**预留**（见第 8 章 checkpointer 实际用 PG）。先想清楚"谁在生产/消费缓存"，再决定要不要引入，别为了技术选型而选型 |

@@point ④ 总体架构：四层分工
@@need 要解决什么
系统大了不分层就会"面条代码"——路由里写业务、业务里调模型、模型里拼字符串。先把职责边界划清楚，每个文件写什么都心里有数。

@@idea 核心思路
LegalMind 的分层（从请求到存储）：

```
浏览器 (Vue3)                    ── /api/* + SSE
   │
   ▼
FastAPI 路由层 (app/api/*)       ── 参数校验、JWT 依赖、SSE 封装
   │
   ▼
Agent 层 (app/agents/*)         ── 意图识别 / 问答 / 文书 / 检索 四枚 Agent
   │
   ▼
LangGraph 工作流 (workflow.py)  ── 状态图编排节点，条件边按意图路由
   │
   ├─► RAG 层 (app/rag/*)       ── 向量检索 + BM25 + 重排序
   │        │
   │        └─► ChromaDB 向量库 + cases 表原始数据
   │
   └─► LLM 层 (app/llm/*)       ── 多供应商客户端 (DeepSeek/OpenAI)、Prompt 模板
   │
   ▼
存储层                          ── PostgreSQL (Tortoise ORM) + Redis
```

要点：**下层不知道上层是谁**。rag 层只做"给 query 返回案例列表"；llm 层只做"给消息返回文本"；agent 层组装它们；workflow 层决定调用顺序。换一家 LLM 供应商只动 llm 层一个文件，这就是分层的价值。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"分层 = 按文件夹放文件" | 分层是**依赖方向的约束**：api 层可以 import agent 层，agent 层**不能** import api 层。光按目录归类但不限制 import，照样写成面条代码 |
| 以为"换供应商只改一个文件 = 改一下 .env 就完事" | .env 只解决模型名/Key/地址，若两家供应商的**参数或接口不完全兼容**（如 temperature 语义、流式格式），还要动 llm 层。分层保证的是"只动 llm 层"，不是"什么都不用动" |

@@point ⑤ 请求的数据流（一次完整咨询）
@@need 要解决什么
模块清单有了、分层有了，但"用户敲一句话回车后，系统内部到底发生什么"还没讲透。理解主链路是后面每章的导航地图。

@@idea 核心思路
一次"法律咨询"请求的完整旅程（对应 `POST /chat/stream`）：

```
1. 用户输入 "离婚财产怎么分割？"
2. 前端 fetch /api/chat/stream（带 JWT），准备消费 SSE
3. FastAPI 校验 JWT → 找到 User → 取/建 ChatSession
4. Tile: 调用 workflow.astream(query, thread_id=session_id)
5. intent_recognition 节点 → IntentAgent 识别意图 = "qa"
6. 条件边按意图路由 → case_retrieval 节点 → RetrievalAgent
7. HybridRetriever 双路召回 15 个候选 → Reranker 重排 → 取前 5
8. qa_generation 节点 → QAAgent 组装 system + 案例 + 历史 → LLM 流式生成
9. 每个 token 经 SSE 推给前端，前端逐字渲染
10. 流结束 → 从 LangGraph 读最终 state 拿 sources → 一并推送
11. ChatMessageRecord 落库（user 消息 + assistant 回复），会话列表可回看
```

"帮我写起诉状"走的分支不同：第 5 步识别出 `document` 意图后，直接跳到 `document_generation` 节点，不走检索（第 6~8 步换成文书模板+参数组装）。这就是**条件边按意图分流**的威力。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"所有请求都要先检索案例" | 只有 qa / search 意图需要检索，**文书生成默认不检索案例**（用模板+参数）。如果给文书也接上检索，反而是把模板逻辑搅浑。链路看意图，不是一条路走到黑 |
| 以为"SSE 是一次性返回整段文本" | SSE 是**逐 token 推流**，第 10 步的 sources 在流**结束后**单独推送。前端必须处理"先拼内容、再接引用"两段事件，漏了第二步就看不到引用来源 |

@@point ⑥ 数据模型一览：四张核心表
@@need 要解决什么
动手写代码前，先知道数据长什么样。业务侧的"用户、案例、会话、消息、文书"要落库，字段设计决定后面 API 好不好写。

@@idea 核心思路
LLM 检索增强生成(Retrieval-Augmented Generation)实现法律咨询时，需要检索"案例"这一核心数据，而支撑业务运转的还有用户与会话类数据。LegalMind 的 PostgreSQL 表设计：

| 表 | 关键字段 | 用途 |
|---|---|---|
| users | id(UUID)、username、email、hashed_password、nickname | 账号体系，JWT 兜底 |
| cases | id、title、case_number、court、judgment_date、case_type、summary、content、laws(JSON数组) | 裁判案例库，RAG 的"语料源" |
| chat_sessions | session_id(UUID)、user(外键)、created_at | 一次多轮对话的容器 |
| chat_messages | id、chat_session(外键)、role、content、created_at | 对话里的每条消息（user/assistant） |
| generated_documents | id、user(外键)、type、content、created_at | 生成过的法律文书存档 |

注意两个设计细节：**主键用 UUID 字符串**（不用自增 int，防撞库+前后端字符串一致）；**laws 用 Postgres 数组（JSON 字段）**存法条列表，避免为每条法条建一张关联表。实际代码里这四张表是 Tortoise 的 Model 类，第 4 章细讲。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"UUID 是加密的，别人猜不到就等于安全" | UUID 只防**枚举遍历**（/cases/1、/cases/2 爬库），不防鉴权漏洞。安全靠的是第 5 章的"每个请求必须验证 JWT + 数据归属校验"，主键只是第一道小门槛 |
| 以为"laws 字段应该拆成『案例-法条』关联表才规范" | 法条列表是**纯展示/过滤**用的字符串数组，没有独立业务逻辑，拆表是过度设计，JSON 数组一次读出一行代码搞定。什么时候该拆表？法条自身有状态流转时再拆 |

@@point ⑦ 环境与配置：.env 里有什么
@@need 要解决什么
数据库地址、LLM 密钥、向量库类型这些"环境相关"的东西不能写死在代码里——换了机器、换了供应商就得改代码，这是灾难。先看配置文件长什么样，你就知道第 2 章要搭什么环境。

@@idea 核心思路
项目根目录 `.env` 是"唯一配置源"，代码里统一由 `settings`（pydantic-settings）读取。它按职责分四组：

| 配置组 | 关键项（占位示例） | 用途 |
|---|---|---|
| 数据库 | `DATABASE_URL=postgresql://...`、`REDIS_URL=redis://...` | 第 2 章 docker-compose 起的服务地址 |
| LLM | `LLM_API_KEY=sk-xxx`、`LLM_BASE_URL=https://api.deepseek.com`、`LLM_MODEL=deepseek-chat` | 第 6 章多供应商客户端读取 |
| RAG | `EMBEDDING_MODEL=BAAI/bge-small-zh`、`EMBEDDING_DIM=512`、`RAG_TOP_K=5`、`RAG_SCORE_THRESHOLD=0.7`、`RERANK_ENABLED=True` | 第 7 章向量化与检索阈值 |
| 认证 | `SECRET_KEY=your-secret-<your-secret>`、`ACCESS_TOKEN_EXPIRE_MINUTES=120` | 第 5 章 JWT 签发 |

纪律：**真实密钥永远只进 .env（且 .env 进 .gitignore），代码里一律通过 `settings` 读取，仓库里只放 `.env.example` 占位版**。下面每章出现的 `settings.XXX` 都对应这里的某一项。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 .env 提交进 Git 仓库 | .env 里有 LLM Key 和数据库密码，Git 历史里删不掉，扫号机器人几小时内就会抓到。**先写进 .gitignore 再创建文件**；已经提交了就立即吊销 Key 重建 |
| 以为"改了 .env 立即生效" | pydantic-settings 在**进程启动时**读一次 .env，改完必须重启 uvicorn（`--reload` 会自动重启，但改 .env 本身不触发 reload 规则时需手动重启） |
| `.env` 里把值写成 `"sk-xxx"`（带引号） | 引号会被当成值的一部分读进去；值直接写，不加引号 |

@@point ⑧ 部署形态：docker-compose 起依赖
@@need 要解决什么
法律系统没跑起来之前，最烦的是"环境装不上"——Postgres 装半天、Redis 装半天、版本还不兼容。用容器一次性把依赖拉起，是本项目开发环境的第一课，也是第 2 章的先导。

@@idea 核心思路
项目自带 `docker-compose.yml`，一条命令起两个基础设施：

| 服务 | 镜像 | 关键配置 |
|---|---|---|
| postgres | postgres:16-alpine | POSTGRES_USER=legal_user / PASSWORD=<db_password> / DB=legal_db，端口 5432，volume 持久化 |
| redis | redis:7-alpine | 端口 6379，开启 AOF 持久化（appendonly yes） |

```bash
docker-compose up -d        # 后台拉起 Postgres + Redis
docker-compose down         # 停止
# 验证：docker compose ps 两个服务都是 healthy
```

注意：**开发阶段业务数据也全在 Postgres**（会话、消息、文书都落库），Redis 在这版主要是为 LangGraph 状态缓存预留 + 容器编排演示；真正持久化多轮对话状态的是 `langgraph-checkpoint-postgres`（第 8 章展开）。容器只放基础设施，业务代码仍然本地跑——这样改代码不用重启容器。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `docker-compose down -v` 后数据全没了，哭 | `-v` 会**删掉 volume（数据卷）**，`down` 不带 `-v` 才保留数据。重置数据库用 `down -v`，日常停服用 `down` |
| 以为"业务代码也要打进容器跑" | 开发期容器只放 Postgres/Redis，业务代码本地跑（改完 `--reload` 秒生效）。打容器是第 12 章生产部署才做的事——开发期容器化代码只会拖慢迭代 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **完整系统蓝图** | 痛点→8 模块→13 项技术→四层架构，后面的章节都是这张图的局部放大 |
| **请求主链路** | "入参→意图识别→检索→生成→SSE→落库"十一步，调试时知道卡在哪一环 |
| **配置纪律** | .env 是唯一配置源、密钥不进代码、容器只管基础设施——第 2 章立刻用上 |

@@quiz
1. 用一句话说清 LegalMind 的"AI 律师"和通用大模型的本质差别是什么？
2. 四层架构里，如果要把 DeepSeek 换成 OpenAI，需要动哪些文件？为什么其他层不用动？
3. 意图识别节点输出 `document` 后，工作流会跳过哪一步？为什么文书生成不需要检索案例？
4. cases 表的 `laws` 字段为什么用 JSON 数组而不是单独建表？
5. 为什么主键选 UUID 而不是自增 int？至少说两个理由。
6. 真实 LLM API Key 应该放在哪里？代码里通过什么对象读取？
7. docker-compose 在这套架构里负责什么？哪些东西不能放容器里跑（本项目里）？

@@links
讲义|LegalMind 法律咨询系统：项目介绍|#
官网|FastAPI 官方文档|https://fastapi.tiangolo.com/
官网|LangChain 官方文档|https://python.langchain.com/
官网|LangGraph 官方文档|https://langchain-ai.github.io/langgraph/