# -*- coding: utf-8 -*-
"""结构一致性体检：目录说的，和正文写的，必须是同一件事。

为什么要有这个脚本
------------------
2026-10-27 出过一次事故：阶段 9 的前两章和阶段 10 共用同一个源文件（`NAV` 里
`src` 重复），结果阶段 9 的页面副标题写着「阶段 10 · 糖尿病」，正文也在讲另一个
项目 —— 目录和正文对不上，但页面本身看不出错，人眼极难发现。

这个脚本查三件事（都是那次事故的直接特征）：

  1. `NAV` 里有没有两个阶段挂同一个 `src`（共用一份正文）
  2. 每章 `@@sub` 里写的阶段号，和 `NAV` 给它的阶段号是否一致
  3. 每章 `@@h1` 的章号，和文件名前缀的章号是否一致（03-第三章-… 对应「第三章」）

用法：
    python tools/check_consistency.py        # 有问题返回 1，没问题返回 0
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_site import CONTENT, NAV  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

CN = "零一二三四五六七八九十"
NUM = {}
for i, ch in enumerate(CN[:11]):
    NUM[ch] = i
NUM.update({"十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
            "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
            "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24,
            "二十五": 25, "二十六": 26, "二十七": 27, "二十八": 28})


def cn2int(s: str):
    s = s.strip()
    if s.isdigit():
        return int(s)
    return NUM.get(s)


def stage_no(s: str):
    m = re.search(r"阶段\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


def chapter_no(s: str):
    m = re.search(r"第\s*([零一二三四五六七八九十\d]+)\s*章", s or "")
    return cn2int(m.group(1)) if m else None


def main() -> int:
    problems = []

    # 1. src 重复
    dup = [k for k, v in Counter(c["src"] for c in NAV).items() if v > 1]
    for k in dup:
        owners = ["%s/%s" % (c["dir"], c["file"]) for c in NAV if c["src"] == k]
        problems.append("src 重复：%s 被 %d 个页面共用 → %s" % (k, len(owners), "、".join(owners)))

    checked = 0
    for c in NAV:
        p = CONTENT / (c["src"] + ".md")
        if not p.exists():
            continue
        checked += 1
        t = p.read_text(encoding="utf-8")
        where = "%s/%s" % (c["dir"], c["file"])

        # 2. @@sub 的阶段号
        m = re.search(r"(?m)^@@sub\s*(.*)$", t)
        want, got = stage_no(c["stage"]), stage_no(m.group(1)) if m else None
        if want is not None and got is not None and want != got:
            problems.append("%s：目录是阶段 %s，正文 @@sub 写的是阶段 %s" % (where, want, got))

        # 3. @@h1 的章号 vs 文件名前缀
        h = re.search(r"(?m)^@@h1\s*(.*)$", t)
        file_no = re.match(r"(\d+)-", Path(c["src"]).name)
        if h and file_no:
            want, got = int(file_no.group(1)), chapter_no(h.group(1))
            if got is not None and want != got:
                problems.append("%s：文件名是第 %d 章，正文 @@h1 写的是第 %d 章" % (where, want, got))

    print("  检查 %d 个章节 / %d 个目录条目" % (checked, len(NAV)))
    if problems:
        print()
        for x in problems:
            print("  ★ " + x)
        print()
        print("  ══ %d 处不一致，先修再推 ══" % len(problems))
        return 1
    print("  ✓ 一致：没有共用源文件，阶段号与章号全部对得上")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())