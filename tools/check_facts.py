# -*- coding: utf-8 -*-
"""按 tools/facts.py 里的「错误写法」扫全库；也能把清单生成成文档。

  python tools/check_facts.py            # 扫描，列出命中的章节与行号
  python tools/check_facts.py --check    # CI 用：有命中就退出码 1
  python tools/check_facts.py --doc      # 重新生成 docs/事实清单.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from facts import FACTS  # noqa: E402

CONTENT = ROOT / "content"
DOC = ROOT / "docs" / "事实清单.md"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def scan():
    hits = []
    for p in sorted(CONTENT.glob("*.md")):
        if p.name.startswith("_"):
            continue
        lines = p.read_text(encoding="utf-8").split("\n")
        for f in FACTS:
            for pat in f.get("bad") or []:
                rx = re.compile(pat)
                for i, ln in enumerate(lines, 1):
                    if rx.search(ln):
                        hits.append((f["id"], p.name, i, ln.strip()[:60]))
    return hits


def write_doc():
    out = ["# 事实清单（错过的那些）", "",
           "> 由 `tools/facts.py` 生成，别手改；要加一条就改那个文件。",
           "> 检查器 `tools/check_facts.py --check` 会在 CI 里盯住这些「错误写法」复发。", ""]
    for f in FACTS:
        out.append("## %s" % f["fact"])
        out.append("")
        out.append("- **正确**：%s" % f["right"])
        out.append("- **曾经的错**：%s" % f["wrong"])
        out.append("- **涉及章节**：%s" % f["chapters"])
        if f.get("bad"):
            out.append("- **检查器盯的写法**：%s" % "、".join("`%s`" % b for b in f["bad"]))
        else:
            out.append("- **检查器盯的写法**：（无法用正则安全匹配，靠人读）")
        out.append("")
    DOC.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("已写 %s（%d 条事实）" % (DOC, len(FACTS)))


def main() -> int:
    if "--doc" in sys.argv:
        write_doc()
        return 0
    hits = scan()
    if not hits:
        print("✓ 事实清单里的错误写法一条都没出现（%d 条事实在盯）" % len(FACTS))
        return 0
    print("✗ 命中 %d 处（说明旧说法又出现了）：" % len(hits))
    by_id = {f["id"]: f for f in FACTS}
    for fid, name, line, text in hits:
        print("  %s:%d  [%s] %s" % (name, line, fid, text))
        print("     正确说法：%s" % by_id[fid]["right"][:90])
    return 1 if "--check" in sys.argv else 0


if __name__ == "__main__":
    raise SystemExit(main())