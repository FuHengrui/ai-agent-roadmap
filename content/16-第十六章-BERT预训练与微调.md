@@h1 第十六章　BERT预训练与微调
@@sub 阶段 22 · 自然语言处理与Transformer架构　|　BERT　|　难度 ★★★★

@@why 这一章在解决什么问题
ELMo 的"双向"只是前向后向拼接，不是真融合；而且迁移要靠特征拼接，改造成本高。**BERT（Bidirectional Encoder Representations from Transformers）** 用两个创新一举解决：**① Masked Language Model（掩码语言模型）做到真双向预训练；② "预训练 + 微调"范式——直接对预训练模型做小改动微调，一个模型适配四大类 NLP 任务**。它定义了现代 NLP 的应用方式。

@@prep 开始之前
要装 transformers，第一次跑还要联网下 bert-base-chinese 的权重。

@@goal 学到这儿就够了
能说清 BERT 怎么做到真双向、预训练加微调怎么换头适配任务，能跑通一次中文分类微调，这章就算过了。

@@map 上一章→本章→下一章
上一章 ELMo 留下"伪双向、迁移重"的缺口。**本章 BERT 用 Transformer 编码器 + 掩码语言模型补上双向缺口，并把迁移方式升级为微调**。下一章 GPT 从"编码器"转向"解码器"，用生成式预训练在生成类任务上登顶——预训练三巨头聚齐。

@@point ① 为什么是"双向"：BERT 的出发点
@@need 要解决什么
ELMo 的双向"假"在哪？BERT 怎么做到真双向？

@@idea 核心思路
ELMo：前向 LM 只看上文、后向 LM 只看下文，最后**拼接**——每个词都没在"同一个模型里"同时看到完整上下文。

BERT 的做法：**直接让模型同时看左右两侧**再预测目标词，即 **Masked Language Model（MLM）**：

- 训练时随机**遮盖**句中部分词（15%）。
- 让模型根据**剩余所有词**（左右都可见）去预测被盖住的词。

```
输入: [CLS] 我 [MASK] 学习 [SEP]
目标: 预测 [MASK] = 爱
```

这迫使模型利用**左右两侧上下文**——真正的一次性双向融合，而非两个方向的拼接。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把 MLM 误当成"填空完型"的玩具 | 它是逼模型学双向上下文的核心训练任务，等价于"词语义推断"训练 |
| 以为 BERT 预训练也用语言模型 | BERT 用 MLM（+NSP），不是标准语言模型；这正是它能双向的原因 |

@@point ② MLM 的 15% 策略：遮哪些、怎么遮
@@need 要解决什么
掩码语言模型到底怎么选词、怎么遮盖？

@@idea 核心思路
对每个训练句：随机选 **15% 的 token** 参与遮盖，其中：

- **80%**：替换为 `[MASK]`。
- **10%**：替换为随机词。
- **10%**：保持不变（还是原词）。

为什么这么"绕"？这一设计的动机：

- 若全用 `[MASK]`：预训练见过大量 `[MASK]`，但微调/推理时没有 `[MASK]`——分布不一致。
- 掺入随机词与原文：迫使模型不只"看标记"，还要**依赖上下文判断每个位置是否可信**，学到的表示更鲁棒。

预测时只对**被选的 15% 位置**计算损失，其他位置不管。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 全部用 [MASK] | 预训练/推理分布不一致，下游掉点；必须按 80/10/10 比例混合 |
| 对全部 token 算损失 | 只对被遮盖的 15% 算 MLM 损失，其余位置是"填空辅助"不参与监督 |

@@point ③ BERT 的两个输入任务：MLM + NSP
@@need 要解决什么
除了猜词，BERT 还要学句子之间的关系，怎么办？

@@idea 核心思路
BERT 预训练有**两个目标**：

**① MLM**（上面讲过）：学词级双向语义。

**② NSP（Next Sentence Prediction）**：判断句子 B 是不是句子 A 的下一句。

```
输入: [CLS] 今天天气不错 [SEP] 我们出去散步 [SEP]   → 标签: IsNext
输入: [CLS] 今天天气不错 [SEP] 我爱吃火锅 [SEP]     → 标签: NotNext
```

- 随机 50% 是真实下一句（IsNext）、50% 是随机句（NotNext）。
- 训练目标：对 `[CLS]` 位置输出二分类。
- 意义：让模型学习**句子级关系**（连贯性、逻辑），对 QA、推理、NLI 这类任务有用。

两个任务联合训练，词级 + 句级信息一起进表示。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 NSP 现在还被用 | 后续研究（RoBERTa）发现 NSP 收益有限，但理解 BERT 原版必学；从中看到"多任务预训练"的思想 |
| `[CLS]` 位置的用途 | BERT 约定用 `[CLS]` 输出代表"整句表示"，分类任务用它接分类头 |

@@point ④ BERT 与 Transformer 编码器的关系
@@need 要解决什么
BERT 的结构和上一章的 Transformer 编码器是什么关系？

@@idea 核心思路
**BERT = Transformer 的编码器栈叠**（无解码器、无交叉注意力）：

| 部件 | Transformer 编码器 | BERT |
|---|---|---|
| 主体 | 多头自注意力 + FFN | 完全一致 |
| 输入 | 词嵌入 + 位置编码 | 词嵌入 + 位置编码 + 段嵌入 |
| 堆叠 | 6 层（原论文的 base 配置，可调；别和 BERT-base 的 12 层混） | BERT-base=12 层 / BERT-large=24 层 |
| 特殊 token | 无 | [CLS] / [SEP] / [MASK] |
| 训练任务 | 无（监督微调） | MLM + NSP 预训练 |

差异点就三处：**特殊 token、段嵌入（Segment Embedding 区分两句话）、预训练目标**。结构学明白了，BERT 就是"把编码器拿去预训练"。

size 参考：BERT-base = 12 层、12 头、hidden 768、约 1.1 亿参数；BERT-large = 24 层、16 头、hidden 1024、约 3.4 亿。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 BERT 是全新架构 | BERT 直接复用 Transformer 编码器，创新在"预训练任务"与"微调范式" |
| 混淆层数与头数 | 层=堆叠深度，头=注意力并行通道；base 是 12 层 12 头，别记混 |

@@point ⑤ 段嵌入与特殊 token：BERT 的输入格式
@@need 要解决什么
BERT 输入 "两句话 + 三个特殊 token"，编码上怎么处理？

@@idea 核心思路
BERT 输入 = **词嵌入 + 位置编码 + 段嵌入**，三者相加：

- **词嵌入**：每个 token 查表（含 [CLS]/[SEP]/[MASK]）。
- **位置编码**：同样用可学习的绝对位置（学到型，非三角函数）。
- **段嵌入**：标记 token 属于"句子 A 还是句子 B"（同维向量相加），让模型区分两句话。

标准输入格式：

```
[CLS] 句子A [SEP] 句子B [SEP]
  ↑      ↑      ↑      ↑
 分类   第一句  分隔/第二句起点   结束
```

`[SEP]` 分隔句子，`[CLS]` 输出作为整句表示接分类头。这一段把"两句话怎么打包"机制化了。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘记加段嵌入 | 没段嵌入，[SEP] 两侧句子信息混在一起，句子关系任务学不动 |
| 位置编码用错类型 | BERT 是用"学出来"的位置嵌入，不是 Transformer 原文的三角编码（两种都可以，实现不同） |

@@point ⑥ 四类微调任务：一个 BERT 打天下
@@need 要解决什么
预训练好的 BERT 怎么适配不同任务？答案：只换"头"。

@@idea 核心思路
微调（Fine-tuning）= **加载预训练权重后继续训练**（BERT 默认全参更新，也可以只调一部分）+ 按任务**换一个输出头**。四大类任务：

```
① 句子对分类（如: 文本蕴含 NLI）
   输入: [CLS] A [SEP] B      → CLS → 分类头 → 蕴含/矛盾/无关

② 单句分类（如: 情感分析）
   输入: [CLS] 好评 [SEP]     → CLS → 分类头 → 积极/消极

③ 问答抽取（如: SQuAD）
   输入: [CLS] 问题 [SEP] 文章 → 每个词位置输出两个分数
   → 起点头 softmax + 终点头 softmax → 回答区间

④ 序列标注（如: 命名实体识别 NER）
   输入: [CLS] 句 [SEP]       → 每个 token 过分类头 → B-ORG/I-PER...
```

关键洞察：**同一个预训练模型，只换头部 + 全参微调（通常 2–4 个 epoch），就能吃下理解类任务的绝大多数形态**。这正是 BERT 能"一个模型打天下"的原因。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为每类任务要重训 BERT 主体 | 主体只做轻量微调（通常几个 epoch），任务差异主要体现为"头"的不同 |
| 问答抽取当作文本生成 | SQuAD 式抽取=预测起止位置，不是生成式回答（那是 GPT 的地盘） |

@@point ⑦ 微调实操：用 Hugging Face 两分钟跑情感分类
@@need 要解决什么
不用从零训练数天，怎么快速用 BERT 完成一个下游任务？

@@idea 核心思路
Hugging Face `transformers` 把"预训练 + 微调"封装成几行代码：

```python
from transformers import (
    BertTokenizer, BertForSequenceClassification,
    Trainer, TrainingArguments,
)

model_name = "bert-base-chinese"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(
    model_name, num_labels=2)

dataset = ...   # (text, label) 准备一个标准 Dataset
model.train()
trainer = Trainer(
    model=model,
    args=TrainingArguments(output_dir="ckpt", num_train_epochs=3)   # 位置参数已弃用，用关键字,
    train_dataset=dataset,
)
trainer.train()
```

核心事实：

- `from_pretrained` 一步拿到预训练权重。
- `BertForSequenceClassification` 自动加好分类头。
- 训练仍是常规 Trainer——**不在微调期间重新预训练**。

这是现代 NLP 工程师的日常：**下载权重 → 微调 → 上线**，全程不触碰模型内部。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 微调时又想"从头训练 BERT" | 微调 = 已有权重上小步继续训；从头训需要海量算力与数据，那不是微调 |
| 忘记按任务选模型类 | 分类用 ForSequenceClassification、问答用 ForQuestionAnswering、标注用 ForTokenClassification——选错头任务跑不通 |

@@point ⑧ BERT 的贡献与局限
@@need 要解决什么
BERT 开创了什么？它自己又留了什么"坑"给后续模型？

@@idea 核心思路
**贡献（里程碑意义）：**

1. **真双向预训练**：MLM 让每个词同时利用左右上下文。
2. **预训练 + 微调成为标准范式**：一套权重适配多任务。
3. **深度表示被大范围验证**：12/24 层编码器表示远超浅层模型。

**局限（GPT/后续模型补的坑）：**

1. **不能生成**：编码器结构没有自回归生成能力（做不了翻译的自由解码/文案生成）。
2. **MLM 需候选**：预训练需要 mask 任务，与生成式 LM 目标不统一。
3. **输入长度受限**：512 token 上限，长文档处理麻烦。
4. **训练成本高**：Transformer 编码器体量大，需专门算力。

了解贡献与局限，就能理解为什么 GPT 用"解码器 + 生成式目标"走出另一条路。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 BERT 是全能的 | 它是"理解类任务"的王牌，生成类任务要交给 GPT 式模型 |
| 把 512 上限当无限长 | 长文本要切窗/长文本技术解决，硬塞会截断信息 |

@@summary
本章建立 BERT 完整认知：

| 问题 | 答案 |
|---|---|
| 真双向怎么实现 | MLM 掩码语言模型（15% 遮盖，看左右预测） |
| 80/10/10 | [MASK]/随机词/原文 混合，解决分布不一致 |
| 预训练任务 | MLM（词级）+ NSP（句级）联合 |
| 结构 | Transformer 编码器 + 段嵌入 + 特殊 token |
| 输入格式 | [CLS] A [SEP] B [SEP] |
| 四类微调 | 句对分类/单句分类/问答抽取/序列标注，换头即可 |
| 实操 | Hugging Face 几行代码微调 |
| 局限 | 不能生成、512 上限、训练贵 |

一句话记住本章：**BERT 用掩码语言模型做到真双向预训练，以"预训练 + 微调"范式仅靠换输出头就能适配分类、问答、标注等四大类任务——理解类 NLP 从此进入"下载权重、微调、上线"的工业化流程；但它天生不擅长生成，这个缺口正好由下一章的解码器王者 GPT 来补。**

@@quiz
1. ELMo 的"双向拼接"与 BERT 的"真双向"有什么区别？
2. BERT 的 MLM 具体怎么执行？15% 的 token 内部又如何分配？
3. 为什么 MLM 要混合 [MASK]/随机词/原文三种策略？
4. NSP 任务是什么？为什么要有这个任务？
5. BERT 与 Transformer 编码器在结构上有什么异同？段嵌入解决什么问题？
6. 写出 BERT 对"句对分类/问答抽取/序列标注"三类任务的微调方式。
7. BERT 有哪些"做不了"的任务？为什么这些任务要交给解码器式模型（GPT）？

@@links
参考|BERT预训练与微调|#
文档|BERT 原文（Pre-training of Deep Bidirectional Transformers for Language Understanding）|https://arxiv.org/abs/1810.04805
文档|Hugging Face BERT 中文微调教程|https://huggingface.co/docs/transformers/model_doc/bert