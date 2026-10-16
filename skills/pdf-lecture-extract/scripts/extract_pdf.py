# -*- coding: utf-8 -*-
"""PDF 讲义提取器 —— 把讲义 PDF 转成「可读的文字 + 可看的图片」。

为什么需要它
------------
讲义是 PDF，AI 直接读 PDF 有两个问题：
  1. 页数多、排版散，直接读会浪费大量 token 且容易漏内容
  2. **讲义里的图（架构图、截图、流程图）往往比文字更重要**，
     但纯文字提取会把图丢掉

这个脚本一次做完两件事：
  · 文字 → 带页码标记的 Markdown（方便引用「第 3 页说……」）
  · 图片 → 导出成 PNG 文件，AI 可以逐个「看」并描述

用法
----
    python extract_pdf.py <pdf路径> [输出目录]

    # 例：抽一章的讲义
    python extract_pdf.py "D:\\课程\\章节1\\Mysql.pdf" "D:\\临时\\mysql"

输出
----
    <输出目录>/
    ├── <名字>.md           带页码的文字
    ├── images/             导出的图片（已过滤掉小图标）
    └── _summary.txt        统计摘要（页数/字数/图数）

退出码
------
    0  正常
    1  参数错误 / 文件不存在
    2  打开失败（加密、损坏）
"""

from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 小于这个尺寸的图基本是图标/装饰，跳过
MIN_IMG_BYTES = 6 * 1024
# 文字少于此值/页，判定为「扫描版」（文字靠图承载）
SCANNED_THRESHOLD = 40


def clean_text(t: str) -> str:
    """PDF 抽出来的文字常有奇怪换行和多余空格，收拾一下。"""
    t = t.replace("\u00a0", " ").replace("\ufeff", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return "\n".join(ln.rstrip() for ln in t.split("\n")).strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    src = Path(sys.argv[1])
    if not src.exists():
        print("!! 找不到文件：%s" % src)
        return 1

    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / (src.stem + "_提取")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"
    img_dir.mkdir(exist_ok=True)

    try:
        import pymupdf
    except ImportError:
        print("!! 缺 pymupdf，先装：python -m pip install pymupdf")
        return 2

    try:
        doc = pymupdf.open(src)
    except Exception as e:  # noqa: BLE001
        print("!! 打开失败：%s" % e)
        return 2

    if doc.is_encrypted and not doc.authenticate(""):
        print("!! PDF 有密码，无法打开")
        return 2

    print("=" * 70)
    print("  提取：%s" % src.name)
    print("=" * 70)
    print("  页数：%d" % doc.page_count)

    md = ["# %s\n" % src.stem, "> 由 extract_pdf.py 从讲义 PDF 自动提取\n"]
    total_chars = 0
    img_count = 0
    seen_xref = set()
    per_page = []

    for i in range(doc.page_count):
        page = doc[i]
        text = clean_text(page.get_text())
        total_chars += len(text)
        per_page.append(len(text))

        md.append("\n---\n\n## 第 %d 页\n" % (i + 1))
        md.append(text if text else "（本页没有文字，内容可能是图片）")

        # ---- 抽图 ----
        for i2, info in enumerate(page.get_images(full=True)):
            xref = info[0]
            if xref in seen_xref:          # 同一张图在多页复用，只导一次
                continue
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.width < 60 or pix.height < 60:
                    continue
                if pix.n - pix.alpha >= 4:  # CMYK → RGB
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                data = pix.tobytes("png")
                if len(data) < MIN_IMG_BYTES:
                    continue
                name = "p%03d_%d.png" % (i + 1, i2 + 1)
                (img_dir / name).write_bytes(data)
                seen_xref.add(xref)
                img_count += 1
                md.append("\n> 📷 本页有图：`images/%s`（%d×%d）\n" % (name, pix.width, pix.height))
            except Exception:  # noqa: BLE001
                continue

    md_path = out_dir / (src.stem + ".md")
    md_path.write_text("\n".join(md), encoding="utf-8")

    avg = total_chars / max(doc.page_count, 1)
    lines = [
        "文件：%s" % src.name,
        "页数：%d" % doc.page_count,
        "字数：%d（平均 %.0f 字/页）" % (total_chars, avg),
        "导出图片：%d 张" % img_count,
        "文字版：%s" % md_path.name,
        "图片目录：images/",
        "",
    ]
    if avg < SCANNED_THRESHOLD:
        lines += [
            "⚠️ 这份 PDF 每页文字很少 —— 很可能是【扫描版】或【以图为主】。",
            "   处理建议：不要只依赖文字，务必逐张看 images/ 里的图。",
        ]
    else:
        lines.append("✓ 文字提取正常，图片已单独导出（图里的信息也要看）")

    (out_dir / "_summary.txt").write_text("\n".join(lines), encoding="utf-8")

    print()
    for ln in lines:
        print("  " + ln)
    print()
    print("  输出目录：%s" % out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
