# -*- coding: utf-8 -*-
"""数一数这个库到底有多少东西 —— README 里那几个数字的口径就在这儿。

为什么要有这个脚本
------------------
README 上的「2,189 个知识点 / 2,070 条避坑 / 1,628 道自测题」以前是手写的，
改内容就会漂，谁也不知道哪个数是对的。这里把**口径**固定下来：

    阶段     NAV 里出现的不同 stage 数
    章节     NAV 的条目数（= 生成的页数）
    知识点   content 里 `@@point` 的个数
    避坑     `@@trap` 块的个数（一个块 = 一个"坑"，块里通常是一张表）
    自测题   `@@quiz` 段里以「1. 2. 3.」开头的行数
    正文字数 去掉 `@@` 指令行和空白字符后的字符数

只统计 NAV 里真正有源文件的章节，未整理的占位章节不算。

README 里那几个数字是手写的，改内容就会漂（2026-10-27 就漂过一次：页面写 5,053，
实际 2,070）。`--check` 会把 README 表格里的数字跟实际算一遍的结果比对，不一致返回 1，
CI 里跑一次就再也不会漂了。

用法：
    python tools/stats.py          # 打印
    python tools/stats.py --md     # 打印成 README 里那段表格
    python tools/stats.py --check  # 比对 README，不一致返回 1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_site import CONTENT, NAV  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def count() -> dict:
    stages, points, traps, quiz, chars = set(), 0, 0, 0, 0
    chapters = 0
    for c in NAV:
        p = CONTENT / (c["src"] + ".md")
        if not p.exists():
            continue
        chapters += 1
        stages.add(c["stage"])
        t = p.read_text(encoding="utf-8")
        points += len(re.findall(r"(?m)^@@point", t))
        traps += len(re.findall(r"(?m)^@@trap", t))
        m = re.search(r"(?ms)^@@quiz\s*\n(.*?)(?=^@@|\Z)", t)
        if m:
            quiz += len(re.findall(r"(?m)^\s*\d+[\.、]", m.group(1)))
        body = "\n".join(ln for ln in t.split("\n") if not ln.startswith("@@"))
        chars += len(re.sub(r"\s", "", body))
    return {
        "阶段": len(stages),
        "章节": chapters,
        "知识点": points,
        "避坑": traps,
        "自测题": quiz,
        "正文字数": chars,
    }


def check_readme(d: dict) -> int:
    """比对 README.md 表格里的数字。返回 0 = 一致。"""
    readme = ROOT / "README.md"
    if not readme.is_file():
        print("  !! 没有 README.md")
        return 1
    t = readme.read_text(encoding="utf-8")
    labels = {"阶段": "阶段", "章节": "章节", "知识点": "知识点",
              "避坑": "避坑记录", "自测题": "自测题"}
    problems = []
    for key, label in labels.items():
        m = re.search(r"\|\s*\**%s\**\s*\|\s*\**([\d,]+)" % re.escape(label), t)
        if not m:
            problems.append("README 表格里找不到「%s」这一行" % label)
            continue
        got = int(m.group(1).replace(",", ""))
        if got != d[key]:
            problems.append("「%s」README 写 %s，实际 %s" % (label, format(got, ","), format(d[key], ",")))

    m = re.search(r"约\s*([\d,]+)\s*万字", t)
    if m:
        got = int(m.group(1).replace(",", ""))
        real = round(d["正文字数"] / 10000)
        if abs(got - real) > 1:
            problems.append("「正文字数」README 写约 %d 万字，实际约 %d 万字" % (got, real))

    if problems:
        print()
        for x in problems:
            print("  ★ " + x)
        print()
        print("  ══ README 数字和实际不一致：改完内容记得同步数字（python tools/stats.py --md）══")
        return 1
    print("  ✓ README 数字与实际一致（阶段 %d / 章节 %d / 知识点 %s / 避坑 %s / 自测 %s）"
          % (d["阶段"], d["章节"], format(d["知识点"], ","),
             format(d["避坑"], ","), format(d["自测题"], ",")))
    return 0


def main() -> int:
    d = count()
    if "--check" in sys.argv:
        return check_readme(d)

    if "--md" in sys.argv:
        print("| 项 | 数量 |")
        print("|---|---|")
        print("| 阶段 | %d |" % d["阶段"])
        print("| 章节 | %d |" % d["章节"])
        print("| 知识点 | {:,} |".format(d["知识点"]))
        print("| **避坑记录** | **{:,} 条** |".format(d["避坑"]))
        print("| 自测题 | {:,} 道 |".format(d["自测题"]))
        print("| 正文字数 | 约 %d 万字 |" % round(d["正文字数"] / 10000))
        return 0

    for k, v in d.items():
        if k == "正文字数":
            print("  正文字数 {:,}（约 {} 万字）".format(v, round(v / 10000)))
        else:
            print("  {} {:,}".format(k.ljust(5, "　"), v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())