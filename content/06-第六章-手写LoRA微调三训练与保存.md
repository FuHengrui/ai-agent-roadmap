@@h1 第六章　手写 LoRA 微调（三）：训练与保存
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　难度 ★★★

@@why 这一章在解决什么问题
模型工作台和数据都备好了，现在要**点火**：把 LoRA 挂到模型上、配好训练超参、跑起 Trainer、把训练好的权重保存下来。这一章是全流程的高潮，也是报错高发区——`get_peft_model` 报找不到模块、训练显存爆炸、loss 不下降、保存完不知道存了啥，每个坑都能卡你一整天。

学完这一章，你会得到两个可复用的关键产物：**挂好 LoRA 的可训练模型** + **训练结束后保存下来的 LoRA 权重目录**（几十到几百 MB，而不是几个 GB 的完整模型——这正是 LoRA 的意义）。

@@prep 开始之前
第 5 章的数据集 token 化完成就能开始：除了显卡，只用再 `pip install tensorboard`（看训练曲线用，不是 transformers 自带的）；其余不用装。

@@goal 学到这儿就够了
能挂上 LoRA、配好超参跑完训练并保存出几十 MB 的权重，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章（手写 LoRA 二）：数据准备完成——train/eval 数据集已 token 化、验收通过
**本章** ← 你在这里：LoraConfig + get_peft_model 挂载 → TrainingArguments 配参 → Trainer.train() → 保存 LoRA 权重
下一章：手写 LoRA（四）测试微调效果、合并权重、上传 Hugging Face——交付闭环
再往后：Unsloth 提速 → GGUF/Ollama 部署 → LLaMA-Factory WebUI
阶段终点：你能独立完成"环境→数据→训练→部署"微调全链路

@@point ① 配置 LoRA：LoraConfig 的每个参数
@@need 要解决什么
第 3 章讲过 r / α / target_modules 原理，现在要看它们在代码里长什么样。`LoraConfig` 每个字段管什么、怎么填？照抄会错在哪？——这一节把配置和原理对上号。

@@idea 核心思路
示例代码（整理为可运行版）：

```python
from peft import LoraConfig, TaskType

lora_config = LoraConfig(
    r=8,                      # 低秩矩阵的秩：补丁宽度
    lora_alpha=32,            # 缩放因子：补丁强度（实际强度 ≈ α/r = 4）
    target_modules=["q_proj", "v_proj"],  # 挂载哪些层（见第4章架构图）
    lora_dropout=0.1,         # 补丁随机失活，防过拟合
    bias="none",              # 不动偏置，最省
    task_type=TaskType.CAUSAL_LM,  # 因果语言模型任务
)
```

参数速记表：

| 参数 | 作用 | 常用值 |
|---|---|---|
| r | 秩：A(d×r)、B(r×k) 的宽度 | 8/16/32 |
| lora_alpha | 强度缩放，看 α/r 这个比值 | 常见 1~4×r；示例 r=8、α=32 即 4×r |
| target_modules | 挂在哪 | `["q_proj","v_proj"]` 起步 |
| lora_dropout | 防过拟合 | 0.05~0.1 |
| bias | 是否训偏置 | "none" |
| task_type | 任务类型 | CAUSAL_LM |

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `get_peft_model` 报 "module q_proj not found" | 模块名和模型架构对不上（比如模型叫 self.query）。**先 print(model) 看真实模块名**（第 4 章），再填 target_modules |
| 忘记显式 `lora_alpha`，效果弱到看不见 | PEFT 的 `lora_alpha` 默认是 **8**，和 r 无关——r=16 时默认强度只有 0.5。**始终显式配 α**（如 4×r），变化才可观 |
| dropout 设 0.5 这种离谱值 | dropout 太高会把补丁学信号丢掉，训练半天不收敛。0.05~0.1 之间试 |

@@point ② 挂载 LoRA：prepare + get_peft_model
@@need 要解决什么
配置写好了，还差两步"接入"：如果是量化模型，要先 `prepare_model_for_kbit_training` 做准备；然后 `get_peft_model` 真正把 LoRA 补丁挂上去。挂完怎么确认"挂上了"？

@@idea 核心思路
示例代码：

```python
from peft import get_peft_model, prepare_model_for_kbit_training

# 量化模型训练前的准备（4bit/8bit 加载时必调）
model = prepare_model_for_kbit_training(model)
# 把 LoRA 配置应用到模型上
peft_model = get_peft_model(model, lora_config)
print(peft_model)   # ← 关键验证：输出里应出现 lora_A / lora_B
```

为什么量化后要 prepare：`prepare_model_for_kbit_training` 做的是**把底座参数全部冻结**、把 LayerNorm 等敏感层转回 fp32、并开启 gradient checkpointing——真正“可训练”的是随后挂上去的 LoRA 补丁。不做这步，量化模型上训练可能完全不动或报错。

验证"挂上了"的方法：再次 print 模型，注意力层里能看到：

```
(q_proj): lora.Linear(...)
    (lora_dropout): ...
    (lora_A): Linear(1536, 8)   ← 补丁来了
    (lora_B): Linear(8, 1536)
```

只要看到 lora_A/lora_B，就说明这个层挂载成功——你没挂的层（如 gate_proj）不会出现这个结构。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了 prepare_model_for_kbit_training，量化模型训练报错/不动 | 4bit 加载 + 训练的组合必须 prepare；**非量化（fp16 / bf16 加载，本来就是半精度）时这步可省**，环境里默认都装了 bitsandbytes，加了最稳 |
| 看不到 lora_A/lora_B 就开训 | 先 debug：检查 get_peft_model 是否成功、print 是否显示 PEFT 结构。**没挂上就训练 = 训了个原模型**，白烧电 |
| 以为"挂 LoRA 后再打印的模型还是原来那坨" | 挂载后模型结构会多出 lora_* 子层、参数统计变化。看到多出的部分才是挂成功的标志 |

@@point ③ TrainingArguments：训练超参每个字段
@@need 要解决什么
训练是门"玄学调参"？其实每个超参都有明确职责。这节把 TrainingArguments 逐行翻译成人话，并标出显存/效果/速度三维取舍——之后你就能自己改参数，而不是只会抄。

@@idea 核心思路
训练参数（整理为可运行版）：

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    output_dir="./results",          # 日志/检查点输出目录
    num_train_epochs=3,              # 训练轮数
    learning_rate=2e-4,              # 学习率
    per_device_train_batch_size=4,   # 每卡训练批次
    per_device_eval_batch_size=4,    # 每卡验证批次
    gradient_accumulation_steps=2,   # 梯度累积：等效 batch 翻倍
    weight_decay=0.01,               # 权重衰减防过拟合
    evaluation_strategy="epoch",     # 每个 epoch 结束评估一次
    save_strategy="epoch",           # 每个 epoch 保存一次
    load_best_model_at_end=True,     # 训练结束自动加载最佳模型
    push_to_hub=False,               # 训练完不自动传 HF
    report_to=["tensorboard"],       # 训练日志记录到 tensorboard
    logging_dir="./logs",            # 日志目录
    label_names=["labels"],          # 告诉 Trainer 标签字段名
)
```

三维速记：
- **显存不够** → 减小 batch_size + 加大 gradient_accumulation_steps（等效 batch 不变，显存降）；
- **epoch 卡死/过拟合** → 看验证 loss，早停或降学习率；
- **训练太久** → 加大 batch（显存允许时）、减少 epoch。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 显存 OOM 还硬扛 batch=4 | 降 `per_device_train_batch_size=2` 或 1，同时 `gradient_accumulation_steps` 翻倍到 4，等效 batch 不变、显存掉一半 |
| 忘了 `label_names=["labels"]`，Trainer 找标签报错 | 自定义字段名时 Trainer 会猜错。**显式声明标签字段**，报错秒消 |
| `evaluation_strategy` 参数名版本不同报错 | 新版 transformers 建议用 `eval_strategy`（evaluation_strategy 兼容保留但警告）。看本地版本文档，用哪个都行但要一致 |

@@point ④ Trainer：把一切都连起来
@@need 要解决什么
模型、数据、超参都齐了，Trainer 就是把它们组装起来的"总机房"——传模型、训练参数、数据集、分词器，一行 train() 开跑。这一节看清 Trainer 的接线图。

@@idea 核心思路
示例代码：

```python
from transformers import Trainer

trainer = Trainer(
    model=peft_model,        # 挂好 LoRA 的模型
    args=training_args,      # 超参
    train_dataset=train_dataset,  # 训练集（第5章产物）
    eval_dataset=eval_dataset,    # 验证集
    tokenizer=tokenizer,     # 分词器
)
# 开始训练
trainer.train()              # ← 点火
```

Trainer 内部替你干了全套脏活：自动批处理、梯度累积、评估触发、保存检查点、日志记录、tensorboard 写入。**新手只要保证输入（模型/数据/超参）对，Trainer 就是可靠的"驾驶员"**。

训练过程中你会看到：进度条、各 step 的 loss、每个 epoch 的 eval loss。观察点：**训练 loss 应逐步下降，eval loss 也应下降或持平**——若 eval loss 开始升高而 train loss 继续降，就是过拟合信号。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| `trainer.train()` 立刻报 "dataset missing labels" | 训练/验证集里没有 labels 列（第 5 章 preprocess 漏写或 remove_columns 误删）。回到数据验收那步 |
| 训练进度条 0% 卡很久 | 首次运行在序列化/编译/数据加载，正常；若 10 分钟以上没动，查是否磁盘慢或数据量异常 |
| 想中途停止但想保留已训部分 | Trainer 自动按 save_strategy 存检查点，中断后 `trainer.train(resume_from_checkpoint="./results/checkpoint-xxx")` 可续训（无需我们手动处理） |

@@point ⑤ 保存 LoRA 权重：model.save_pretrained + 分词器
@@need 要解决什么
训练结束，现在要把成果"存下来"——但 LoRA 微调的产物不是整个大模型，而是**补丁权重 + 分词器 + 配置**。存什么、存哪、多大，直接影响第 7 章的加载。

@@idea 核心思路
示例代码：

```python
peft_model_path = "./lora_model"
tokenizer.save_pretrained(peft_model_path)   # 保存分词器
trainer.save_model(peft_model_path)          # 保存 LoRA 模型（补丁）
```

保存后 `./lora_model` 目录里有什么：

| 文件 | 内容 |
|---|---|
| adapter_config.json | LoRA 配置（r/α/modules/base 模型名等） |
| adapter_model.safetensors | 真正的 A/B 补丁权重 |
| tokenizer 相关 | tokenizer_config / vocab 文件 |

关键点：
- **没有完整 model 权重**（几个 GB），而是补丁：本章这种 1.5B + 只挂 q/v + r=8 的配置，adapter 只有几万参数（不到 1 MB）；换成 7B 全挂线性层才会到几十 MB 级——这就是 LoRA 最核心的工程价值：**轻、快、可复用**；
- `adapter_config.json` 里记录了 `base_model_name_or_path`，第 7 章按它找回底座；
- 完整模型一份都不落？——要的（合并版）在下一章 merge 时再产生，训练阶段先存补丁即可。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为存的是完整模型，传到别处发现打不开 | LoRA 权重**必须配合同名底座**使用：加载时先载底座、再挂 adapter（第 7 章）。单独拿 adapter 文件给别人用，对方也得先下载底座 |
| 只 save 了模型没 save tokenizer | 加载时 tokenizer 找不到，乱码一堆。**tokenizer 和模型要一起存**（示例里两行都写了） |
| 保存路径被多次覆盖 | LoRA 迭代训练会覆盖旧版本。**按实验命名目录**（如 lora_epoch3 / lora_r16）留档，方便对比回退 |

@@point ⑥ 训练监控：tensorboard 怎么看
@@need 要解决什么
训练跑了半小时，怎么知道它在变好？不能全靠肉眼看进度条。tensorboard 就是训练过程的"仪表盘"——loss 曲线、学习率、梯度范数都可视化，一眼看出过拟合、不收敛。

@@idea 核心思路
训练参数里 `report_to=["tensorboard"]` + `logging_dir="./logs"` 已把日志写好。查看方法：

```bash
tensorboard --logdir ./logs
# 浏览器打开 http://localhost:6006
```

重点看四张图：

| 曲线 | 健康形态 | 问题形态 |
|---|---|---|
| train/loss | 稳步下降 | 不降=学习率太低/数据错；陡升=爆了 |
| eval/loss | 下降后持平 | 开始回升=过拟合 |
| learning_rate | 按调度下降 | 异常=调度配置错 |
| 梯度范数 | 平稳小值 | 爆炸(NaN)=学习率太高/数据脏 |

GPU 显存不够看不到吗？——tensorboard 用 CPU 就能跑，只读日志文件，不占训练资源。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| tensorboard 页面打开空白 | `--logdir` 路径要指到**含 events 文件的目录**；logs 与 results 结构不同，别指错层级 |
| loss 前几个 step 异常大 | 正常：初始未拟合，loss 高是常态；持续几个 epoch 不降才是问题 |
| 训练到一半 loss 变 NaN | 典型原因：学习率太高 / 数据里有空样本 / fp16 溢出。先降学习率，再看数据（第 5 章 filter 空行） |

@@point ⑦ 常见训练中报错速查表
@@need 要解决什么
把这一章最容易踩的报错集中成一张速查表，训练报错时不用全网搜——按"现象→原因→解法"三步查就好。

@@idea 核心思路
| 报错现象 | 根因 | 解法 |
|---|---|---|
| CUDA out of memory | 显存不足 | 降 batch → 加梯度累积 → 量化(QLoRA) → 换小模型 |
| TrainingArguments 参数名报错 | 版本 API 变更 | 用 `eval_strategy` 或按文档版本对齐 |
| ModuleNotFoundError: peft/bitsandbytes | 没装 | `pip install peft bitsandbytes`（在 lora_env 里） |
| Found no labels in dataset | 数据缺 labels | 回第 5 章：preprocess_function 里必须产出 labels 列 |
| loss = nan / inf | 学习率过高/数据脏/数值溢出 | 降学习率 → 清洗数据空行 → 换 bf16/fp32 |
| RuntimeError: expected GPU but CUDA unavailable | torch 装成 CPU 版 | 重装 cu 版 torch（第 4 章）并验证 cuda.is_available() |
| Unexpected key in adapter | adapter 和底座架构不匹配 | 确认 base_model_name_or_path 和保存时一致 |

建议把这张表存在工程 README 里——报错先查表，30 秒定位，避免全网漫游。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 同一个报错反复出现，每次重新搜 | **记录报错+解法到你的笔记**。同一项目里报错高度重复，积累 10 条你就成了老手 |
| 报错信息和网上"一模一样"但解法无效 | 版本不同：先看本地库版本（pip show），再对网上的版本滤波，别盲目照抄 |
| 报错就重装"全家桶" | 重装是最后手段。先看**堆栈最后一行**是哪个库的哪个函数——通常改参数或补 import 就能解决 |

@@point ⑧ 本章验收：训练产物齐全
@@need 要解决什么
收尾验收：训练跑完 ≠ 任务完成，得确认"产物齐、可复用"。三样东西检查到位，第 7 章才能无缝续上：能用微调模型做推理测试。

@@idea 核心思路
验收清单：

| # | 产物 | 检查方式 |
|---|---|---|
| 1 | `./results/` 检查点 | 目录存在、含 checkpoint-* |
| 2 | `./lora_model/` LoRA 权重 | adapter_config.json + adapter_model.safetensors 在 |
| 3 | `./logs/` 训练日志 | events.* 文件在，tensorboard 能打开 |
| 4 | 训练 loss 曲线 | 整体下降，eval loss 无明显反弹 |
| 5 | 解码验证数据 | （第5章已验）确认无脏数据残留在训练集 |

全过 = LoRA 微调训练闭环完成。此时你的显存里已经住着一个"见过 LaMini 指令数据"的模型——下一章就用它来做推理测试、合并权重、上传 Hugging Face，完成最后交付。

另外提醒：把 train 脚本整理成一个 `train_lora.py`（加载模型+配置LoRA+训练+保存全流程），后续 Unsloth / LLaMA-Factory 章节可以直接对照学习两种"更快/更省事"的替代方案。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了保存 lora_model 就关了环境 | 权重在内存里，会话结束即失。**训练一结束立刻 save**（顺序都是先 train 后 save），养成习惯 |
| results 和 lora_model 混为一谈 | results 是日志/检查点（可续训的大物件），lora_model 是轻量补丁（交付物）。**交付用 lora_model，训练维护看 results** |
| 只验收了"没报错" | 没报错≠训得好。**看 loss 曲线**才算完成真实验收——这是和"照着跑完"的分界线 |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **LoraConfig + get_peft_model 挂载** | 每个参数和原理对上号，挂载成功有验证方法（lora_A/lora_B） |
| **会翻译的 TrainingArguments** | batch/梯度累积/学习率三维取舍，显存不够知道怎么改 |
| **一次真实的训练体验** | Trainer 组装全流程，从点火到监控 loss 曲线，报错有速查表 |
| **LoRA 权重产物** | adapter_config + adapter_model.safetensors，轻量、可复用、交付物标准形态 |

下一章收官：加载回微调模型 → 生成测试看效果 → merge 合并成完整模型 → 上传 Hugging Face 分享你的工作成果。

@@quiz
1. LoraConfig 里 r=8、lora_alpha=32 的实际生效强度是多少？为什么这样配？
2. 怎么确认 LoRA 真的挂载到模型上了？（至少一种方法）
3. 显存 OOM 时，保持等效 batch 不变应怎么调两个参数？
4. Trainer 训练一次要检查哪两个主要观察对象？什么时候判定过拟合？
5. LoRA 训练保存的目录里有哪些核心文件？和完整模型的区别是什么？
6. tensorboard --logdir 指向哪个目录？打开后重点看哪两张 loss 图？
7. 训练产物里 results 和 lora_model 的作用分别是什么？交付/续训各用哪个？

@@links
参考|大模型 DeepSeek 微调与应用：配置 LoRA 超参数、训练模型与保存模型|#
官网|Hugging Face Trainer 文档|https://huggingface.co/docs/transformers/main_classes/trainer
官网|PEFT 保存/加载指南|https://huggingface.co/docs/peft/developer_guides/save_load