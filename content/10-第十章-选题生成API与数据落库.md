@@h1 第十章　选题生成 API 与数据落库
@@sub 阶段 9 · 智能运营平台　|　实践　|　难度 ★★★★

@@why 这一章在解决什么问题
AI 的大脑（选题 Bot）装好了，后端也要会"使唤"它并把结果存下来。本章是**前后端与 AI 第一次真正打通**的关键一战：前端点"开始生成" → 后端调 Coze 选题 Bot → 拿到 50 标题 JSON → 提取清洗 → 写入 t_sections/t_titles → 前端能查主题列表、能按主题加载全部内容。

本章画重点：**AI 输出是"半可信"的**——模型可能多打一个反引号、少一个冒号、把解释文字和 JSON 混在一起。所以"从 AI 文本里可靠地抠出 JSON"（_extract_json）是本项目最容易翻车、也最见功力的环节。

@@prep 开始之前
第 9 章的 Coze 调用调通了就能开始，这章不用装新东西，重点在接口和落库。

@@goal 学到这儿就够了
能跑通 /start 生成到落库、再从 /themes 查回来，能从乱文本里抠出 JSON，就算过了。

@@map 这一章在整个知识库里的位置
上一章：Coze API 调用与工作流——AI 调用层就绪
**本章** ← 你在这里：选题生成 API——/start → Coze → 解析 → 落库 → 可查询
下一章：文案创作与编辑——选中标题后生成正文
再往后：配图与 OSS 上传发布

@@point ① create.py：内容生成路由的骨架
@@need 要解决什么
三个接口（/start 生成、/themes 主题列表、/load 加载内容）怎么组织？它们对应前端创作发布页的三个动作。

@@idea 核心思路
```python
router = APIRouter()   # prefix="/v1/create"

@router.post("/start")       # 提交主题 → 调 AI 生成并落库
@router.get("/themes")       # 当前用户历史主题（去重）
@router.get("/load")         # 按主题加载全部板块与标题
```
三者关系（前端动作流）：**start（生成素材）→ themes（看有什么主题）→ load（点开一个主题看内容）**。

所有接口第一行都是 `user_id = await get_current_user_id(...)`（第 6 章依赖）——**数据按用户隔离**，这是平台多账号运作的前提。

@@point ② /start 接口：参数校验先行
@@need 要解决什么
"开始生成"是最重的接口（十几秒到一分钟不等），参数不对就别浪费一次 AI 调用。

@@idea 核心思路
```python
@router.post("/start")
async def start(theme: str, user_id: int = Depends(get_current_user_id)):
    if not theme or not theme.strip():
        raise HTTPException(status_code=400, detail="主题不能为空")
    # theme 为空 → 400：在调 AI 之前就拦住，而不是白烧 token
    text = await hot_topic(theme)          # 调 Coze 选题 Bot（见第 8/9 章）
    data = _extract_json(text)             # 关键一步：从 AI 输出里抠 JSON
    if data is None:
        raise HTTPException(status_code=500, detail="AI 返回格式异常，请重试")
    ...
```

设计顺序铁律：**校验 → 调 AI → 解析 → 落库 → 返回**，每步失败都有明确的状态码（400 参数问题、500 AI/解析问题）。400 的错误永远不该让用户重试 AI 调用。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 空主题也去调了 Coze 白花钱 | 没在路由层做 strip 校验；空串/纯空格必须 400 拦截 |
| 调 AI 失败返回 500 但无细节 | 异常要捕获并记录 Bot ID/主题/错误，返回统一 500 提示 |
| 初学者以为校验是"多余代码" | 校验决定接口的"失败语义"，前端提示全靠它，一次到位省后续排查 |

@@point ③ _extract_json：从 AI 文本里可靠地抠出 JSON
@@need 要解决什么
AI 输出常是"文本 + JSON 混排"（甚至 Markdown 代码块），json.loads 直接解析必炸。需要一个"容忍度极高"的提取器。

@@idea 核心思路
核心套路：**先用正则找代码块/JSON 段，再尝试解析，失败逐级降级**。
```python
import json, re

def _extract_json(text: str):
    # 1) 先尝试直接解析（最干净的情况）
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2) 提取 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 3) 找第一个 { 到最后一个 } （容忍前后解释文字）
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            return None
    return None
```
- 三个层级从严格到宽松，**一级不行降级下一级**；
- 全部失败返回 None → 上层报"AI 返回格式异常"。

认知：**这不是"苟且写法"，是 AI 应用的标准防御**。真实项目中，模型输出 10% 概率带多余文字/反引号，这一函数把"偶发失败"变成"稳定服务"。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| json.loads 直接抛异常搞崩接口 | 没包 try；AI 文本不可信，任何解析都必须防御式处理 |
| `rfind("}")` 找不到闭合 | 输出被截断；此时应返回 None 并提示重试，而不是猜一个 |
| 提取出的 JSON 结构对不上（缺板块） | 提取只是第一步，结构校验（5 个 key）还要另做（见下一点）|

@@point ④ 结构校验：解析成功 ≠ 数据可用
@@need 要解决什么
_extract_json 拿到的是"合法 JSON"，但可能是 `{"title": "..."}` 而不是我们约定的 5 板块结构。落库前必须校验形状。

@@idea 核心思路
```python
EXPECTED = ["每日行业热点", "热点榜单", "专业知识榜单", "人设共鸣", "灵感广场"]

missing = [k for k in EXPECTED if k not in data]
if missing:
    raise HTTPException(500, f"AI 返回缺少板块: {missing}")
```
**校验内容**：
1. 五个板块 key 全在（缺则报错，不落库）；
2. 每个板块是列表且每条含 title 字段；
3. title 非空、长度合理（>0 字符，<=100 等）。

结构校验的意义：**把"坏数据"挡在数据库外面**。宁可让用户重试一次，也不往库里写半成品——因为半成品的清理成本远高于一次 AI 重试。

@@point ⑤ 落库：Section 先写，Title 后写
@@need 要解决什么
50 条标题要按"主题 → 板块 → 标题"挂起来，写入顺序与关联 id 怎么处理？

@@idea 核心思路
```python
# 1) 每个板块先建 Section，拿到 id
section = await Section.create(
    user_id=user_id, source_name=theme, name=板块名
)
# 2) 再用 section.id 批量建 Title
for i, item in enumerate(板块标题列表, start=1):
    await Title.create(
        section_id=section.id,
        title=item["title"],
        sort_order=i,            # 1..10
        status="0",              # 0 未生成（文案还没做）
    )
```
流程本质：**先主后从、先拿外键再写子表**——这正好呼应第 4 章"Section/Title 用普通 IntField 存 id，无级联"的设计，写入顺序由业务代码保证一致性。

批量场景优化：50 条逐条 create 有 N 次 DB 往返，可改用 `bulk_create` 一次写入——量级小时差异不明显，但要知道有这条路。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 落库后 themes 查不到这个主题 | user_id 没传或传错（用鉴权里的 user_id，别用前端传的旷值） |
| 标题顺序乱 | sort_order 写错或没写；枚举时用 enumerate start=1 |
| 事务：板块建成功、标题失败一半 | 需要事务包裹整批写入（Tortoise in_transaction），失败整体回滚，不残留孤儿板块 |

@@point ⑥ /themes 接口：主题去重
@@need 要解决什么
前端历史页要展示"我生成过哪些主题"，而 source_name 会重复（同一主题多次生成）——查询要 DISTINCT。

@@idea 核心思路
```python
@router.get("/themes")
async def themes(user_id: int = Depends(get_current_user_id)):
    rows = await Section.filter(user_id=user_id).order_by("-created_at")
    # 去重：按 source_name 保留最新一条
    seen, result = set(), []
    for r in rows:
        if r.source_name and r.source_name not in seen:
            seen.add(r.source_name)
            result.append({"source_name": r.source_name, "count": 板块数或标题数})
    return result
```
要点：
- **先按时间倒序再遍历去重** → 每个主题保留"最新一次生成"；
- source_name 为空（板块无主题）时跳过或单独归类；
- 返回结构带 count（该主题下板块/标题数）让前端卡片直接展示。

@@trap 坑在哪
去重要在**排序之后**做，否则"保留最新一条"会失效——先按时间倒序再遍历去重，才能保证每个主题留下的是最后一次生成；顺序反了会留下最早那条，前端展示的是过期选题。

@@point ⑦ /load 接口：按主题加载完整内容
@@need 要解决什么
点开一个主题，前端要一次性拿到"所有板块 + 板块下全部标题（含文案/状态）"。这就是素材页的数据来源。

@@idea 核心思路
```python
@router.get("/load")
async def load(theme: str, user_id: int = Depends(get_current_user_id)):
    sections = await Section.filter(user_id=user_id, source_name=theme)
    sections = await Section.annotate(标题用 prefetch 或循环查询)
    result = []
    for sec in sections:
        titles = await Title.filter(section_id=sec.id).order_by("sort_order")
        result.append({
            "name": sec.name,
            "titles": [{"id": t.id, "title": t.title, "status": t.status,
                        "content": t.content} for t in titles]
        })
    return result
```
要点：
- **load 是只读接口**，返回结构直接喂前端素材页渲染；
- titles 里带 status——前端据此显示"未生成/已生成/已发布/已废弃"徽标；
- 量大时用 `prefetch_related` 一次拿齐，别在循环里 N+1 查询。

⚠️ 边界：theme 参数在 URL 里（GET），**中文主题要 URL 编码**——axios 会自动处理，但 Postman/curl 手测时别漏 encodeURIComponent。

@@trap 坑在哪
| 现象 | 原因 |
|---|---|
| 前端加载慢/数据库连接数爆 | 循环内逐条查标题（N+1）；用 prefetch_related 或按 section_id in (...) 批量查 |
| 中文主题 GET 请求 400/乱码 | 未 URL 编码；axios 自动处理，手测工具要手动 encode |
| load 返回空但明明生成过 | user_id 不匹配（另一个账号登录）或 source_name 精确匹配失败（空格/换行） |

@@point ⑧ 从 start 到 load 的完整链路回顾
@@need 要解决什么
四章积累的知识点，在这里串成一条可运行的链路。心里有链路图，出问题才知道在哪一环。

@@idea 核心思路
```
前端 CreatePublish 点"开始生成"
  → POST /v1/create/start {theme}
  → 依赖注入鉴权（401/403 兜底）
  → 参数校验（空主题 400）
  → coze_agent.hot_topic(theme)   [第 9 章 SDK 调用，15-90s]
  → _extract_json(text)           [本章，容忍混排]
  → 结构校验（5 板块齐全）         [本章，坏数据不入库]
  → 事务落库 Section + Title      [本章]
  → 返回成功 + 主题标识
前端随后 GET /v1/create/load?theme=xxx 拉全量
  → 素材页渲染板块与标题
```
任何一个环节崩了，错误码就告诉你问题在哪一段：400 校验、401/403 鉴权、500 AI/解析/落库。

@@summary 这一章你学到了什么
- create.py 三接口：/start（生成）/themes（主题去重）/load（加载内容），全部按用户隔离
- /start 铁序：校验 400 → 调 AI → 解析 → 落库；空主题绝不烧 token
- _extract_json 三级防御：直接解析 → 代码块提取 → 首尾大括号截取，失败返回 None
- 解析成功 ≠ 可用：5 板块 key 与标题结构必须显式校验，坏数据不入库
- 落库顺序：先 Section 后 Title，事务包裹防孤儿数据；bulk_create 优化批量
- /themes：倒序 + 去重保留最新，返回带 count；/load：倒序 sort_order + prefetch 防 N+1
- 中文主题 GET 要 URL 编码；错误码即链路定位器（400→校验 401/403→鉴权 500→AI/解析）

@@quiz
1. /start 接口对空主题的处理是？
   A. 直接调 AI　　B. 400 拦截，不浪费 AI 调用　　C. 默认"综合"　　D. 忽略
2. _extract_json 的提取策略是？
   A. 只 json.loads　　B. 直接解析→代码块→首尾大括号，逐级降级　　C. 正则硬抠　　D. 不解析
3. JSON 合法但缺少"灵感广场"板块，正确做法是？
   A. 照常落库　　B. 结构校验拦截并提示重试　　C. 自动补空板块　　D. 忽略
4. 落库时 Section 与 Title 的写入顺序是？
   A. 先 Title 后 Section　　B. 先 Section 拿 id 再 Title　　C. 同时写　　D. 无所谓
5. 50 条标题逐条 create 的问题与优化？
   A. 没问题　　B. N 次往返，可用 bulk_create　　C. 必须逐条　　D. 会丢数据
6. /themes 主题去重的技巧是？
   A. SELECT DISTINCT　　B. 先按时间倒序再遍历去重保留最新　　C. 全部返回　　D. GROUP BY 随机
7. 中文主题走 GET /v1/create/load 必须？
   A. 转成拼音　　B. URL 编码　　C. 改为 POST　　D. 放请求体

@@links
参考|智能运营平台.pdf|#
官方|Tortoise 查询集参考|https://tortoise.github.io/query.html
官方|MDN URL 编码|https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent