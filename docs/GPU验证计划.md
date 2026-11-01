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
