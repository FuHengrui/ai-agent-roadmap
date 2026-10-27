@@h1 第九章　Unsloth 实战：加载模型、数据与训练
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　|　难度 ★★★

@@why 这一章在解决什么问题
环境就绪了，现在真刀真枪：用 Unsloth 完整跑一遍 DeepSeek-R1-1.5B 的 LoRA 微调——加载模型、配 LoRA 参数、准备 Alpaca 数据、SFTTrainer 训练、和手写基线对比。

为什么值得学？因为这一章你**亲手把"快 2~5 倍、省 70% 显存"验证一遍**，而且代码量比手写更少——感受工具化改造流程的威力。同时你会见到手写线性里没有的一招：**unsloth 式 LoraConfig（r=16，target_modules='all-linear'）**。

学完这一章，你就有两个可复用的套路：手写版（懂原理）与 Unsloth 版（重效率），按需选用。

@@map 这一章在整个知识库里的位置
上一章：Unsloth 环境就绪、选型原则
**本章** ← 你在这里：FastLanguageModel 加载+4bit → Unsloth LoraConfig → Alpaca 数据 → SFTTrainer 训练 → 对比
下一章：把微调产物转 GGUF、用 Ollama 轻量部署（本章 merge 后导出）
再往后：LLaMA-Factory WebUI 微调（一站式终点）
阶段终点：手写 + Unsloth + 部署三条线全部打通

@@point ① FastLanguageModel：Unsloth 的加载入口
@@need 要解决什么
手写时用 AutoModelForCausalLM 加载，Unsloth 用 FastLanguageModel——它比 Auto 版多做了什么事？加载时 4bit 量化、max_seq_length 怎么设？

@@idea 核心思路
示例代码（整理为可运行版）：

```python
from unsloth import FastLanguageModel
import torch

max_seq_length = 2048   # 输入输出最大长度（token 数）

# 加载模型 + 自动套用 Unsloth 优化内核，并做 4bit 量化
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/DeepSeek-R1-Distill-Qwen-1.5B",
    max_seq_length=max_seq_length,
    dtype=None,              # None=自动选择（fp16/bf16）
    load_in_4bit=True,       # 4bit 量化：显存降到约 1.8GB
)
```

与 Auto 加载的差异：

| 维度 | AutoModelForCausalLM | FastLanguageModel |
|---|---|---|
| 内核 | 标准 PyTorch | Unsloth 优化（第 8 章原理） |
| 量化 | 需另配 bitsandbytes | `load_in_4bit=True` 一步到位 |
| max_seq_length | 默认模型内定 | 显式参数，配合 RoPE 缩放 |
| 显存 | 标准 | 量化 + 内核优化，整体大幅下降 |

`max_seq_length=2048` 的含义：**训练时最长输入+输出合起来的 token 数**。超长的样本会被截断。按你的数据最长长度设，设太大费显存、太小截断丢信息。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `model_name` 填错/找不到 | 检查是否带 `unsloth/` 前缀、名字是否拼对；网络问题用 HF 镜像（第 10 章更多）。**先试官方给的 unsloth/ 镜像名**，它已处理好格式 |
| max_seq_length 设 8192 显存爆 | 长度直接决定显存（注意力与长度平方相关）。**先 2048 跑通**，再按需加大 |
| load_in_4bit=True 报 bitsandbytes 错误 | 缺库或环境不支持。`pip install bitsandbytes`；Windows 原生请回第 8 章换 WSL2/Colab |

@@point ② Unsloth 的 LoraConfig：target_modules 全线性
@@need 要解决什么
手写时 target_modules 只挂 q_proj/v_proj。Unsloth 加载后，用了一套"更狠"的配置：**r=16 且 target_modules='all-linear'**——什么意思？为什么这样反而更省显存？

@@idea 核心思路
示例代码（整理为可运行版）：

```python
from peft import LoraConfig

model = FastLanguageModel.get_peft_model(
    model,
    r=16,                        # 秩：比手写 8 翻倍，补丁更有容量
    target_modules=["q_proj","k_proj","v_proj","o_proj",
                    "gate_proj","up_proj","down_proj"],
    # ↑ 即 'all-linear'：所有线性层全挂
    lora_alpha=16,
    lora_dropout=0,              # Unsloth 建议：dropout 设为 0
    bias="none",
    use_gradient_checkpointing="unsloth",  # 高级显存省法
    random_state=3407,           # 复现种子
)
```

对比要点：
- **'all-linear'（=把所有线性层列全）**：全部线性层都挂 LoRA = 补丁覆盖面大、自由度更高。看起来显存该更大？——不，量化+梯度检查点把省下来的显存补回来了，反而**总占用略低于只挂 q/v 的手写方案**；
- `lora_alpha=16`：α=r，强度=1（不放大也不缩小），配 r=16 常用；
- `lora_dropout=0`：Unsloth 官方建议 **dropout=0**——量化环境下 dropout 收益低还增加开销；
- `random_state`：固定种子，保证"换模型/换参数"对比时结果可复现。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 'all-linear' 报错（很老版本的 PEFT 不认识） | 该字符串是 PEFT 新特性。**升级 peft** 或升级代码里把 7 个模块名写全（也给了展开写法） |
| 担心"全线性层都挂 = 显存爆炸" | 实测结论：结合 4bit + 梯度检查点，**总显存并不上升**——这正是 Unsloth 省显存的表现，别凭直觉放弃 |
| dropout=0 心里发虚 | 官方文档也这么建议；过拟合用"早停/数据集质量"管，别在 Unsloth 场景硬加 dropout。**跟随官方推荐**再谈自定义 |

@@point ③ 数据集格式：Alpaca 长这样
@@need 要解决什么
第 5 章手写版用了 LaMini 数据，这一章出现新面孔：**Alpaca 格式**（instruction/input/output 三字段）。它长什么样、怎么构造对话/提示模板、和手写版有什么区别？

@@idea 核心思路
Alpaca 数据三条记录示例：

```python
example = {
    "instruction": "请解释什么是机器学习",
    "input": "",
    "output": "机器学习是让计算机从数据中自动学习规律……"
}
```

- `instruction`：指令（必填）；
- `input`：额外上下文，可为空字符串（很多库里是可选）；
- `output`：期望回答（监督标签）。

Alpaca 与 LaMini 的异同：
- 都是"指令-回答"监督对——**本质一样**；
- Alpaca 显式区分 instruction/input 两字段；LaMini 常直接给整句 QA；
- 训练时把 instruction(+input) 拼成 prompt（系统+用户），output 是标签——**模板和训练一致**这条纪律不变（第 5 章 trap 依然有效）。

构造 prompt 时注意：**DeepSeek-R1 系模型带特殊系统提示**（让模型先想再答），需要用数据集的模板原样拼接，否则训练风格错乱。具体模板字符串以模型卡为准。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 数据只有两列（Q/A），套 Alpaca 报错 | Alpaca 结构要求三字段。**两列数据改成 LaMini/ShareGPT 路线**（第 11 章有 ShareGPT），别硬套模板 |
| input 字段全填了长文本，token 超长 | input 是"附加上下文"，别把整篇资料塞进去。**短 input（或不填）**，长文档走 RAG 路线 |
| 拼接 prompt 时漏掉系统提示 | R1 系模型没系统提示会"答非所问/风格漂移"。**用模型卡的 System Prompt 模板**拼接（代码里有现成常量） |

@@point ④ 复制 5 条数据做起跑：小数据先验证链路
@@need 要解决什么
上来就全量数据训练，错一个 bug 要等一小时。正确姿势：**先取几十条数据跑通全链路**，再放开全量。这一节讲这招和它的判断标准。

@@idea 核心思路
做法（整理）：

```python
# 数据集已有 dataset["train"] 后，先小样跑通
dataset_tiny = dataset["train"].select(range(50))

# 同一套 Trainer 配置去训练
trainer = SFTTrainer(... )  # 见下一节
trainer.train()
```

小样验证三件事：
1. **数据管道通**：字段名、模板拼接、length 设置没报错；
2. **训练能收敛**：小样本下 loss 快速下降，说明优化器/学习率没配错；
3. **生成能产出**：训完用第 7 章的 generate 法问问它，能看到"有点样子"。

通过后再全量训：把 `select(range(50))` 换回完整数据集，其余代码原样重跑。**小样跑通 = 全量 90% 安全**，这 10 分钟值得花。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 小样跑通就放开全量，结果全量报 OOM | 全量数据更长/更多，batch 撑爆。**全量首次用更小 batch 起步**，平稳后再上调 |
| 小样 50 条训 1 轮看不出收敛 | 样本太少 loss 波动大正常。**先看"能生成有意义的回复"**，别指望小样本 loss 平滑 |
| 小样能跑但一换数据就报错 | 换的是脏数据（空行/超长/字段缺失）。**加数据清洗**（第 5 章 filter/length 检查）再全量 |

@@point ⑤ SFTTrainer：一键训练 + 学习率/批次
@@need 要解决什么
数据准备好了，Unsloth 版的训练器叫 **SFTTrainer**（trl 库），比手写 Trainer 更省事——数据集格式、长度截断、模板拼接它大半自动处理。这一节把训练参数配置讲清楚。

@@idea 核心思路
典型配置（整理为可运行版）：

```python
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,       # 已按模板拼好 prompt 的数据
    dataset_text_field="text",         # 告诉它哪个字段是"拼接后文本"
    max_seq_length=max_seq_length,     # 自动截断
    dataset_num_proc=2,                # 多进程预处理
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,                # 学习率预热
        num_train_epochs=1,
        learning_rate=2e-4,
        logging_steps=1,               # 每步打日志
        optim="adamw_8bit",            # 8bit 优化器：省显存
        seed=3407,
        output_dir="outputs",
    ),
)
trainer.train()
```

几个关键参数人话翻译：
- `dataset_text_field="text"`：数据预处理时把 instruction/input/output 拼成 `text` 列，SFTTrainer 按它训练（**不用再手写 preprocess 函数**——这是比手写版省事的地方）；
- `optim="adamw_8bit"`：8bit 优化器降显存（需要 bitsandbytes）；
- `warmup_steps=5`：前 5 步学习率从小升到大，训练更稳。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了拼 text 列，报 "no text field" | SFTTrainer 要整条文本。**预处理时把三字段拼成 text**（含系统提示模板），再喂数据集 |
| optim adamw_8bit 报 bitsandbytes 缺失 | `pip install bitsandbytes`；或换 `optim="adamw_torch"`（显存略升但能跑） |
| logging_steps=1 日志刷屏 | 训练轮数多时每 step 都打。**改 10~50**，观测平滑曲线即可 |

@@point ⑥ 训练过程观察：loss 怎么看、中途怎么停
@@need 要解决什么
训练真的开跑了：进度条、loss 数字、每步日志。这一节教你看懂这些输出：loss 降到多少算正常？中途想停怎么安全停？日志里哪些信号是"坏了"？

@@idea 核心思路
训练开始的输出长这样：

```
{'loss': 2.83, 'learning_rate': ..., 'epoch': 0.0}
{'loss': 1.96, 'learning_rate': ..., 'epoch': 0.0}
{'loss': 1.55, ...}
```

判读规则：
- **loss 应逐 step 下降**，前几十步降得快（学习率预热+拟合开始），随后放缓；
- 最终 loss 落在数据集语言混乱度的合理范围（参考：指令数据常见 0.5~2.5，取决于数据量/长度）；
- **epoch 数值从 0 涨到 1** = 训练完一轮。

中途停的三种方式：
| 方式 | 适用 |
|---|---|
| Ctrl+C（前台） | 想立即停，检查点已按 save_strategy 存好 |
| 等 step 结束停 | 加 `KeyboardInterrupt`/脚本里手动 break 逻辑 |
| 提前结束 | 调 `num_train_epochs` 低于当前轮次 + resume |

注意：**显存/磁盘满**比"loss 不降"更常见也更危险——边跑边看磁盘余量，别让 checkpoint 写爆盘。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| loss 先降后回升 | 学习率冲到最优点之后震荡。**降学习率/加 warmup**；回升持续 = 过拟合，配合 eval 判断 |
| loss 从第 1 步就是 NaN | 学习率爆表 / 数据有空样本 / 精度问题。**学习率降到 1e-5 试**，再查数据 |
| 磁盘被 checkpoint 写满 | 每 epoch 存一份很快爆盘。**调大 save_steps 或清理旧 checkpoint**，保存策略要按磁盘量配 |

@@point ⑦ 训练完保存 & 对比：把提速"实锤"下来
@@need 要解决什么
验证 Unsloth 价值最硬的方式：同硬件、同数据，分别跑手写版和 Unsloth 版，记录**时间与显存**两点。这一节给出对比方法和保存产物的要求。

@@idea 核心思路
对比实验设计：

| 维度 | 手写基线 | Unsloth |
|---|---|---|
| 同样数据量 | LaMini 取 500 条 | 同 500 条 |
| 训练时间 | 记录 wall time | 记录 wall time |
| 峰值显存 | nvidia-smi 抓 | nvidia-smi 抓 |
| loss 走势 | 记录 | 记录 |

记录方式：
```python
import time
t0 = time.time()
trainer.train()
print("训练耗时:", time.time() - t0)  # 秒
```
显存：训练中另开终端 `watch -n 1 nvidia-smi`（Linux/WSL2）抓峰值。

保存产物（和手写版同样的姿势）：

```python
model.save_pretrained("lora_model_uns")
tokenizer.save_pretrained("lora_model_uns")
```

经验值参考：同样 1.5B、同样数据，Unsloth 通常比手写快 2~5 倍、显存低 30~70%（4bit 功不可没）。**以你本机实测为准**，数字进你的笔记。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 对比时手写版没开 4bit、Unsloth 开了 | 不公平：量化本身省显存。**要么两边都 4bit 要么都 fp16**，控制变量 |
| 对比只看时间不看 loss 质量 | 快 ≠ 好。**比对 loss 终值与生成效果**，都达标才算"同样结果，更快" |
| 忘记记录显存峰值 | 事后无法补测。**先记录再做其他事**；两张图（时间/显存）一起进笔记最完整 |

@@point ⑧ 本章验收：Unsloth 链路完成
@@need 要解决什么
收尾验收：Unsloth 微调闭环三件套——训练跑通、产物保存、对比数据落袋。全过，工具线的主干就通了，下一章直奔部署。

@@idea 核心思路
验收清单：

| # | 检查项 | 标准 |
|---|---|---|
| 1 | 训练完成 | loss 有下降趋势，epoch 跑满（或预设轮数） |
| 2 | 产物保存 | `lora_model_uns/` 含 adapter_config + adapter_model.safetensors |
| 3 | 对比数据落袋 | 训练耗时 + 峰值显存已记录（和手写版对照） |
| 4 | 快速生成验证 | 用第 7 章 generate 法（装回 FastLanguageModel 推理模式）对 1~2 个问题出结果 |
| 5 | 环境不污染 | 手写环境 lora_env 未受影响（原训练脚本还能跑） |

补充：Unsloth 推理时也有加速姿势（`FastLanguageModel.for_inference(model)` + 输入转同 device），比普通 generate 提速，第 10 章导出前可顺手用。

全过 = 工具化微调通路建成。下一章把产物合并且导出 GGUF，交给 Ollama 做推理部署——"训完就能跑"的最后一公里。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 训练完忘保存又开新会话 | 环境销毁权重就没了。**训练一结束立刻 save**（两次 Ctrl 都救不回没落盘的权重） |
| dev 机试跑后没写笔记，隔周忘参数 | 参数/结果不记 = 白跑。**实验记录模板**（数据量/模型/r/时长/显存/loss/生成样例）固定下来 |
| 对比时把"快"归因于 4bit 就够 | Unsloth 内核优化也贡献显著。**想分清就再加一组"手写+4bit"对照**——有精力再补，没精力就记住"这套组合整体收益" |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **Unsloth 加载组合拳** | FastLanguageModel + 4bit + max_seq_length，显存骤降 |
| **新一代 LoraConfig 玩法** | all-linear、r=16、dropout=0、gradient checkpointing 的取舍 |
| **Alpaca 数据 + SFTTrainer** | 数据模板拼接、text 字段、免手写 preprocess 的一键训练 |
| **实打实的提速证据** | 时间/显存/效果三对比，你亲手验证了"快 2~5 倍" |

下一章：把 LoRA 产物 merge 成完整模型 → 导出 GGUF → Ollama 本地跑起来——阶段 12 的"部署线"启动。

@@quiz
1. FastLanguageModel.from_pretrained 相比 Auto 版多了哪两个关键能力（参数层面）？
2. 'all-linear' 的含义是什么？为什么这套配置总显存反而低？
3. Alpaca 格式的三个字段是什么？和 LaMini 的本质区别是什么？
4. 为什么建议先取 50 条数据跑通全链路？
5. SFTTrainer 里 dataset_text_field 的作用是什么？少了它会怎样？
6. 训练时 loss 先降后回升，最可能的两个原因和对应解法？
7. 对比 Unsloth 与手写基线时，必须控制的两个变量是什么？

@@links
参考|大模型 DeepSeek 微调与应用：Unsloth 加载模型与训练、数据集准备、保存与对比|#
官网|Unsloth 官方教程（1.5B 起步）|https://github.com/unslothai/unsloth
官网|TRL SFTTrainer 文档|https://huggingface.co/docs/trl/main/en/sft_trainer