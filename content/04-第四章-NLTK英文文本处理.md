@@h1 第四章　NLTK英文文本处理
@@sub 阶段 22 · 自然语言处理与Transformer架构　|　英文处理　|　难度 ★★☆

@@why 这一章在解决什么问题
中文有 jieba，英文呢？英文虽然天然空格分词，但"run、runs、ran、running"要归成一个词，"New York"是一个整体还是两个词？这一章引入英文 NLP 的老牌工具库 **NLTK**：学会分句分词、词形还原（lemmatization）、Text 对象、分块（chunking）和名词短语提取，把英文词法加工的活补齐。

@@prep 开始之前
要装 nltk，还要下载 punkt、wordnet 这些数据包，第一次跑之前先下好。

@@goal 学到这儿就够了
能对英文做分句分词、词形还原和名词短语提取，能说清词干提取与词形还原的区别，这章就算过了。

@@map 上一章→本章→下一章
上一章把中文词法（分词、关键词、词性）打通了。**本章切换到英文战场：NLTK 的分句分词、词形还原、分块与名词短语提取**，顺便对比中英文工具链的异同。下一章进入词向量：Word2Vec 如何用稠密向量表达词义，这是从"词法"迈向"语义"的分水岭。

@@point ① NLTK 是什么
@@need 要解决什么
处理英文文本（分词、还原、语法分析），有没有一站式工具？

@@idea 核心思路
**NLTK（Natural Language Toolkit）** 是 Python 最老牌、最经典的英文 NLP 工具库，提供从分词、词形还原、词性标注到句法分析、语料库的一整套能力：

- **文本处理**：分句、分词、停用词过滤。
- **词形处理**：词干提取、词形还原。
- **语法层面**：分块、句法树、命名实体识别（简单版）。
- **语料库**：内置电影评论、布朗语料等，可当教学与研究数据。

安装：

```bash
pip install nltk
```

首次使用部分功能需下载数据资源：`nltk.download('punkt_tab')   # NLTK 3.8.2+ 分词要用 punkt_tab，只下 punkt 会 LookupError`（分词模型）、`nltk.download('wordnet')`（词形还原词典）等。它是英文文本分析的标准起点，非常适合做特征工程和小型 NLP 实验。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 装完不下载数据资源直接跑 | 会报 `LookupError`，按提示 `nltk.download('xxx')` 下载对应资源 |
| 拿 NLTK 处理中文 | 它的分词器、语料以英文为主，中文请用 jieba |

@@point ② 分句与分词：英文也没有想象中简单
@@need 要解决什么
英文按空格 split 就行？遇到 "Dr. Smith" 和 "U.S.A." 怎么办？

@@idea 核心思路
英文初中级用法是空格分词，但**标点粘连**是坑：`Dr.` 里的句点不是句子结束、`U.S.A.` 里的点不能拆开。NLTK 的分句分词器专门处理这类歧义：

```python
import nltk
nltk.download('punkt_tab')   # NLTK 3.8.2+ 分词要用 punkt_tab，只下 punkt 会 LookupError

from nltk.tokenize import sent_tokenize, word_tokenize

text = "Dr. Smith visited the U.S.A. He loves NLP."
sentences = sent_tokenize(text)
print(sentences)
# ['Dr. Smith visited the U.S.A.', 'He loves NLP.']
tokens = word_tokenize(sentences[0])
print(tokens)
# ['Dr.', 'Smith', 'visited', 'the', 'U.S.A.', '.']
```

`sent_tokenize` 分句、`word_tokenize` 分词，底层用无监督算法学习"哪些句点是句子边界"，比无脑 split 稳得多。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 直接 `text.split()` 做英文分词 | 标点粘连、缩写会被拆坏，规范做法用 word_tokenize |
| 忘了分句直接长文本分词 | 句号本身是 token，分析语法前先分句更符合语言结构 |

@@point ③ 词干提取 vs 词形还原
@@need 要解决什么
"running、runs、ran"和"run"在统计时算一个词吗？怎么归一？

@@idea 核心思路
英文有丰富变形（复数、时态、比较级），需要把变形词归回原型。两条路线：

- **词干提取（Stemming）**：粗暴砍后缀，`running → runn`，可能得到非完整词。
- **词形还原（Lemmatization）**：基于词典和词性还原为**合法词元**，`running(v) → run`，`better(a) → good`。

```python
from nltk.stem import WordNetLemmatizer

lemmatizer = WordNetLemmatizer()
print(lemmatizer.lemmatize("running", "v"))  # run
print(lemmatizer.lemmatize("better", "a"))   # good
print(lemmatizer.lemmatize("cats"))          # cat（默认按名词）
```

词形还原通常**配合词性标注**使用（动词按动词还原、名词按名词还原），结果更准确；词干提取更快但可能产生非词。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 混淆 stemmer 和 lemmatizer | 前者机械砍后缀、不保证是词；后者查词典还原、结果是原型词 |
| 还原时不传词性 | 不传词性默认按名词还原，动词变形（running）还原不出来，先 pos 标注再还原 |

@@point ④ Text 对象：NLTK 的文本容器
@@need 要解决什么
把一篇文章"打包"成可统计、可检索的对象，NLTK 提供了什么便捷结构？

@@idea 核心思路
**`nltk.text.Text`** 是对词列表的高层封装，自带很多文本分析方法和属性：

```python
from nltk.book import text1  # 内置《白鲸》文本，演示用
# 或：Text(word_tokenize(content))

len(text1)          # 总词数
sorted(set(text1))  # 去重后的词汇表
text1.count("whale")   # 词频
text1.concordance("monster")  # 上下文检索（KWIC）
text1.similar("ship")  # 找出用法相似的词
text1.dispersion_plot(["whale", "ship"])  # 词分布图
```

它在教学和快速探索文本时特别顺手：一句话完成词频、上下文、相似词查询，不必自己写循环。生产环境通常用更重的工具，但 Text 对象做"先看一眼数据"很高效。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 以为 Text 是唯一容器 | 它只是便捷封装，底层还是 token 列表；要精细控制就自己处理列表 |
| `from nltk.book import *` 卡住 | 首次加载 book 语料会先提示下载，在无网络环境要提前下载资源 |

@@point ⑤ 分块（Chunking）：把词拼成短语
@@need 要解决什么
词序列有了，怎么把它们拼成"名词短语""动词短语"这种更大的语法单位？

@@idea 核心思路
**分块（Chunking）** 是把**相邻的词按规则聚合成短语块**，通常基于词性标注结果：

```python
import nltk
from nltk import pos_tag, RegexpParser
from nltk.tokenize import word_tokenize

sentence = "The quick fox jumps over the lazy dog."
tokens = word_tokenize(sentence)
nltk.download('averaged_perceptron_tagger_eng')   # 词性标注器要单独下
tagged = pos_tag(tokens)   # 先做词性标注

# 规则：名词短语 = 可选冠词/形容词 + 名词
grammar = "NP: {<DT>?<JJ>*<NN.*>}"
parser = RegexpParser(grammar)
tree = parser.parse(tagged)
print(tree)
```

分块使用的是**正则式语法**：`{<DT>?<JJ>*<NN.*>}` 表示"DT(冠词)可选 + JJ(形容词)任意个 + NN(名词)"拼成一个名词短语 NP。分块是句法分析的轻量版：不要求完整句法树，只按模式抓取感兴趣的短语。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 正则语法写错导致空结果 | 模式里的标签必须与 pos_tag 输出一致（NN、NNS、NNP…），先打印 tagged 核对 |
| 以为分块=句法分析 | 分块只做局部短语归并，不分析句子整体结构（谁修饰谁、主谓宾关系） |

@@point ⑥ 名词短语提取：专有名词的高级外挂
@@need 要解决什么
"New York""artificial intelligence"这种多词整体，怎么一次性抽出来？

@@idea 核心思路
**名词短语提取】常见套路 = 分块规则提取 NP + 过滤**：用上一节的分块把 `DT? JJ* NN*` 归并为 NP，再取每个 NP 的叶子词拼回短语：

```python
from nltk import pos_tag, RegexpParser
from nltk.tokenize import word_tokenize

text = "New York is a big city. AI changes education."
tagged = pos_tag(word_tokenize(text))
grammar = "NP: {<NNP>+|<DT>?<JJ>*<NN.*>}"
tree = RegexpParser(grammar).parse(tagged)

for subtree in tree.subtrees(filter=lambda t: t.label() == "NP"):
    words = [w for w, t in subtree.leaves()]
    print(" ".join(words))
# 输出形如：New York  city  AI  education
```

`<NNP>+` 专门连续捕捉专有名词（New York），普通名词短语规则兜底其他 NP。这套组合在**实体词提取、关键词扩展**里很实用。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 用分块做复杂实体识别 | 人名地名嵌套、缩写场景分块规则会漏，正式场景用命名实体识别（NER）模型 |
| 提取结果含重复子串 | NP 嵌套时（大短语包小短语）会重复输出，用后处理去重 |

@@point ⑦ 停用词表：英文也有"的、了"
@@need 要解决什么
英文里 "the、a、is、of" 这类词怎么快速过滤？

@@idea 核心思路
NLTK 内置了常用**英文停用词表**：

```python
from nltk.corpus import stopwords
nltk.download('stopwords')

stop = set(stopwords.words('english'))
tokens = ["I", "love", "the", "sun", "and", "moon"]
filtered = [w.lower() for w in tokens if w.lower() not in stop]
print(filtered)
# ['love', 'sun', 'moon']
```

要点：

- 停用词过滤前通常先 `lower()` 统一大小写，否则 "The" 和 "the" 不一致。
- 要不要过滤要对齐任务：情感分析里 "not"（其实在停用词表里，做情感分析时要专门剔掉）语义重要，别乱过滤；主题抽取可以过滤。
- 可以组合 `stopwords.words('english')` 与自己的领域停用词表取并集。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 过滤前不转小写 | "The" ≠ "the"，停用词匹配不到，白过滤 |
| 通用停用词表不够 | 不同领域要补白名单/黑名单，别一刀切 |

@@point ⑧ 拼一个英文文本分析小流水线
@@need 要解决什么
把 NLTK 的分词、停用词、词形还原、词频串起来，怎么组一条完整链路？

@@idea 核心思路
典型英文预处理流水线（也是很多任务的标准模板）：

```python
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from collections import Counter

def clean_text(text):
    tokens = word_tokenize(text.lower())
    stops = set(stopwords.words("english"))
    lemm = WordNetLemmatizer()
    result = []
    for w, tag in pos_tag(tokens):
        if w in stops or not w.isalpha():
            continue  # 过滤停用词和非字母
        # 简化词性映射：前两位识别 v/a/n
        pos = tag[0].lower()
        if pos not in "van":
            pos = "n"
        result.append(lemm.lemmatize(w, pos))
    return result

text = "The cats are running quickly in the park."
print(Counter(clean_text(text)))
# Counter({'cat': 1, 'run': 1, 'park': 1, ...})
```

链路：**小写化 → 分词 → 词性标注 → 停用词过滤 → 按词性还原 → 统计**（注意标注在过滤之前——人是代词、the 是限定词，这些判断得靠词性；先过滤掉它们，词性标注反而更不准）。每一步都有对应 NLTK 组件，这套模板可直接应用到分类、主题、相似度等任务的特征构建上。

@@trap 坑在哪
| 现象 | 原因 / 怎么办 |
|---|---|
| 顺序颠倒（先还原再过滤/先过滤再标注） | 词性标注要在过滤前做（过滤掉的词不影响），还原要在标注后做（依赖词性） |
| `w.isalpha()` 把 "A.I." 这类切碎 | 简单清洗会丢缩写，需要的话另行处理连字符/缩写规则 |

@@summary
本章走完英文 NLTK 的整条词法链：

| 问题 | 答案 |
|---|---|
| NLTK | Python 经典英文 NLP 工具库 |
| 分句分词 | sent_tokenize / word_tokenize，处理缩写标点 |
| 词形还原 | Lemmatizer 基于词典还原，通常配 pos_tag |
| Text 对象 | 词列表的高层封装，内置统计/检索/相似词 |
| 分块 | 基于词性规则把词拼成短语（NP/VP） |
| 名词短语 | NNP 连续提取 + NP 规则，抽取多词实体 |
| 停用词 | stopwords.words('english')，配套小写化 |
| 流水线 | 小写→分词→停用词→标注→还原→统计 |

一句话记住本章：**英文处理用 NLTK 一条链走完：word_tokenize 分词、stopwords 过滤、pos_tag 标注、WordNetLemmatizer 还原，分块规则则可以按模式拼出名词短语——和 jieba 那条线是"中文版/英文版"的同构工具书。**

@@quiz
1. NLTK 的 sent_tokenize 和 word_tokenize 解决什么问题？为什么比直接 split 稳？
2. 词干提取和词形还原的区别是什么？为什么词形还原通常要配合词性标注？
3. 什么是分块（Chunking）？"NP: {<DT>?<JJ>*<NN.*>}" 这条规则表达了什么？
4. Text 对象提供了哪些开箱即用的分析方法？
5. 英文停用词过滤前为什么要统一小写？
6. 写出英文文本预处理的完整流水线顺序，并说明为什么顺序不能乱。
7. 想抽取文本中的多词专有名词（如 New York），应该怎么做？

@@links
参考|NLTK英文处理|#
文档|NLTK 官方文档与教程|https://www.nltk.org/
文档|NLTK Book（在线教材）|https://www.nltk.org/book/