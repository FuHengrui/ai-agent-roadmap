@@h1 第七章　RNN歌词生成实战
@@sub 阶段 22 · 自然语言处理与Transformer架构　|　RNN实战　|　难度 ★★★

@@why 这一章在解决什么问题
上一章的 RNN 公式还停在纸面上，这一章直接把它变成能跑的程序：**用 RNN 训练一个"歌词生成器"**。输入一堆歌词文本，模型学会下一个字该写什么，最终能自动续写出通顺的句子。这一章走通"数据准备 → 模型搭建 → 训练 → 采样生成"的完整闭环，你会亲眼看到"接话"能力的诞生过程。

@@prep 开始之前
沿用前面装好的 PyTorch，这章不用装新东西；家用 CPU 就能跑，不用等显卡。

@@goal 学到这儿就够了
能自己搭出字符级 RNN、跑完训练并采样出句子，能说清每一步在做什么，这章就算过了。

@@map 上一章→本章→下一章
上一章学了 RNN 原理（隐藏状态、BPTT、梯度问题）。**本章用 PyTorch 把原理落成代码：字符级 RNN 歌词生成实战**。下一章进入 LSTM：如果生成效果不好、长歌词前后不连贯，罪魁祸首就是梯度消失——LSTM 的门控机制是解药。

@@point ① 任务定义：字符级文本生成
@@need 要解决什么
"让 RNN 写歌词"具体是个什么任务？它到底在预测什么？

@@idea 核心思路
**字符级文本生成（Char-level Language Model）**：把文本拆成**一个一个字符**（汉字/字母），让模型学会"给定前面的字符，预测下一个字符"。

- 输入：`"床前明月"` → 预测下一个字 → `"光"`。
- 训练目标：最大化每个位置的"下一个字符"预测正确率。
- 预测时：把新预测的字拼回输入，继续预测下一个——**自回归（autoregressive）生成**，像滚雪球一样一句句滚出来。

为什么用字符而不是词：歌词语料通常不大，**字符粒度词汇表小（几千个汉字）**，训练更简单，且天然不用分词。家用 CPU 也能跑。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为预测的是"整句" | 每一步只预测"下一个字符"，整句是反复拼出来的 |
| 语料里混入多余字符 | 只保留歌词文本字符，歌词文件里常见的编号、标题注释要去掉 |

@@point ② 数据准备：把歌词变成数字序列
@@need 要解决什么
一坨歌词文本，怎么变成 RNN 吃得下的 (输入, 目标) 样本对？

@@idea 核心思路
流程三步：**去重建词表 → 字符转索引 → 切样本**。

```python
import torch

text = open("lyrics.txt", encoding="utf-8").read()
chars = sorted(set(text))        # 去重得字符集
char2idx = {c: i for i, c in enumerate(chars)}
idx2char = {i: c for c, i in char2idx.items()}
vocab_size = len(chars)          # 词表大小

# 样本：序列长度 seq_len=20
input_text = "明月几时有把酒问青天"
data = [char2idx[c] for c in input_text]
inputs = torch.tensor(data[:-1])   # 输入："明月几时有把酒问青"
targets = torch.tensor(data[1:])   # 目标："月几时有把酒问青天"
```

关键点：**输入是除掉最后一个的所有字符，目标是除掉第一个的所有字符**——错位一位，正好组成"前一个字 → 下一个字"的监督对。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 目标对了位 | 目标必须是输入右移一位，错位会让模型学到"预测自己" |
| 没处理文件编码 | 中文歌词文件用 utf-8 打开，Windows 下用 gbk 编码的文件要先转码 |

@@point ③ 模型搭建：Embedding + RNN + Linear
@@need 要解决什么
字符索引怎么进入"能算梯度"的网络？模型三层结构怎么搭？

@@idea 核心思路
标准字符级语言模型三层：

```python
import torch.nn as nn

class CharRNN(nn.Module):
    def __init__(self, vocab_size, embed_dim=64,
                 hidden_dim=128):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim)  # 字符→向量
        self.rnn = nn.RNN(embed_dim, hidden_dim, batch_first=True)  # 记忆
        self.fc = nn.Linear(hidden_dim, vocab_size)  # 隐藏→字符概率

    def forward(self, x):
        emb = self.embed(x)
        out, h = self.rnn(emb)
        logits = self.fc(out)   # 每个位置一个"下一个字符"得分
        return logits
```

- **Embedding 层**：字符 ID → 稠密向量（提前用上了第 5 章思想）。
- **RNN 层**：逐字符累计上下文，输出每个位置的隐藏状态（1 个 RNN 单元即可）。
- **Linear 层**：隐藏状态 → 词表大小的 logits，Softmax/交叉熵后即为"下个字符概率"。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 忘了 batch_first | 输入形状 [batch, seq] 时 RNN 要设 batch_first=True，否则维度对不上报错 |
| fc 输出维度写错 | 输出必须是 vocab_size，等于"每个字符一票" |

@@point ④ 训练循环：交叉熵 + 反向传播
@@need 要解决什么
模型搭好了，怎么让它一步步学会"接话"？

@@idea 核心思路
训练循环与分类任务几乎一致，只多了"展平"：

```python
import torch.optim as optim

model = CharRNN(vocab_size)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(100):
    # inputs/targets: [batch, seq] -> [batch*seq]
    loss = criterion(
        model(inputs).reshape(-1, vocab_size),
        targets.reshape(-1),
    )
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(model.parameters(), 5.0)  # 防爆炸
    optimizer.step()
    print(f"epoch {epoch}: loss={loss.item():.4f}")
```

注意两点：**损失在展平的所有位置计算**（每个字符都参与训练），**梯度裁剪兜底**（RNN 训练标配，防梯度爆炸）。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| loss 不降 | 检查 lr（太大震荡太小爬不动）、数据量（太少学不到）、序列长度 |
| 忘了 clip | RNN 极易爆炸，clip 是一定要加的护栏，不加 loss 可能突然 NaN |

@@point ⑤ 采样生成：训练完怎么"写歌词"
@@need 要解决什么
模型学完了，怎么从概率里"续写"出一整段歌词？

@@idea 核心思路
推理时模型只吃"当前字符"，靠自回归一步步生成（temperature 控制随机性）：

```python
def generate(model, start, length=50, temperature=0.8):
    model.eval()
    chars = list(start)
    with torch.no_grad():
        for _ in range(length):
            x = torch.tensor([char2idx[c] for c in chars[-20:]]).unsqueeze(0)
            logits = model(x)[0, -1] / temperature
            probs = torch.softmax(logits, dim=-1)
            next_idx = torch.multinomial(probs, 1).item()
            chars.append(idx2char[next_idx])
    return "".join(chars)

print(generate(model, "明月", 30))
```

关键点：

- **temperature 采样**：温度越低越"保守"（常选最高概率字，重复多但稳）；越高越"有创意"（随机性强，可能乱）。0.6~1.0 常用。
- `torch.multinomial` 按概率分布随机抽，比 `argmax` 更接近人写歌词的多样性。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 温度太低生成复读机 | loss 已收敛但输出全是重复句，把 temperature 调高到 0.8~1.2 再看 |
| 温度太高生成乱码 | 概率几乎均匀随机，接近胡言乱语，调低 |
| 忘了 model.eval() | 不关 dropout/bn，推理结果不稳定 |

@@point ⑥ 效果评估：怎么判断"歌词写得像不像"
@@need 要解决什么
生成的句子没法用准确率衡量，怎么客观判断效果好？

@@idea 核心思路
文本生成的质量评估要"多角度"：

1. **损失值（loss）**：越低说明模型越"懂"训练文本的统计规律（但过拟合会背诗而不泛化）。
2. **困惑度（Perplexity）**：语言模型标准指标 = exp(交叉熵)，越小越好，等价于"平均几个候选里选对"。
3. **人工可读性**：抽 10 句生成结果，看语句通顺度、主题延续性、有没有"自创但合理"的词组。
4. **多样性**：同一提示词跑多次，看输出是否单调重复（复读机=采样策略问题）。

工程建议：**loss 是过程指标，人工抽读是验收指标**——多跑几个 temperature 对比，挑观感最好的一组参数存档。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 只看 loss 判断生成质量 | loss 低但输出可能机械复刻训练句，必须配合人工抽读 |
| 一次生成就定论 | 采样有随机性，同一模型多生成几次再评价，别拿单次结果下结论 |

@@point ⑦ 实战中的常见坑与调参经验
@@need 要解决什么
跑完发现效果差，一般卡在哪？先调什么？

@@idea 核心思路
按"影响力"排序的经验清单：

1. **数据量**：几百行歌词太少，至少几万行；数据决定上限，模型只是逼近上限。
2. **序列长度**：太短记忆不足（前后不连贯），太长训练慢且 RNN 记不住——20~50 字符起步。
3. **hidden 维度**：64~256 常用，太小欠拟合、太大过拟合（小数据尤其明显）。
4. **学习率**：0.001~0.01 起步，loss 震荡就降。
5. **epoch 数量**：观察 loss 曲线，平台期就停；**过拟合时训练 loss 降、生成质量反而退步**。
6. **换 LSTM**：如果长句不连贯，RNN 的梯度消失是元凶——直接换 LSTM（下一章）通常明显改善。

排查原则：**一次只动一个变量**，对照 loss 和人工输出决定去留。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 小语料上堆大模型 | 参数越多越容易背训练集，输出全是原文碎片；数据少就减小 hidden/加深正则 |
| 调参毫无章法 | 先固定数据/序列长度/学习率，再逐个动 hidden、epoch、temperature |

@@point ⑧ 本项目与真实语言模型的关系
@@need 要解决什么
这个几十行的"玩具 RNN"和 ChatGPT 有多大关系？

@@idea 核心思路
关系比想象中大得多——**原理完全同源**：

- **任务一致**：都是"给定前文，预测下一个 token"（自回归语言建模），只是 token 从"字符"换成"子词"。
- **训练一致**：同样的交叉熵 + 梯度下降，只是数据规模从几万字到几万亿 token。
- **生成一致**：同样的 temperature 采样自回归续写。
- **差异在规模与架构**：GPT 把 RNN 换成 Transformer（并行 + 长依赖），把几万字语料换成几万亿 token 的预训练规模。

所以这一章你亲手写出的 `generate()` 函数，就是大模型"对话生成"的最小原型——把数据换成全网语料、RNN 换成 96 层 Transformer，就是 GPT 的雏形。理解了这个，后面看 GPT 就完全不会陌生。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为玩具项目没用 | 它是理解大模型的最小切片，调参经验（温度、过拟合、数据质量）全部可迁移 |
| 过度简化"只是放大" | 放大带来工程质变（RLHF、并行、对齐），但"预测下一个词"的内核不变 |

@@summary
本章完成了 RNN 的第一个真实项目：

| 环节 | 关键点 |
|---|---|
| 任务定义 | 字符级自回归：预测下一个字符 |
| 数据准备 | 建字符表、字符转索引、错位切样本 |
| 模型 | Embedding → RNN → Linear(vocab) |
| 训练 | 交叉熵 + 梯度裁剪 + Adam |
| 生成 | temperature 采样自回归续写 |
| 评估 | loss + 困惑度 + 人工抽读 + 多样性 |
| 调参 | 数据>序列长度>维度>lr>epoch |
| 与大模型关系 | 同一内核，规模与架构差异 |

一句话记住本章：**字符级 RNN 歌词生成就是"预测下一个字"的最小语言模型：数据错位成样本、训练用交叉熵加梯度裁剪、生成靠 temperature 采样，而它和 GPT 的区别只是"换模型 + 换数据规模"——有了这个项目打底，后面学 Transformer 的大模型会顺很多。**

@@quiz
1. 字符级文本生成中，模型每一步的输入输出分别是什么？"自回归"指什么？
2. 数据切样本时为什么要"右移一位"生成目标？
3. 画出 CharRNN 的三层结构，说明每层各自的作用。
4. 训练时为什么要 `reshape(-1, ...)` 算损失？梯度裁剪起什么作用？
5. temperature 的高与低分别会对生成结果产生什么影响？你会怎么选取？
6. 生成质量差时，按影响力排序，你首先会检查什么？
7. 这一章的 generate() 和 GPT 的对话生成，原理上有什么异同？

@@links
参考|RNN歌词生成实战|#
文档|PyTorch 文本生成教程（官方）|https://pytorch.org/tutorials/intermediate/char_rnn_generation_tutorial.html
文档|nn.RNN API 文档|https://pytorch.org/docs/stable/generated/torch.nn.RNN.html