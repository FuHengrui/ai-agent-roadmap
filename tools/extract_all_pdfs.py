# -*- coding: utf-8 -*-
"""批量提取多个阶段里的讲义 PDF。

结构会镜像原目录，输出到 _建立知识库\\_阶段NN提取\\<阶段名>\\<章>\\<PDF名>\\

用法：
    python extract_all_pdfs.py 5 6 7 8
    python extract_all_pdfs.py 5 6 7 8 --force     # 已提取过的也重做

跳过规则：输出目录里已经有 <PDF名>.md 就跳过（除非 --force）。
"""

from __future__ import annotations

import io
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ======================================================================
#  配置区 —— 按你自己的环境改
# ======================================================================
PY = sys.executable          # 用当前解释器

# 讲义提取脚本（见本仓库 skills/pdf-lecture-extract/）
EXTRACTOR = (Path(__file__).resolve().parent.parent
             / "skills" / "pdf-lecture-extract" / "scripts" / "extract_pdf.py")

# 原始资料目录（按阶段分文件夹，形如 "1.xxx" "2.xxx"）
SRC_BASE = Path(os.environ.get("SRC_BASE", r"D:\课程资料"))

# 提取结果输出到仓库根目录下的 _提取/
OUT_BASE = Path(__file__).resolve().parent.parent


def human(n: float) -> str:
    return "%.1f MB" % (n / 1024 / 1024) if n > 1024 * 1024 else "%.1f KB" % (n / 1024)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv

    if not args:
        print(__doc__)
        return 1

    if not EXTRACTOR.exists():
        print("!! 找不到提取脚本：%s" % EXTRACTOR)
        return 1

    grand_t0 = time.time()
    total_pdf = done = skipped = failed = 0
    total_img = 0

    for num in args:
        # 找该阶段的目录（名字以 "N." 开头）
        cands = [d for d in SRC_BASE.iterdir() if d.is_dir() and d.name.startswith(num + ".")]
        if not cands:
            print("\n  !! 找不到阶段 %s（以 '%s.' 开头的目录）" % (num, num))
            continue
        stage = cands[0]
        out_stage = OUT_BASE / ("_阶段%s提取" % num.zfill(2)) / stage.name

        pdfs = sorted(stage.rglob("*.pdf"))
        print("\n" + "=" * 74)
        print("  阶段 %s  ——  %s" % (num, stage.name))
        print("  找到 %d 个 PDF，输出到 %s" % (len(pdfs), out_stage.name))
        print("=" * 74)
        total_pdf += len(pdfs)

        for pdf in pdfs:
            rel = pdf.relative_to(stage)
            out = out_stage / rel.parent / pdf.stem
            md = out / (pdf.stem + ".md")

            if md.exists() and not force:
                print("  · 跳过（已提取）%-46s" % rel.name)
                skipped += 1
                continue

            t0 = time.time()
            r = subprocess.run([PY, str(EXTRACTOR), str(pdf), str(out)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            dt = time.time() - t0

            if r.returncode != 0 or not md.exists():
                print("  ✗ 失败 %-46s" % rel.name)
                tail = (r.stdout or "") + (r.stderr or "")
                for ln in tail.strip().split("\n")[-3:]:
                    print("      %s" % ln)
                failed += 1
                continue

            # 从 _summary.txt 抠出页数/图数
            pages = imgs = "?"
            s = out / "_summary.txt"
            if s.exists():
                for ln in s.read_text(encoding="utf-8").split("\n"):
                    if ln.startswith("页数："):
                        pages = ln.split("：")[1]
                    if ln.startswith("导出图片："):
                        imgs = ln.split("：")[1].replace(" 张", "")
            try:
                total_img += int(imgs)
            except ValueError:
                pass

            print("  ✓ %-44s %4s 页  %3s 图  %5.1fs" % (rel.name[:44], pages, imgs, dt))
            done += 1

    print("\n" + "=" * 74)
    print("  合计：%d 个 PDF  →  提取 %d，跳过 %d，失败 %d，共 %d 张图"
          % (total_pdf, done, skipped, failed, total_img))
    print("  总耗时 %.1f 分钟" % ((time.time() - grand_t0) / 60))
    print("=" * 74)

    # ---------- 输出树 ----------
    print("\n  提取结果：")
    for d in sorted(OUT_BASE.glob("_阶段*提取")):
        files = [p for p in d.rglob("*") if p.is_file()]
        sz = sum(p.stat().st_size for p in files)
        print("    %-30s %3d 个文件  %8s" % (d.name, len(files), human(sz)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
