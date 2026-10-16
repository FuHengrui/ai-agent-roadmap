---
name: pdf-complex-extract
description: Use when a PDF cannot be handled by simple text extraction — scanned/image-only PDFs with no text layer, multi-column academic layouts where reading order matters, PDFs with complex tables, or math-heavy documents. Provides a decision tree and the concrete options (local OCR, Marker, cloud APIs) with their hardware costs. Do not use this for ordinary single-column lecture PDFs — pdf-lecture-extract is faster and needs no extra dependencies.
license: MIT (本技能为本项目自建)
compatibility: 首选方案需 tesseract-ocr；Marker 方案需 Python 3.10+ / PyTorch / 推理服务，**不建议在 4GB 无 GPU 机器上本地运行**
---

# 复杂 PDF 提取

## Overview

`pdf-lecture-extract` 处理不了的那类 PDF，用这个技能。

**先判断是不是"复杂 PDF"。** 不是的话别用这个技能——纯属浪费。

## When to Use

**判断标准：跑完 `pdf-lecture-extract` 之后，出现下面任一情况：**

| 症状 | 说明 | 属于 |
|---|---|---|
| `_summary.txt` 报 `⚠️ 很可能是扫描版` | 平均每页文字 < 40 字，内容在图片里 | 扫描版 |
| 抽出来的文字是乱码 | PDF 用了自定义编码 | 编码异常 |
| 文字读起来**顺序是乱的** | 多栏排版被按列串读 | 多栏 |
| 表格抽出来是一堆错位文字 | 复杂表格 | 表格 |
| 公式变成了乱码符号 | 没有 LaTeX 层 | 公式 |

**不复杂就别用**：单栏、以文字为主的讲义，`pdf-lecture-extract` 完全够用，而且零依赖。

## Decision Tree

```
跑 pdf-lecture-extract
        ↓
  看 _summary.txt
        ↓
  ┌─ "文字提取正常" ──────────→ ✅ 就这样用，图自己看
  │
  ├─ "⚠️ 扫描版" ────────────→ ① tesseract OCR（轻量，先试这个）
  │                            ② 不行 → Marker 云端 API
  │
  ├─ 乱码 / 多栏 / 复杂表格 ──→ Marker（云端 API，别本地跑）
  │
  └─ 只是想看图里的内容 ─────→ 不用换工具！直接把 images/ 里的图读出来看
```

## Option 1: OCR（扫描版的首选）

**轻量，本地可跑。**

```bash
# 1) 装 tesseract（Windows 装 UB-Mannheim 版）
# 2) 装 Python 绑定
python -m pip install pytesseract pdf2image pillow

# 3) PDF → 图片 → OCR
python -c "
import pytesseract
from pdf2image import convert_from_path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
for i, img in enumerate(convert_from_path('讲义.pdf', dpi=200), 1):
    print(f'## 第 {i} 页')
    print(pytesseract.image_to_string(img, lang='chi_sim+eng'))
"
```

**中文识别要装语言包**：`chi_sim`（简体）。没装的话默认只有英文，中文会全是乱码。

**注意**：OCR 对**排版复杂**的页面效果一般（分栏、表格会串行）。简单页面够用。

## Option 2: Marker（复杂 PDF 的正解）

[datalab-to/marker](https://github.com/datalab-to/marker)（40k ⭐，Apache 2.0 代码授权）

**能力**：PDF / 图片 / PPTX / DOCX / XLSX → Markdown / JSON / HTML
**强项**：多栏阅读顺序、表格→HTML、公式→LaTeX、去页眉页脚、**图片可转文字描述**

### ⚠️ 不要在本机本地跑

Marker 需要：

| 要求 | 说明 |
|---|---|
| PyTorch | CPU 版就有 2–3 GB |
| 推理服务 | NVIDIA GPU → vllm + Docker；CPU → llama.cpp 的 `llama-server` |
| 模型 | surya 是**视觉语言模型**，吃内存 |

**4GB 无 GPU 的机器跑它，会非常痛苦。** 用下面的云端方案。

### 推荐用法：云端 LLM + 轻量本地

```bash
pip install marker-pdf

# 关键：--use_llm 让推理走云端，本地只跑小的布局模型
marker_single 讲义.pdf \
  --output_format markdown \
  --use_llm \
  --llm_service marker.services.openai.OpenAIService \
  --openai_base_url https://api.deepseek.com \
  --openai_model deepseek-chat \
  --openai_api_key $env:LLM_API_KEY
```

**参数说明**：

| 参数 | 作用 |
|---|---|
| `--use_llm` | 用 LLM 提升质量（合并跨页表格、格式修正），**并让图片变成描述** |
| `--disable_image_extraction` | 不导出图片文件。**配合 `--use_llm` 时，图会被替换成文字描述** |
| `--mode fast` | CPU 优化模式（GPU 上默认 balanced，质量更高） |
| `--page_range "0,5-10"` | 只处理指定页 |
| `--force_ocr` | 强制 OCR（应对乱码） |

### 纯云端（零本地依赖）

Datalab 提供托管 API，免费额度 $5：

```bash
pip install datalab-python-sdk
```

适合：**偶尔处理几份复杂 PDF**，不值得为它装 PyTorch。

**注意**：把文件传到云端 = 内容出了本机。**如果 PDF 含敏感内容，不要用云端。**

## Option 3: 只是想看图（最容易被忽略）

**如果 `pdf-lecture-extract` 已经导出了 `images/`，而你只是想知道图里是什么 ——
不要换工具，直接把图读出来看。**

前提：**你（智能体）是多模态的、能读图。**

这一步比任何工具都快，而且没有中间转述的信息损失。

## Pitfalls

| 现象 | 原因 / 处理 |
|---|---|
| tesseract 中文全是乱码 | 没装 `chi_sim` 语言包 |
| Marker 报 out of memory | 内存不够。降 `--workers`、拆小 PDF、或改用云端 |
| Marker 起不来推理服务 | 没装 `llama-server`（CPU）或 Docker+NVIDIA Toolkit（GPU） |
| Marker 结果比预期差 | 试试 `--force_ocr`（PDF 里的文字层可能是坏的） |
| 云端 API 费用失控 | **先 `--page_range` 跑 2 页试水**，确认效果再整本跑 |
| 多栏还是乱 | 确认用的是 Marker 而不是 OCR；OCR 处理分栏会串行 |

## 授权注意

- **Marker 代码**：Apache 2.0，**可商用**
- **Marker 模型权重**：modified AI Pubs Open Rail-M —— 研究、个人、**营收/融资 < $5M 的初创免费**；超过要付费
- 如果你的产出准备**商业售卖**，用之前先确认这条

## Notes

- 这个技能是**方案文档**，不是脚本。选好方案后照上面命令行执行。
- **先试最轻的方案**：OCR 比 Marker 轻得多，Marker 云端比本地轻得多。
- 处理完复杂 PDF 后，后续流程和普通 PDF 一样：**图要自己看，然后按知识库规格写内容**。
