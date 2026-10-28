@@h1 第十一章　RAG 医学知识库
@@sub 阶段 10 · 安康智慧健康管理平台（糖尿病AI健康助手）　|　难度 ★★★★★

@@why 这一章在解决什么问题
大模型有通识但"不专精"——糖尿病的最新指南、食物 GI 表、用药规范，模型可能记错或乱编。本章搭建**RAG（检索增强生成）**：把 20 条医学知识提前存进向量库，回答问题时先检索最相关的几条，再"带着资料"让模型回答。本章解决三件事：**一是 ChromaDB 向量库的接入**（持久化、集合、余弦相似度），**二是中文嵌入模型与批量入库**（MiniLM 多语言模型 + 批次写入），**三是检索→过滤→格式化上下文的完整链路**（RAGEngine）。

关键认知：**RAG 的本质是"给模型开卷考试"**——模型不是凭记忆瞎答，而是先查资料、再按资料作答，从根上减少幻觉。

@@prep 开始之前
第 9 章的 LLM Key 备好就能开始；chromadb 依赖第 3 章已装，不用再配环境。

@@goal 学到这儿就够了
能建出可持久化的向量库、检索出相关医学条目并拼进提示词，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：健康仪表盘（前端消费）
**本章** ← 你在这里：RAG 医学知识库——给对话装上"资料库"
下一章：LangGraph 工作流——把 RAG 编排进多步对话
阶段终点：chat 接口回答问题时"有据可依"

@@point ① RAG 是什么：为什么 AI 助手需要它
@@need 要解决什么
直接问大模型"二甲双胍怎么吃"，它可能答个大概甚至出错——怎么办？

@@idea 核心思路
RAG 四步链路：
1. **离线**：把可靠知识（指南、食物表）切块 → 向量化 → 存入向量库；
2. **在线**：用户提问 → 把问题向量化 → 在库里找 top_k 最相似的知识；
3. **组装**：检索到的知识 + 患者上下文 + 用户问题，一起拼成提示词；
4. **生成**：模型基于"给定资料"作答。

```
用户提问 ──→ ①向量化 ──→ ②相似度检索(chroma)
                              │ top_k 条
用户提问 + 检索知识 + 患者档案 ──→ ③LLM 生成回答
```

效果对照：
| 方式 | 例子（问"低血糖怎么办"） |
|---|---|
| 无 RAG | 模型按记忆泛泛而谈 |
| 有 RAG | 检索到"处理：立即口服15g葡萄糖，15分钟后复测血糖"，回答有出处 |

**工程上 RAG = 向量检索 + 提示词组装**，两件事都要在本章落地。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 RAG 是"联网搜索" | RAG 检索的是**预置知识库**，不是实时网页；离线把知识塞进库 |
| 知识没切块直接塞 | 20 条按"单条=一小段"组织即可；长文需要切块，块太大检索不精准 |

@@point ② ChromaDB 接入：持久化客户端与集合
@@need 要解决什么
向量库选型与接入——怎么创建、持久化到哪、用什么相似度？

@@idea 核心思路
```python
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

class VectorStore:
    def __init__(self):
        chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR")           # ./data/chroma_db
        Path(chroma_persist_dir).mkdir(parents=True, exist_ok=True)     # 目录先建好
        self.client = chromadb.PersistentClient(path=chroma_persist_dir)  # 持久化客户端
        # 中文嵌入模型：多语言 MiniLM
        self.embeddings = HuggingFaceEmbeddings(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            encode_kwargs={"normalize_embeddings": True},
        )
        self.collection = self.client.get_or_create_collection(
            name=os.getenv("CHROMA_COLLECTION_NAME"),      # medical_knowledge
            metadata={"hnsw:space": "cosine"},             # 余弦相似度
        )
```

逐句解读：
- **PersistentClient**：ChromaDB 持久化到本地目录（`./data/chroma_db`），重启不丢数据；
- **get_or_create_collection**：集合不存在就创建——幂等，重复启动不报错；
- **hnsw:space=cosine**：检索相似度用余弦距离，语义相近距离小；
- **MiniLM 多语言模型**：paraphrase-multilingual-MiniLM-L12-v2 支持中文语义向量化，是本项目的嵌入模型。

嵌入模型选择的取舍：**多语言小模型**体积小、中文可用、本地推理快；相比 OpenAI embedding（API 计费）零成本。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 客户端报路径不存在 | 先 `Path(dir).mkdir(parents=True, exist_ok=True)` 再建 PersistentClient |
| 模型下载失败/首跑很慢 | MiniLM 首次要下载权重；网络不行可离线放置 HF 缓存（HF_TOKEN 配好） |
| 相似度方式理解反 | `hnsw:space: cosine` 是**越小越相似**（距离），不是越高越相似 |

@@point ③ 文档入库：MD5 ID 与批量写入
@@need 要解决什么
20 条知识怎么写入向量库？ID 怎么生成？一次全写会不会卡？

@@idea 核心思路
```python
def add_documents(self, documents, metadatas=None, ids=None):
    if ids is None:
        import hashlib
        ids = [hashlib.md5(document.encode("utf-8")).hexdigest() for document in documents]
    embeddings = self.embeddings.embed_documents(documents)
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        self.collection.add(
            documents=documents[i:i+batch_size],
            embeddings=embeddings[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size],
        )
```

三处设计：
1. **MD5 作 ID**：同文本同一哈希 → 重复导入去重（同内容不会再插一遍），且不依赖自增序号；
2. **嵌入批量生成**：一次 embed_documents 全部向量化（比逐条快得多）；
3. **分批 add**：每批 100 条写入——大数据量时防内存峰值、防超时。

注意：本项目 knowledge_base.py 外层用 `doc_0..doc_19` 固定 ID（便于定位更新）；add_documents 默认 MD5 是"防重复"的兜底策略。两条路径都合法的场景：**带业务序号的库用固定 ID，纯内容库用哈希 ID**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 重复启动知识被导入两遍 | init_knowledge_base 里 `count()>0` 就 return，天然幂等 |
| 编码错误 | `document.encode("utf-8")`（编码名要写正确）；中文内容编码必须 utf-8 |
| 一次灌上万条卡死 | 必须分批；batch_size=100 是工程经验值 |

@@point ④ 检索：相似度查询与结果"脱壳"
@@need 要解决什么
查出来的向量结果嵌套多层（documents/metadatas/distances 都带外层数组），怎么取到干净数据？

@@idea 核心思路
```python
def query(self, query_text, top_k=None, where=None):
    top_k = int(top_k or os.getenv("RAG_TOP_K", 5))   # .env 读出来是字符串，必须转 int
    query_embedding = self.embeddings.embed_query(query_text)
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    # ChromaDB 返回嵌套结构，逐层"脱壳"
    return {
        "documents": results["documents"][0] if results.get("documents") else [],
        "metadatas": results["metadatas"][0] if results.get("metadatas") else [],
        "distances": results["distances"][0] if results.get("distances") else [],
    }
```

必须理解的坑：
- **ChromaDB 返回结构**是 `{"documents": [["结果1","结果2",...]]}`——因为 API 支持"一次查多个问题"，多套了一层列表；
- **脱壳**：`results["documents"][0]` 取第一个查询的问题结果；
- **where 过滤**：可加元数据过滤 `{"category": "饮食管理"}`——按分类检索的关键，LangGraph 意图分流全靠它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了取 [0] | 拿到的是二维列表，拼接会出错 |
| n_results 是字符串 | RAG_TOP_K 从 .env 读是 str，ChromaDB 可能报类型错；转 int |
| where 写成 category 字符串 | 必须 `{"category": "饮食管理"}` 字典形式 |

@@point ⑤ 20 条医学知识：分类与来源设计
@@need 要解决什么
知识库内容从哪来？怎么组织才能支撑"按意图检索"？

@@idea 核心思路
DIABETES_KNOWLEDGE 结构 = **content + category + source** 三元组。20 条按 8 个分类：

| 分类 | 示例内容 | 来源 |
|---|---|---|
| 血糖管理 | 空腹目标4.4-7.0，餐后<10.0；<3.9为低血糖 | 中国2型糖尿病防治指南 |
| 低血糖 | 症状+处理：15g葡萄糖、15分钟复测 | 糖尿病低血糖诊治指南 |
| 高血糖 | >13.9警惕酮症酸中毒 | 中国2型糖尿病防治指南 |
| 血糖监测 | HbA1c 目标<7.0%，每3个月测 | ADA糖尿病诊疗标准 |
| 饮食管理 | GI<55优选；每日膳食纤维25-30g | 医学营养治疗指南 |
| 运动管理 | 每周≥150分钟中等强度；血糖>13.9/5.6不宜运动 | ADA/防治指南 |
| 用药管理 | 二甲双胍一线药；胰岛素注射轮换 | 防治指南/胰岛素指南 |
| 并发症 | 视网膜病变每年查眼底；糖尿病足日检 | 防治指南 |

设计价值：
- **category 是"意图"的落点**：用户问饮食 → 只检"饮食管理"分类，精准且省算力；
- **source 是"可信度背书"**：回答可标注"来源：中国2型糖尿病防治指南"，患者信任度拉满；
- **内容短句化**：每条 1-2 句，直接可作引用片段，无需切块。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 知识内容太长不分条 | 检索返回"一大坨"无重点；单条控制在 50-100 字 |
| 来源缺失 | source 字段是回答"出处"的依仗，落库时必填 |
| 分类名与意图映射不一致 | 血糖→血糖管理、饮食→饮食管理…必须先定字典再写库，避免对不上 |

@@point ⑥ init_knowledge_base：启动即入库
@@need 要解决什么
知识什么时候写进向量库？服务重启会不会重写一遍？

@@idea 核心思路
```python
def init_knowledge_base() -> None:
    if vector_store.count() > 0:
        return                                    # 已有数据直接跳过
    documents = [item["content"] for item in DIABETES_KNOWLEDGE]
    metadatas = [{"category": item["category"], "source": item["source"]}
                 for item in DIABETES_KNOWLEDGE]
    ids = [f"doc_{i}" for i in range(len(DIABETES_KNOWLEDGE))]
    vector_store.add_documents(documents=documents, metadatas=metadatas, ids=ids)
    print("知识库初始化完成，文档数量：", vector_store.count())
```

调用时机回顾（第五章）：main.py 的 lifespan 里 `init_knowledge_base()`——**服务一启动，知识就绪**。

幂等三保险：count>0 跳过 + 固定 doc_{i} ID + add_documents 内部按 ID 覆盖——重启多少次都不会重复灌库。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 想更新某条知识 | 用固定 ID doc_3 覆盖 add 或 delete 后重加；哈希 ID 做不到"按业务定位" |
| 日志没打印"初始化完成" | 说明 count>0 走了跳过分支；属正常幂等行为 |
| 启动太慢卡住 | MiniLM 首次下载权重在网络慢时会久；第二次起有缓存 |

@@point ⑦ 相似度转分数：search_knowledge
@@need 要解决什么
ChromaDB 给的是"距离"（越小越相似），业务上要"分数"（越大越相关）——怎么转换？还能按分类过滤吗？

@@idea 核心思路
```python
def search_knowledge(query, category=None, top_k=5) -> List[Dict]:
    where = {"category": category} if category else None
    results = vector_store.query(query_text=query, top_k=top_k, where=where)
    docs, metas, dists = results.get("documents") or [], results.get("metadatas") or [], results.get("distances") or []
    out = []
    for i in range(len(docs)):
        score = 0.0
        if i < len(dists) and dists[i] is not None:
            score = max(0.0, 1.0 - float(dists[i]))   # 距离0.1 → 分数0.9
        meta = metas[i] if i < len(metas) else {}
        out.append({"content": docs[i], "metadata": meta or {}, "score": score})
    return out
```

两处关键转换：
- **距离→分数**：`score = 1 - distance`（余弦距离在[0,2]区间，1-距离映射到约[-1,1]，再 max(0,·) 截断负值）——距离 0.1 是非常像，得 0.9 分；
- **where 过滤**：category 参数直接变 ChromaDB 过滤条件，让检索只在指定分类内进行。

输出统一为 `[{content, metadata, score}]` ——RAGEngine 的 min_score 过滤就基于这个 score 字段。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 分数算成负数 | max(0.0, 1-distance) 截断；距离>1 时避免负分入列 |
| category 为空时 where=None | 全库检索（health_query 场景）；有分类能提精度但会漏跨类知识 |
| dists 长度与 docs 不一致 | 边界用 `i < len(dists)` 防御性取数 |

@@point ⑧ RAGEngine：检索到上下文的最后一公里
@@need 要解决什么
检索出的多篇文档怎么变成"能喂给 LLM 的引用格式"？低分噪音怎么滤掉？

@@idea 核心思路
```python
class RAGEngine:
    def retrieve(self, query, category=None, top_k=5, min_score=0.3) -> str:
        raw_docs = search_knowledge(query=query, category=category, top_k=top_k)
        docs = [d for d in raw_docs if d["score"] >= min_score]   # 低分过滤
        return self._build_context(docs)

    def _build_context(self, docs) -> str:
        if not docs:
            return "暂无相关参考知识"
        parts = []
        for i, doc in enumerate(docs, start=1):
            meta = doc["metadata"] or {}
            category = meta.get("category", "未分类")
            source = meta.get("source", "未知来源")
            parts.append(f"[参考{i}]({category} | 来源：{source})\n{doc['content']}")
        return "\n\n".join(parts)
```

两个核心设计：
1. **min_score=0.3 过滤**：相似度低于 0.3 的结果视为噪音丢弃——宁缺毋滥，避免"答非所问还带引用"；
2. **上下文格式化**：输出带编号、带分类、带来源的引用文本：
```
[参考1](饮食管理 | 来源：中国2型糖尿病防治指南)
糖尿病患者每日碳水化合物应占总热量的45-60%...
```
**"给模型看的上下文"和"给检索的人看的列表"是两回事**——RAGEngine 负责把结构化结果变成 LLM 友好的文本块。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 过滤后为空仍硬要用 | 返回"暂无相关参考知识"，交给 LLM 明确说明"资料不足" |
| 分数阈值太高检索太少 | 0.3 是针对本项目知识量与模型调过的经验值，换库需重调 |
| 引用格式里来源缺失 | meta.get("source", "未知来源") 兜底，格式永远完整 |

@@summary
这一章你实际拿到的是**三样东西**：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **RAG 完整链路** | 离线灌库（向量化+批量入）→ 在线检索（相似度+分类过滤）→ 组装上下文（过滤+格式化） |
| **ChromaDB 工程细节** | 持久化客户端、cosine 距离、MD5/固定 ID 幂等、嵌套结果脱壳 |
| **可解释的检索结果** | content+category+source 三元组，回答带出处，幻觉从源头被压 |

@@quiz
1. RAG 的四步链路是什么？"开卷考试"比喻对应哪一步？
2. PersistentClient 与普通 Client 的区别？数据存在哪个目录（.env 里哪个键）？
3. 本项目为什么用固定 doc_{i} 作为 ID？MD5 作 ID 解决什么问题？
4. ChromaDB 查询结果为什么取 `[0]`？不脱壳会怎样？
5. 距离 0.1 与 0.9 对应的分数各是多少？负数怎么处理？
6. min_score=0.3 的作用？过滤后为空时 RAGEngine 返回什么？
7. category 字段在意图分流（下一步 LangGraph）中扮演什么角色？

@@links
参考|安康智慧健康管理平台：糖尿病AI健康助手|#
官网|ChromaDB 官方文档|https://docs.trychroma.com/
官网|HuggingFace MiniLM 多语言模型|https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2