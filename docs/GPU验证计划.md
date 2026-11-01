# GPU / torch 验证计划

> 现状：全书 238 章，**25 章真跑过**（见 `docs/代码验证清单.md`），剩下 213 章只有静态判定。
> 卡点不是「不想跑」，是**本机装不上 torch**：
>
> ```
> PermissionError: [WinError 5] 拒绝访问
> Error loading "torch\lib\torch_python.dll"
> ```
>
> 这条从 2026-10-31 起就存在。下面按「由便宜到贵」列三条路。

## 需要 GPU/torch 的章有多少

| 阶段 | 章数 | 依赖 |
|---|---|---|
| 阶段 12 · 大模型微调（LoRA / Unsloth / LLaMA-Factory） | 12 | torch + transformers + peft，微调还需要 ≥16G 显存 |
| 阶段 21 · PyTorch 深度学习 | 15 | **只要 torch（CPU 版就够）** |
| 阶段 23 · 模型压缩（剪枝/量化/蒸馏） | 9 | torch；量化部分最好有 GPU |
| 阶段 24 · vLLM 推理服务 | 5 | 要真 GPU（CUDA）+ vLLM |
| **合计** | **41** | 其中**只有 5 章真的需要 GPU**，其余 torch CPU 就行 |

> 全书提到 `torch` 的章共 35 个 —— 也就是说**32 章的卡点是「torch 装不上」，不是「没显卡」**。

## 路径一：先花 10 分钟试本地修（免费）

Windows 上 torch DLL 加载失败最常见的原因是**缺 VC++ 运行库**或被杀软拦。

1. 装 [Microsoft Visual C++ Redistributable 2015-2022 x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. 重开终端，试：
   ```powershell
   python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
   ```
3. 还报 WinError 5 → 把 Python 目录加进杀软白名单再试

**成功的话：15 章 PyTorch + 9 章模型压缩的 CPU 部分立刻能跑，一分钱不花。**

## 路径二：云 GPU（按小时租，跑完就关）

书里本来就教了 **AutoDL** 和 **ModelScope**，用它们验证最一致。

| 平台 | 适合 | 说明 |
|---|---|---|
| **AutoDL** | 最省事，镜像自带 torch | 按小时计费，有 RTX 4090 / A5000 档；`docs` 里阶段 19 有完整开机器流程 |
| **阿里云 PAI-DSW** | 有免费试用额度 | 与书里阶段 19 同一套控制台 |
| **ModelScope 创空间 / Notebook** | 有免费额度 | 显存 16G/24G 两档，额度会调整 |
| Google Colab / Kaggle | 免费 T4/P100 | 要能访问 Google；适合跑「纯验证」不跑长训练 |

⚠️ **价格/额度每季度都变，一律以官网当前页为准**（这也是本书正文的口径）。

**建议租用规格**：
- 只跑 torch（阶段 21/23 大部分）：**CPU 实例就够**，便宜得多
- 跑 LoRA 微调（阶段 12）：**≥16G 显存**（7B + 4bit 才勉强）
- 跑 vLLM（阶段 24）：**≥24G 显存**

**预计耗时**：装环境 20 分钟 + 41 章跑一遍 1–2 小时。按小时租，跑完立刻关机。

## 路径三：借一台有 N 卡的机器（最彻底）

如果有游戏本/实验室机器，能把 Docker、Spark、CUDA 全部一次补齐。

---

## 上机后怎么跑（三条命令）

仓库里已经准备好批量脚本 `tools/run_gpu_batch.py`：

```bash
git clone <仓库> && cd ai-agent-roadmap
pip install torch transformers peft            # CPU 版即可；GPU 机器按官网命令装
python tools/run_gpu_batch.py --json gpu.json   # 自动挑「提到 torch」的 35 章来跑
```

只跑某阶段：

```bash
python tools/run_gpu_batch.py --stage 21
```

输出长这样：

```
[ 1/35] 阶段 21    09-第九章-nnModule模型构建与前向传播.md    OK (通过6 报错0 跳过0)
[ 2/35] 阶段 21    10-第十章-损失函数.md                    ERR (通过2 报错1 跳过0)
       块3  [ERR] RuntimeError: ...
```

**跑完要做的三件事**：

1. 有报错的章：按报错修正文（这轮就是为了找这些）
2. 修完更新 `docs/代码验证清单.md`（章数、块数、通过数）
3. 同步 `docs/维护手册.md` 第 8 节的边界数字

## 一句话

**别一上来就租贵卡**：先花 10 分钟装 VC++ 运行库，大概率 32 章就解锁了；
真的只剩微调和 vLLM 那 17 章时，再按小时租一张 24G 卡，两小时能收工。

## 附：12 章微调的租卡清单（只在真跑微调时才用）

阶段 12 是唯一「必须真 GPU + 真模型」的一块。2026-11-01 那次实跑只验证到「语法与依赖边界」——
因为本机没装 `peft` / `unsloth` / `llamafactory`，也没下模型和数据集。下面是把它们跑通要准备的东西。

### 各章要什么

| 章 | 干什么 | 需要的模型 | 需要的文件 | 显存 |
|---|---|---|---|---|
| 12-01 微调全景 | 概念 | 无 | 无 | 0 |
| 12-02 三大技术对比 | 概念 | 无 | 无 | 0 |
| 12-03 LoRA 原理 | 概念 + 公式 | 无 | 无 | 0 |
| 12-04 环境与模型加载 | 下载底座 | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`（约 3GB） | — | 加载约 4GB |
| 12-05 数据准备 | 构造指令数据 | 同上（分词器） | 自己造的 json | <1GB |
| 12-06 训练与保存 | 真训练 | 同上 | 12-05 的数据 | **≥8GB**（1.5B + LoRA，fp16） |
| 12-07 测试/合并/上传 | 合并权重 | 同上 | `./lora_model`（12-06 产物） | ≥8GB（合并时翻倍） |
| 12-08 Unsloth 入门 | 装库 + 概念 | 无 | 无 | 0 |
| 12-09 Unsloth 实战 | 真训练 | `unsloth/DeepSeek-R1-Distill-Qwen-1.5B` | 12-05 的数据 | **≥10GB**（4bit + 梯度检查点也吃显存） |
| 12-10 GGUF/Ollama | 转格式 + 本地跑 | 12-09 的 adapter | `resp.json` | 转 GGUF 要 CPU 内存 ≥16GB |
| 12-11 LLaMA-Factory | 框架训练 | `Qwen2.5-7B`（约 15GB） | `data/chinese_medical.json` | **≥24GB**（7B 全参不行，只能 LoRA 4bit） |
| 12-12 WebUI | 配置 + 监控 | 同上 | `dataset_info.json` | 至少 16GB |

### 装什么

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121   # 按机器 CUDA 版本选
pip install transformers peft accelerate datasets
pip install unsloth                                                    # 只有 12-08/09/10 需要
pip install llamafactory                                               # 只有 12-11/12 需要（Python ≥3.11）
```

### 下什么

```bash
# 1.5B 底座（12-04/06/07/09 共用，约 3GB）
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --local-dir ./models/r1-1.5b
# 或走 ModelScope（国内快）：
modelscope download --model deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B --local_dir ./models/r1-1.5b
```

### 建议的租卡策略

| 目标 | 卡 | 预计耗时 |
|---|---|---|
| 只跑 12-04 ~ 12-07（1.5B LoRA） | **RTX 4090 24G**（或 A5000） | 装环境 30 分钟 + 训练 10~20 分钟 |
| 加上 12-09（Unsloth） | 同上 | +20 分钟 |
| 加上 12-11/12（7B） | **A100 40G 或 2×4090** | +1 小时（含下 15GB 模型） |

**按小时租的话，1.5B 那 4 章两小时内能收工**；7B 那两章建议单独一次跑。

> 价格、显卡型号、免费额度都随平台调整，**以官网当前页为准**。

### 跑完怎么回填

```bash
python tools/run_gpu_batch.py --stage 12 --json gpu12.json
```

有报错就贴出来，我按报错修正文；全通过就把 `docs/代码验证清单.md` 里阶段 12 那几行从「静态判定」改成「已实跑」。
