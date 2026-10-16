@@h1 第八章　Unsloth 入门：把微调提速 2~5 倍
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　2 课时　|　难度 ★★

@@why 这一章在解决什么问题
手写 LoRA 教会你原理，但真跑起来它"又慢又费显存"——4GB 显存装 1.5B 模型都勉强。Unsloth 就是"LoRA 的涡轮增压"：**训练快 2~5 倍、显存省最多 70%**，代码却几乎一样（还是用你学会的 LoraConfig + SFTTrainer）。

这一章回答三件事：
1. Unsloth 到底做了什么让它这么快？（原理层：不重写、只改内核算子）
2. 装它有什么前置要求？和手写环境冲突吗？
3. 用什么模型开跑最合适？（DeepSeek-R1-1.5B 就在名单里）

学完这一章，你的工具箱里多了一把"免费的性能钥匙"。

@@map 这一章在整个知识库里的位置
前四章：手写 LoRA 全流程（原理与基线）
**本章** ← 你在这里：Unsloth 是什么、怎么装、选什么模型
下一章：Unsloth 实战——加载模型 → 准备 Alpaca 数据 → SFTTrainer 训练 → 对比手写提速
再往后：GGUF/Ollama 部署（微调产物上线）
再往后：LLaMA-Factory WebUI 一站式方案
阶段终点：既懂原理、又会工具，微调效率与产出双达标

@@point ① Unsloth 是什么：不重写模型，只改内核
@@need 要解决什么
"快 2~5 倍、省 70% 显存"听着像营销话术。它是怎么做到的？会不会改乱了模型？——这一节把 Unsloth 的工作方式讲明白，消除"黑魔法"疑虑。

@@idea 核心思路
Unsloth 的核心手段（讲义表述），一句话说就是：

**它没有改写模型结构，只替换了 PyTorch 的运行内核（kernels）与注意力实现**：

| 传统方式 | Unsloth 方式 |
|---|---|
| PyTorch 通用算子逐层计算 | 手写 CUDA 内核，融合多个算子成一次调用 |
| 标准 attention | 用 Triton 手写更优的 attention 实现 |
| 精度 fp16/bf16 直接算 | 自动处理数值溢出与精度问题 |
| 模型本身一视同仁 | 逐模型定制（llama 系、qwen 系专门优化） |

所以：
- **模型权重、结构、训练逻辑全不变**——你学的 LoRA 理论照样成立；
- 快是因为**算得少、访存少**：内核融合 + 更聪明的内存布局；
- 省显存是因为**梯度累积、检查点、分段计算等细节被优化**（结合 LoRA 只训补丁，整体显存大幅下降）。

结论：Unsloth = 同一套 LoRA 训练的"换引擎"，不是换车。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为"用了 Unsloth 就要改代码逻辑" | 接口高度兼容（第 9 章你会看到还是 LoraConfig/Trainer 那一套）。**原理不变，只是更快的引擎** |
| 担心"优化会改坏训练结果" | 训练目标是收敛到相同效果；实测准确率与标准做法相当。**追求速度同时精度不掉**，才有意义 |
| 以为它只支持特定几个模型 | 官方支持大多数主流开源模型（llama/qwen/mistral 等系列），含 DeepSeek-R1 蒸馏系列。**不在支持名单的才需要手写** |

@@point ② 系统要求：先看你的电脑够不够格
@@need 要解决什么
装任何库第一关是"我机器能不能跑"。Unsloth 对显卡、驱动、Python 版本有明确要求——先对照清单自检，避免装完报错再返工。

@@idea 核心思路
讲义系统要求（整理为清单）：

| 项目 | 要求 |
|---|---|
| 显卡 | NVIDIA GPU，**8GB 显存**以上（Q4 量化微调） |
| 驱动 | 已装 NVIDIA 驱动 + CUDA 可用 |
| Python | 3.10~3.12（讲义环境以 3.11 为例） |
| PyTorch | 2.3.0+（CUDA 版本） |
| bitsandbytes | 有它支持 QLoRA 4bit 量化微调 |

补充说明：
- 显存不够 8GB？→ 用 **QLoRA（4bit 量化 + LoRA）**，同样模型显存再降约 70%，4GB 卡也能玩转 1.5B~7B 模型；
- 纯 CPU / AMD / Mac？→ Unsloth 支持有限，本课程以 NVIDIA CUDA 为主线（讲义环境为 Colab T4 ~15GB 显存，够跑 7B 量化微调）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Windows 上 Unsloth 安装报错（Wheel 编译失败） | Unsloth 官方主要支持 Linux/WSL2/Colab，Windows 原生支持有限。**优先 WSL2（Ubuntu）或 Colab**，别在 Windows 硬磕 |
| 显存 4GB 硬跑 7B 全量 LoRA | OOM 没悬念。**Q4 量化 + LoRA** 是低显存标准姿势；或换 1.5B 等小模型 |
| Python 3.13 装不上 Unsloth 依赖 | 部分 cuda 扩展对较新 Python 支持滞后。**用 3.10~3.12**（conda 建环境最稳） |

@@point ③ 安装：pip 一行搞定
@@need 要解决什么
环境要求过关了，安装就一句话的事。但要注意：装 unsloth 必须和 torch 版本匹配，别在旧的 lora_env 里硬装导致冲突。

@@idea 核心思路
讲义安装命令（Linux/WSL2/Colab）：

```bash
pip uninstall unsloth -y          # 如果有旧版，先卸
pip install --upgrade pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

要点：
- 上面是 Colab 一键版（它自动配好配套 torch）；
- 本地 WSL2 装：`pip install unsloth` 即可，但仍需**先确认 torch 是 CUDA 版**（第 4 章验证法）；
- 验证安装：

```python
import unsloth
print(unsloth.__version__)   # 能 import 不报错 + 有版本号 = 装好
```

版本纪律：Unsloth 更新频繁，和 transformers 存在版本绑定。**升级 transformers 前先查 Unsloth 兼容性**，否则接口对不上全盘报错。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `unsloth[colab-new]` 在本地报错 | 该后缀是给 Colab 环境用的。**本地用 `pip install unsloth`**（WSL2/Linux），并配好 CUDA 版 torch |
| 升级 transformers 后 Unsloth 各种报错 | 版本绑定被打破。**固定版本组合**：先装 Unsloth，看它要求的 transformers 版本，再装对应版 |
| `import unsloth` 报内核相关错误 | 常见于 torch 是 CPU 版/CUDA 不可用（第 4 章 cuda.is_available() 先测）。修好 CUDA 再回来 |

@@point ④ 模型选择：DeepSeek-R1-1.5B 为什么是"起步标配"
@@need 要解决什么
Unsloth 支持几十个模型，选哪个跑第一遍？这一节给三条选择标准，并解释为什么课程选 **DeepSeek-R1-1.5B** 作为全程示范。

@@idea 核心思路
| 模型 | 显存需求（Q4 LoRA） | 特点 | 适合谁 |
|---|---|---|---|
| DeepSeek-R1-1.5B | ~1.8GB | 轻、快、推理风格强 | 课程示范 / 起步期 |
| Qwen2.5-7B | ~5GB | 中文强、通用 | 中文任务主力 |
| Llama-8B | ~6GB | 通用强 | 英文任务主力 |

选型三原则：
1. **显存红线**：模型量化后显存 ≤ 你卡的一大半（留给数据和梯度）；
2. **任务语言**：中文任务优先 Qwen/DeepSeek；英文任务 Llama/Mistral 也稳；
3. **先小后大**：第一遍跑通用 1.5B，确认链路后再上百亿模型——**链路不通换大模型只会放大问题**。

DeepSeek-R1-1.5B 的定位：**显存门槛最低、速度最快、推理风格适合演示对齐效果**，是"先跑通再上强度"的理想第一步。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 第一次就跑 70B 模型 | 显存评估不过关必然 OOM 或卡死。**1.5B 起步，链路通了再换 7B/14B**，按阶梯升级 |
| 只看"参数量"不看量化后显存 | **量化后显存 = 干货**。官网页/代码里 Q4 量化后显存数字比原始参数量更有参考价值 |
| 中途想换模型但懒于重配 | 换模型 = 改 model 名 + 查支持名单 + 重跑，成本并不高。**支持名单里找同系列最大能装下的**即可 |

@@point ⑤ Colab 也是好选择：免费 T4 跑起来
@@need 要解决什么
本地显卡不够格怎么办？——Colab 免费 T4（15GB 显存）直接能跑 7B 量化微调。这一节说清 Colab 路线：怎么开、怎么装、怎么传数据，适合"硬件不够但想上强度"的场景。

@@idea 核心思路
Colab 使用的要点（讲义流程）：
1. 打开 [colab.research.google.com] → 新建笔记本 → 选 T4 GPU 运行时；
2. 前三格运行讲义给出的安装代码（含 unsloth 一键装）；
3. 后续代码格按第 9 章流程走：加载模型 → 数据 → SFTTrainer → 训练；
4. 数据/结果文件用 Colab 的"上传/下载"或挂载 Google Drive 存取。

Colab + T4 的典型能力边界：

| 配置 | 可跑的极限 |
|---|---|
| T4 15GB 显存 | 7B 模型 Q4 LoRA 微调（~5GB 显存），轻松 |

注意：免费版会话约 12 小时断线、GPU 可能不等分配——**训练到一半记得手动存 checkpoint**（第 6 章 save 策略，到 Colab 依然适用）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| Colab 运行时分配不到 GPU | 免费版高峰期排队。**等几分钟重试**或"更换运行时类型"再连；实在不行用本地 WSL2 小模型 |
| 断线后训练全丢 | **本地（Drive）持续保存 checkpoint**，重新连上后 resume_from_checkpoint 续训。别把"最后一刻保存"当默认 |
| 上传数据集不支持中文大文件 | Colab 上传窗口对文件大小有限制。**大文件走 Google Drive 挂载**（drive.mount 后直接读路径） |

@@point ⑥ qwen/llama/别的：识别"同族模型"
@@need 要解决什么
DeepSeek-R1 蒸馏版其实是 Qwen 架构的"马甲"。这引出模型族（model family）概念——理解它，你就能判断"某个模型 Unsloth 支不支持"，并能套用同一套代码。

@@idea 核心思路
关键认知（讲义明确提示）：

**DeepSeek-R1-Distill-Qwen-1.5B 的架构 = Qwen 架构**（蒸馏自 R1 但骨架是 Qwen），同理 R1-Distill-Llama-8B 就是 Llama 架构。

影响：
- Unsloth 的优化按**架构族**做（"llama" 开头的优化，通吃所有 llama 架构模型）；
- 加载代码几乎一样：`FastLanguageModel.from_pretrained(模型名)`，Unsloth 自动识别架构并套对应优化；
- 你不需要为"马甲模型"单独查"是否支持"——**认架构族即可**。

"模型族"速记：

| 架构族 | 代表模型 | 中文适配 |
|---|---|---|
| Qwen 族 | Qwen2.5、R1-Distill-Qwen | 强 |
| Llama 族 | Llama3、R1-Distill-Llama | 中 |
| Mistral 族 | Mistral、Phi-3 | 中 |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| "DeepSeek-R1-1.5B 不是 Qwen 吗？为什么跟 Qwen 代码一样？" | 蒸馏模型的架构继承逼近源模型骨架。**按架构族写代码**，别认错系列名 |
| 冷门架构模型用 Unsloth 报错 | Unsloth 只优化主流架构。**冷门模型退回手写 LoRA**（第 4~7 章的能力这时候派上用场） |
| 用错了"家族"对应的代码片段 | 认准架构族名写加载/训练代码。**不确定就 print(model)** 看内部结构对号入座 |

@@point ⑦ Unsloth 与手写基线的关系：快但不是"魔法"
@@need 要解决什么
有人觉得"会用 Unsloth 就不用手写 LoRA 了"——这是误解。Unsloth 快在哪里、能替代什么、替代不了什么？把边界划清，你才知道什么时候该用工具、什么时候该回到底层。

@@idea 核心思路
对比表（Unsloth vs 手写基线，基于讲义与原理）：

| 维度 | 手写 LoRA 基线 | Unsloth |
|---|---|---|
| 训练速度 | 标准 | 快 2~5 倍 |
| 显存占用 | 标准 | 省最高 70% |
| LoRA 原理 | 完全透明 | 同样透明（接口没变） |
| 代码量 | 稍多 | 几乎相同（换 FastLanguageModel） |
| 适用模型 | 任意 | 主流架构 |
| 教学价值 | **理解本质** | 生产效率 |

结论：**Unsloth 优化的是性能层，不是理论层**。如果第 6~7 章你理解了什么在训练，Unsloth 只是让它跑得更快；如果直接上来用 Unsloth，遇到报错你连"它在优化哪里"都不知道。

先手写、后工具——这就是课程的顺序逻辑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| "我直接用 Unsloth 不学原理了" | 调参、排错、换模型全靠原理兜底。**原理是根，工具是叶**；根不稳叶子先黄 |
| 以为 Unsloth 一定是"最优解" | 冷门模型、特殊任务可能需要手写。**工具选择看场景**，Unsloth 是加速选项不是唯一选项 |
| 对比测试时不服"2~5 倍" | 提速与模型、显卡、batch 相关。**教程基准 = 相同硬件下同一模型对比**；自己机器实测为准 |

@@point ⑧ 本章验收：环境就绪清单
@@need 要解决什么
下一章要开跑，先把环境验收做扎实："import 成功"不等于"能训练"。本章验收几件事，确保第 9 章一上来就是干活的节奏。

@@idea 核心思路
验收清单（逐项打勾）：

| # | 检查项 | 通过标准 |
|---|---|---|
| 1 | 显卡就绪 | `torch.cuda.is_available()` → True |
| 2 | 显存达标 | `torch.cuda.get_device_name()` 确认 NVIDIA；显存 ≥8GB（低配用 Q4） |
| 3 | Unsloth 可导入 | `import unsloth` 无报错，有版本号 |
| 4 | 模型可加载 | `FastLanguageModel.from_pretrained("unsloth/DeepSeek-R1-Distill-Qwen-1.5B")` 能加载（第 9 章会细讲，这里先试装） |
| 5 | 环境独立 | 新的 conda 环境，不污染手写 LoRA 环境 |

环境管理建议：手写环境 `lora_env`、工具环境 `unsloth_env` 分开（conda 两套），避免 torch 版本冲突毁掉已跑通的链路。

全过 → 第 9 章直接进入加载模型与训练参数，一条路跑到训练完成。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `import unsloth` 成功但仍无法训练（报内核缺失） | import 只验证包存在，CUDA 内核编译/加载另有报错。**按 error 栈找对应 CUDA 环节**，用第 9 章训练代码做终验 |
| 手写环境里 pip 装 unsloth 把 torch 升版本 | 依赖冲突把已验证链路弄坏。**独立环境 + requirements.txt 锁定版本**，是环境管理的基本功 |
| "验证模型能加载"这一步就报显存不够 | 模型名换更小的（如 0.5B）或走 Q4 量化加载。**别跳过验证直接冲训练**——第 9 章同样会炸 |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **Unsloth 原理** | 只换内核不换模型，速度/显存收益的机制清楚了 |
| **环境前置清单** | 显卡/驱动/Python/torch 要求逐项可自查 |
| **安装方法** | 一行 pip + 版本纪律，Colab 与本地两条路线 |
| **选型眼光** | 按显存红线/任务语言/先小后大选模型，认架构族 |

下一章上手实操：FastLanguageModel 加载、Alpaca 数据集、SFTTrainer 一键训练，与手写基线对比"快了多少钱"。

@@quiz
1. Unsloth 加速的核心机制是什么？（一句话）
2. Windows 原生装 Unsloth 常遇什么问题？推荐的替代环境是什么？
3. 选微调模型的三原则是什么？
4. DeepSeek-R1-Distill-Qwen-1.5B 属于哪个架构族？判断依据是什么？
5. 为什么说"先手写 LoRA、再用 Unsloth"？换个模型遇到报错，谁兜底？
6. Colab 免费版的两个典型限制是什么？对应解法？
7. 本章验收清单里最关键的显存相关检查是什么？

@@links
讲义|大模型 DeepSeek 微调与应用：Unsloth 介绍与系统要求、模型选择、Colab 使用|#
官网|Unsloth 官方仓库（模型支持名单）|https://github.com/unslothai/unsloth
官网|Colab 免费版说明|https://colab.research.google.com/signup