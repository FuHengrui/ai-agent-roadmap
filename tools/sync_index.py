# -*- coding: utf-8 -*-
"""把 index.html / README.html 的侧边栏和章节表同步成 site_config.NAV 的结构。

为什么需要这一步
----------------
首页和 README 是手写的（不走流水线），而侧边栏和章节表必须跟 NAV 完全一致，
否则点进去就是 404。改了章节结构之后跑一次这个脚本即可。

★ 路径规则
----------
首页在根目录，章节在阶段子目录里，所以链接要写成：
    index.html  →  阶段01-大语言模型基础与工程化实践/01-第一章-xxx.html
"""

from __future__ import annotations

import io
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001 —— 被重定向到管道／文件时可能不支持
    pass

# --- 路径：全部相对仓库根目录，clone 下来就能跑 ---
ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"

# 可选：构建完顺便同步到别处（比如你自己的交付目录）。
# 不设这个环境变量就不同步。用法：  set KB_DEPLOY=D:\我的交付目录
_DEPLOY = os.environ.get("KB_DEPLOY")
DEPLOY = Path(_DEPLOY) if _DEPLOY else None
sys.path.insert(0, str(ROOT / "tools"))
from site_config import NAV, SITE_TITLE, SITE_SUB  # type: ignore

# 哪些章节已经有源文件（没有的渲染成灰色「待整理」，不做死链）
CONTENT = ROOT / "content"
AVAILABLE = {i for i, c in enumerate(NAV) if (CONTENT / (c["src"] + ".md")).exists()}


def chapter_href(c: dict) -> str:
    return "%s/%s" % (c["dir"], c["file"])


def sidebar_html(cur: str = "index.html") -> str:
    """总览 + 各阶段分组的侧边栏（相对根目录）。

    cur 是当前页面的文件名，用来决定「总览」里哪一条高亮 ——
    否则在 README 页面上也会把「需求地图」标成当前页。
    """
    def cls(name: str) -> str:
        return ' class="cur"' if name == cur else ""

    L = ['  <div class="brand">%s<small>%s</small></div>' % (SITE_TITLE, SITE_SUB),
         '  <h2>总览</h2>',
         '  <a href="index.html"%s>需求地图</a>' % cls("index.html"),
         '  <a href="README.html"%s>怎么读</a>' % cls("README.html"),
         '  <a href="search.html"%s>搜索</a>' % cls("search.html")]
    last = None
    for i, c in enumerate(NAV):
        if c["stage"] != last:
            last = c["stage"]
            L.append('  <h2>%s</h2>' % last)
        if i not in AVAILABLE:
            L.append('  <span class="pending">%s</span>' % c["title"])
            continue
        L.append('  <a href="%s" class="sub">%s</a>' % (chapter_href(c), c["title"]))
    return "\n".join(L)


def chapters_by_stage():
    g = OrderedDict()
    for i, c in enumerate(NAV):
        g.setdefault((c["dir"], c["stage"]), []).append((i, c))
    return g


def main() -> int:
    # ---------------- index.html ----------------
    p = SITE / "index.html"
    if not p.exists():
        print("!! 缺少 index.html"); return 1
    t = p.read_text(encoding="utf-8")

    # 1) 侧边栏
    # ★ 必须从 brand 块开始匹配：sidebar_html() 里包含 brand，
    #   如果只从 <h2>总览</h2> 开始替换，每跑一次就会多出一个 brand 块。
    t2 = re.sub(r'  <div class="brand">.*?</nav>',
                sidebar_html("index.html") + "\n</nav>", t, count=1, flags=re.S)
    if t2 == t:
        print("  · index 侧边栏未变（可能已同步）")
    t = t2

    # 2) 修掉所有旧式平铺链接（01-第一章-xxx.html → 阶段01-.../01-第一章-xxx.html）
    for c in NAV:
        t = t.replace('href="%s"' % c["file"], 'href="%s"' % chapter_href(c))

    p.write_text(t, encoding="utf-8", newline="\n")
    print("  ✓ index.html 已同步（侧边栏 + %d 条章节链接）" % len(NAV))

    # ---------------- README.html ----------------
    r = SITE / "README.html"
    if r.exists():
        rt = r.read_text(encoding="utf-8")
        rt2 = re.sub(r'  <div class="brand">.*?</nav>',
                     sidebar_html("README.html") + "\n</nav>",
                     rt, count=1, flags=re.S)
        if rt2 == rt:
            print("  · README 侧边栏未变")
        else:
            print("  ✓ README.html 侧边栏已同步")
        r.write_text(rt2, encoding="utf-8", newline="\n")

    # ---------------- 可选：同步到 KB_DEPLOY ----------------
    import shutil
    if DEPLOY and DEPLOY.exists():
        for f in (p, ):          # index.html
            d = DEPLOY / f.name
            shutil.copy2(f, d)
        if r.exists():
            shutil.copy2(r, DEPLOY / r.name)
        print("  已同步 index.html / README.html 到 %s" % DEPLOY)

    # ---------------- 报告 ----------------
    print()
    print("  阶段结构：")
    for (d, name), items in chapters_by_stage().items():
        print("    %-42s %d 章" % (name, len(items)))
        for _, c in items:
            print("        %s" % c["file"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
