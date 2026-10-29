@@h1 第十章　聊天与文书生成 API
@@sub 阶段 11 · LegalMind 法律咨询系统　|　难度 ★★★

@@why 这一章在解决什么问题
Agent 工作流是最强大脑，但用户够不着它——浏览器只认 HTTP 接口。本章把大脑装进 API 外壳：**聊天接口**（流式/非流式、会话列表、历史消息、删除会话）和**文书生成接口**（模板列表、生成、流式生成），全部带上鉴权、落库、SSE 推流。
最难的部分是**流式接口**：LLM 逐 token 吐字，要经由 FastAPI 的 StreamingResponse 以 SSE 格式实时推给前端，同时**流结束后还能拿到 sources**（前端要展示引用案例）。学完本章，前端只需要接四个 URL，就能获得"打字机式"的法律咨询服务。

@@prep 开始之前
第 9 章的工作流能跑就能开始，这章不用装新东西，写的是接口和 SSE 推流。

@@goal 学到这儿就够了
能做出聊天四接口和文书三接口、流式推字并带回引用，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章（第九章 Agent 工作流）：workflow.run/astream 已可用，checkpointer 已持久化
**本章** 你在这里：把工作流包装成 REST API——聊天四接口 + 文书三接口，鉴权 + SSE + 落库
下一章：前端初始化与路由——Vue3 工程、axios 封装、登录态、页面骨架
再往后：前端聊天页/文书页接上本章的流式接口
阶段终点：浏览器里能注册登录、发消息、看到打字机式回答

@@point ① 聊天 API 路由的整体设计
@@need 要解决什么
一个聊天功能需要哪些接口？从"前端要什么"倒推：发消息、列会话、看历史、删会话——四个能力对应四个 URL，缺一不可。
@@idea 核心思路
`app/api/chat.py` 的四组接口：
| 方法与路径 | 功能 | 是否需要登录 |
|---|---|---|
| POST `/api/chat/send` | 非流式发消息（一次返回全文） | ✅ |
| POST `/api/chat/stream` | 流式发消息（SSE 逐字返回） | ✅ |
| GET `/api/chat/sessions` | 当前用户会话列表（最近 50 个） | ✅ |
| GET `/api/chat/sessions/{id}/messages` | 某会话历史消息 | ✅ |
| DELETE `/api/chat/sessions/{id}` | 删除会话 | ✅ |
请求体统一用 Pydantic 模型校验：
```python
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None    # None 表示新会话

class ChatResponse(BaseModel):
    response: str
    intent: str
    sources: List[dict]
    session_id: str
```
设计要点：**session_id 由前端生成后传入——**但后端每次都必须用 _get_owned_session 校验归属**，否则拿到别人的 session_id 就能往他人会话里写消息。/send 与 /stream 里不能只调 `_ensure_session`（那是 get_or_create，会直接命中别人的会话）**（`None` 则后端生成）——这样前端可以在 SessionStorage 里先记住，避免"发完消息不知道会话 ID 是什么"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把"聊天/检索/文书"的逻辑直接写进路由函数 | 路由层越来越厚、测试没法下手；路由只做参数解析和响应包装，业务走 service/agent 层 |

@@point ② 会话与消息落库：_ensure_session / _record_messages
@@need 要解决什么
光把回答推给用户不行——刷新页面聊天记录就没了。每次收发都要落库：会话（ChatSession）+ 消息（ChatMessageRecord），并且**归属到当前用户**。
@@idea 核心思路
```python
async def _get_user_obj(user_info: dict) -> User:
    return await User.get(id=user_info["user_id"])

async def _ensure_session(session_id: str, user_obj: User) -> ChatSession:
    """确保会话存在且属于当前用户（不存在则创建）"""
    session, _ = await ChatSession.get_or_create(
        session_id=session_id,
        defaults={"user": user_obj},
    )
    return session

async def _record_messages(session: ChatSession, user_msg: str, assistant_msg: str) -> None:
    """把一轮对话写入消息表，供侧边栏 UI 读取"""
    await ChatMessageRecord.create(chat_session=session, role="user", content=user_msg)
    await ChatMessageRecord.create(chat_session=session, role="assistant", content=assistant_msg)
```
- `get_or_create`：已存在（返回的 session_id 是历史会话）则复用，不存在则创建——**天然支持"新会话/续聊"两种场景**。
- 每轮**写两条消息**（user + assistant），保证历史回放时角色完整。
- 越权防护：查询消息前校验 `session.user_id == user_info["user_id"]`，他人会话一律 404（第 4 章 `_get_owned_session` 就是这个职责）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 消息先塞进响应流再落库，失败时前端有消息、库里没有 | 顺序想清楚：先确认会话存在，流式结束后把完整消息落库；断流/报错也要有落库兜底或标记失败 |

@@point ③ 非流式接口 /send：跑完整图拿结果
@@need 要解决什么
最简单的形态：调用 workflow.run 跑完整流程，把最终回答一次性返回。它适合测试、文档接口和不需要打字机体验的场景。
@@idea 核心思路
```python
@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest, user=Depends(get_current_user)):
    user_obj = await _get_user_obj(user)
    session_id = request.session_id or str(uuid.uuid4())
    session = await _ensure_session(session_id, user_obj)

    # 跑完整工作流（含 checkpointer 记忆续接）
    result = await workflow.run(query=request.message, thread_id=session_id)

    await _record_messages(session, request.message, result["response"])

    return ChatResponse(
        response=result["response"],
        intent=result.get("intent", ""),
        sources=result.get("sources", []),
        session_id=session_id,
    )
```
三步走：**确保会话 → 跑图 → 落库并返回**。`workflow.run` 内部把 thread_id 传给 LangGraph，checkpointer 自动续接该会话的历史消息——多轮对话的记忆由此实现。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 慢请求客户端超时重发，LLM 被调两次 | 非流式接口要设合理的服务端超时和客户端重试策略；生成类接口考虑幂等键，避免重复扣费/重复生成 |

@@point ④ 流式接口 /stream：SSE 与 StreamingResponse
@@need 要解决什么
打字机效果的本质是"服务器端流式传输"。FastAPI 的 `StreamingResponse(media_type="text/event-stream")` 就是 SSE（Server-Sent Events）的标准载体：**响应不断开，内容一块块吐**。
@@idea 核心思路
```python
@router.post("/stream")
async def stream_message(request: ChatRequest, user=Depends(get_current_user)):
    user_obj = await _get_user_obj(user)
    session_id = request.session_id or str(uuid.uuid4())
    session = await _ensure_session(session_id, user_obj)

    async def generate():
        full_text = ""
        try:
            # 1. 流式走工作流，只收集 qa_generation 节点的 token
…（以下省略 25 行，完整代码见仓库对应位置）
                yield f"data: {json.dumps({'sources': sources}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'content': f'抱歉，处理出错：{e}'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```
SSE 协议格式：每帧 `data: JSON\n\n`，前端按行解析；`[DONE]` 表示结束。事件类型可以是 `content` / `sources` / 错误文案——前端靠 JSON 字段区分。
@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 前端收不到流 | 忘记设 `media_type="text/event-stream"` 或 Nginx 缓冲了响应（需关 buffering） |
| 流结束后 sources 拿不到 | stream_mode 下最终 state 不自动暴露；必须 `graph.aget_state(config)` 单独读 |
| 重复生成异常串 | 抛异常时也要先 yield `[DONE]`，否则前端永远等"结束" |
| 落库把 token 增量写进去 | 落库用累计的 full_text，不是每个 chunk |

@@point ⑤ session_id 的生成与归属校验
@@need 要解决什么
sessions 接口要防"看别人的会话"。三条规则：**不存在的会话 404、别人家的 404、读取按用户过滤**。
@@idea 核心思路
```python
async def _get_owned_session(session_id: str, user_info: dict) -> ChatSession:
    """获取属于当前用户的会话，不存在或越权则 404"""
    session = await ChatSession.get_or_none(session_id=session_id)
    if not session or str(session.user_id) != user_info["user_id"]:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session
```
归属校验的三条防线：
- **取数时**：`ChatSession.get_or_none(session_id=...)` 拿不到就 404。
- **比对时**：`str(session.user_id) != user_id` 越权访问也 404（**不告诉对方"这会话存在"**——隐私即安全）。
- **列表接口**：`ChatSession.filter(user=user_obj)` 只查自己的，天然隔离。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 校验只看 session 存在，不校验归属 | 只靠"能找到"就把 A 的会话数据发给 B；取会话时必须把当前用户 id 一起带进查询条件 |

@@point ⑥ 会话列表与历史消息接口
@@need 要解决什么
前端侧边栏要显示"历史会话"（标题 + 时间），点开要能回放消息。两个查询接口把聊天记录"捞"出来。
@@idea 核心思路
```python
@router.get('/sessions')
async def list_sessions(user=Depends(get_current_user)):
    user_obj = await _get_user_obj(user)
    sessions = await ChatSession.filter(user=user_obj).order_by("-created_at").limit(50)
    result = []
    for s in sessions:
        # 标题取该会话第一条用户消息的前 30 字
        last_msg = await ChatMessageRecord.filter(
            chat_session=s, role="user"
        ).order_by("created_at").first()
…（以下省略 4 行，完整代码见仓库对应位置）
        })
    return {'sessions': result}

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user=Depends(get_current_user), limit: int = 50):
    session = await _get_owned_session(session_id, user)
    messages = await ChatMessageRecord.filter(chat_session=session).order_by("created_at").limit(limit)
    return {"messages": [{"role": m.role, "content": m.content} for m in messages]}
```
两个细节：**标题用"第一条 user 消息截断 30 字"**（太长的截断，空会话显示"新对话"）；**消息按 created_at 正序**（保持对话先后），limit 默认 50 防超长响应。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 分页接口不排序或排序字段不稳定，翻页出现重复/丢失 | 历史消息按创建时间稳定排序 + 用时间戳+id 作游标，别用普通 offset 边插入边翻页 |

@@point ⑦ 文书生成接口：模板 + 生成 + 流式
@@need 要解决什么
文书和聊天共用一个大脑，但入口不同：文书要**选类型、填参数、可选引用案例**。三个接口把 DocumentAgent 包起来。
@@idea 核心思路
`app/api/documents.py` 的三接口：
```python
class DocumentGenerateRequest(BaseModel):
    document_type: str          # 起诉状/答辩状/合同/律师函/上诉状
    query: str                  # 用户需求描述
    params: Dict                # 表单参数（原被告姓名、金额等）
    use_references: bool = True # 是否检索参考案例

@router.get("/templates")
async def get_templates():
    return {"templates": [
        {"type": "起诉状", "description": "民事起诉状"},
…（以下省略 9 行，完整代码见仓库对应位置）
    references = []
    if request.use_references:
        references = await RetrievalAgent().retrieve(query=request.query, top_k=3)
    result = await agent.generate(
        document_type=request.document_type, params=request.params,
        query=request.query, references=references)
    return {"content": result["content"], "document_type": result["document_type"],
            "references": result["references"]}
```
- `use_references=True` 时先按 query 检索 3 个参考案例喂给生成器——**没有检索，纯模板生成就会"空有格式没依据"**。
- 中文类型名（起诉状）→ 模板（civil_complaint）的映射在 DocumentAgent 内部完成。
- 流式版 `/generate/stream` 与聊天流同构：`agent.astream_generate(...)` 逐 token 推 SSE。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用同步代码包住长耗时的 LLM 生成，把事件循环卡死 | 生成逻辑必须异步（async def + await），或用 run_in_executor 丢线程池；否则一个用户生成，全站请求排队 |

@@point ⑧ 前端 SSE 解析：从字节流到消息
@@need 要解决什么
前端拿到 SSE 响应，要自己解析"data: 行"——这不是 axios 的活，得用 fetch + ReadableStream。写一个通用解析器，聊天和文书流都复用。
@@idea 核心思路
`api/chat.js` 的流式封装（核心是 AsyncGenerator + AbortController）：
```text
export function streamSendMessage(message, sessionId) {
  const controller = new AbortController()

  async function* generate() {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
…（以下省略 22 行，完整代码见仓库对应位置）
        if (payload === '[DONE]') { yield { done: true }; return }
        try { yield JSON.parse(payload) } catch { /* 忽略脏行 */ }
      }
    }
  }

  return { abort: () => controller.abort(), stream: generate() }
}
```
三个关键点：**TextDecoder 处理 UTF-8 中文断字节**（token 边界可能切在中文中间）；**buffer 保留半行**（网络包可能在 \n 中间断开）；**AbortController 支持用户点"停止生成"**。

@@summary
这一章你实际拿到的是**三样东西**：
| 拿到了什么 | 为什么要紧 |
|---|---|
| **完整聊天 API** | 发消息/列会话/查历史/删会话，鉴权落库全齐 |
| **SSE 流式链路** | 后端 StreamingResponse + 前端 ReadableStream 解析，打字机体验 |
| **文书生成闭环** | 模板选择 + 参数 + 参考案例，五类文书一键生成 |

@@quiz
1. 聊天功能需要哪五个接口？各自解决什么场景？
2. _ensure_session 怎么同时支持"新会话"和"续聊"？get_or_create 的用法是什么？
3. /send 和 /stream 的核心区别？分别适合什么场景？
4. SSE 的帧格式是什么？为什么 stream 接口最后必须发 [DONE]？
5. 为什么 stream_mode 下要额外调 graph.aget_state() 拿 sources？
6. _get_owned_session 为什么要返回 404 而不是 403？
7. 会话列表的"标题"怎么生成？空会话显示什么？

@@links
参考|LegalMind 法律咨询系统：聊天与文书生成 API|#
官网|FastAPI StreamingResponse 文档|https://fastapi.tiangolo.com/advanced/custom-response/
官网|SSE 协议规范|https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events