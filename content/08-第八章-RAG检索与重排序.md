@@h1 第八章　RAG 检索与重排序
@@sub 阶段 11 · LegalMind 法律咨询系统　|　难度 ★★★

@@why 这一章在解决什么问题
第 7 章向量库建好了，但"检索"远不止"向量搜一下"这么简单。法律场景有两个硬需求：**案号和法条编号要能精确命中**（向量检索在这上面会漏），**命中结果要按相关度排好序**（向量分高的未必是最该引用的）。
LegalMind 的 RetrievalAgent 用 **"多路召回 + 重排序"** 的组合拳：向量检索（语义）+ BM25 关键词检索（字面）双路召回 15 条候选，再用词重叠打分重排，截取最相关的 5 条进 prompt。这条路就是当下 RAG 系统的标准骨架。学完本章，你掌握的不只是"查案例"，而是**一套可以复用到任何垂直领域的检索范式**。

@@prep 开始之前
第 7 章的向量库建好了就能开始，这章不用装新东西，加的是 BM25 和重排。

@@goal 学到这儿就够了
能做出双路召回加重排序、把 5 条最相关判例拼进 prompt，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章（第七章 向量库）：ChromaDB 里已有案例向量，similarity_search 可用了
**本章** 你在这里：把检索升级为完整 RAG——向量+BM25 双路召回、重排序、过滤、阈值筛选
下一章：Agent 系统与 LangGraph——RetrievalAgent 成为工作流里的"case_retrieval 节点"
再往后：第 10 章聊天/文书 API 用上 QAAgent 这套 RAG 链路
阶段终点：检索质量可调可验，QA 回答有据可依

@@point ① RAG 的完整链路回顾
@@need 要解决什么
7 章讲完，RAG 的各个零件都齐了，但"它们怎么串起来"需要一次收拢——否则容易只见树木不见森林。
@@idea 核心思路
RAG（Retrieval-Augmented Generation，检索增强生成）标准五步：
```text
① 建库：语料切片 → 嵌入 → 存向量库（第 7 章已完成）
② 召回：用户 query → 向量检索 + BM25 双路召回 → 合并去重（本章重点）
③ 重排：对候选按相关度打分排序，截取 Top-K（本章重点）
④ 增强：检索结果拼进 prompt（第 6 章 QA_PROMPT 的 {cases}）
⑤ 生成：LLM 依据案例 + 法条生成回答（第 6 章）
```
**为什么检索质量决定生成质量**：LLM 再聪明，喂进去的是垃圾案例，输出就是引用错误案例的"专业胡说"。RAG 系统的性能上限由检索端决定，这是行业内公认的"Garbage in, garbage out"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 RAG = 向量检索一步 | 完整链路是 拆块→向量化→双路召回→重排→拼 prompt→生成；漏掉重排或检索质量调试，答案相关性全靠运气 |

@@point ② HybridRetriever：向量 + BM25 双路召回
@@need 要解决什么
第 7 章讲过纯向量在案号/法条上的短板。HybridRetriever 把两路检索合并，用"召回广度"换"查全率"——先多捞，再精筛。
@@idea 核心思路
`app/rag/retriever.py` 的 HybridRetriever 核心：
```python
class HybridRetriever:
    def __init__(self):
        self.vector_store = get_vector_store()                        # Chroma
        self.bm25_index, self.bm25_cases = self._build_bm25_index()   # rank-bm25

    def _build_bm25_index(self):
        """从向量库重建 BM25 索引。注意：Chroma 的 get() 直接给字符串，不是 Document"""
        raw = self.vector_store.db.get()
        docs = [str(d) for d in raw["documents"]]                     # ← 这里已经是字符串
        metas = raw.get("metadatas") or [{} for _ in docs]
        cases = [{"content": d, **m} for d, m in zip(docs, metas)]    # 统一成 dict
        tokenized = [list(jieba.cut(d)) for d in docs]                # 中文必须分词
        return BM25Okapi(tokenized), cases

    def retrieve(self, query: str, top_k: int = 5):
        # ① 向量召回（返回 Document，先转成 dict）
        vector_hits = self.vector_store.similarity_search(query, top_k=top_k * 3)
        vector_cases = [{"content": d.page_content, **d.metadata} for d in vector_hits]

        # ② BM25 召回（本身就是 dict，两边结构对齐才能合并）
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25_index.get_scores(tokenized_query)
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k * 3]
        bm25_cases = [self.bm25_cases[i] for i in order if scores[i] > 0]

        # ③ 合并去重：都取 case_number，别一边 Document 一边 str
        merged = {}
        for c in vector_cases + bm25_cases:
            key = c.get("case_number") or ("__nocase_%d" % id(c))   # 空案号不能都并成一条
            merged.setdefault(key, c)
        return list(merged.values())
```
三个要点：
- **中文必须分词**：BM25 是词袋模型，中文要先 `jieba.cut` 切词。不切的话一整句只当一个 token，query 和文档几乎永远对不上，召回直接归零。
- **候选池放大**：每路捞 `top_k*3`（15 条），重排才有足够的选择空间。
- **归一去重**：合并后可能同一案例两边都命中，按 case_number 去重，避免重复进 prompt。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 双路结果直接拼接 | 向量和 BM25 得分量纲不同，直接 concat 会偏向某一路；先各自归一化/打分再合并（见 reranker） |
| BM25 路没做关键词归一 | 中文不切词时整句成一个 token，等于完全不匹配（不是"区分不出"）；检索前做基础归一（全半角、大写、去空白）并统一切词 |

@@point ③ Reranker：词重叠启发式重排
@@need 要解决什么
合并后的候选顺序是"先向量后 BM25"，不一定按相关度排。重排序器要用一个**更准的信号**重新打分——本项目用词重叠（query 与文档共同词数），简单高效、可解释。
@@idea 核心思路
`app/rag/reranker.py`：
```python
class Reranker:
    async def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        scored_docs = []
        query_terms = set(jieba.cut(query.lower()))   # 中文必须分词，否则整句当一个词、重叠打分退化成 0/1

        for doc in documents:
            content = doc.get("content", "")
            title = doc.get("title", "")
            # 打分：query 的词在文档标题/正文中出现越多分越高
            score = sum(1 for term in query_terms if term in content or term in title)
            scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)   # 降序
        return [doc for _, doc in scored_docs[:top_k]]       # 截取 Top-K
```
定位与局限**要说透**：
- 这是**轻量启发式**重排（词频/词重叠），不是模型重排（如 cross-encoder/BGE-Reranker）——好处是零依赖秒算，坏处是信号粗糙。
- 项目用 `RERANK_ENABLED=True` 开关控制；生产环境想提精度，把这里的打分函数换成 **BGE-reranker 或 cohere rerank**，接口完全兼容。
- 重排的价值：**向量分高的"语义像"，重排后的"字面更像"**——法律场景用户问法往往带关键词，词重叠信号很有效。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 重排分数和相似度分数混为一谈 | 相似度是"像不像"，重排是"符不符合问题意图"；调试时两列分开看，别用一个阈值同时卡 |

@@point ④ RetrievalAgent：把三件事包装成一个接口
@@need 要解决什么
召回、重排、过滤逻辑不能散在调用方。RetrievalAgent 作为"检索门面"，对外只有 `retrieve(query, top_k, filters)` 一个方法，Agent 层和 API 层调它就好。
@@idea 核心思路
`app/agents/retrieval_agent.py`：
```python
class RetrievalAgent:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.reranker = Reranker() if settings.RERANK_ENABLED else None

    async def retrieve(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        # 1. 多路召回（候选池的放大在 retriever 内部做一次，别再叠加）
        candidates = self.retriever.retrieve(query=query, top_k=top_k, filters=filters)

        # 2. 重排序（可选；不开就用截断）
        candidates = self.reranker.rerank(query, candidates, top_k) if self.reranker else candidates[:top_k]
        return candidates

    async def search_by_keywords(self, keywords: list[str], top_k: int = 10) -> list[dict]:
        """关键词检索（案例搜索页用）"""
        return await self.retrieve(" ".join(keywords), top_k)

    async def search_by_article(self, article: str, top_k: int = 10) -> list[dict]:
        """按法条检索：laws 在 Chroma 里是拼接串，只能拉回内存做子串筛"""
        hits = self.retriever.retrieve(query=article, top_k=top_k * 3)
        return [h for h in hits if article in (h.get("laws") or "")][:top_k]
```
**设计亮点**：`filters` 参数一路透传——向量侧交给 Chroma 的 metadata 过滤，BM25 侧可在合并时过滤。案例搜索页的"按法院/按案件类型"筛选（第 9 章）就靠它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 三个组件在接口里各跑各的，失败没有兜底 | 单路失败（如向量库挂了）整个检索崩；把"降级到另一路"写进流程，重排结果为空就原样返回召回结果 |

@@point ⑤ 检索结果怎么进 prompt
@@need 要解决什么
检索出 5 条案例，不能直接把 dict 丢给 LLM——要格式化成"案例清单"文本，让模型一眼看懂每个案例的标题、案号、法院、要旨、法条。
@@idea 核心思路
QAAgent（第 9 章）+ 第 6 章 `QA_SYSTEM_PROMPT` 的组装（`_format_cases`）：
```python
def _format_cases(self, cases: list[dict]) -> str:
    if not cases:
        return "暂无相关案例参考。"
    formatted = []
    for i, case in enumerate(cases, 1):
        formatted.append(
            f"【案例{i}】\n"
            f"标题：{case.get('title', '未知')}\n"
            f"案号：{case.get('case_number', '未知')}\n"
            f"法院：{case.get('court', '未知')}\n"
            f"裁判要旨：{case.get('summary', '未知')}\n"
            f"相关法条：{case.get('laws', '未知')}\n"
        )
    return "\n".join(formatted)
```
- **案号/法院/要旨/法条四项全给**——这是"引用依据"原则的原料（第 6 章回答原则 3）。
- 无案例时给"暂无相关案例参考"——LLM 会老老实实说没查到，而不是编一个。
- 案例是**当轮 system** 注入，**绝不进长期 messages**（第 8 章 Agent 部分详述，防上下文膨胀）。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 检索结果全是 0 分的垃圾 | 向量库没建好或过滤条件太严；先查 add 成功没、阈值是否过狠 |
| 案例重复出现 | 合并去重没生效；检查 case_number 是否一致（空值会导致去重失败） |
| BM25 结果为空 | 中文没分词（jieba 没装/没调用），BM25 对整句中文不敏感 |
| prompt 里案例太多/token 超限 | TOP_K 调小；案例文本截断（summary 只取前 500 字） |

@@point ⑥ 检索质量调试：参数从哪调
@@need 要解决什么
检索不准时，90% 的修复调的不是模型，而是几个**配置参数**。把"调什么、往哪调"列成清单，别瞎改代码。
@@idea 核心思路
`.env` 里的检索参数就是调试面板：
| 参数 | 调大 | 调小 | 场景 |
|---|---|---|---|
| `RAG_TOP_K` | 更多案例、更全 | 更快、更聚焦 | 综合问答 5，文书参考 3 |
| `RAG_SCORE_THRESHOLD` | 更严、更精准 | 更松、更多召回 | 语料质量高调高，语料少调低 |
| `RERANK_ENABLED` | 开重排 | 关重排保速度 | 精度优先开，耗时敏感关 |
| 候选池倍数 `top_k*3` | 重排选择更多 | 更快 | 语料库大时可以调 5 倍 |
调试流程：**先跑检索冒烟测试 → 看分数分布 → 调阈值 → 看漏召回 → 调 TOP_K**。一次只调一个参数，记录效果。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 召回条数一改（top_k）就发现答案质量跳变 | 别只顾 top_k，先看召回内容本身对不对；问题往往在 chunk 切分和阈值，不在最后的条数旋钮 |

@@point ⑦ 过滤条件的透传设计
@@need 要解决什么
案例搜索页要"只看北京的案例""只看劳动争议"，聊天里可能也要"按法条限定"。过滤逻辑不能写死在检索函数里，做成**可透传的参数**。
@@idea 核心思路
过滤参数从 API → Agent → Retriever → Chroma 一路透传：
```text
# API 层（case 搜索接口）
filters = {}
if court:     filters["court"] = court
if case_type: filters["case_type"] = case_type
if article:   filters["laws"] = {"$in": [article]}

results = await agent.retrieve(query=q, top_k=limit, filters=filters or None)
```
Chroma 的 metadata **只支持标量**（字符串/数字/布尔），不能存数组；`laws` 入库时拼成一个字符串（如 `"民法典第1087条;婚姻法第39条"`）。这样只能做**精确等于**，按单个法条筛就得把候选拉回内存过滤：
```text
filter={"court": "北京市第一中级人民法院"}          # 等值过滤
filter={"laws": {"$eq": "民法典第1087条"}}   # 只能整串相等；想按单个法条筛，拉回内存再过滤
```
- **API 层拿 query 参数 → 组 filters → 透传**，检索内部逻辑完全不变。
- 向量检索支持 metadata 过滤（查得快），BM25 侧在合并时一并对齐过滤即可。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 过滤字段名前端传 camelCase、后端收 snake_case，静默过滤空 | 跨端字段约定必须一致（文档里约死并且联调时对照），过滤条件透传前做一层字段映射 |

@@point ⑧ 检索链路验证：端到端冒烟
@@need 要解决什么
全链路写完后，用一个能覆盖"向量 + BM25 + 重排 + 过滤"四个特性的测试查询，确认检索质量没退化。
@@idea 核心思路
```python
# scripts/retrieval_agent_smoke.py
import asyncio
from app.agents.retrieval_agent import RetrievalAgent

async def main():
    agent = RetrievalAgent()

    # 1. 纯语义查询（考验向量路）
    r1 = await agent.retrieve("夫妻闹离婚 房子归谁")
    print("语义查询:", [c["title"] for c in r1])

    # 2. 精确案号查询（考验 BM25 路）
    r2 = await agent.retrieve("（2024）京01民终1024号")
    print("案号查询:", [c["title"] for c in r2])

    # 3. 带过滤查询（考验 filters 透传）
    r3 = await agent.retrieve("劳动争议", filters={"case_type": "劳动争议"})
    print("过滤查询:", [c["title"] for c in r3])

asyncio.run(main())
```
- 语义查询命中离婚案 → 向量路 OK。
- 案号查询精确命中 → BM25 路 OK。
- 过滤查询只返回劳动争议 → filters 透传 OK。
三条全过，检索端就绪，可以放心交给第 9 章的 Agent 使用了。

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **双路召回范式** | 向量管语义 + BM25 管精确，案号法条不再漏检 |
| **重排精筛流水线** | 候选池放大 → 词重叠打分 → Top-K，顺序就是质量 |
| **可调可验的检索端** | 四个配置参数 + 三条冒烟查询，检索质量可视化 |

@@quiz
1. 完整说一遍 RAG 五步以及本章补齐了哪两步？
2. HybridRetriever 双路合并为什么按 case_number 去重？不去重会怎样？
3. BM25 对中文为什么必须先分词？举一个"不分词就废"的例子。
4. 本项目 Reranker 的打分信号是什么？它和模型重排有什么区别与取舍？
5. RetrievalAgent 的 filters 参数一路透传给谁？案例搜索页的法院筛选怎么实现？
6. 检索案例进 prompt 时为什么必须带案号和法院？"暂无相关案例参考"这句提示的价值在哪？
7. 调试检索"召回太多垃圾"应该调大还是调小 RAG_SCORE_THRESHOLD？为什么？

@@links
参考|LegalMind 法律咨询系统：RAG 检索与重排序|#
官网|rank-bm25 文档|https://github.com/dorianbrown/rank_bm25
官网|LangChain RAG 教程|https://python.langchain.com/docs/tutorials/rag/
官网|jieba 分词|https://github.com/fxsjy/jieba
