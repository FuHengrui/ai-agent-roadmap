# -*- coding: utf-8 -*-
"""知识库交付前自检：结构完整性 + 链接可达性 + 样式加载。

用法：python verify_site.py
退出码 0 = 全部通过；1 = 有问题（会列出具体页面）。
"""

from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

D = Path(__file__).resolve().parent.parent / "site"
# 这个工具页自带的 style 是内联的，链接是 JS 模板串，跳过检查
SKIP = {"资料链接填写工具.html"}


def pages():
    out = []
    for dp, _dn, fn in os.walk(D):
        for f in fn:
            if f.endswith(".html"):
                out.append(Path(dp) / f)
    return sorted(out)


def main() -> int:
    req = {
        "开篇需求": 'class="why"',
        "位置图": 'class="map"',
        "知识点": 'class="point"',
        "need段": 'class="step need"',
        "小结": "本章小结",
        "自测": "自测：能不能答上来",
        "资料块": 'class="links"',
    }
    allp = pages()
    problems = []

    print("=" * 78)
    print("  页面结构检查")
    print("=" * 78)
    for p in allp:
        rel = str(p.relative_to(D))
        if p.name in SKIP:
            print("  ·  %-56s （工具页，跳过）" % rel)
            continue
        t = p.read_text(encoding="utf-8")
        is_chapter = p.parent.name.startswith("阶段")
        miss = [k for k, v in req.items() if v not in t] if is_chapter else []
        flag = "✓" if not miss else "✗"
        if miss:
            problems.append((rel, "缺块: " + ",".join(miss)))
        print("  %s  %-56s %s" % (flag, rel, ("缺 " + ",".join(miss)) if miss else "六块齐全"))

    print()
    print("=" * 78)
    print("  链接与样式检查")
    print("=" * 78)
    for p in allp:
        rel = str(p.relative_to(D))
        if p.name in SKIP:
            continue
        t = p.read_text(encoding="utf-8")
        base = p.parent
        dead = []
        for h in re.findall(r'(?:href|src)="([^"]+)"', t):
            if h.startswith(("http", "#", "mailto")) or "${" in h:
                continue
            if not (base / h).resolve().exists():
                dead.append(h)
        m = re.search(r'href="([^"]*style\.css)"', t)
        css_ok = bool(m) and (base / m.group(1)).resolve().exists()
        ok = not dead and css_ok
        if not ok:
            problems.append((rel, "死链=%s css=%s" % (dead or "无", "OK" if css_ok else "缺")))
        print("  %s  %-52s css=%-3s 死链=%s" % ("✓" if ok else "✗", rel,
                                               "OK" if css_ok else "缺", dead or "无"))

    print()
    print("=" * 78)
    if problems:
        print("  ✗ 发现 %d 个问题：" % len(problems))
        for rel, why in problems:
            print("      %s  ——  %s" % (rel, why))
        return 1
    print("  ✓ 全部通过：%d 个页面，结构完整、无死链、样式正常" % (len(allp) - len(SKIP)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
