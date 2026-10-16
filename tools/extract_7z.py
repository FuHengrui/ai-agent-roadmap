# -*- coding: utf-8 -*-
"""解压阶段 03 的两个 .7z 代码包（Windows 上没有 7-Zip，用 py7zr）。

输出到 <仓库根>\_提取\代码\<包名>\
"""

from __future__ import annotations

import io
import os
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ======================================================================
#  配置区 —— 按你自己的环境改
# ======================================================================
SRC = Path(os.environ.get("SRC", r"D:\课程资料\代码"))
OUT = Path(__file__).resolve().parent.parent / "_提取" / "代码"


def main() -> int:
    try:
        import py7zr
    except ImportError:
        print("!! 缺 py7zr。装一下：python -m pip install py7zr")
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("*.7z"))
    if not files:
        print("!! 没找到 .7z：%s" % SRC)
        return 1

    for f in files:
        name = f.stem
        dst = OUT / name
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True, exist_ok=True)
        print("=" * 70)
        print("  解压 %s（%.1f KB）" % (f.name, f.stat().st_size / 1024))
        print("=" * 70)
        try:
            with py7zr.SevenZipFile(f, mode="r") as z:
                names = z.getnames()
                print("  包内条目 %d 个" % len(names))
                z.extractall(path=dst)
        except Exception as e:  # noqa: BLE001
            print("  !! 失败：%s" % e)
            continue

        # ---- 结构概览 ----
        nf = sum(1 for _, _, fs in os.walk(dst) for _ in fs)
        total = sum(pp.stat().st_size for pp in dst.rglob("*") if pp.is_file())
        print("  解出 %d 个文件，%.1f MB" % (nf, total / 1024 / 1024))
        print()
        # 只显示前 3 层，避免刷屏
        base_depth = len(str(dst).split(os.sep))
        shown = 0
        for dp, dns, fs in os.walk(dst):
            depth = len(dp.split(os.sep)) - base_depth
            if depth > 3:
                dns[:] = []
                continue
            print("  %s[%s]" % ("  " * depth, os.path.basename(dp) or "."))
            for x in sorted(fs)[:14]:
                sz = (Path(dp) / x).stat().st_size
                print("  %s  %-44s %8.1f KB" % ("  " * (depth + 1), x, sz / 1024))
                shown += 1
            if len(fs) > 14:
                print("  %s  ... 还有 %d 个文件" % ("  " * (depth + 1), len(fs) - 14))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
