@@h1 第十章　模型格式与部署：GGUF、Safetensors 与 Ollama
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　2 课时　|　难度 ★★★

@@why 这一章在解决什么问题
模型训练/微调再牛，如果不能"被业务调用"，价值就是零。部署第一课是**认清模型格式**：`safetensors`、`gguf`、`onnx`、`bin` 到底什么区别？为什么 Ollama 只认 GGUF？微调完的模型怎么变成 Ollama 能跑的东西？

这一章回答三件事：
1. 四种常见模型格式各自是什么、干什么用、什么场景选哪个；
2. 把 LoRA 合并后转 GGUF（`save_pretrained_gguf`）；
3. 用 Ollama 本地跑起来，用 HTTP 接口调用。

学完这章，你的微调成果就有了"可配置、跨平台、轻量"的落地形态。

@@map 这一章在整个知识库里的位置
上一章：Unsloth 微调完成，拿到 lora_model_uns
**本章** ← 你在这里：模型格式全景 → 合并+转 GGUF → Ollama 部署 → 接口调用
下一章：LLaMA-Factory 框架与数据集（换工具做微调）
再往后：WebUI 微调与监控（LLaMA-Factory 收官）
再往前：第 7 章合并的 merged_model，正是本章导出的输入
阶段终点：微调产物端到端上线，可服务真实请求

@@point ① 四种格式全景：谁是谁
@@need 要解决什么
下载模型时经常看到 pytorch_model.bin、model.safetensors、.gguf、.onnx——眼都花了。这一节给出全景表，从此看格式知用途。

@@idea 核心思路
| 格式 | 本质 | 优点 | 典型场景 |
|---|---|---|---|
| PyTorch (.bin) | pickle 序列化张量 | 兼容老代码 | 历史库、旧教程；正被取代 |
| Safetensors | 纯张量二进制 + 索引 | 安全、快、零 pickle 风险 | **Hugging Face 主流默认** |
| GGUF | 分片量化张量（q4_0/q8_0/K-quants） | 小、内存映射、跨平台 | **Ollama/llama.cpp 部署** |
| ONNX | 通用推理图格式 | 跨框架、硬件加速 | 服务端/边缘部署 |

简称速记：
- **bin → safetensors**：HF 生态在升级，新模型默认 safetensors；看到 bin 只有"兼容旧接口"时才用；
- **GGUF**：专为推理做的"已量化、可分段加载"格式，Ollama/llama.cpp 家人；
- **ONNX**：追求部署效率与硬件加速（ONNX Runtime / TensorRT 等）时用。

关键认知：**格式之间要转换**。微调训练的产物是 safetensors（LoRA/合并后），要进 Ollama 就得转 GGUF——这就是本章的主线动作。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 拿 safetensors 直接塞给 Ollama，报错不认识 | Ollama 只认 GGUF。**先转格式再部署**，格式是部署的"语言"，说错语言人家听不懂 |
| 看到 .bin 就在"是不是旧模型"上纠结 | bin 只是序列化方式，模型能力看架构与权重。**优先用 safetensors 版**（安全+快），除非必须兼容 |
| 四种格式全要学全用 | 主线只需掌握 safetensors（训练/交付）+ GGUF（部署）；ONNX/bin 了解即可。**抓两头、放中间** |

@@point ② 合并 LoRA + 转 GGUF：save_pretrained_gguf
@@need 要解决什么
第 7 章学会了 merge_and_unload 合并；这一章要一步到位：**合并 + 导出 GGUF**。Unsloth 提供了 `save_pretrained_gguf` 一条龙，参数少、坑也少。这一节讲用法与量化级别选择。

@@idea 核心思路
讲义/Unsloth 代码（整理为可运行版）：

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/DeepSeek-R1-Distill-Qwen-1.5B",
    max_seq_length=2048, load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(model, ...)  # LoRA 配置（第9章）
trainer.train()  # 或加载已训好的 lora_model_uns（用 PeftModel 方式）

# 合并 + 导出 GGUF（多种量化等级一次出）
model.save_pretrained_gguf("model_gguf", tokenizer, quantization_method="q4_k_m")
```

量化等级怎么选（常见 K-quants）：

| 标识 | 含义 | 体积 vs 原始 | 质量 |
|---|---|---|---|
| q4_k_m | 4bit 混合量化（K-quant 中间档） | ~25% | 推荐默认 |
| q8_0 | 8bit 量化 | ~50% | 质量高、体积大 |
| f16 | 不量化 | 100% | 质量满 |

选型口诀：**默认 q4_k_m**——体积质量性价比最好；显存/质量有特别需求再走 q8_0 或 f16。

导出后目录里会有 `*.gguf` + `*.json`（超参/分词器信息），它们就是 Ollama 的原材料。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `save_pretrained_gguf` 报找不到分词器/配置 | 导出前模型和 tokenizer 必须已加载且配套；**先正常跑一遍训练/推理再导出** |
| 导出好几个 q 档文件，磁盘爆了 | 每个 q 档都会生成一份。**只导需要的档位**（默认 q4_k_m 一份，别贪多） |
| 转完 GGUF 文件比预期大 | 检查是否导出成 f16（未量化）或包含多分片。**查导出的 json** 确认量化档位与分片数 |

@@point ③ GGUF 的原理优势：为什么 Ollama 爱它
@@need 要解决什么
"Ollama 只认 GGUF"不是任性——GGUF 的特性正好配得上"本地推理"场景：量化压缩、内存映射、支持 CPU/GPU 混合。这一节讲透这三点，你就明白部署选型为什么以 GGUF 为默认。

@@idea 核心思路
GGUF 三大法宝（对照普通 safetensors）：

| 特性 | 说明 | 部署收益 |
|---|---|---|
| 内建量化 | 权重以 q4/q8 等压缩形态存储 | 体积小 4~10 倍，内存占用低 |
| mmap（内存映射） | 加载时按页映射，不必整体读入 | 秒级冷启动、多进程共享 |
| 分片设计 | 头信息+张量表+权重块 | CPU/GPU 混合推理、灵活调度 |

配合 Ollama 的场景：
- 你 4GB 显存机器，7B 模型 q4 量化后 ~5GB，放得下、跑得动；
- 模型文件是"文件即服务"：Ollama 提供统一入口，你只管调用。

结论：GGUF = "为本地部署而生的格式"；Ollama = "吃 GGUF 的推理服务"。这俩是阶段 12 部署线的黄金搭档。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为量化一定"严重损伤"模型 | q4 量化对 1.5B~7B 模型整体质量损失可接受（尤其微调后的风格对齐任务）。**先跑 q4 看效果，不达标再升 q8** |
| 在 CPU-only 环境调 GPU 参数 | Ollama 会自动探测硬件。**别手动指定 device 过死**；报 GPU 错就让它纯 CPU 跑 |
| mmap 的内存节省"以为永不占内存" | mmap 省的是冷启动与共享；推理时权重页仍会驻留。**按模型量化后体积估内存**（7B q4 ≈ 5GB） |

@@point ④ Ollama 安装与拉模型：一行命令开始
@@need 要解决什么
GGUF 有了，接下来是部署入口：装 Ollama、把模型"倒入"它、然后就能聊。这一节走通"下载→导入→跑"三步，重点交代换成你自己模型的导入方法。

@@idea 核心思路
步骤（讲义流程，具体命令以官网为准）：

```bash
# 1. 安装 Ollama（Windows/macOS/Linux 官网下载）
curl -fsSL https://ollama.com/install.sh | sh   # Linux 示例

# 2.（可选）直接拉官方预训练模型（不用自己的就跳过）
ollama pull qwen2.5:7b

# 3. 导入你自己的 GGUF：写一个 ModelFile
# 内容示例：
# FROM ./model_gguf/xxx-q4_k_m.gguf
# TEMPLATE """{{ .Prompt }}"""

# 4. 创建模型
ollama create my-r1 -f ./Modelfile
# 5. 跑起来
ollama run my-r1
```

导入自有模型的关键：
- **Modelfile 里 FROM 指向你的 gguf 路径**；
- TEMPLATE 给出提示模板（R1 系要配系统提示模板，不然风格不对）；
- `ollama create` 后 `ollama run` 即可对话；`ollama list` 查看已装模型。

通过 `ollama run` 互动只是验证；真正调用走 API（下一节）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Modelfile 的 FROM 路径带中文/空格报错 | 路径里别搞中文空格；**把 gguf 放纯英文目录**再写 FROM |
| ollama run 立刻退出/反复重启 | 显存不足时自动退；**缩小模型（q4 + 更小模型）或关后台进程**腾显存 |
| 忘记 TEMPLATE 导致风格跑偏 | R1 系不配模板会答非所问。**照模型卡抄 TEMPLATE**（含 system 指令），这是部署常被忽略的一条 |

@@point ⑤ Ollama API 调用：HTTP 方式接入业务
@@need 要解决什么
命令行 `ollama run` 只能自己玩；业务接入要走 **HTTP API**。这一节演示 `/api/generate` 与 `/api/chat` 的调用，让你的模型能被代码（脚本/Web/服务）使用——微调成果正式"上线"。

@@idea 核心思路
Ollama 默认监听 `http://localhost:11434`。生成接口调用（curl 示例）：

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "my-r1",
  "prompt": "什么是机器学习？",
  "stream": false
}'
```

Python 调用（requests 示例）：

```python
import requests

resp = requests.post("http://localhost:11434/api/generate",
    json={"model": "my-r1", "prompt": "什么是机器学习？", "stream": False})
print(resp.json()["response"])
```

要点：
- `/api/generate`：单轮补全；`/api/chat`：多轮对话（带 messages 数组）；
- `stream: false`：一次性拿完整结果；想流式输出（打字机效果）设 true，按行处理；
- **模型名用 `ollama create` 起的名字**（如 my-r1），不是文件名。

这样，任何会发 HTTP 请求的程序——脚本、Flask 服务、前端——都能调你的微调模型了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 请求报 connection refused | Ollama 服务没起（`ollama serve`）或端口被占。**先启动服务再调 API** |
| 400 错误模型名不对 | `ollama list` 看你 create 的名字，**API 里 model 字段与之一致** |
| stream=true 时 response 是 chunks 而非完整串 | 流式每行一个 JSON。**要完整结果就 stream=false**；流式要自己拼 chunk 的 response 字段 |

@@point ⑥ 部署链路复盘：从 LoRA 补丁到可调用服务
@@need 要解决什么
碎片步骤走完，需要一张总图：LoRA 补丁 → 合并 → GGUF → Ollama → API，每一环的输入输出是什么、在哪一环最容易卡。这张图就是你给别人讲"微调后怎么上线"的提纲。

@@idea 核心思路
完整部署链路（对应讲义与本章各节）：

```
lora_model_uns（补丁，几百MB）
   │ PeftModel 两步加载（第7章）
   ▼
merged（完整模型 safetensors，GB级）
   │ 合并 + save_pretrained_gguf
   ▼
model_gguf/*.gguf + *.json（量化，~25%体积）
   │ Modelfile 指向 gguf → ollama create
   ▼
Ollama 服务（localhost:11434）
   │ /api/generate 或 /api/chat
   ▼
任何业务代码（HTTP 调用）
```

各环节卡点表：

| 环节 | 常卡点 | 缓解 |
|---|---|---|
| 合并 | 显存不足 | 先加载 4bit 再 merge，或 CPU merge |
| 导出 GGUF | 档位/分词器缺失 | 先跑通推理再导出，只导 q4_k_m |
| Modelfile | 路径/TEMPLATE | 路径纯英文、模板照模型卡 |
| API 接入 | 服务没起/模型名错 | ollama serve + ollama list 核对 |

把这张图存进你的工程 README——它就是"微调模型上线手册"第一页。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只到"ollama run 能对话"就宣布上线 | 对话 ≠ 服务化。**API 调通**（curl 或代码）才算可被业务调用 |
| 每环节都重新下载模型（GitHub/HF） | 部署线每步产物可复用。**合并后的 merged/save 的 gguf 都本地留档**，别重复下载 |
| 从 LoRA 到 API 各步是"别人笔记"抄的 | 亲手走一遍 + 每环节做最小验证（merge 后能 generate、gguf 后能 ollama run）。**链路是自己的才算会** |

@@point ⑦ 常见模型部署报错速查
@@need 要解决什么
部署是"报错高发段"：格式、路径、显存、服务四类问题反复出现。集中成速查表，遇到直接查，别从头排查。

@@idea 核心思路
| 报错现象 | 根因 | 解法 |
|---|---|---|
| Ollama 不认 safetensors | 格式不对 | 先转 GGUF 再 create |
| create 时 not found | FROM 路径/文件名错 | 核对 gguf 绝对路径与文件名 |
| 加载模型即崩（OOM） | 显存不够 | 换 q4 档/更小模型/减 context |
| 中文乱码/花屏 | 模板或分词器不配套 | 用模型卡 TEMPLATE，分词器一起导出 |
| API connection refused | Ollama 没起 | `ollama serve` 后再调 |
| 400 unknown model | 模型名不符 | `ollama list` 核对 create 的名字 |
| 推理奇慢 | CPU 推理/上下文过大 | 换 GPU 环境；num_ctx 调小 |
| 回答重复刷屏 | 采样参数缺约束 | API 传 temperature/repeat_penalty 等参数 |

照这个表过一遍，80% 的部署问题 5 分钟内能定位。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 报错就重装 Ollama | 重装解决不了路径/格式问题。**先查表核对**，重装是最后手段 |
| 报错信息只看第一行 | 关键往往在最后几行（哪个库/文件/路径）。**从栈底往上读** |
| 网上解法版本不符（新老 Ollama 差异） | 新版本 API/命令有变。**看官方文档当前版**，别照抄过时帖 |

@@point ⑧ 本章验收：模型真能对外服务
@@need 要解决什么
最后一关验收：不只看"能跑"，要看"能被调用"。三项验收：GGUF 生成、Ollama 列表、HTTP 返回。通过=部署正式落地。

@@idea 核心思路
| # | 验收项 | 操作方法 | 通过标准 |
|---|---|---|---|
| 1 | GGUF 产物存在 | 列出 model_gguf/ | 有 *.gguf + *.json（量化档位正确） |
| 2 | Ollama 模型已创建 | `ollama list` | 有 my-r1（名字对） |
| 3 | 对话可用 | `ollama run my-r1 你好` | 正常中文回复、风格正常 |
| 4 | API 可调用 | curl /api/generate | 返回 JSON 含 response |
| 5 | 业务接入就绪 | Python requests 再跑一遍 | 脚本拿到结果 |

再加一条加分项：把推理脚本封装成一个 `chat_once(prompt)` 函数（第 7 章 generate 思路，换 HTTP 实现）——以后所有"调用微调模型"的场景都复用它。

全过 → 阶段 12 的部署线竣工：从微调到服务只差一次 HTTP 请求。剩下的三章转到"更省事的框架"：LLaMA-Factory 把微调变成填表。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| curl 能通、Python 通不了 | 多半是 JSON 格式/编码问题。**用 resp.json() 拿字段**，别手剥文本 |
| API 返回了但内容为空 | prompt 模板/字段名错（如 stream 解析）。**对照官方 JSON 结构逐字段核对** |
| "验收完就丢"不写文档 | 部署参数（模型名/端口/模板）没人记得住。**写一份 launch.md**：启动 Ollama→模型列表→curl 示例，10 行就能让别人接手 |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **格式全景图** | safetensors/GGUF/ONNX/bin 各归其位，不再被格式绕晕 |
| **GGUF 导出技能** | save_pretrained_gguf + 量化档位选择（q4_k_m 起步） |
| **Ollama 部署技能** | 安装→Modelfile→create→run→API，一步步接上业务 |
| **端到端产物** | 微调模型成为 localhost:11434 上可调用服务，`chat_once` 封装即用 |

下一章进入框架线：LLaMA-Factory 支持哪些训练方法、环境怎么装、数据集怎么注册——把微调从"写代码"变成"配配置"。

@@quiz
1. safetensors、GGUF、ONNX、bin 四种格式各典型用于什么场景？
2. 导出 GGUF 时默认推荐哪个量化档位？它的体积约是原始的多少？
3. GGUF 的三大特性是什么？为什么这些特性适合本地部署？
4. 导入自定义 GGUF 到 Ollama 需要哪两类文件/操作（Modelfile 里的关键两行）？
5. 业务代码调用微调模型走哪个接口？stream=true 和 false 的区别？
6. 部署链路从 LoRA 补丁到 API 共几步？每步产物是什么？
7. 部署报错"connection refused"最可能的原因是什么？怎么解？

@@links
讲义|大模型 DeepSeek 微调与应用：模型格式、GGUF 导出与 Ollama 部署|#
官网|Ollama 官方文档（Modelfile/API）|https://github.com/ollama/ollama
官网|Unsloth GGUF 导出指南|https://github.com/unslothai/unsloth/wiki/GGUF