@@h1 第五章　手写 LoRA 微调（二）：数据准备与预处理
@@sub 阶段 12 · 大模型高效微调与对齐技术　|　难度 ★★★

@@why 这一章在解决什么问题
模型工作台搭好了，但**模型吃不了中文句子，只能吃数字（token）**。你手上有原始问答数据，它们长这样："指令：请翻译……回应：……"。要让 LoRA 学会"按指令回答"，至少要做四件事：找一个合适的公开数据集、看懂它的字段、拆成训练/验证集、把文本转成模型能吃的 token 序列——这四件事合起来叫**数据准备与预处理**。

很多微调翻车不是模型问题，而是数据问题：字段名对不上、标签算错、序列截断导致回答被切掉、批次大小和最大长度不匹配。这一章用 **LaMini-instruction 数据集**走一遍完整的数据流水线，每一个坑都标注出来。

@@prep 开始之前
第 4 章的环境和模型能加载就能开始；这章要下 LaMini 数据集，不用装新库。

@@goal 学到这儿就够了
能看懂数据集字段、切出训练集验证集并 token 化，这一章就算过了。

@@map 这一章在整个知识库里的位置
上一章（手写 LoRA 一）：环境 + DeepSeek 模型加载完成——"锅"和"火"都有了
**本章** ← 你在这里：准备"菜"——加载 LaMini 数据、拆训练/验证、写分词预处理，产出模型能吃的 token 数据集
下一章：手写 LoRA（三）配置 LoRA 超参 + 训练 + 保存——数据喂进 Trainer，真正开始训练
再往后：测试/合并/上传 → Unsloth → GGUF/Ollama → LLaMA-Factory WebUI
阶段终点：你能完整跑通"数据→训练→部署"一条龙

@@point ① 认识 LaMini-instruction 数据集
@@need 要解决什么
教材第一步是"先看到数据长什么样"。LaMini-instruction 是谁、里面有什么字段、为什么适合当微调教材？不搞清楚字段结构，后面所有处理代码都是瞎写。

@@idea 核心思路
数据集档案：

| 属性 | 内容 |
|---|---|
| 卡片名 | MBZUAI/LaMini-instruction |
| 全称 | LaMini-LM: A Diverse Herd of Distilled Models from Large-Scale Instructions |
| 类型 | 指令-回应对（instruction → response） |
| 覆盖 | 知识问答、推理、对话生成、文本总结等多领域 |
| 用途 | 教模型"理解指令并给出回应"，适合 LLM 微调 |

加载并"看两眼"是最快的认识方式：

```python
from datasets import load_dataset
dataset = load_dataset("MBZUAI/LaMini-instruction", split="train[:10]")
print(dataset.column_names)   # ['instruction', 'response']
print(dataset[:2])            # 看前两条样本
```

字段只有两个：`instruction`（指令）和 `response`（回应）——**没有 input 字段**。这个细节直接影响第 6 章训练时的标签构造（下一节展开）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 加载时网络失败/data 卡住 | 与模型同理，可设置 HF 镜像；或用 `trust_remote_code=True` 处理个别数据集需要自定义代码的情况 |
| 以为"所有指令数据集都长这样" | 有的数据集有第三个字段 input（如 Alpaca 风格），有的叫"prompt/output"。**每次先 print(column_names) 再写处理函数**，别想当然 |
| 一次加载全量数据太大 | 用 `split="train[:10]"` 先读 10 条做测试！正式训练再换 `split="train"`。先小后大，避免白等下载 |

@@point ② 手动拆分：训练集与验证集
@@need 要解决什么
一个数据集不能全拿去训练——没有"没见过的数据"来验证，你无法知道模型是不是过拟合/背答案。所以要把数据按比例拆成**训练集**（学）和**验证集**（考）。

@@idea 核心思路
这里用 `train_test_split` 手动拆：

```python
from datasets import load_dataset
# 正式加载训练集（按需取量，这里示例取 10000 条）
dataset = load_dataset("MBZUAI/LaMini-instruction", split="train[:10000]")
# 90% 训练 / 10% 验证，固定随机种子保证可复现
train_dataset = dataset.train_test_split(test_size=0.1, seed=42)

train_dataset_raw = train_dataset["train"]
eval_dataset_raw = train_dataset["test"]
print(len(train_dataset_raw), len(eval_dataset_raw))  # 9000 / 1000
```

要点：
- `test_size=0.1`：10% 留给验证；
- `seed=42`：随机种子，**下次重跑拆出来的分布一样**——超参对比实验的前提；
- 拆完先记住"原始"集（`_raw`）：预处理要在它们之上 map，别把原数据弄丢。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 不设 seed，每次实验结果都不一样 | 没有 seed，训练/验证划分每次不同，A/B 对比全失真。**凡涉及随机切分先写 seed**（训练超参里 seed=3407 也是同理） |
| 只拆了一次就没留"最终测试集" | 训练集学、验证集调参，模型选完还要**第三个未见过集测最终效果**。正式项目建议三重划分；教材演示用两重够用，但要知道差别 |
| 用全量数据训练、验证集为 0 | 等于自测开卷，loss 再低也不代表泛化。验证集必须独立存在 |

@@point ③ 理解 preprocess：把文本变成模型的"食物"
@@need 要解决什么
模型吃 token 不吃汉字。数据准备的核心函数就是"把 instruction+response 拼成模板 → 分词器编码成 input_ids → 再把 response 部分标成 labels"。这段代码是微调数据的"翻译官"，一定要逐行读懂。

@@idea 核心思路
preprocess_function 拆解：

```python
from transformers import AutoTokenizer

# 定义数据预处理函数
def preprocess_function(examples):
    # 取出指令和回应
    instructions = examples["instruction"]
    responses = examples["response"]
    # 构造模型输入提示："指令: xxx\n回应:"
    prompt = [f"指令: {instruction}\n回应:" for instruction in instructions]
    # 分别编码：输入侧截断到 512
    model_inputs = tokenizer(
        prompt, max_length=512, truncation=True, padding="max_length")
    labels = tokenizer(
        responses, max_length=512, truncation=True, padding="max_length")
    # 把回应 token 作为标签
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# 批量处理训练集 / 验证集
train_dataset = train_dataset_raw.map(
    preprocess_function, batched=True,
    remove_columns=train_dataset_raw.column_names)
eval_dataset = eval_dataset_raw.map(
    preprocess_function, batched=True,
    remove_columns=eval_dataset_raw.column_names)
```

三个关键设计：
1. **prompt = 指令拼上"回应:"**——既是输入，也提示模型"现在轮到你回答了"；
2. **labels = response 的 token**——模型要"猜"的就是这段回应；注意这里 label 是把整段 response 当监督信号（简化版，未对 prompt 部分 mask）；
3. **padding="max_length"**：同批样本对齐到 512，Trainer 才能一次性算。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接传汉字给模型 `model.generate("你好")` | 必须走 tokenizer：`tokenizer("你好", return_tensors="pt").to(device)`；不编码模型根本不知道你在说什么 |
| truncation 忘了写，长样本全模型一次性塞爆 | 不截断 → 输入超出模型上下文会自动报错或内存爆炸。**max_length + truncation=True 成对出现** |
| padding 方式理解错 | `padding="max_length"` 是"本 batch 最长对齐"，不是固定 512；还可 `padding=True`（动态）。理解差异，别混用 |

@@point ④ labels 之谜：为什么"回应"当标签，指令不当
@@need 要解决什么
很多初学看到 `model_inputs["labels"] = labels["input_ids"]` 会懵：训练时模型要预测的是什么？为什么指令部分不参与监督？这一节用"完形填空"的比喻讲透因果语言模型（CAUSAL_LM）的训练逻辑。

@@idea 核心思路
因果语言模型的训练 = **逐 token 完形填空**：给它"前面的所有 token"，让它预测"下一个 token"，然后用正确答案（labels）算损失。

在我们的数据里：
- 模型看到 `指令: 你好\n回应:` 这串，要接着预测的内容就是 `response` 的 token；
- 所以 **labels 必须对齐 response**：这批数据的监督信号=回应文本；
- 简化版实现把整个 response 都当标签（不回填 prompt 部分），教材可跑；**严格版**会用 `-100` 把 prompt 对应的 label 屏蔽掉（LLaMA-Factory/Unsloth 内部就是这么干的，见第 9、12 章），避免"让模型学预测自己的提问"。

为什么要屏蔽 prompt 的 loss？——否则模型在"预测指令本身"上也要学对，浪费容量还容易歪。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| labels 没设，Trainer 报 "loss is None" / 疯狂告警 | 没有 labels，语言模型无从计算损失。**labels 是训练的必要字段**，忘设 = 训了个寂寞 |
| labels 长度和 input_ids 不一致 | 两者都截到 512 且 padding 策略相同可对齐；若用动态 padding，必须保证 input_ids/labels 用**同一批次的同一长度规则**构造 |
| 以为"labels 就是期望输出文本本身" | labels 是**token ID 数组**（数字），不是字符串。字符串→token 的转换就是 tokenizer 干的活 |

@@point ⑤ map 与 batched：为什么用 batched=True
@@need 要解决什么
`dataset.map(fn, batched=True)` 这行代码几乎每本教程都有，但很多人不知道 batched 是干嘛的、不写行不行。这直接影响代码效率和正确性。

@@idea 核心思路
map 的行为：

| 参数 | 意思 | 不写会怎样 |
|---|---|---|
| fn | 逐条或逐批调用的函数 | —— |
| batched=True | **一次处理一批样本**（批量 list 传入） | 改成逐条处理，速度慢数倍~数十倍 |
| remove_columns | 处理后删掉原始列 | 数据集列越来越多，占用内存 |

为什么 batched 快：分词器（tokenizer）内部对批量输入有**批量优化**（如 padding 一次到位、batch 内并行），逐条调用等于放弃这些优化，10000 条数据能慢到天荒地老。

这里的 preprocess_function 接收的 `examples` 是**字典：列名→该列的一个 batch 列表**（所以函数里用 `examples["instruction"]` 取到的是列表、再列表推导式逐个拼模板）——这就是 batched 模式的数据形态。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 函数里误以为 examples 是"一条样本" | batched=True 时 examples 的每个字段是**一组样本的列表**；逐条写的函数（examples["instruction"] 是字符串）会全线崩溃。要么函数按 batch 写，要么 batched=False 逐条 |
| 忘写 remove_columns，见内存暴涨 | 原列（大段原文）不删会一直带着。**处理完空转一次 remove_columns**，数据更小更快 |
| 二次 map 时发现数据格式不对 | map 有缓存机制，改函数后要 `load_from_cache_file=False` 重跑，否则用的是旧缓存结果 |

@@point ⑥ 检查预处理结果：肉眼验证数据没喂错
@@need 要解决什么
预处理写完不算完——**必须抽查**：token 解码回文本是否和原数据一致？有没有把回答截断没了？这一检查动作省下的排错时间远超写代码的时间。

@@idea 核心思路
验证检查三步：

```python
# 1. 看 shape：有没有 padding 成功
print(train_dataset.shape)  # (9000, 3)：三列 input_ids/labels/attention_mask
# 2. 抽查一条：token 数够不够（有没有把答案截没）
sample = train_dataset[0]
print("input_len:", len(sample["input_ids"]), "label_len:", len(sample["labels"]))
# 3. 解码验证：token 还原文本，确认和原始 instruction 对得上
text = tokenizer.decode(sample["input_ids"])
print(text)  # 应看到"指令: xxx\n回应:"
print(tokenizer.decode(sample["labels"]))  # 应看到原 response
```

三个断言：
- 长度都 ≤ 512（截断生效）；
- 解码后的指令跟原 dataset 第一条一致；
- labels 解码出来是原 response 开头（而不是乱码/空）。

**"解码回人类语言看一眼"** 是数据工程师的核心手艺——一切 token 预处理都能用 decode 反向验证。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只看 shape 不 decode，训练完才发现数据是乱的 | 形状对不代表内容对（padding 错位、字段取错）。**decode 是最后一道人工防线**，训练前必做 |
| decode 出来的文本夹杂特殊符号如 `<\|endoftext\|>` | padding 位置被 pad token 填充或混入特殊 token 是正常的，不影响训练；若强迫症可用 `skip_special_tokens=True` 看正文 |
| 截断导致多数样本 response 被切没 | `max_length=512` 装不下"长指令+长回答"时，应答被腰斩。解法：调大 max_length（显存允许）或**数据侧先做清洗**（太长的样本丢弃/切分） |

@@point ⑦ 指令格式的取舍：这里为什么用"指令:\n回应:"
@@need 要解决什么
你可能注意到：LaMini 没有 chat 模板，就直接拼 `"指令: {instruction}\n回应:"`。为什么不套用 DeepSeek 的官方 Chat 模板？不同模板对训练结果影响有多大？——理解模板，你才不会被"哪个模板对"搞晕。

@@idea 核心思路
模板的本质：**告诉模型"哪段是输入、哪段该输出"的格式约定**。

| 方案 | 格式示例 | 适合 |
|---|---|---|
| 简化模板 | `指令: xxx\n回应:` | 教学/快速起步，可控、直观 |
| 模型官方 Chat 模板 | `<\|user\|>...<\|assistant\|>...`（tokenizer.apply_chat_template） | 生产项目，与模型预训练格式一致 |
| Alpaca 模板 | `### Instruction: ...\n### Response:` | 第 9 章 Unsloth 使用 |

会不会"格式错了模型学不会"？——微调本质上会**学会你的格式**：只要训练/推理用同一模板，模型就能跟着学会"看到回应:就接话"。所以一致性 > 完美性：**训测同模板**比"用最官方模板但训测不一致"强得多。

这里主线统一用"指令:/回应:"模板，后文推理测试也是同一格式（第 7 章），正符合"一致性"原则。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 训练用一个模板，测试用另一个 | 模型只在"训练的格式"下见过任务，换格式就"失忆"（表现骤降）。**把模板固化成变量**（如 alpaca_prompt 一样全局定义），训/测都引用它 |
| 以为"模板随便写，反正模型都会" | 底层模型若预训练时只见过 ChatML，你的"指令:/回应:"模板可能让它困惑（少部分模型）。**先试官方模板**（apply_chat_template），效果不好再换 |
| 在 template 里忘记产出"回应:"前缀 | 测试生成时要先拼好"回应:"让模型接着写，否则它可能从"指令:"重新起草 |

@@point ⑧ 本章验收：数据流水线全通
@@need 要解决什么
数据准备环节收尾前，把所有检查合并成一套"验收动作"，确认"模型 + 数据"双就绪，第 6 章训练才能一把过。

@@idea 核心思路
验收清单（对着跑一遍）：

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | column_names | `['instruction','response']` |
| 2 | 拆分比例 | train/test ≈ 9:1，种子固定 |
| 3 | 预处理后台并 | train_dataset/eval_dataset 各有 input_ids、labels |
| 4 | decode 抽查 | 解码=原 instruction + 原 response |
| 5 | 长度检查 | 都在 max_length 内，无空样本 |

全过 = 数据侧就绪。把 preprocess_function + 拆分代码存成 `prepare_data.py`，第 6 章直接 import 复用——这也是正式项目的姿态：**数据、模型、训练三文件分离**，各管一摊，好修好查。

如果检查发现"空样本"（response 为空），预处理函数里加一行过滤：删掉 response 长度 < 1 的行——空标签样本会让 loss 出 NaN。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 到训练才发现数据列不对，返工一整晚 | **数据验收必须在训练前完成**，靠 decode 抽查锁定内容正确性——这是排队最长的坑，前置检查最划算 |
| 空样本/异常样本导致 loss=NaN | 预处理函数里显式过滤空 response；训练参数加 `ignore_data_skip` 前先确认数据无脏行 |
| "我每一步都看着对，但训练 loss 不降" | 回顾三点：labels 是否设置、模板训练测试是否一致、学习率是否合理（第 6 章）。**数据先对，再谈调参** |

@@summary
这一章你实际拿到的是：

| 拿到了什么 | 为什么要紧 |
|---|---|
| **LaMini 数据的加载与认识** | column_names 先看后写，字段结构了然于胸 |
| **train/valid 手动拆分** | 90/10 + seed=42，验证集独立，实验可复现 |
| **完整的预处理函数** | instruction+response → prompt/labels token 化，map(batched) 批量高效，labels 用于监督 |
| **肉眼验收法** | shape + len + decode 三步，把"数据没喂错"变成可执行动作 |

数据就绪，下一章点火：LoRA 挂载（get_peft_model）、TrainingArguments 超参、Trainer 训练、保存 LoRA 权重——训练真正跑起来。

@@quiz
1. LaMini-instruction 的字段名是什么？加载后第一件事应该做什么？
2. `train_test_split(test_size=0.1, seed=42)` 中 seed 的作用是什么？不设会怎样？
3. 为什么 labels 用 response 的 token 而不是 instruction 的 token？
4. `datasets` 的 `map(..., batched=True)` 有什么好处？batched 模式下函数收到的 examples 长什么样？
5. 用 30 秒写出发自这一章的"肉眼验收三步"是什么？
6. "训练用 A 模板、测试用 B 模板"会造成什么问题？正确做法是什么？
7. 预处理产出空 labels 样本会导致什么？怎么提前预防？

@@links
参考|大模型 DeepSeek 微调与应用：加载数据集与数据预处理|#
官网|Hugging Face Datasets 文档（map/加载）|https://huggingface.co/docs/datasets/
数据集|MBZUAI/LaMini-instruction|https://huggingface.co/datasets/MBZUAI/LaMini-instruction