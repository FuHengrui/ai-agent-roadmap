@@h1 第七章　手写 LoRA 微调（四）：测试、合并与上传
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　2 课时　|　难度 ★★★

@@why 这一章在解决什么问题
训练完了，LoRA 权重躺在 `./lora_model`——但**工作没完**：你怎么证明它真的变强了？怎么把它从"训练态"变成"能线上用的完整模型"？怎么把成果分享给全世界/同事？

这一章回答三个收尾问题：
1. **测试**：加载回微调模型，用真实问题生成回答，验证 LoRA 生效（微调前后对比）；
2. **合并**：把补丁（A×B）焊回底座 W，产出一个独立的完整模型（第 10 章导出 GGUF、跑 Ollama 的前置）；
3. **上传**：把模型推到 Hugging Face Hub，让任何人有 URL 就能下载使用。

学完这一章，手写 LoRA 的"环境→数据→训练→测试→部署"闭环全部走通，你算真正"玩过一次微调"了。

@@map 这一章在整个知识库里的位置
上一章（手写 LoRA 三）：训练完成，拿到 lora_model 补丁权重
**本章** ← 你在这里：加载测试（生成回答）→ merge_and_unload 合并 → save 合并模型 → push 到 Hugging Face
下一章：从"手写"转到"工具"——Unsloth 提速微调（训练快 2~5 倍、省 70% 内存）
再往后：GGUF/Ollama 部署（本章合并产物直接用）→ LLaMA-Factory WebUI 一站式微调
阶段终点：既能手搓 LoRA，也会用主流工具/部署链路

@@point ① 加载方式：先底座、再补丁
@@need 要解决什么
测试第一步：把训练好的 LoRA 权重加载回来。它和加载原始模型不一样——**先载底座（base model），再叠补丁（LoRA）**。为什么必须两步？直接载 lora_model 目录行不行？

@@idea 核心思路
讲义代码（整理为可运行版）：

```python
from peft import PeftConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

peft_model_path = "./lora_model"

# 1. 读 LoRA 配置（里面记着底座模型名）
config = PeftConfig.from_pretrained(peft_model_path)

# 2. 先加载底座模型（名字存于 config.base_model_name_or_path）
model = AutoModelForCausalLM.from_pretrained(
    config.base_model_name_or_path,
    device_map="auto", torch_dtype=torch.float16)

# 3. 再把补丁叠上去
model = PeftModel.from_pretrained(model, peft_model_path)

# 4. 加载分词器（存于 lora_model 或底座）
tokenizer = AutoTokenizer.from_pretrained(peft_model_path)
```

为什么两步：**LoRA 权重不是完整模型**——它只是补丁，必须贴回到同名底座上才有意义。`adapter_config.json` 里记录了 `base_model_name_or_path`，加载时自动找回底座。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接 `AutoModelForCausalLM.from_pretrained("./lora_model")` 报错 | 目录里没有完整模型权重，只有补丁。**必须走 PeftModel 两步加载**（先底座后补丁） |
| "Unexpected key(s)" 报错 | 底座模型和保存时记录的不一致（换过模型/路径）。确认 `config.base_model_name_or_path` 指向正确的底座 |
| 底座下载很慢/失败 | 和之前一样用 HF 镜像；或本地已有底座时直接传本地路径 |

@@point ② 合并权重：merge_and_unload 把补丁焊回去
@@need 要解决什么
补丁模式不能直接转 GGUF、不能跑 Ollama、别人也没法直接用。**合并（merge）**把补丁算进底座，产出"无 LoRA 痕迹"的完整模型——为什么非合不可？

@@idea 核心思路
讲义代码：

```python
# 合并 LoRA 权重并卸载适配器
model = model.merge_and_unload()

# 保存合并后的模型（完整模型！）
model.save_pretrained('./merged_model')
tokenizer.save_pretrained('./merged_model')
```

merge 的本质（对应第 3 章公式）：

$$W_{merged} = W + \frac{\alpha}{r} \cdot AB$$

| 合并前 | 合并后 |
|---|---|
| W 冻结 + A、B 两个补丁 | 一个包含补丁效果的 W' |
| 依赖 adapter_config + 底座 | 独立完整模型，谁都能直接用 |
| 体积小（几百 MB） | 体积=底座大小（GB 级） |

要点：
- `merge_and_unload()` 的 **unload** 是卸载 PEFT 结构，把模型恢复正常形态；
- 合并后的 `./merged_model` 是**独立模型**：可导出 GGUF（第 10 章）、推 Hugging Face、直接 from_pretrained 加载。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 合并完还想继续微调 | 合并后补丁信息已"烧"进 W，再训练要么重挂 PEFT 要么就是全量微调。**训练迭代阶段保留 lora_model，最后再合并**部署版 |
| merged_model 好几个 GB，以为存错 | 正常：合并=完整模型体积。**loRA 补丁（小、可复用）和合并模型（大、可部署）两个都留**，用途不同，别删错 |
| merge 时显存不足 | 合并需要把补丁+底座同时在显存，可先 `model = model.to("cpu")` 再 merge，速度慢点但能过 |

@@point ③ 写 generate_text：让模型真正"开口"
@@need 要解决什么
加载完成了，怎么让模型生成回答？`model.generate` 是入口，但直接生成会输出一堆 token 数字——要写一个 `generate_text` 函数，把"输入文本→编码→生成→解码"封装起来，这也是第 9、10 章都会用到的模式。

@@idea 核心思路
讲义代码（整理为可运行版）：

```python
import torch

def generate_text(input_text):
    # 构造提示（模板要和训练时一致！见第5章）
    prompt = f"指令: {input_text}\n回应:"
    # 编码：return_tensors="pt" 转张量，并移到模型所在设备
    input_ids = tokenizer(prompt, return_tensors="pt").to(model.device)
    # 关闭梯度计算（推理不需要）
    with torch.no_grad():
        output = model.generate(**input_ids)
    # 解码：跳过特殊标记
    response = tokenizer.decode(output[0], skip_special_tokens=True)
    return response.split("回应:")[1].strip()

# 测试
print(generate_text("你好"))
```

四个要点：
1. **模板必须和训练一致**（指令:/回应:）：否则模型"失忆"（第 5 章 trap）；
2. `return_tensors="pt"`：转成 PyTorch 张量；
3. `torch.no_grad()`：推理不开梯度，省显存更快；
4. `.split("回应:")[1]`：从输出里剥出模型真正"回答"的部分。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 输出是一串数字，不是文字 | 忘了 decode：`tokenizer.decode(output[0], skip_special_tokens=True)`。generate 返回的是 token ID |
| 模型回答重复刷屏（"你好你好你好…"） | 生成参数没限制：加 `max_new_tokens=128`、`do_sample=True, temperature=0.7` 控制长度与多样性 |
| `.to(model.device)` 报错/张量设备不一致 | input_ids 和模型必须在同一设备；`model.device` 取模型当前设备，别硬编码 "cuda"（CPU 机器会炸） |

@@point ④ 效果验证：微调前后对比
@@need 要解决什么
模型"会说话了"，但**怎么证明 LoRA 让它变强了**？光靠感觉不行——用同一批测试问题，对比"原始 DeepSeek"和"LoRA 微调后"的回答，看差异是否合理、是否符合数据集的风格。

@@idea 核心思路
对比方法（三条）：

| 方法 | 操作 | 判读 |
|---|---|---|
| 同题对照 | 原始底座 vs 合并模型，同一个 `generate_text` 跑同样问题 | 微调后的回答应更贴合训练集风格/更会按指令 |
| 换模板对照 | 用"指令:/回应:"格式问它没训过的领域 | 通用能力不应崩（过拟合灾难则崩） |
| 客观指标 | 用验证集算 loss（微调模型 eval loss 应更低） | 数字说话：loss 降 = 学到了 |

实操上，先跑 3~5 个训练集内问题（看是否学到），再跑 2~3 个训练集外问题（看泛化）。**微调模型的答案应该更像"数据集的说话方式"**——比如数据集中回答都带"您好"，它也应带上。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只拿训练集数据测，"全对"就宣布成功 | 训练集的题它背下来了，没说服力。**必须留测试问题**（第 5 章 eval 集或新写），看泛化 |
| 微调后通用能力明显崩坏 | 过拟合/数据质量差。对策：加数据量、调低 lora_alpha、加 dropout、减 epoch |
| 看不出任何差异，以为失败 | 可能是个好消息：它没忘通用知识，只是风格微调不明显。用**数据集风格特征**（话术、格式）来验证，别只看"有没有区别" |

@@point ⑤ 上传 Hugging Face：把成果推上去
@@need 要解决什么
本地模型再强也只有你自己能用。上传 HF Hub 后，任何人用一段 URL 就能拉取——部署、协作、分发全打通。这一节走通"登录→上传"两步，并强调**密钥纪律**。

@@idea 核心思路
三步流程：

```bash
# 1. 安装 SDK（如未装）
pip install huggingface_hub
# 2. 登录（需要 HF 账号里的访问令牌）
huggingface-cli login
# 输入 token 时粘贴：hf_xxxxxxxx（设置里生成）
```

```python
# 3. 上传模型和分词器
repo_name = "<你的用户名>/lora-test"   # 仓库名：用户名/模型名

tokenizer = AutoTokenizer.from_pretrained("./merged_model")
tokenizer.push_to_hub(repo_name)

model = AutoModelForCausalLM.from_pretrained("./merged_model")
model.push_to_hub(repo_name)
```

要点：
- **仓库名必须含你的用户名**（如 `kalistaaa/lora-test`）；
- 先传 tokenizer、再传模型（模型文件大，传完别慌）；
- 也可以在网页创建 "New Model" 仓库，再本地 push（二选一）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 token 写进代码/笔记/发给别人 | 令牌等于账号钥匙。**token 只在 huggingface-cli login 交互时粘贴**；代码里不要 hardcode。泄露了立刻去 HF 设置吊销重建 |
| push 报 401/403 | 令牌无效或权限不足：重新 login；检查令牌是否勾选了 write 权限 |
| 上传后模型列表是空的 | 确认 push_to_hub 是否成功跑完（大文件要等）；tokenizer 先传、模型后传，网页刷新看 repo 页 |

@@point ⑥ 模型上传的"密钥纪律"清单
@@need 要解决什么
整个 LoRA 流程里，最容易被"顺手"的坑就是密钥和环境变量：token、API Key、用户名。它们一旦泄露进公开仓库，几小时就会被扫号机器人抓走。这节把纪律写成清单，养成肌肉记忆。

@@idea 核心思路
四条铁律：

| # | 纪律 | 说明 |
|---|---|---|
| 1 | 令牌不落盘 | 只在 login 交互式粘贴，绝不写进 .py/.md/.env 提交 |
| 2 | 仓库检查"确实提交前再想一遍" | push 前跑 `git status` / 检查有没有把 `./lora_model`、`./merged_model` 误传（模型几 GB 也不该进代码仓库） |
| 3 | 用环境变量做配置 | 训练代码里的模型名、路径、repo 名用变量/配置，别散落硬编码 |
| 4 | 泄露立即吊销 | 一旦怀疑 token 泄露，马上去 HF 设置 regenerate，不要"先观察" |

记住：**公开仓库是公开的**——你 push 上去的每个文件（包括带 token 的训练脚本）都全世界可见。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `.env` 或 `config.py` 带着 API Key 进 git | 先加 `.gitignore` 再提交；已经提交过立刻吊销 Key。Git 历史里的凭据删不掉（除非改写历史），别心存侥幸 |
| 把 merged_model（几个 GB）也 pushed 到代码仓库 | 模型上 HF 用 `model.push_to_hub`，不要放进 git 代码库。**容器/代码/大文件三处分开放** |
| 该传的分支没传（main vs develop） | push 前想清楚目标仓库和分支；HF 模型仓默认 main，别推到奇怪分支导致别人拉不到 |

@@point ⑦ 手写 LoRA 全流程回顾：从环境到上线
@@need 要解决什么
四章实战下来，代码块散在各处。这一节把"环境→模型→数据→训练→测试→合并→上传"串成一张总图——它既是总结，也是后面 Unsloth/LLaMA-Factory 章节对照的"手写基线"。

@@idea 核心思路
完整流水线（对应各章）：

```
第4章 环境        conda lora_env + torch(cu126) + transformers/peft/datasets
第4章 模型加载     AutoTokenizer + AutoModelForCausalLM (DeepSeek-R1-1.5B, fp16, auto)
第5章 数据加载     load_dataset(LaMini-instruction) → train_test_split(0.1, seed=42)
第5章 预处理       instruction+response → input_ids/labels（编码512截断）
第6章 LoRA挂载     LoraConfig(r=8, α=32, q/v) + prepare + get_peft_model
第6章 训练         Trainer(train/eval, TrainingArguments) → 观察loss
第6章 保存         tokenizer.save + trainer.save → ./lora_model
第7章 测试         PeftModel 加载补丁 → generate_text 对比
第7章 合并         merge_and_unload → ./merged_model（完整模型）
第7章 上传         huggingface-cli login → push_to_hub
```

这套基线的三处可替换升级点（后文主线）：
- 训练太慢/太费显存 → **Unsloth**（第 8/9 章）；
- 部署要轻量 → **GGUF + Ollama**（第 10 章）；
- 想用现成框架点按钮 → **LLaMA-Factory WebUI**（第 11/12 章）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| "我会手写，就够用了" | 手写帮你理解原理，但生产效率上 Unsloth/LLaMA-Factory 更省事。**先手写懂原理，再用工具提效**——两条腿走路 |
| 把流程图当"一次必须全跑完" | 中间环节可复用：换数据只需重跑第 5~6 章；换底座只需第 4 章改 model_name。**流程模块化，改哪跑哪** |
| 全流程跑通一次就不再验证 | 环境漂移（装新包）可能悄悄破坏链路。**留一个 smoke 脚本**按图跑通核心几步，新环境一键回归 |

@@point ⑧ 本章验收：交付物齐不齐
@@need 要解决什么
最后一关：确认四个交付物都在、且每一件都是"真货"。验收通过，手写 LoRA 这段旅程才算正式毕业。

@@idea 核心思路
验收清单：

| # | 交付物 | 验收标准 |
|---|---|---|
| 1 | `./lora_model/` | adapter_config + adapter_model.safetensors 存在，能被 PeftModel 加载 |
| 2 | `./merged_model/` | 完整模型，能从 `./merged_model` 直接 from_pretrained |
| 3 | 生成功能 | `generate_text("你好")` 输出正常中文回答 |
| 4 | 对比记录 | 微调前/后同一问题回答有可说明的差异（风格/指令遵从） |
| 5 | HF 仓库 | 上传成功，网页可看到模型文件 |

再加一条进阶验收：拿第 10 章的 GGUF 导出试跑一次（Ollama 能 Chat）——"训练→部署"闭环就彻底通了。

到这一步，你已经是"手搓过 LoRA 的人"。接下来三章全是"更快的路"：Unsloth 提速训练、GGUF/Ollama 轻量上线、LLaMA-Factory 一站式懒人方案。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| merged/lora 两套都留着但搞混用途 | lora_model=可迭代轻量补丁；merged_model=可部署完整模型。**存到不同目录并写 README**，注明各自用途 |
| HF 上 model 文件没传全（如只传了 config） | 检查 push 输出/网页文件列表；大文件推送失败会"静默部分完成"，重传该文件即可 |
| 验收至此就认为"上线了" | 还差部署一环（第 10 章）：合并模型要转 GGUF + Ollama 才算真能被业务调用。**验收≠上线**，闭环到第 10 章收尾 |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **测试能力** | two-step 加载（底座+补丁）、generate_text 封装、微调前后对比方法 |
| **合并能力** | merge_and_unload 焊回补丁，产出可部署的完整模型（第 10 章前置） |
| **分发能力** | huggingface-cli login + push_to_hub 上传模型，密钥纪律四铁律 |
| **完整闭环** | 环境→数据→训练→测试→合并→上传总图，手写 LoRA 毕业 |

下一章进入工具加速线：Unsloth 凭什么快 2~5 倍、省 70% 内存？怎么用它微调 DeepSeek？

@@quiz
1. 为什么加载 LoRA 权重要"先底座、后补丁"两步？直接载 lora_model 会发生什么？
2. merge_and_unload() 在数学上做了什么操作？合并前后的模型有什么区别？
3. generate_text 里 `skip_special_tokens=True` 和 `torch.no_grad()` 各起什么作用？
4. 验证微调效果时，"只拿训练集问题测"错在哪里？正确做法是什么？
5. 上传 Hugging Face 的仓库名格式是什么？push 前要确认什么？
6. 写出关键词生成的密钥纪律（至少三条）。
7. 从环境到上传的完整流水线按顺序写出来（八步）。

@@links
讲义|大模型 DeepSeek 微调与应用：测试微调后的模型、模型上传 Hugging Face|#
官网|Hugging Face Hub 文档（上传/令牌）|https://huggingface.co/docs/hub/models-uploading
官网|PEFT 显存优化指南（合并/卸载）|https://huggingface.co/docs/peft/conceptual_guides/memory