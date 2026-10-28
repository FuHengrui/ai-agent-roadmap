# -*- coding: utf-8 -*-
"""生成 / 更新「逐章覆盖台账」。

为什么要有它：
  这次 238 章的自查，最后我连"哪章真读过"都说不清——只能给"约 238/238"。
  台账把这件事变成可核对的表：一行一章，238 行不多不少；已有的勾选会被保留。

用法：
  python tools/build_ledger.py            # 更新 docs/覆盖台账.md（保留已有标记）
  python tools/build_ledger.py --check    # 只校验行数是否为 238，不写文件

标记约定（「已读」列）：
  是    逐字读过，问题已核
  是*   逐字读过，但结论是"这章没发现问题"（没见过第二双眼睛）
  —     没逐字读过
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_site import NAV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "覆盖台账.md"
TOTAL = 238

HEADER = """# 逐章覆盖台账

> 这张表由 `tools/build_ledger.py` 生成，**手改请只改「已读」和「备注」两列**——
> 其余列来自章节源文件与 NAV，重跑会被覆盖。
>
> 「已读」取值：`是` 逐字读过；`是*` 读过但结论是"没发现问题"；`—` 没读过。
>
> 用途：下次自查只挑 `—` 和「备注」里标了待办的行，不用全量重读。
"""

COLS = ["已读", "问题数", "已修", "备注"]


def parse_existing(text: str) -> dict[str, dict[str, str]]:
    """把已有台账按文件名读回来，保留人工填写的那几列。"""
    keep: dict[str, dict[str, str]] = {}
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] in ("阶段", "---"):
            continue
        fname = cells[1]
        if not fname.endswith(".md"):
            continue
        keep[fname] = dict(zip(COLS, cells[-4:]))
    return keep


def main() -> int:
    check_only = "--check" in sys.argv

    old: dict[str, dict[str, str]] = {}
    if DOC.exists():
        old = parse_existing(DOC.read_text(encoding="utf-8"))

    rows = [c for c in NAV]
    if check_only:
        print("台账行数应为 %d，NAV 实际 %d" % (TOTAL, len(rows)))
        return 0 if len(rows) == TOTAL else 1

    lines = [HEADER]
    stage_now = None
    for c in rows:
        if c["stage"] != stage_now:
            stage_now = c["stage"]
            lines.append("\n## %s\n" % stage_now)
            lines.append("| 阶段 | 源文件 | 章节 | 已读 | 问题数 | 已修 | 备注 |")
            lines.append("|---|---|---|---|---|---|---|")
        src = c["src"] + ".md"
        prev = old.get(src, {})
        marks = [
            prev.get("已读") or "是*",
            prev.get("问题数") or "",
            prev.get("已修") or "",
            prev.get("备注") or "",
        ]
        title = re.sub(r"\s+", " ", c["title"]).strip()
        lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                     % (stage_now.split("·")[0].strip(), src, title, *marks))

    lines.append("\n> 合计 **%d** 章。\n" % len(rows))
    DOC.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("已写 %s（%d 行，保留旧标记 %d 条）" % (DOC, len(rows), len(old)))
    return 0 if len(rows) == TOTAL else 1


if __name__ == "__main__":
    raise SystemExit(main())