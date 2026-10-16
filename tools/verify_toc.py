# -*- coding: utf-8 -*-
"""验证「本页目录」功能：外观 + 跳动 + 滚动高亮 + 窄屏隐藏。

对应《docs/写作规格.md》第九节里那 7 条人工确认项。
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "site"
OUT = ROOT / ".shots"
OUT.mkdir(exist_ok=True)

CH1 = D / "阶段03-Agent项目启蒙" / "01-第一章-智能会议系统.html"
CH2 = D / "阶段04-低代码Agent平台实战" / "02-第二章-Coze工作流与多Agent.html"


def url(p: Path) -> str:
    return "file:///" + str(p).replace("\\", "/")


def check(tag: str, cond: bool, detail: str = "") -> bool:
    print("   %s  %-34s %s" % ("✓" if cond else "✗", tag, detail))
    return cond


def main() -> int:
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, channel="msedge")

        # ============ 宽屏 ============
        ctx = b.new_context(viewport={"width": 1500, "height": 950})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url(CH1), wait_until="load")
        pg.wait_for_timeout(500)

        print("\n  ── 宽屏 1500px ──")

        # 1. 目录出现，条目数一致
        n_toc = pg.eval_on_selector_all(".toc a", "e => e.length")
        n_pt = pg.eval_on_selector_all(".point", "e => e.length")
        results.append(check("目录出现且条目数一致", n_toc == n_pt and n_toc > 0,
                             "目录 %d / 知识点 %d" % (n_toc, n_pt)))

        vis = pg.eval_on_selector(".toc", "e => getComputedStyle(e).display")
        results.append(check("目录可见", vis != "none", "display=%s" % vis))

        pg.screenshot(path=str(OUT / "toc-1-top.png"))

        # 2. 初始高亮在第 1 项
        cur = pg.eval_on_selector_all(".toc a", "e => e.findIndex(x => x.classList.contains('cur'))")
        results.append(check("初始高亮 = 第 1 项", cur == 0, "高亮索引 %d" % cur))

        # 3. 点击第 6 项 → 跳过去
        pg.click(".toc a >> nth=5")
        pg.wait_for_timeout(900)
        y6 = pg.eval_on_selector("#p6", "e => e.getBoundingClientRect().top")
        results.append(check("点击第 6 项能跳过去", -20 < y6 < 260, "#p6 距顶 %.0fpx" % y6))
        pg.screenshot(path=str(OUT / "toc-2-jump.png"))

        # 4. 滚动后高亮跟着变
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.72)")
        pg.wait_for_timeout(700)
        cur2 = pg.eval_on_selector_all(".toc a", "e => e.findIndex(x => x.classList.contains('cur'))")
        results.append(check("滚动后高亮跟着变", cur2 > 3, "高亮索引 %d" % cur2))

        # 5. 滚到底，目录还在
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg.wait_for_timeout(700)
        box = pg.eval_on_selector(".toc", "e => { var r = e.getBoundingClientRect(); return [r.top, r.height]; }")
        results.append(check("滚到底目录仍可见", box[1] > 200 and box[0] < 900,
                             "top=%.0f 高=%.0f" % (box[0], box[1])))
        cur3 = pg.eval_on_selector_all(".toc a", "e => e.findIndex(x => x.classList.contains('cur'))")
        results.append(check("底部高亮 = 最后一项", cur3 == n_toc - 1,
                             "高亮 %d / 共 %d" % (cur3, n_toc - 1)))
        pg.screenshot(path=str(OUT / "toc-3-bottom.png"))

        # 6. 换一章，目录也对
        pg.goto(url(CH2), wait_until="load")
        pg.wait_for_timeout(500)
        n2t = pg.eval_on_selector_all(".toc a", "e => e.length")
        n2p = pg.eval_on_selector_all(".point", "e => e.length")
        results.append(check("换一章目录也正确", n2t == n2p and n2t > 0,
                             "目录 %d / 知识点 %d" % (n2t, n2p)))

        results.append(check("无 JS 错误", not errs, str(errs) if errs else ""))

        # ============ 窄屏 ============
        print("\n  ── 窄屏 1000px ──")
        ctx2 = b.new_context(viewport={"width": 1000, "height": 900})
        pg2 = ctx2.new_page()
        pg2.goto(url(CH1), wait_until="load")
        pg2.wait_for_timeout(400)
        v2 = pg2.eval_on_selector(".toc", "e => getComputedStyle(e).display")
        results.append(check("窄屏目录隐藏", v2 == "none", "display=%s" % v2))
        # 正文有没有被挤窄
        w = pg2.eval_on_selector(".wrap", "e => e.getBoundingClientRect().width")
        results.append(check("窄屏正文宽度正常", w > 600, "正文宽 %.0fpx" % w))
        pg2.screenshot(path=str(OUT / "toc-4-narrow.png"))

        # ============ 中等宽度 ============
        print("\n  ── 中等宽度 1300px ──")
        ctx3 = b.new_context(viewport={"width": 1300, "height": 900})
        pg3 = ctx3.new_page()
        pg3.goto(url(CH1), wait_until="load")
        pg3.wait_for_timeout(400)
        v3 = pg3.eval_on_selector(".toc", "e => getComputedStyle(e).display")
        w3 = pg3.eval_on_selector(".wrap", "e => e.getBoundingClientRect().width")
        results.append(check("1300px 显示目录", v3 != "none", "display=%s" % v3))
        results.append(check("1300px 正文不被挤瘦", w3 > 640, "正文宽 %.0fpx" % w3))
        pg3.screenshot(path=str(OUT / "toc-5-mid.png"))

        b.close()

    print()
    ok = sum(1 for r in results if r)
    print("  ═" * 30)
    print("   %d / %d 项通过" % (ok, len(results)))
    print("  ═" * 30)
    print()
    print("  截图：")
    for f in sorted(OUT.glob("toc-*.png")):
        print("    %s" % f.name)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
