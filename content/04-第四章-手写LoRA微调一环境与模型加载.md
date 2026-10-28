@@h1 第四章　手写 LoRA 微调（一）：环境与模型加载
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　难度 ★★★

@@why 这一章在解决什么问题
前两章全是理论，你这会儿一定手痒：**到底怎么把一个 DeepSeek 模型"挂上"LoRA 开始微调？** 从零搭一套可复现的环境，往往是新手第一个劝退点——要么 torch 装错版本、要么模型加载报"cuda 不可用"、要么显存爆掉。这一章就是"实战第一脚"：创建虚拟环境、装齐依赖、真正把 DeepSeek-R1-Distill-Qwen-1.5B 加载进显存，并看懂打印出来的模型架构。

学完这一章，你手里有一个**能加载预训练模型的工作台**——下一章喂数据，第三节就开训。所有步骤都按清单来，遇到环境报错也有坑位表可查。

@@prep 开始之前
要有一块 NVIDIA 显卡和 conda：装 CUDA 版 torch 和 peft，加载 1.5B 模型要几 GB 空间。

@@goal 学到这儿就够了
能建好环境、把 deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B 加载进显存并确认 GPU 可用，就算过了。

@@map 这一章在整个知识库里的位置
上一章（LoRA 原理）：懂了低秩补丁（W+AB）为什么省、参数怎么设置
**本章** ← 你在这里：动手第一步——建 conda 环境、装依赖、加载 DeepSeek-R1-Distill-Qwen-1.5B，验证 torch/GPU/模型可用
下一章：手写 LoRA（二）加载 LaMini 指令数据集并做预处理——把"问答对"变成模型能用的 token
再往后：训练与保存 → 测试合并上传 → Unsloth → GGUF/Ollama → LLaMA-Factory
阶段终点：你能独立从环境到部署跑通一整套 LoRA 微调

@@point ① 环境总览：这次微调需要哪些"零件"
@@need 要解决什么
很多新手死在新环境第一步：直接在 base 环境里 pip install，装到一半要 python 2.7 的依赖，把系统环境搞烂。先看清需要的"零件清单"，再用虚拟环境隔离，才不翻车。

@@idea 核心思路
环境清单拆成四组：

| 零件 | 命令/内容 | 作用 |
|---|---|---|
| 虚拟环境 | `conda create -n lora_env python=3.9` | 隔离项目依赖，坏了大不了重装 |
| 基础库 | `pip install transformers peft datasets` | 模型/微调/数据三件套 |
| 量化支持 | `pip install bitsandbytes accelerate` | 4bit 微调（QLoRA）与大模型加速 |
| 深度学习框架 | `pip install torch torchvision torchaudio --index-url .../cu126` | CUDA 版 PyTorch，GPU 训练的核心 |

**顺序很重要**：先建环境 → 再装库 → 最后装 torch。为什么 torch 单独装？因为它必须匹配你的**显卡驱动/CUDA 版本**，官网自动装的往往不带 GPU 支持，星前装完后一跑就报 "CUDA not available"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接 `pip install torch` 完事，训练时 `torch.cuda.is_available()` 返回 False | 默认 PyPI 的 torch 是 CPU 版。**必须用 CUDA 版本安装源**（如 cu126 对应 CUDA 12.6）重装；装完立即 `python -c "import torch;print(torch.cuda.is_available())"` 验证 |
| conda 环境建了但没激活，pip 装到了 base | 每次新开终端**先 `conda activate lora_env`**，用 `which python` 确认路径在环境里再安装；否则两套环境互相污染 |
| python 版本乱选 | 本项目指定 3.9（transformers/peft 对 3.9 兼容性最稳）；日后用 Unsloth 时再用 3.11 另建环境（第 8 章），两个环境并行不冲突 |

@@point ② 第一步：创建并激活虚拟环境
@@need 要解决什么
环境隔离怎么做才"干净可复现"？一张命令清单，从建环境到确认环境生效，避免"装了半天发现装错地方"。

@@idea 核心思路
三行命令，加一行验证：

```bash
conda create -n lora_env python=3.9   # 创建，-n 是名字
conda activate lora_env               # 激活
pip install transformers peft datasets # 基础三件套
python --version                      # 验证：必须显示 3.9.x
```

要点：
- `-n lora_env` 是环境名，可自取但**保持全英文小写**；
- 激活后用 `python --version` 和 `which python` 双重确认——`which` 显示的环境路径里要包含 `lora_env`；
- 这三件套先装，torch 单独下一步装，避免版本冲突时一团乱麻。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `conda activate` 报 "CommandNotFoundError" | conda 还没初始化 shell：跑 `conda init bash`（或对应 shell），重开终端再激活 |
| 装完发现 pip 装的是 base 的包 | 激活环境后 `pip --version` 检查 pip 路径；某些机器要 `python -m pip install` 才能绑定正确解释器 |
| 环境名用了中文/空格 | 部分工具对非 ASCII 环境名支持差，报错诡异。环境名一律英文小写加下划线 |

@@point ③ 第二步：安装基础依赖与量化支持
@@need 要解决什么
transformers/peft/datasets 是三件套，bitsandbytes/accelerate 是"量化+加速"的进阶件。哪些必装、哪些可选、装错版本会怎样——一条命令讲清楚。

@@idea 核心思路
命令拆解：

```bash
# 基础依赖
pip install transformers peft datasets
# 量化支持（4bits 微调需安装）
pip install bitsandbytes accelerate
```

| 库 | 干什么 | 不装会怎样 |
|---|---|---|
| transformers | 加载模型/分词器/训练器 | 没它寸步难行 |
| peft | LoraConfig / get_peft_model | 第 6 章挂 LoRA 全靠它 |
| datasets | 加载 Hugging Face 数据集 | 第 5 章加载 LaMini 失败 |
| bitsandbytes | 4bit/8bit 量化（QLoRA） | 显存不够时没法省 |
| accelerate | device_map 自动分配、多卡加速 | 加载时无法 "auto" 分设备 |

要不要装 bitsandbytes 取决于你的显存：**8GB 及以下强烈建议（量化后模型小 4 倍）**；24GB+ 可以先不装，LoRA 直接跑。这里默认都装，照着做最稳。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| bitsandbytes 在 Windows 上 import 报错 | 老版本对 Windows 支持差：升级到最新版（`pip install -U bitsandbytes`）；还不行就用 4bit 之外的方案或转 WSL（Unsloth 官方也推荐 WSL） |
| transformers 和 peft 版本互相不兼容 | 报 "cannot import LoraConfig" 多半是 peft/transformers 版本组合问题：`pip install -U transformers peft` 一起升级到最新稳定版 |
| 想装 GPU torch 却忘了先装 bitsandbytes | 顺序无严格限制，但**先装 torch 并验证 cuda 可用，再装其他库**——torch 是地基，地基错了上面全白搭 |

@@point ④ 第三步：安装 CUDA 版 PyTorch（关键一步）
@@need 要解决什么
这一步是新手重灾区：torch 装了，但用不了 GPU。为什么必须用 `--index-url` 指定 cu 版本？CUDA 版本怎么和显卡驱动匹配？——把它装在"驱动 → CUDA 工具包 → torch 构建版本"这条链上理解。

@@idea 核心思路
安装命令（以 cu126 为例）：

```bash
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu126
```

关键认知：
- PyPI 默认 torch 是 **CPU 构建**，训练速度差上百倍；
- `cu126` 表示**为 CUDA 12.6 构建**的 torch（`.so` 已编译好 GPU 内核），前提是你的**显卡驱动**支持该 CUDA 版本；
- NVIDIA 显卡看驱动要求：**驱动是"底层"，CUDA 工具包和 torch 是"上层"**。显卡驱动够新（如 550+），cu120/cu126 基本都能跑；老卡（如 10 系）需注意 cu 版本不要太高。

装完立刻验证：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
# 期望输出：2.x.x+cu126  /  True
```

`True` 就是对环境的第一次验收：**GPU 可用，后面的训练才有意义**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `torch.cuda.is_available()` False | 三查：① 装的是不是 cu 版（`torch.__version__` 应含 `+cu126`）；② 驱动是否够新（`nvidia-smi` 看右上角 CUDA Version）；③ 是否在 GPU 机器上。逐项排查，**不要重装同款再试** |
| 显存不够大的卡（如 4GB）硬跑 DeepSeek-R1-1.5B 全精度 | 叠三层解药：4bit 量化（bitsandbytes）+ LoRA（只训补丁）+ 用小模型。1.5B 4bit 约 1GB 出头，普通卡能扛 |
| torch 版本过高与 transformers 不兼容 | 官方组合推荐看 transformers 的 requirements；报格式错误优先 `pip install -U transformers`，别盲目换 torch 大版本 |

@@point ⑤ 认识主角：DeepSeek-R1-Distill-Qwen-1.5B
@@need 要解决什么
动手加载之前，总得先认识要调教的模型：它是什么底子、多大、"蒸馏"是什么意思？选它当教材主角不是因为最强，而是因为**小到单卡能跑、强到微调有肉眼可见效果**。

@@idea 核心思路
本章用的模型：

| 属性 | 内容 |
|---|---|
| 模型名 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` |
| 底子 | Qwen2（Qwen 2 架构，1.5B 参数） |
| 角色 | DeepSeek-R1 的**蒸馏（Distill）**版本——用 R1 大模型的输出去训练小 Qwen |
| 为什么选它 | 推理能力不俗 + 约 15 亿（1.5B）参数，普通消费级 GPU 友好 |

"R1-Distill" 的含义正是第 2 章的知识蒸馏实战形态：**教师（R1 大模型）→ 学生（Qwen-1.5B）**。它自带"会推理"的属性，任务微调时更容易看出 LoRA 前后的差异。

加载它需要 Hugging Face 网络可达（国内可用镜像 `HF_ENDPOINT=https://hf-mirror.com`），首次会自动下载约 3GB 权重。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 下载模型卡在 "Connection error" | 国内直连 HF 不稳定：设置镜像 `export HF_ENDPOINT=https://hf-mirror.com` 后重试；或用 `hf_transfer` 加速 |
| 首次运行以为"卡死了" | 1.5B 首次下载+加载要好几分钟，`from_pretrained` 期间无输出是正常的。给它时间，别乱杀进程 |
| 想用更大的 DeepSeek-R1（7B/14B/32B） | 学生阶段先 1.5B 跑通全流程；换大模型只要改 `model_name`，但显存按比例涨（4bit 7B 约 4~5GB） |

@@point ⑥ 加载代码：分词器 + 模型
@@need 要解决什么
LoRA 微调的第一个真实代码块来了。两行加载为什么写法是 `device_map="auto"` 和 `torch_dtype=torch.float16`？它们各自防什么坑？

@@idea 核心思路
示例代码（整理为可运行版）：

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
# 分词器：把文字切成 token
tokenizer = AutoTokenizer.from_pretrained(model_name)
# 模型：device_map="auto" 自动分配设备
# torch_dtype=torch.float16 使用半精度浮点数
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.float16
)
print(model)
```

三个关键参数：
- `device_map="auto"`：让 accelerate 自动把各层放到可用的 GPU/CPU 上（显存不够时部分层落 CPU，不直接爆显存）；
- `torch_dtype=torch.float16`：半精度（fp16），显存占用和计算量差不多减半，训练速度更快；
- `print(model)`：打印架构，用于确认加载成功并观察结构（下一个知识点）。

这就是"工作台"就绪的验收：**能打印出模型结构、不报错，说明环境 + 模型链路通了**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘记 `device_map="auto"`，模型全跑 CPU 或报 OOM | 不指定时默认全内存模式；显存小必炸。**统一加 auto**，让路径自动分配 |
| fp16 老卡（10 系列）不稳定 | 老卡对 fp16 支持差，可尝试 `torch.float32`（占显存翻倍）或 bf16（需较新卡，见第 8 章 is_bfloat16_supported）；新卡（20 系+）fp16 没问题 |
| 报错 "Some weights are not used" | 只是告警不是错误：模型加载时的权重映射提示，通常不影响使用，别被吓到 |

@@point ⑦ 看懂打印出来的模型架构
@@need 要解决什么
模型加载后会打印一大坨结构。新手看着像天书，但里面藏着微调的关键信息——**你要 LoRA 挂载的 q_proj/v_proj 就在这个结构里**。学会读它，后面填 target_modules 就不靠猜。

@@idea 核心思路
打印出来的核心结构（Qwen2 1.5B 节选）：

```
Qwen2ForCausalLM(
  (model): Qwen2Model(
    (embed_tokens): Embedding(151936, 1536)
    (layers): ModuleList(
      (0-27): 28 x Qwen2DecoderLayer(
        (self_attn): Qwen2Attention(
          (q_proj): Linear(in_features=1536, out_features=1536, bias=True)
          (k_proj): Linear(in_features=1536, out_features=256, bias=True)
          (v_proj): Linear(in_features=1536, out_features=256, bias=True)
          (o_proj): Linear(in_features=1536, out_features=1536, bias=False)
        )
        (mlp): Qwen2MLP(
          (gate_proj): Linear(1536 -> 8960)
          (up_proj): Linear(1536 -> 8960)
          (down_proj): Linear(8960 -> 1536)
        )
      )
    )
  )
  (lm_head): Linear(1536, 151936)
)
```

能读出什么：
- **28 层**解码器（1.5B 量级的常见深度）；
- 隐藏维 1536、词表 151936——先有数，后面算参数量也不慌了；
- **q_proj / k_proj / v_proj / o_proj / gate_proj / up_proj / down_proj** 就是第 6 章 `target_modules` 可选的模块名（LoRA 就挂在这些 Linear 上）；
- k/v 投影 out=256 < 1536，是 GQA 分组注意力设计（省 K/V 缓存），正常的。

print(model) 不只是"看看"，它是对照填参的字典。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"不同模型的模块名都一样" | Qwen 是 q_proj/v_proj；LLaMA 是 q_proj/k_proj/v_proj/o_proj（名字相近）；有的模型叫 self.query/self.key。**以 print 出来的实际名字为准**，否则 PEFT 报找不到模块 |
| 被 8960/1536 这种不对称数值吓到 | MLP 升维再降维是 Transformer 常规设计（4 倍系数：1536×4≈6144，这里 8960 是官方放大版），不是打印错乱 |
| 只看了名字没验证"挂上了" | 第 6 章 `get_peft_model` 后再 print 一次，会显示 `lora_A/lora_B` 子模块——那才是挂载成功的证明 |

@@point ⑧ 本章验收：加载成功的"三步确认"
@@need 要解决什么
环境配没配好，不是"没报错"就完事——把验收动作固定成三步，以后每台新机器都照做，10 分钟排除 90% 的环境问题。

@@idea 核心思路
三步确认清单：

| # | 动作 | 通过标准 |
|---|---|---|
| 1 | `python --version` | 3.9.x（环境内） |
| 2 | `python -c "import torch;print(torch.cuda.is_available())"` | `True` |
| 3 | 跑完上面的加载代码 | 成功 `print(model)` 出 Qwen2ForCausalLM 结构 |

三条都过 → 环境 + 模型链路 OK，下一步数据准备；任一失败 → 按前文坑位表排查。

再给一条"防呆"建议：把三步写成一个 `check_env.py` 脚本保存（环境名、torch 版本、cuda 可用性、模型名），换机器/重装后一键复验，避免"过了三天忘记怎么配的"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| "昨天能跑，今天就报错" | 最常见的：环境被污染（新 pip 装包升级了 torch）。**每次装新库前先记录 torch 版本**，出问题可回退；用 requirements.txt 锁定版本更稳 |
| 验收"全过"但训练还报显存 OOM | 加载成功 ≠ 能训练：训练还要暂存梯度与优化器状态（第 3 章）。OOM 就按第 4 节"三层解药"（量化+LoRA+小模型）降负担 |
| 换了机器后 cuda 可用性变 False | 新机器驱动/CUDA 版本不同：看 `nvidia-smi` 的 CUDA Version，重新装匹配 `cuXXX` 的 torch，工具箱脚本里记一笔"这台机器用 cuXXX" |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **一套隔离的 conda 环境** | lora_env + transformers/peft/datasets + bitsandbytes/accelerate + CUDA torch，互不污染、可复现 |
| **能加载 DeepSeek 模型的代码** | AutoTokenizer + AutoModelForCausalLM（device_map=auto / fp16），这是后续所有训练的前提 |
| **读模型架构的技能** | 28 层、q_proj/v_proj 这些名字=第 6 章 target_modules 的字典，不再靠猜 |
| **三步验收法** | python 版本 / cuda 是否可用 / 模型能否打印，换机器 10 分钟排雷 |

下一章：给"工作台"喂数据——加载 LaMini 指令数据集、看数据长什么样、拆训练/验证集、写预处理函数把"指令-回应"转成 token。

@@quiz
1. 为什么 torch 要单独用 `--index-url .../cu126` 安装，而不是直接 `pip install torch`？
2. `torch.cuda.is_available()` 返回 False，按顺序排查哪三件事？
3. `device_map="auto"` 和 `torch_dtype=torch.float16` 分别解决什么问题？
4. DeepSeek-R1-Distill-Qwen-1.5B 里 "Distill" 是什么意思？这和第二章哪个技术对应？
5. 从打印出的模型结构里，你能说出哪几个可作 LoRA target_modules 的模块名？
6. 为什么说"print(model) 不只是看看"？
7. 显存只有 4GB 想微调 1.5B 模型，按本章建议怎么降负担？（至少说三层）

@@links
参考|大模型 DeepSeek 微调与应用：配置环境与加载预训练模型|#
官网|Hugging Face 模型页：DeepSeek-R1-Distill-Qwen-1.5B|https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
官网|PyTorch 安装（CUDA 版本选择）|https://pytorch.org/get-started/locally/