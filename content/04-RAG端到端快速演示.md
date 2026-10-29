@@h1 第四章　RAG 端到端快速演示
@@sub 阶段 6 · 企业级RAG系统架构与实现　|　实操　|　难度 ★★★

@@why 这一章在解决什么问题
前三章你分别认识了向量库、ES、RAG 理论——但**理论到能跑的代码之间还隔着一条河**：文档怎么切块、向量用哪个模型、检索完怎么拼 Prompt、大模型 API 怎么接、最后怎么给用户一个网页界面？每步都有几十种做法，没人给你串一遍，自己拼三天也拼不利索。

这一章把前面所有知识焊成一个**能真正跑起来的端到端 RAG Demo**：不吃外卖文档，直接用一份社保政策 FAQ 当语料，从「装环境」一路走到「网页问答」，七个 Python 文件七个环节，每一步都讲清楚"为什么这么写"。跑完它，你就拥有一个最小可用的业务问答系统骨架。

@@prep 开始之前
要装 uv 和 Python，备好一家大模型的 API Key；BGE 模型首次运行要下载，留点网速和磁盘。

@@goal 学到这儿就够了
能说清七个文件各自管哪一段、为什么入库和问答要分开，能自己把整条链路跑通并换掉语料，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章：RAG 基础理论——为什么是检索增强生成、怎么设计链路
**本章** ← 你在这里：端到端演示——把链路变成能跑的七段代码
前面的铺垫：向量数据库选型（Chroma 就是这里的存储）、Embedding（BGE 就是这里的向量器）
下一阶段：你可以基于这个骨架换成自己的文档、自己的业务
阶段终点：企业内部知识问答系统的第一版原型在你手里

@@note info 这一章你要达到什么程度
12 个知识点，对应 7 个 Python 文件组成的完整链路。**看代码务必自己动手跑一遍**（包小、数据小、全程几分钟跑通），跑通了再谈"改成我的场景"。

@@point ① 项目总览：一个 RAG 系统由哪几块拼成
@@need 要解决什么
第一次看到一个 RAG 项目，最容易懵的是"怎么这么多文件、每个是干嘛的、谁先谁后"。动手前必须有全局地图，否则会陷在单文件细节里出不来。

@@idea 核心思路
这个 Demo 由 7 个 Python 文件组成，按执行顺序正好是 RAG 的完整链路：

```text
离线入库（跑一次）                    在线问答（跑服务）
01_数据解析.py ──→ 02_文本分块.py ──→ 03_向量化入库.py ──┐
   读 FAQ 文档       切成小段          调 BGE 模型进 Chroma │
                                                         ├──→ 06_pipeline集成.py
04_调用大模型.py ──→ 05_封装API接口.py ───────────────────┘        │
   LLM 怎么请求      LLM 封装成函数                            │
                                                         07_Web界面.py
                                                     Streamlit 网页问答
```

用一句话记住分工：**01~03 是"把资料变成检索库"，04~05 是"让模型能回答问题"，06 把两者串起来，07 给用户一个网页**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为"每次都要从头跑一遍 7 个文件"** | 01~03 是**离线入库，跑一次就够**；04~07 是**在线服务**。每次提问都重灌库，纯属白等 |
| 以为这些文件没什么依赖关系 | 顺序是硬约束：**没入库就检索不到，没封装就串不起来**。跳步跑必报错 |
| 以为"文件多 = 项目复杂" | 这是**分层**，每个文件职责单一。真要改什么，只动对应那一个——这正是它的价值 |

@@point ② 环境准备：uv 一脚蹬
@@need 要解决什么
Python 项目最烦人的是环境：装错版本、依赖打架、换台机器跑不起来。这一章的 Demo 用 **uv**（新一代 Python 包管理器）解决这事——一条命令装依赖，一条命令跑程序。

@@idea 核心思路
```bash
# 安装 uv（Windows）
pip install uv
# 或者官网脚本：powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 在项目目录，根据 pyproject.toml 一键装好所有依赖
uv sync
# 之后跑任何脚本都带 uv run，自动使用项目环境
uv run python 01_数据解析.py
```

为什么是 uv 而不是裸 pip：
- `pyproject.toml` 声明依赖（相当于含版本锁的 requirements）
- `uv sync` 全自动建虚拟环境 + 装依赖，不需要手搓 venv
- 团队里换台机器，`uv sync` 一条命令恢复同样环境

依赖清单就五样：`sentence-transformers`（向量）、`chromadb`（向量库）、`openai`（大模型 SDK）、`streamlit`（网页）、`pdfplumber`（PDF 解析）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为 `uv run` 可以省掉，直接 `python xx.py`** | 那用的是**系统 Python**，项目依赖根本找不到（或者版本不对）。**必须 `uv run`** |
| 以为 `uv sync` 每次跑都行、不跑也行 | 只在依赖变化后需要重跑；但**换机器、拉了别人代码之后必跑**。忘了就会报"找不到模块" |
| 忘了把 `uv.lock` 提交进版本库 | 锁文件不进库，团队每个人装出来的版本就不一样——**"我这能跑"的经典来源** |
| 全局 `pip install` 装依赖 | 会和系统里其他项目打架。uv 的价值就是**每个项目一个隔离环境** |

@@point ③ 数据解析：PDF/TXT 怎么变成干净的文本
@@need 要解决什么
知识库的第一口饭是"原始文档"。但 PDF 里的文字是排版好的，直接读出来会带上换行、分页符、表格碎片，**整段语义被切得稀碎**——必须先解析、清洗，再交给后面的环节。

@@idea 核心思路
用 `pdfplumber` 处理 PDF（也兼容 .txt 直接读）：
```python
import pdfplumber

def extract_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text
```

拿到的是"带排版噪声的原始文本"，后续还要清洗：
| 常见噪声 | 处理方式 |
|---|---|
| 页眉页脚、页码 | 正则删除（"第 X 页"、网站名） |
| 多余换行 | 合并进正常段落（PDF 换行 ≠ 语义换行） |
| 空白/乱码 | strip + 过滤空段 |

演示语料是一份《社会保险政策 FAQ》（data/faq.pdf + faq.txt），解析后得到几十条"问题-答案"形态的问答条目——**问答对是 RAG 最理想的小语料**（检索到哪条，答案就是哪条）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **以为 `extract_text()` 出来的就是干净文本** | 它带出的是**排版文本**：页眉页脚、页码、分页换行、表格碎片。**不清洗就分块，等于把噪声一起向量化**，检索结果会被污染 |
| 以为 PDF 里的换行就是段落换行 | PDF 的换行是**排版换行**——一行放不下就换。直接按行处理会把一句话切碎 |
| 扫描版 PDF 抽出空白 | 那类 PDF **没有文字层**（本质是图片），`extract_text()` 返回空。要上 OCR |
| 以为 PDF 里的表格能自动读好 | `pdfplumber` 能抽表格，但要**单独处理**（`extract_tables()`），混在正文里会变成一堆错位文字 |

@@point ④ 文本分块：为什么不能把整篇扔进去
@@need 要解决什么
直接拿整份 FAQ（几十页）去向量化入库会怎样？检索时一条记录几十万字，跟问题"像不像"根本算不准；就算捞回来，也超了模型上下文窗口。**向量化和检索的最小单位必须是"小块"**——这就是分块（chunking）。

@@idea 核心思路
分块原则：**每块语义完整 + 块与块之间留重叠**。
```python
def split_text(text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
    """按字符切分，相邻块重叠 overlap 个字符"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap   # 往前补 overlap，防止语义腰斩
    return chunks
```
两个关键参数：
- **chunk_size（块大小）**：200~500 字符最常见。太小语义碎片化，太大检索精度下降
- **overlap（重叠）**：切分点恰好落在"一句话中间"时，前后两块的语义都被打断，重叠能挽救

还有更聪明的分块（按段落/按 Markdown 标题结构切，本 Demo 用字符切打底）——**理解为什么切比会用库更值钱**：一切检索效果的瓶颈往往就在这块。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **chunk_size 一味调大或调小** | 太大 → 一块里混了好几个主题，检索不精准、还挤爆上下文；太小 → 语义被切碎，捞出来是半句话。**200~500 字是起点，要按语料实测调** |
| **忘了 `overlap`** | 切点正好落在一句话中间时，前后两块的语义**都被打断**。overlap 就是专门救这个的 |
| 所有文档都用固定字数硬切 | 对 FAQ、制度、Markdown 这类**有结构**的文档，按段落/标题切更好。固定字数会把"一问一答"从中间劈开 |
| 检索效果差就先去调 Prompt | **分块是检索效果的最大变量**。效果不好时，第一个该回来看的就是这里——不是 Prompt |

@@point ⑤ 向量化：BGE 小模型把文本变成向量
@@need 要解决什么
块切好了，现在要把每块文字变成向量存进向量库。选哪个 Embedding 模型？开源、中文好、轻量、免费跑——**BGE（BAAI/bge-small-zh）** 就是这个 Demo 的选择：国产开源、512 维、约 100MB，中文语义效果好，个人电脑 CPU 就能跑。

@@idea 核心思路
```python
from sentence_transformers import SentenceTransformer

# 首次运行会自动下载模型（约 100MB 级），之后本地缓存
model = SentenceTransformer("BAAI/bge-small-zh")

def embed_texts(texts: list[str]) -> list[list[float]]:
    # normalize_embeddings=True 等价归一化：与向量库的点积=余弦相似度
    return model.encode(texts, normalize_embeddings=True).tolist()
```
三个要点：
1. **同库同模型**：入库和查询必须用同一个模型，换模型=全库重灌
2. **归一化**：`normalize_embeddings=True` 让向量长度统一为 1，之后向量库里的"点积距离"直接等价于"余弦相似度"，写法最简单
3. **批量编码**：库里有几千块，一次 `encode(全部块)` 而非循环逐条——GPU/CPU 都能提速

**而后每个 chunk 带着：向量 + 原文 + 元数据(id/来源) 一起入库**——向量用于检索，原文用于喂给模型，元数据用于溯源展示。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **忘了 `normalize_embeddings=True`** | 不归一化时，点积会被**向量模长**放大——而不同文本的模长本来就没法比（跟句子长短也没有必然关系），于是分数排序失真，语义更近的反而排不上来。归一化后点积就等于余弦相似度。。用余弦就该显式归一化 |
| 循环逐条 `encode` 几千块 | 慢几十倍。**批量 encode** 是这几行代码里最值钱的优化 |
| 第一次运行以为卡死了 | 首次要**下载模型**（约 100MB），慢是正常的；之后走本地缓存 |
| 以为"换个更强的 Embedding 模型"能直接替换 | **必须全库重灌**：新旧模型的向量不在同一个空间，混着比毫无意义 |

@@point ⑥ 向量入库：Chroma 持久化本地库
@@need 要解决什么
向量有了，得有个"库"装起来——第一章选型里说过，教学/原型场景 Chroma 最省心：**pip 装完、本地目录持久化、API 三行能跑**，不用起服务。这个 Demo 就用它。

@@idea 核心思路
```python
import chromadb

client = chromadb.PersistentClient(path="chroma_db")   # 数据持久化到本地目录
collection = client.get_or_create_collection("faq_kb") # 集合=一张"表"

# 入库：ids / embeddings / documents(原文) / metadatas(溯源)
collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    embeddings=embeddings,
    documents=chunks,                                  # 原文一定存！检索后要拿它给模型
    metadatas=[{"source": "faq.pdf", "chunk": i} for i in range(len(chunks))],
)
```
为什么一定要存 documents 原文：**向量库返回的只是"id+分数"，给大模型看的、给用户引用的都是原文**。只存向量不存原文 = 检了个寂寞。

warm-up：Chroma 也在第一次查询时自动加载；生产要主动 `collection.count()` 确认入库条数（演示跑完应等于 chunk 总数，这个数对不上就是上面哪步漏了）。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **只存向量、不存 `documents` 原文** | 检索出来只有 id 和分数，**模型没东西可看、用户也没法溯源**。原文必须一起存 |
| **忘了核对入库条数** | 跑完不查 `collection.count()`，中途漏了都不知道，后面检索结果莫名其妙。**这个数必须和 chunk 数对上** |
| 重复跑入库脚本 | Chroma 的 `add` 遇到已存在的 id **不会覆盖**（跳过或告警）。要更新得用 `upsert`，或入库前先 `delete_collection` 重建 |
| 以为 Chroma 能扛生产 | 它的定位是原型和教学。真上生产要评估 Qdrant / Milvus |

@@point ⑦ 检索：从 Top-K 到"带回来三段"
@@need 要解决什么
库里有了几十条 FAQ 块。现在用户问"养老金领取条件是什么"——怎么捞？答案是**把问题也向量化，去 Chroma 里找最像的 K 条**。

@@idea 核心思路
```python
def retrieve(query: str, k: int = 3) -> list[dict]:
    # 问题向量化（同模型！）
    query_vec = model.encode([query], normalize_embeddings=True).tolist()
    # 向量库检索 Top-K
    res = collection.query(query_embeddings=query_vec, n_results=k)
    # 返回原文 + 距离 + 元数据
    return [
        {"content": doc, "distance": dist, "meta": meta}
        for doc, dist, meta in zip(res["documents"][0], res["distances"][0], res["metadatas"][0])
    ]
```
三个设计决策：
- **k=3**：取多少条喂给模型？太少答不全，太多稀释上下文还费 token。Demo 用 3，生产按资料复杂度调
- **启发式过滤**：距离超过阈值的直接丢弃（相关性不强硬塞进去会带偏模型）
- **返回 distance**：前端可以展示"置信度"，也是调参抓手（阈值调大调小）

**效果自检**：问"养老金怎么领"，看返回的三条是不是真的相关——如果召回的是"社保卡怎么补办"，先回去调 chunk_size / k / 阈值，别急着怪模型。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **`k` 拍脑袋定死** | k 太小 → 该有的资料没进来，答不全；太大 → 稀释上下文、还多花钱，模型更容易被无关内容带偏。**要按资料复杂度实测调** |
| 不做相关性阈值过滤 | 距离很远的段落也硬塞进 Prompt，**模型会照着不相关的资料编**。相关性不到的应该直接丢 |
| **答得不好就先去换大模型** | 先看"召回的这三条到底相不相关"。**不相关就是分块/模型/k 的问题，换 LLM 一点用没有** |
| 问题忘了用同一个模型向量化 | 入库一个模型、查询另一个模型，向量空间不一致，检索结果近乎随机 |

@@point ⑧ 构建 Prompt：把小抄按格式摆好
@@need 要解决什么
检索到三段原文还不够——大模型只认文字。要把"指令 + 原文 + 问题"拼成一个结构清晰的文本（这一步叫增强 Augment），拼法直接影响答案质量：**格式越清晰，模型越少跑偏**。

@@idea 核心思路
```python
def build_prompt(query: str, contexts: list[dict]) -> str:
    # 原文用分隔线隔开，编号列出
    ctx = "\n\n---\n\n".join(
        f"【片段{i+1}】\n{c['content']}" for i, c in enumerate(contexts)
    )
    prompt = f"""你是一个严谨的问答助手。请严格依据下面的资料回答问题。

【资料】
{ctx}

【问题】
{query}

【要求】
1. 只依据资料回答，不要使用资料外的知识
2. 资料没有答案时，明确回答"根据现有资料，无法回答该问题"
3. 回答简洁、口语化，适合直接念给用户听"""
    return prompt
```
三个防翻车设计：
- **"只依据资料"**：压制幻觉的关键指令
- **"没有就明说不知道"**：第二道保险
- **格式固定**：模型对"结构清晰 + 编号 + 明确指令"的遵从度远高于随意拼接

调 Prompt 的效果立竿见影，但**永远记住第三章的铁律：检索质量决定上限，Prompt 只是别拖后腿**。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **忘了写"资料里没有就明说不知道"** | 少了这句，模型会**拿资料以外的知识硬答**——幻觉又回来了。这是 RAG Prompt 里最不能省的一条 |
| 把几段资料不加分隔地拼在一起 | 模型分不清哪段是哪段，容易串在一起答。**要编号 + 加分隔线** |
| 以为 Prompt 调好了就能救检索 | 检索捞回来的东西不对，Prompt 写得再花也没用。**顺序永远是先修检索，再调 Prompt** |
| 资料一股脑全塞进去 | 会**超上下文被截断**，而且你不知道它截了哪一段（往往是最关键的尾部）。要控制条数和总长度 |

@@point ⑨ 调用大模型：OpenAI 兼容接口一鱼多吃
@@need 要解决什么
Prompt 拼好了，最后一步把它发给大模型然后拿到答案。你可能会想：每个厂商 API 都不一样，代码怎么写才通用？现在的行业答案：**大家都兼容 OpenAI 的接口格式**，一套 SDK 换 base_url 就能切换多家模型。

@@idea 核心思路
```python
import os
from openai import OpenAI

# ⚠️ 密钥绝不写死在代码里：从环境变量读（安全铁律）
# Windows: set DASHSCOPE_API_KEY=你的key / Linux: export
client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],      # 你自己的 Key（去模型平台控制台申请）
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 通义千问兼容端点
)

def call_llm(prompt: str, temperature: float = 0.3) -> str:
    resp = client.chat.completions.create(
        model="qwen-plus",          # 换成 glm-4-flash / deepseek-chat 等只需改这里
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,    # 问答场景压低随机性，宁稳勿飘
    )
    return resp.choices[0].message.content
```
为什么 `temperature=0.3`：问答要确定性（同一问题两次回答尽量一致），温度越高越"敢编"。RAG 场景的惯例是 **0.2~0.5**。

切换模型清单：
| 平台 | base_url | 模型示例 |
|---|---|---|
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-plus / qwen-turbo |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 401 鉴权失败 | 环境变量没设 / Key 复制多了空格；用 `print(os.environ.get("DASHSCOPE_API_KEY"))` 自查 |
| 报"model not found" | 模型名与平台不匹配（如把 qwen 的名字传给 GLM）；对照上表 |
| base_url 写错 | 兼容端点必须带 `/compatible-mode/v1` 后缀，漏了必挂 |

@@point ⑩ 封装 API 层：把检索和生成解耦
@@need 要解决什么
Demo 里直接"检索+生成"写在一起也能跑，但一改需求就动全身：换个检索库要改生成代码、加个日志要动主流程。**工程上要分层**——把大模型调用封装成独立函数（05_封装API接口.py 干的事），业务代码只关心"给它问题，它回答案"。

@@idea 核心思路
```python
# api_client.py（05 文件的骨架）
import os

from openai import OpenAI

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LLMClient:
    """统一封装大模型调用，对内对外只暴露 generate()"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url=BASE_URL)
        self.model = "qwen-plus"      # 换模型只改这一处

    def generate(self, system: str, user: str, **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            **kwargs,
        )
        return resp.choices[0].message.content
```
封装后的好处：
- **换模型/换平台只改一个文件**（base_url + model 名）
- **全局加日志、加超时、加重试**只动这里
- 上层（pipeline、网页）调 `llm.generate(...)`，完全不感知底层换了谁

这也解释了为什么 Demo 的文件是"检索一个文件、生成一个文件、集成一个文件"——**每一层的替换成本极低，这是工程思维不是洁癖**。

@@point ⑪ 端到端 Pipeline：把整条链路串成一句话
@@need 要解决什么
各零件都齐了，最后要有一个"总装"函数：输入问题 → 输出答案。它就是 RAG 的**唯一对外入口**，也是你将来替换任何一环的接缝处（详情见 06_pipeline集成.py）。

@@idea 核心思路
```python
class RAGPipeline:
    """端到端编排：检索 → 增强 → 生成"""
    def __init__(self, model, collection, llm: LLMClient):
        self.model = model          # Embedding 模型
        self.collection = collection  # 向量库
        self.llm = llm              # 大模型客户端

    def _retrieve(self, query: str, k: int = 3):
        """检索这一步单独抽出来：换向量库只改这里"""
        return retrieve(query, k=k)      # retrieve 是上一节写的检索函数

    def answer(self, query: str) -> dict:
        # ① 检索
        contexts = self._retrieve(query, k=3)
        if not contexts:            # 检索为空直接拦住，别浪费一次模型调用
            return {"answer": "资料库中没有相关内容", "sources": []}
        # ② 增强
        prompt = build_prompt(query, contexts)
        # ③ 生成
        answer = self.llm.generate(system="你是严谨的问答助手", user=prompt)
        # ④ 带溯源返回
        return {
            "answer": answer,
            "sources": [c["meta"] for c in contexts],  # 来源给用户，可点开核对
        }
```
这个类的价值：**未来升级全是"换零件"**——
- 检索要加 Rerank？只改 `_retrieve` 内部
- 要混合检索（向量+ES）？扩展 `_retrieve`
- 要换 LLM？构造时换 `llm`
- 要加过滤/日志？在 `answer` 里插一两行

同理，`answer()` 返回 `answer + sources` 的结构，让上层（网页）**永远不直接碰内部细节**。

@@point ⑫ Web 界面：Streamlit 三行代码出网页
@@need 要解决什么
Pipeline 是命令行能跑了，但"给业务同学演示、让同事试用"需要一个网页界面——不写前端、不搭服务，Python 里最偷懒的方案就是 Streamlit：**把脚本文件一跑就是网页，改一行刷新即生效**（详情见 07_Web界面.py）。

@@idea 核心思路
```python
import streamlit as st

st.set_page_config(page_title="社保政策问答助手", layout="wide")
st.title("社保政策问答助手（RAG Demo）")
st.caption("资料：社会保险政策 FAQ（本地向量库）")

query = st.text_input("请输入你的问题（例如：养老金领取条件是什么？）")

if query and st.button("提问", type="primary"):
    with st.spinner("检索资料中..."):
        result = pipeline.answer(query)
    # 答案
    st.markdown("#### 回答")
    st.write(result["answer"])
    # 溯源
    if result["sources"]:
        with st.expander("查看引用来源"):
            for s in result["sources"]:
                st.write(f"来源：{s}")
```

启动：
```bash
uv run streamlit run 07_Web界面.py
# 浏览器自动打开 http://localhost:8501
```

任意一个问题走完整链路演示：
```text
用户输入 → Streamlit 捕获
        → pipeline.answer()
             ├─ 问题向量化 → Chroma Top-3
             ├─ 拼 Prompt（指令+资料+问题）
             └─ LLM 生成答案
        → 网页展示 答案 + 引用来源
```

**跑通验收清单**（照着做一遍）：问一条 FAQ 里有的问题（答案应贴合资料）→ 问一条资料里没有的问题（应回复"无法回答"，而不是硬编）→ 点开"引用来源"核对答案出处。三条都过了，你的第一个 RAG 系统就正式成立。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| **每次提问都卡好几秒** | Streamlit **每次交互都会把整个脚本从头重跑一遍**——如果模型和向量库是写在脚本顶层加载的，每次提问都会重新加载一次。必须用 `@st.cache_resource` 把模型、collection、pipeline 缓存起来 |
| 以为改一行代码不用重启 | Streamlit 支持热重载，但**缓存过的对象不会自动刷新**（改了加载逻辑要清缓存） |
| 把检索到的原文全展示出来 | 界面会变得又长又乱。**默认折叠（`st.expander`），用户想核对时再展开** |
| 没有加载态提示 | 用户点了按钮半天没反应，以为坏了。要 `st.spinner("检索中…")` |
| 以为 Streamlit 能直接上生产 | 它的定位是**演示和内部工具**。要做正式产品还是前后端分离 + 正规 Web 框架 |

@@summary
这一章你亲手搭完了一个端到端 RAG 系统，七个文件七个环节全部跑通：
- 01 数据解析：PDF/TXT 变干净文本
- 02 文本分块：chunk_size + overlap 保住语义
- 03 向量化：BGE 小模型把文本变 512 维向量
- 04/05 大模型接入：OpenAI 兼容接口 + 分层封装，密钥只走环境变量
- 06 Pipeline 编排：检索→增强→生成→溯源四步总装
- 07 Streamlit：三行代码出问答网页

而且你掌握了"换零件"的能力：换文档换语料、换 Embedding、换向量库、换大模型、加混合检索、加重排序——依赖的是你对链路每一环的理解，而不是某个库的 API。这个骨架，就是你做企业知识问答系统的第一版原型。

@@quiz
1. 向量化入库和查询时，Embedding 模型应该？
   A. 入库用大的、查询用小的　　B. 必须同一个模型　　C. 随便换，向量库会兼容　　D. 查询不需要向量化
2. Chroma 入库时为什么要同时存 documents（原文）？
   A. 原文可以用来算相似度　　B. 检索后要把原文喂给大模型和用户溯源　　C. 向量库强制要求　　D. 存原文能省向量
3. 分块参数 chunk_size = 200、overlap = 50 的含义是？
   A. 每 200 个字符切一块，下一块从 150 字处开始（重叠 50 字，防止语义腰斩）　　B. 每块 200 字，块间丢 50 字　　C. 200 字以上的块才入库　　D. 每块最多 200 词
4. 答案质量差、答非所问时，首先该排查的是？
   A. 换更强的大模型　　B. 检查检索召回的相关性（再调 chunk/阈值/k）　　C. 把 temperature 调高　　D. 增加 Prompt 里的赞美词
5. 密钥的正确管理方式是？
   A. 直接写进代码方便复制　　B. 放环境变量（os.environ）读，代码只留占位　　C. 写进 git 仓库备份　　D. 放进 Prompt 让模型保管

@@links
参考|章节3_RAG端到端快速演示.pdf|#
源码|rag_demo（7 个 Python 文件全量源码）|#
官网|uv 包管理器|https://docs.astral.sh/uv/
官网|sentence-transformers（BGE 模型）|https://github.com/huggingface/sentence-transformers
官网|Chroma 向量库|https://docs.trychroma.com
官网|Streamlit 网页框架|https://streamlit.io/
官网|通义千问（百炼）|https://bailian.console.aliyun.com/
官网|智谱 GLM 开放平台|https://open.bigmodel.cn/