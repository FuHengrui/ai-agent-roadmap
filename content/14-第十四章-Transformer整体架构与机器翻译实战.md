@@h1 第十四章　Transformer整体架构与机器翻译实战
@@sub 阶段 22 · 自然语言处理与Transformer架构　|　Transformer搭建　|　难度 ★★★★

@@why 这一章在解决什么问题
前面学了自注意力、多头注意力、位置编码等一堆零件，这一章把它们**组装成整机**：完整的 Transformer 由编码器（Encoder）和解码器（Decoder）构成，编码器负责"读懂原文"，解码器负责"生成译文"——两者之间用**交叉注意力**对接，解码器内部用**掩码自注意力**防止偷看未来。最后用 PyTorch 实跑一遍"英译中"的最小翻译系统，把理论落到代码。

@@prep 开始之前
沿用前面装好的 PyTorch 就能跑，这章不用装新东西；上一章的零件要能对上号。

@@goal 学到这儿就够了
能搭出编码器解码器并跑通一次中译英，能说清掩码自注意力和交叉注意力各防什么，这章就算过了。

@@map 上一章→本章→下一章
上一章集齐了单层零件。**本章完成整机组装：编码器堆 N 层、解码器堆 N 层（掩码多头注意力 + 交叉注意力），端到端跑通翻译**。下一章进入预训练时代：ELMo 首次实现"动态词向量"，宣告从"训练词向量"转向"预训练语言模型"。

@@point ① Transformer 总览：编码器-解码器全家福
@@need 要解决什么
Transformer 整机由哪几大块组成？各自负责什么？

@@idea 核心思路
Transformer 整机 = **输入处理 + 编码器 + 解码器 + 输出层**：

```
源句 → 词嵌入+位置编码 → [编码器 ×N]
                              │ 每层输出(含全句信息)
翻译起点 → 词嵌入+位置编码 → [解码器 ×N] → 线性层 → Softmax → 预测词
```

- **编码器（Encoder）**：N 层堆叠，每层 = 多头自注意力 + FFN。输出是源句每个词的**全上下文表示**（携带全句信息）。
- **解码器（Decoder）**：N 层堆叠，每层比编码器**多一个子层**——掩码多头自注意力 → 交叉注意力 → FFN。
- **输出层**：线性层把解码器输出映射到词表大小，Softmax 出概率。

编码器管"理解"，解码器管"生成"，中间靠交叉注意力桥接——这是翻译类任务的标准「编码器-解码器（seq2seq）」结构（双塔是检索里的说法，别混）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为编码器和解码器结构完全相同 | 解码器**只多一个交叉注意力子层**；"掩码自注意力"是自注意力加了 mask，不算新增子层 |
| 忘记输出层 | 解码器输出要过 Linear(vocab_size) + Softmax 才能得到单词概率 |

@@point ② 解码器三件套：掩码自注意力、交叉注意力、FFN
@@need 要解决什么
解码器内部为啥要有三种不同的子层？各自管什么？

@@idea 核心思路
解码器单层的三个子层，分工明确：

```
① 掩码多头自注意力（Masked MHA）
   - 作用: 看"已生成的翻译前缀"，防止偷看未来
   - 输入: 自身序列（加了上三角掩码）
   ↓
② 交叉注意力（Cross-Attention）
   - 作用: "看原文"——查询来自解码器，键/值来自编码器输出
   - 输入: Q=解码器当前表示，K/V=编码器最后的输出
   ↓
③ 前馈网络 FFN
   - 作用: 逐位置非线性加工（和编码器一致）
```

翻译时它们是分步协作：**先回顾已写部分，再对照原文找信息，最后加工表达**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 把交叉注意力和自注意力搞混 | 交叉注意力 Q/K/V 来自两个序列（解码器/编码器）；自注意力三者同源 |
| 三个子层顺序调换 | 顺序是设计结果：先掩码自注意力（消化已生成内容）再交叉注意力（对照原文），调换会破坏信息流 |

@@point ③ 交叉注意力：解码器"看原文"的窗口
@@need 要解决什么
生成第 3 个译文词时，模型怎么知道该重点看原文哪一部分？

@@idea 核心思路
交叉注意力就是第 11 章"注意力"的 Transformer 版：

```
Attention(Q, K, V):
  Q ← 解码器当前步的表示（"我现在需要什么"）
  K, V ← 编码器输出（源句每个词的表示，全句可查）
```

- 解码器每生成一个词，都与**源句所有位置**算注意力权重。
- "银行"译成 "bank" 时，Q 会与原文"银行"位置的 K 高度匹配，重点取用那里的 V。
- 这就是**软对齐**：翻译不再靠单个状态向量硬扛，而是按需检索原文任意片段。

实现上，交叉注意力复用一个 MHA 模块，只是把 K/V 从编码器输出传入。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 交叉注意力也加掩码 | 交叉注意力**不加因果掩码**（编码器那边已经看全了），但**源句的 padding 掩码还得传**（`src_key_padding_mask`），否则 pad 位置会参与注意力 |
| 以为 K/V 每层都一样 | 各解码层都有自己的交叉注意力投影，但 K/V **都来自编码器最后一层的输出** |

@@point ④ 位置编码在编码器/解码器都要加吗
@@need 要解决什么
位置编码何时加、加几处？

@@idea 核心思路
**两处都要加**：

- 编码器入口：源句词嵌入 + 位置编码。
- 解码器入口：目标译文词嵌入 + 位置编码。

原因：编码器要区分"我爱学习"与"学习爱我"，解码器要区分"我"是第 1 个词还是第 3 个词，**两端都依赖顺序**。位置编码加入时机都在**嵌入之后、第一层前**，一次性加完，后续各层复用。

同一套公式、同样的加法，只是各自对应的序列不同（源句/目标句）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只在编码器加 | 解码器生成长句同样需要顺序感，漏加会导致生成乱序 |
| 每层都重新加一遍 | 只在输入处加一次，层内不重复叠加 |

@@point ⑤ 完整前向：翻译一条句子走过的路
@@need 要解决什么
从"我爱学习"输入到输出 "I love learning"，数据流过哪些步骤？

@@idea 核心思路
一次完整前向：

```
1. 编码: 我爱学习 → 词嵌入 + 位置编码 → 编码器 N 层
   → 得到 4 个源词表示（每个都含全句信息）
2. 解码起始: 输入 <sos> → 词嵌入 + 位置编码 → 解码器
   - 掩码自注意力: 只看 <sos>
   - 交叉注意力: 对照"我爱学习"4 个位置，重点看"我"
   - FFN 加工 → 输出层 Softmax → 最高概率词 "I"
3. 自回归: 输入 <sos> I → 预测 "love"
   输入 <sos> I love → 预测 "learning"
   输入 <sos> I love learning → 预测 <eos> → 停止
```

关键：**每步只生成一个词，新词立即拼回输入再走下一步**，直到 eos。整条链路 = 编码一次 + 解码多次。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了编码器只跑一次 | 源句编码一次即可复用；解码器每步都跑（输入变长）
| 停止条件缺失 | 无 eos/max_len 就无限生成；推理要同时带两个护栏 |

@@point ⑥ 实战代码：PyTorch 最小 Transformer 翻译（模型定义）
@@need 要解决什么
完整翻译代码几十上百行，最小模型核心几行？

@@idea 核心思路
用 PyTorch 自带的 Transformer 封装，模型定义极简：

```python
import torch
import torch.nn as nn

class TinyTranslator(nn.Module):
    def __init__(self, src_vocab, tgt_vocab,
                 d_model=128, nhead=4, num_layers=2):
        super().__init__()
        self.src_embed = nn.Embedding(src_vocab, d_model)
        self.tgt_embed = nn.Embedding(tgt_vocab, d_model)
        self.transformer = nn.Transformer(
            d_model=d_model, nhead=nhead,
            num_encoder_layers=num_layers,
            num_decoder_layers=num_layers,
            batch_first=True)
        # 正弦位置编码：nn.Transformer 不带 PE，得自己造（可学习版本换成 nn.Embedding）
        self.pos_enc = PositionalEncoding(d_model, max_len=512)
        self.fc_out = nn.Linear(d_model, tgt_vocab)

    def forward(self, src, tgt):
        # src: [batch, src_len], tgt: [batch, tgt_len]
        src = self.src_embed(src) + self.pos_enc(src)   # 位置编码必须自己加
        tgt = self.tgt_embed(tgt) + self.pos_enc(tgt)
        # ⚠️ nn.Transformer 不会自动给你因果掩码，必须自己传，否则解码器能看见未来 token
        tgt_mask = nn.Transformer.generate_square_subsequent_mask(tgt.size(1)).to(tgt.device)
        out = self.transformer(src, tgt, tgt_mask=tgt_mask)
        return self.fc_out(out)            # [batch, tgt_len, vocab]
```

`nn.Transformer` 内置的是**多头注意力 + 前馈 + 残差/LayerNorm**，**没有位置编码**——PE 要自己写、在 embedding 之后相加；`tgt_mask`（因果掩码）、`src_key_padding_mask`/`tgt_key_padding_mask`（pad 掩码）也要自己传。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接喂原始 token | 必须先 Embedding 升维再进 transformer，输出记得过 fc_out 投影到词表 |
| 忘了 mask | 训练要传 `tgt_mask`（上三角 True）与 `src_key_padding_mask`（pad 位置），否则掩码注意力失效 |

@@point ⑦ 实战代码：训练循环与推理
@@need 要解决什么
模型定义好了，训练和翻译怎么跑起来？

@@idea 核心思路
训练核心（Teacher Forcing + 交叉熵）：

```python
criterion = nn.CrossEntropyLoss(ignore_index=PAD_ID)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

for batch in dataloader:
    src, tgt_in, tgt_out = batch      # tgt_in 右移一位，tgt_out 是标签
    logits = model(src, tgt_in)       # [B, T, vocab]
    loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_out.reshape(-1))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
```

推理（自回归 + eos 停止）：

```python
def translate(model, src, max_len=50):
    model.eval()
    with torch.no_grad():
        # TinyTranslator 本身没写 encode/decode，直接取内部的 encoder，并自己加位置编码
        memory = model.transformer.encoder(model.src_embed(src) + model.pos_enc(src))   # 编码一次
        tgt = torch.tensor([[SOS_ID]])     # 从 <sos> 起
        for _ in range(max_len):
            logits = model.transformer.decoder(
                model.tgt_embed(tgt) + model.pos_enc(tgt), memory,
                tgt_mask=nn.Transformer.generate_square_subsequent_mask(tgt.size(1)).to(src.device),
            )   # 解码器每步都要重建因果掩码
            logits = model.fc_out(logits)
            word = logits[:, -1].argmax(-1)
            if word.item() == EOS_ID:
                break
            tgt = torch.cat([tgt, word.unsqueeze(1)], dim=1)  # word 是 [B]，先补一维再拼
    return tgt
```

完整工程配套：数据清洗、中英分词、批处理 pad、按长度排序——但**核心逻辑就这两段**。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 训练/推理输入方式不一致 | 训练喂真实词右移序列，推理喂自己生成的序列——接口要分开设计 |
| 推理每步重新编码 | 编码一次后只重跑解码器即可，重复编码浪费计算且逻辑错误 |

@@point ⑧ 翻译效果与指标：怎么知道模型好坏
@@need 要解决什么
训练完怎么评估翻译质量？常见指标有哪些？

@@idea 核心思路
评估翻译的两类视角：

**1. 自动指标（机器算）：**

| 指标 | 思路 | 说明 |
|---|---|---|
| BLEU | 候选译文与参考译文的 n-gram 重合率 | 越高越好；对表达多样性不敏感 |
| ROUGE | 基于召回，常用于摘要 | 翻译领域次选 |
| 困惑度 PPL | 模型对文本的"惊讶程度" | 训练期监控，越低越好 |

**2. 人工评估**：流利度、忠实度、自然度打分——**最终标准**，因为自动指标无法完全衡量语义正确。

实践建议：BLEU 做粗筛，抽样人工审读做把关；长句、专有名词、习语是重点错误源。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只盯 BLEU 忽略人工 | BLEU 偏好"与参考逐字相近"，正确但措辞不同的译文会被低估，需人工复核 |
| 用训练集困惑度吹效果 | 要算验证集/测试集 PPL 与 BLEU，训练集分数没有意义 |

@@summary
本章完成 Transformer 整机组装与实战：

| 问题 | 答案 |
|---|---|
| 整机构成 | 编码器×N + 解码器×N + 输出层 |
| 编码器子层 | 多头自注意力 + FFN |
| 解码器子层 | 掩码多头自注意力 + 交叉注意力 + FFN |
| 交叉注意力 | Q=解码器，K/V=编码器输出，按需翻原文 |
| 位置编码 | 编码器/解码器入口各加一次 |
| 前向流程 | 编码一次 → 解码逐词自回归 → eos 停止 |
| 实战 | nn.Transformer 一行整机 + 两段核心代码 |
| 评估 | BLEU 自动指标 + 人工审读把关 |

一句话记住本章：**Transformer = 编码器读懂原文 + 解码器逐词生成，解码器内部用掩码自注意力防偷看、交叉注意力翻原文、FFN 做加工；PyTorch 里 nn.Transformer 一句话起整机，训练喂右移序列、推理自回归拼词到 eos——一个最小翻译系统就此跑通。下一章起，主角从"架构"切换到"预训练"：ELMo 率先登场。**

@@quiz
1. 画出 Transformer 整机的结构图，标出编码器与解码器各自的子层。
2. 解码器比编码器多的是哪个子层？它拿什么当 Q、什么当 K/V？
3. 交叉注意力中 Q/K/V 分别来自哪里？为什么叫"交叉"？
4. 位置编码在编码器和解码器都要加吗？为什么？
5. 描述"我爱学习"翻译成英文的完整前向过程（含停止条件）。
6. nn.Transformer 一行封装了什么？实战中还需要手动构造哪些 mask？
7. 训练循环与推理循环在输入上有什么本质区别？BLEU 指标的局限性是什么？

@@links
参考|Transformer整体架构与翻译实战|#
文档|Attention Is All You Need|https://arxiv.org/abs/1706.03762
文档|PyTorch Transformer 官方教程|https://pytorch.org/tutorials/beginner/translation_transformer.html