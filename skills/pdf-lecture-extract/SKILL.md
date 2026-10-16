---
name: pdf-lecture-extract
description: Use when you need to read a lecture PDF (讲义) before writing knowledge-base content, or any time you must extract text and images from a PDF that a human wrote for teaching. Handles page-marked text extraction, embedded image export, and scanned-PDF detection. Do not use for filling PDF forms or editing PDFs — this skill is read-only extraction optimized for course handouts.
license: MIT (本技能为本项目自建，可自由修改)
compatibility: 需要 Python 3.10+ 与 pymupdf（pip install pymupdf）· 无需网络 · 只读操作
---

# PDF 讲义提取

## Overview

把讲义 PDF 转成「AI 好读的文字 + AI 好看的图片」。

**为什么需要它：** 讲义 PDF 直接读有两个问题——

1. 页数多、排版散，直接读浪费大量 token，还容易漏内容
2. **讲义里的图（架构图、截图、流程图）往往比正文更重要**，纯文字提取会把图全丢掉

这个技能一次做完两件事：文字按页导出、图片单独导出。

## When to Use

在这些情况下用：

- 准备写某一章知识库，要先读该章的讲义 PDF
- 需要把 PDF 里的内容变成可引用的文本（带页码，方便说「第 3 页讲了……」）
- 讲义里有关键的图，需要**看到**它们（架构图、界面截图、流程图）
- 不确定一份 PDF 是「文字版」还是「扫描版」

**不要用于：** 填写 PDF 表单、编辑/合并/拆分 PDF、做 OCR。这个技能只做只读提取。

## Quick Start

```bash
# 基本用法：输出到 PDF 同目录下的「<名字>_提取」文件夹
python scripts/extract_pdf.py "D:\课程\章节1\Mysql.pdf"

# 指定输出目录（推荐，输出到临时工作区）
python scripts/extract_pdf.py "D:\课程\章节1\Mysql.pdf" "D:\临时\mysql"
```

输出结构：

```
<输出目录>/
├── <名字>.md          ← 带页码标记的正文
├── images/            ← 导出的图片（已过滤掉小图标）
│   ├── p003_1.png
│   └── p007_2.png
└── _summary.txt       ← 统计摘要（页数 / 字数 / 图数 / 是否扫描版）
```

## Reading the Output

### `_summary.txt` 先看这个

| 里面的提示 | 含义 | 你该怎么做 |
|---|---|---|
| `✓ 文字提取正常` | 文字够多 | 以文字为主，**但图仍要逐张看** |
| `⚠️ 很可能是扫描版/以图为主` | 平均每页文字 < 40 字 | **文字不可靠，必须逐张看 images/** |

### Markdown 里的页码标记

正文按 `## 第 N 页` 分段。**写知识库时可以据此引用**，例如「讲义第 12 页给出的架构是……」。

图的位置有标记：`> 📷 本页有图：images/p003_1.png（800×600）`

## Critical Rule

> **图要逐张看，但别指望每张都是干货。**

实测经验（系列讲义）：一份 61 页的 PDF 抽出 11 张图，**其中多数是「章节封面页」**——
紫底大字写着「依赖注入-路由级 FastAPI」这种，没有技术信息。

所以正确的做法是**先快速扫一遍缩略图，再精读有价值的那些**。分类如下：

| 图的样子 | 是什么 | 处理 |
|---|---|---|
| 紫底/渐变底 + 大字标题 | **章节封面**，装饰用 | 跳过 |
| 白底 + 框线/箭头 + 方框文字 | 架构图、流程图 | ★ **必读，文字里没有等价描述** |
| 软件界面截图 | 操作步骤 | ★ **必读** |
| 表格截图 | 数据 | ★ **必读，数字只在图里** |
| 内存/栈堆示意图 | 概念图 | ★ **必读，这是理解的关键** |
| Excel/代码截图 | 示例 | 按需读 |

**别因为看到几张封面图就认为「这个 PDF 的图没用」而全部跳过。**


## Workflow

写一章知识库时，标准流程是：

```
1. 找到该章的讲义 PDF（在「文档」目录里）
2. 跑这个脚本抽文字和图片
3. 先读 _summary.txt，判断是文字版还是扫描版
4. 读 Markdown 正文（按页读，别一次全读——可能很长）
5. 【关键】逐张看 images/ 里的图，把图里的信息补进理解
6. 用自己的话按知识库规格写章节内容
```

## Pitfalls

| 现象 | 原因 / 处理 |
|---|---|
| `ModuleNotFoundError: pymupdf` | 装一下：`python -m pip install pymupdf` |
| 输出目录里一张图都没有 | 正常。有些讲义是纯文字 PDF，图不在内嵌对象里 |
| 抽出来的文字是一堆乱码 | PDF 用了自定义编码。**别硬啃，换 `pdf-complex-extract` 技能** |
| 文字正常但排版全乱 | 正常现象。PDF 的排版信息在文字提取时会丢失，**不要试图还原排版** |
| PDF 有密码 | 脚本会报错退出。找无密码的版本 |
| 页数很多（>200 页） | 文字会很啰嗦。**先只读前几页判断结构，再挑需要的页精读** |

## When to Switch to Another Skill

**这个技能的边界很清楚：适合「单栏、以文字为主」的讲义。**

遇到下面情况，**别在这里硬啃，转 `pdf-complex-extract` 技能**：

| 症状 | 去哪 |
|---|---|
| `_summary.txt` 报 `⚠️ 很可能是扫描版` | → `pdf-complex-extract`（先试 OCR） |
| 抽出来是乱码 | → `pdf-complex-extract` |
| **多栏排版**（学术论文、杂志），文字顺序读起来是乱的 | → `pdf-complex-extract`（用 Marker） |
| 有**复杂表格**，抽出来是错位文字 | → `pdf-complex-extract`（用 Marker） |
| 公式全变成乱码符号 | → `pdf-complex-extract` |

**但如果只是"想看图里画的是什么"—— 不用换工具。**
直接把 `images/` 里的图读出来看就行（前提是你自己能读图）。

## Notes

- 同 `xref` 的图片只导一次（讲义常把同一张图在正文和目录里各放一次）
- 小于 6 KB 或小于 60×60 的图会被跳过（那基本是项目符号和装饰）
- CMYK 图会自动转 RGB，保证 PNG 能正常打开
- **这个技能是只读的**，不会修改源 PDF
