@@h1 第五章　服务验证与基础调用：curl 与 OpenAI SDK
@@sub 阶段 24 · 大模型时代的模型运维与部署　|　验收实战　|　难度 ★★★

@@why 这一章在解决什么问题
服务起来了，怎么确认真能用？**验证**环节分两路：用 curl 直接打 HTTP 接口看裸响应，用 OpenAI SDK 走"正经客户端"流程。同时把配套的 `server.py` 源码吃透——它演示了从客户端视角调用 vLLM 服务的标准写法。本章是部署链路最后的"关门验收"。

@@prep 开始之前
上一章的服务要还在跑，本地要有 curl，用 SDK 还得装 openai 库。

@@goal 学到这儿就够了
能用 curl 和 OpenAI SDK 各调通一次对话接口，能对着报错判断是服务没起还是参数填错，这章就算过了。

@@map 上一章→本章→下一章
上一章完成了模型下载与服务启动。**本章验收：curl 验证 /v1/models 与对话接口、OpenAI SDK 调用、server.py 源码拆解、常见故障排查**。至此阶段24 完结，模型部署"从装到用到验"全链路闭环。

@@point ① 验证第一步：curl 查模型列表
@@need 要解决什么
服务说"起来了"，怎么用一分钟确认它真的在工作？

@@idea 核心思路
最轻量的验证：用 curl 请求模型列表接口（OpenAI 兼容格式）：

```
curl http://localhost:8000/v1/models
```

成功响应示例（JSON）：

```
{"object": "list", "data": [{"id": "qwen", ...}]}
```

看到返回的 `id` 字段，说明三件事同时成立：**服务进程在跑、端口能通、模型加载完成**。这个 id 就是启动时配置的 served-model-name，后续所有请求的 `model` 字段都填它。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| curl 连接被拒 | 服务没起/端口错/监听地址不对，回查第四章启动配置 |
| 返回的 id 与预期不同 | 客户端请求里的 model 要以返回 id 为准，否则报 404 |

@@point ② 用 curl 发起一次对话请求
@@need 要解决什么
模型列表验证通过，怎么发一条真正的对话？

@@idea 核心思路
用 curl 直接 POST 对话接口（OpenAI 格式）：

```
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [{"role": "user", "content": "你好，介绍一下你自己"}],
    "max_tokens": 100
  }'
```

响应里 `choices[0].message.content` 就是模型生成的内容。要点：

- `model` 填 served-model-name（不是本地路径）。
- `messages` 是 OpenAI 标准的 role/content 列表。
- `max_tokens` 限制本次生成长度。

一个 curl 通了，就证明"服务→模型→生成→回传"整条链路可用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| JSON 格式写错 | 引号/逗号错一个就 400，先本地格式化再提交 |
| model 名填错 | 报模型不存在，回 /v1/models 查真实 id |

@@point ③ 用 Python OpenAI SDK 调用
@@need 要解决什么
生产代码一般不用 curl，SDK 怎么接？

@@idea 核心思路
OpenAI 官方 Python SDK（工业标准）：

```
pip install openai
```

调用代码（和 server.py 同款思路）：

```
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
)
resp = client.chat.completions.create(
    model="qwen",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)
```

三个关键点：**base_url 指向 vLLM、api_key 随便填（vLLM 本地不校验）、model 填 served-model-name**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| base_url 忘了带 /v1 | 路径写错直接连接失败，vLLM 接口都在 /v1 下 |
| api_key 填了真密钥 | 本地 vLLM 不校验 key，填占位符即可，别把真实密钥填进去 |
| model 与返回 id 不一致 | 一切以 /v1/models 返回的 id 为准 |

@@point ④ server.py 源码逐行拆解
@@need 要解决什么
配套的 server.py 只有 9 行，它演示了什么？

@@idea 核心思路
配套的服务器端示例源码语义（9 行演示）：

```
from openai import OpenAI       # ① 引入官方 SDK

client = OpenAI(
    base_url="http://localhost:8000/v1",   # ② 指向 vLLM 服务
    api_key="EMPTY",                       # ③ 本地服务key可占位
)

response = client.chat.completions.create( # ④ 发起对话
    model="qwen3-0.6b",                    # ⑤ 模型名（对应当前加载的模型）
    messages=[{"role": "user", "content": "你好"}],
)
print(response.choices[0].message.content) # ⑥ 打印生成结果
```

核心价值：**完整示范了"客户端 ↔ vLLM 服务"的最小可用代码**——接入 vLLM 的服务调用范式就是这 6 步，看懂它即掌握接入方式。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 照抄 model 名不核对 | server.py 里的模型名要与实际 served-model-name 一致，换模型要改 |
| 只用 print 不用异常处理 | 生产代码要 catch 网络/超时错误并做重试，示例仅教学用途 |

@@point ⑤ 流式输出的客户端写法
@@need 要解决什么
上一章提过流式输出，客户端代码怎么开？

@@idea 核心思路
OpenAI SDK 加一个参数即可开启流式：

```
resp = client.chat.completions.create(
    model="qwen",
    messages=[{"role": "user", "content": "讲个故事"}],
    stream=True,          # 开启流式
)
for chunk in resp:        # 逐块读取
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="")
```

优势：

- 首 token 更快到达（不用等全部生成完）。
- 逐段输出，用户体感接近 ChatGPT。
- 配合 vLLM 前缀缓存与连续批处理，高并发下体验更好。

**教学要点**：流式与普通模式的唯一差别就是 `stream=True` + 迭代响应。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了迭代流式对象 | stream 模式必须 for 循环消费，直接取 choices 会拿不到内容 |
| 混用两种模式代码 | 普通模式整体返回、流式模式分块返回，写法不同别混着抄 |

@@point ⑥ 服务常见故障排查清单
@@need 要解决什么
服务验证不通过，从头到尾怎么排查？

@@idea 核心思路
按"链路"排查法，从外到内：

| 症状 | 排查点 |
|---|---|
| curl 连接失败 | 服务进程？端口？--host 是否 0.0.0.0 |
| 返回 404 | URL 路径（需 /v1/...）、模型名是否匹配 |
| 返回 400 | 请求 JSON 格式、参数名错误 |
| 返回 500/超时 | 显存不足？max-model-len 过大？模型加载失败 |
| 生成质量差 | 模型选错/量化过狠/上下文超长 |

排查顺序口诀：**进程 → 端口 → 路径 → 参数 → 资源**，逐层收窄。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 一上来就怀疑模型 | 90% 的"连不上"是服务/网络层问题，先查进程与端口 |
| 忽略服务端日志 | vllm serve 的终端日志是最全的诊断信息，翻日志比瞎猜快 |

@@point ⑦ 从部署到生产：还差什么
@@need 要解决什么
本地验证通过后，离"线上可用"还差哪些事？

@@idea 核心思路
教学链路（本章终点）与生产链路之间还有增量：

| 环节 | 生产化动作 |
|---|---|
| 部署形态 | 容器化（Docker/NGC）+ 编排 |
| 访问控制 | 认证鉴权、限流、配额 |
| 高可用 | 多实例、负载均衡、健康检查 |
| 可观测 | 监控指标、日志、告警 |
| 成本 | 显存水位、并发上限、量化选型 |

理解意义：**vLLM 已把"推理服务化"这层做透，运维增量是工程化标准动作**——本阶段覆盖到"服务可用+可调用"即达成教学目标。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 验证过就当上线 | 教学验证≠生产就绪，安全/监控/高可用是另一层工程 |
| 忽略成本治理 | 模型越大越费钱，上线前先定好量化和并发策略 |

@@point ⑧ 本章小结：部署链路关门验收全记录
@@need 要解决什么
阶段24 的验收动作怎么归档成"一句话清单"？

@@idea 核心思路
验收三连：

```
① curl /v1/models        → 服务在跑、模型就绪
② curl /v1/chat/completions → 链路可用、能生成
③ OpenAI SDK 调用         → 客户端接入范式 OK（6行代码）
   含流式: stream=True 分块消费
```

排查口诀：**进程→端口→路径→参数→资源**；生产化清单：容器/鉴权/高可用/可观测/成本治理。

至此阶段24"大模型时代的模型运维与部署"五章全部完结：原理→特性→环境→启动→验收。

@@summary
这一章为阶段24 画上验收句号：

| 环节 | 动作 | 判定 |
|---|---|---|
| 模型列表 | curl /v1/models | 返回 id 即服务就绪 |
| 对话请求 | curl /v1/chat/completions | 返回 content 即链路通 |
| SDK 接入 | OpenAI(base_url=...) 6行 | client.chat.completions.create |
| 流式 | stream=True + 迭代 | 逐 block 消费 |
| 排查 | 进程→端口→路径→参数→资源 | 层层收窄 |
| 生产化 | 容器/鉴权/高可用/可观测/成本 | 工程增量 |

一句话记住本章：**部署验收三连：curl /v1/models 看服务就绪，curl /v1/chat/completions 验证能生成，再用 OpenAI SDK（base_url 指向 vLLM、api_key 填 EMPTY、model 填 served-model-name，6 行代码）跑通客户端接入；流式只需 stream=True 后迭代分块消费；遇到问题按"进程→端口→路径→参数→资源"层层排查别瞎猜——至此阶段24 从原理、特性、环境、启动到验收的五章全链路完结，vLLM 部署闭环达成。**

@@quiz
1. 用 curl 验证服务就绪的最简单命令是什么？成功响应里要看哪个字段？
2. 用 curl 发起一次对话请求的完整命令怎么写？三个关键点是什么？
3. 用 OpenAI SDK 调用 vLLM 时，base_url、api_key、model 分别怎么填？为什么？
4. server.py 演示的客户端接入范式是哪几步？
5. 流式输出在 SDK 代码中如何开启？与普通模式的区别？
6. 按顺序写出服务故障排查的五个层次。
7. 教学链路验证通过后，上线生产还差哪些工程化动作？

@@links
参考|部署（章节1-2）|#
文档|OpenAI Python SDK|https://github.com/openai/openai-python
站点|vLLM 服务化示例|https://docs.vllm.ai/en/latest/getting_started/quickstart.html