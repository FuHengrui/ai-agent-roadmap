# -*- coding: utf-8 -*-
"""把 examples/*/检查点.md 渲染成站内页面 site/检查点.html。

为什么要有这一步
----------------
检查点写在 `examples/` 里，但它首先是给**读者**用的——读者多数只看站点，不会去翻仓库目录。
所以把三份检查点合成一个站内页面，从「怎么读」直接链过去。

约定
----
- 只支持检查点用到的 markdown 子集：`## 标题`、`> 引用`、`- 列表`、**加粗**、`行内代码`
- 输出必须**确定性**（不带时间戳），否则 CI 的「站点一致性」天天报红
"""
from __future__ import annotations

import html as H
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
EXAMPLES = ROOT / "examples"

sys.path.insert(0, str(ROOT / "tools"))
from build_site import AVAILABLE, NAV, SITE_SUB, SITE_TITLE, TEMPLATE  # noqa: E402

ORDER = ["阶段09-智能运营平台", "阶段10-健康管理平台", "阶段11-LegalMind"]


def inline(s: str) -> str:
    """**加粗** 与 `行内代码`。先转义再替换，避免 HTML 被吃掉。"""
    s = H.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return s


def md_to_html(text: str) -> str:
    out: list[str] = []
    in_quote: list[str] = []
    in_list = False

    def flush_quote():
        if in_quote:
            out.append("<blockquote>%s</blockquote>" % " ".join(in_quote))
            in_quote.clear()

    def flush_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line:
            flush_quote(); flush_list()
            continue
        if line.startswith("# "):          # 文件标题由页面自己出，跳过
            continue
        if line.startswith("## "):
            flush_quote(); flush_list()
            title = line[3:].strip()
            out.append('<h2 id="%s">%s</h2>' % (slug(title), inline(title)))
            continue
        if line.startswith(">"):
            flush_list()
            in_quote.append(inline(line.lstrip("> ").strip()))
            continue
        if line.startswith("- "):
            flush_quote()
            if not in_list:
                out.append("<ul class=\"cp\">")
                in_list = True
            out.append("<li>%s</li>" % inline(line[2:].strip()))
            continue
        flush_quote(); flush_list()
        out.append("<p>%s</p>" % inline(line.strip()))

    flush_quote(); flush_list()
    return "\n".join(out)


def nav_root() -> str:
    """根目录页面的侧边栏：所有链接都相对 site/ 根。"""
    L = ['  <div class="brand">%s<small>%s</small></div>' % (SITE_TITLE, SITE_SUB),
         '  <h2>总览</h2>',
         '  <a href="index.html">需求地图</a>',
         '  <a href="README.html">怎么读</a>',
         '  <a href="search.html">搜索</a>',
         '  <a href="检查点.html" class="cur">逐章检查点</a>']
    last_stage = None
    for i, c in enumerate(NAV):
        if c.get("stage") and c["stage"] != last_stage:
            last_stage = c["stage"]
            L.append('  <h2>%s</h2>' % last_stage)
        if i not in AVAILABLE:
            L.append('  <span class="pending">%s</span>' % c["title"])
            continue
        L.append('  <a href="%s/%s" class="sub">%s</a>' % (c["dir"], c["file"], c["title"]))
    return "\n".join(L)


def slug(s: str) -> str:
    """给 h2 生成稳定锚点（只留字母数字与中文）。"""
    return "p-" + re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", s).strip("-")


def main() -> int:
    files = []
    for d in ORDER:
        p = EXAMPLES / d / "检查点.md"
        if not p.is_file():
            print("!! 缺少 %s" % p)
            return 1
        files.append((d, p))

    parts = ['<p class="cp-lead">三个实战项目都是「先给关键代码、剩下的自己拼」。'
             '每章做完对一遍下面这 4 行：<strong>目录里应该有</strong> / <strong>跑这条</strong> / '
             '<strong>应该看到</strong> / <strong>卡点</strong>。对不上就回上一节，别往下走。</p>',
             '<p class="cp-lead">本书<strong>不附完整项目代码包</strong>——书上给的是关键代码节选'
             '（阶段 9 约 400 行、阶段 10 约 730 行、阶段 11 约 800 行），真实全栈项目通常 3000 行以上。</p>']

    for d, p in files:
        text = p.read_text(encoding="utf-8")
        parts.append('<hr>')
        parts.append(md_to_html(text))

    body = "\n".join(parts)
    page = TEMPLATE.format(
        title="逐章检查点",
        sub="三个实战项目 · 每章做完对一遍",
        brand="AI Agent 学习路线", brandsub="从 Python 到 Agent 部署",
        css="assets/style.css",
        nav=nav_root(),
        crumb='<div class="crumb"><a href="README.html">怎么读</a> › <strong>逐章检查点</strong></div>',
        body=body, toc="", js="", prev="", next="",
    )
    out = SITE / "检查点.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    print("已写 %s（%d 字节）" % (out.relative_to(ROOT), len(page.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())