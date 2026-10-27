# -*- coding: utf-8 -*-
"""知识库内容流水线：Markdown 源 → 统一风格的 HTML 页面。

为什么要有这一步
----------------
内容如果直接手写 HTML，风格必然漂移，而且换人（或换 AI）接手时没法保证一致。
改成「内容用 Markdown 写、样式由脚本统一注入」后：
  · 内容与样式分离，改样式全站生效
  · 写一章只需关心文字，不用管标签
  · 谁来续写都得到同一个样子

★ 目录规则
----------
每个阶段一个子目录，章节页放自己阶段的目录里：

    建立知识库/
    ├── index.html                    ← 根目录，链接用「阶段XX/文件名.html」
    ├── README.html
    ├── assets/style.css              ← 章节页引用「../assets/style.css」
    ├── 阶段01-大语言模型基础与工程化实践/
    │   └── 01-第一章-xxx.html
    └── 阶段02-AI智能体Web系统构建实战/
        └── 01-第一章-xxx.html

章节间跳转分两种情况：
  · 同阶段 → 直接用文件名
  · 跨阶段 → `../阶段XX/文件名.html`

源文件语法（content/*.md）
-------------------------
    @@h1   第三章　序列
    @@sub  阶段 1 · ...　|　25 课时　|　难度 ★★☆

    @@why  这一章在解决什么问题
    正文……

    @@map  在全局框架里的位置
    上一章 xxx
    **本章** ← 你在这里

    @@note info 为什么先讲这个
    正文……

    @@point ① 知识点名
    @@need 要解决什么      ← 必写
    正文……
    @@idea 核心思路
    正文……
    @@how  怎么做          ← 可选，做法是独立流程时才用
    正文……
    @@trap 坑在哪
    正文……

    @@summary
    @@quiz
    1. 问题
    @@links
    讲义|标题|链接

行内支持 **粗体** 与 `代码`。表格分隔行可省。表格内换行写 <br>。
"""

from __future__ import annotations

import html as H
import io
import os
import re
import sys
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
try:
    from site_config import NAV, SITE_TITLE, SITE_SUB  # type: ignore
except Exception:  # noqa: BLE001
    NAV, SITE_TITLE, SITE_SUB = [], "建立知识库", "AI Agent 学习路线"

# 哪些章节已经有源文件（没有的渲染成灰色「待整理」，不做成死链）
AVAILABLE = {i for i, c in enumerate(NAV) if (CONTENT / (c["src"] + ".md")).exists()}


def next_available(idx: int):
    for i in range(idx + 1, len(NAV)):
        if i in AVAILABLE:
            return i
    return None


def prev_available(idx: int):
    for i in range(idx - 1, -1, -1):
        if i in AVAILABLE:
            return i
    return None


# ======================================================================
# 路径工具：所有链接都算相对路径，因为章节页在阶段子目录里
# ======================================================================
def link_chapter(cur: int, target: int) -> str:
    """从第 cur 章指向第 target 章的相对链接。"""
    if target < 0 or target >= len(NAV):
        return "../index.html"
    a, b = NAV[cur], NAV[target]
    if a["dir"] == b["dir"]:
        return b["file"]
    return "../%s/%s" % (b["dir"], b["file"])


def link_root(cur: int, target: str) -> str:
    """从第 cur 章指向根目录文件（index.html / README.html）。"""
    return "../" + target


# ======================================================================
# 行内格式
# ======================================================================
def inline(s: str) -> str:
    s = H.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # 转义之后再把作者手写的 <br> 放回来——表格里需要换行时用它
    s = s.replace("&lt;br&gt;", "<br>")
    return s


# ======================================================================
# 正文块 → HTML
# ======================================================================
def body(lines: list[str]) -> str:
    out, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        # ---- 代码块 ----
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code = H.escape("\n".join(buf))
            if lang == "cmd":
                out.append('<div class="cmd">%s</div>' % _cmdfmt(code))
            else:
                out.append("<pre>%s</pre>" % code)
            continue

        # ---- Markdown 标题（# / ## / ###）----
        # 必须放在代码块分支【之后】：代码里的注释就长这样（`# 导入依赖`、
        # ASCII 图的边框），先处理代码块才能保证它们不被当成标题。
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = min(len(m.group(1)) + 1, 5)      # # → h2, ## → h3, ### → h4…
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue

        # ---- 表格（分隔行 |---|---| 可有可无）----
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            if not rows:
                continue
            head, rest = rows[0], rows[1:]
            t = ["<table>", "<tr>" + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr>"]
            for r in rest:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</table>")
            out.append("\n".join(t))
            continue

        # ---- 有序列表 ----
        if re.match(r"^\d+[.、]\s", s):
            items = []
            while i < len(lines) and re.match(r"^\d+[.、]\s", lines[i].strip()):
                items.append(re.sub(r"^\d+[.、]\s*", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ol>")
            continue

        # ---- 无序列表 ----
        if s.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ul>")
            continue

        # ---- 段落 ----
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("```", "|", "- ")) \
                and not re.match(r"^\d+[.、]\s", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if not buf:            # 兜底：防止未识别行导致死循环
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def _cmdfmt(code: str) -> str:
    """命令行块：> 开头当提示符，其余当注释/输出。"""
    lines = []
    for raw in code.split("\n"):
        e = H.escape(raw)
        if raw.strip().startswith(">"):
            lines.append('<span class="p">&gt;</span>' + e.split("&gt;", 1)[-1])
        elif raw.strip().startswith("#"):
            lines.append('<span class="c">%s</span>' % e)
        else:
            lines.append(e)
    return "\n".join(lines)


# ======================================================================
# 解析源文件
# ======================================================================
DIRECTIVE = re.compile(r"^@@(\w+)(?:\s+(.*))?$")
# 这些属于知识点卡片内部，不能当一级块解析——否则 @@point 的 body 会变空
SUB = {"need", "idea", "how", "trap"}


def parse(text: str):
    blocks, cur = [], None
    for ln in text.split("\n"):
        m = DIRECTIVE.match(ln.rstrip())
        if m and m.group(1) not in SUB:
            cur = {"k": m.group(1), "arg": (m.group(2) or "").strip(), "body": []}
            blocks.append(cur)
        elif cur is not None:
            cur["body"].append(ln)
    return blocks


def _subblocks(bd):
    out, cur = [], None
    for ln in bd:
        m = DIRECTIVE.match(ln.rstrip())
        if m:
            cur = (m.group(1), (m.group(2) or "").strip(), [])
            out.append(cur)
        elif cur is not None:
            cur[2].append(ln)
    return out


# ======================================================================
# 渲染一页
# ======================================================================
def render(src: Path, idx: int):
    blocks = parse(src.read_text(encoding="utf-8"))
    title = sub = ""
    parts = []
    ntoc = 0
    toc_items = []          # [(编号, 标题)] —— 用来生成右侧「本页目录」
    for b in blocks:
        k, a, bd = b["k"], b["arg"], b["body"]
        if k == "h1":
            title = a
        elif k == "sub":
            sub = a
        elif k == "why":
            parts.append('<div class="why"><span class="tag">%s</span>\n%s\n</div>' % (inline(a), body(bd)))
        elif k == "map":
            rows = [x.strip() for x in bd if x.strip()]
            node = []
            for r in rows:
                if r.startswith("**") and "本章" in r:
                    node.append('<span class="node"><span class="here">%s</span></span>' % inline(r.replace("**", "")))
                else:
                    node.append('<span class="node">%s</span>' % inline(r))
            parts.append('<div class="map"><span class="tag">%s</span>\n%s\n</div>'
                         % (inline(a or "这一章在整个知识库里的位置"), "\n".join(node)))
        elif k == "note":
            kind = (a.split()[0] if a else "info") or "info"
            ttl = a[len(kind):].strip()
            t = '<span class="t">%s</span>\n' % inline(ttl) if ttl else ""
            parts.append('<div class="note %s">%s%s</div>' % (kind, t, body(bd)))
        elif k == "point":
            ntoc += 1
            toc_items.append(a)
            inner = []
            for sk, sa, sbd in _subblocks(bd):
                cls = {"need": "need", "idea": "idea", "how": "how", "trap": "trap"}.get(sk, "")
                inner.append('<div class="step %s"><span class="label">%s</span>\n%s\n</div>'
                             % (cls, inline(sa), body(sbd)))
            parts.append('<div class="point" id="p%d"><div class="head"><span class="no">%d</span>%s</div>'
                         '<div class="body">\n%s\n</div></div>' % (ntoc, ntoc, inline(a), "\n".join(inner)))
        elif k == "summary":
            parts.append('<h2>本章小结</h2>\n' + body(bd))
        elif k == "quiz":
            parts.append('<h4>自测：能不能答上来</h4>\n' + body(bd))
        elif k == "links":
            items, offs = [], []
            for x in bd:
                x = x.strip()
                if not x or "|" not in x:
                    continue
                k2, t2, u2 = (x.split("|") + ["", ""])[:3]
                url = u2.strip()
                if url in ("", "#"):
                    # ★ 占位行：这类行本来就点不开（238 章里还有 301 行），
                    #   渲染成 <a href="#"> 是骗点击，跳回页首更让人困惑。
                    #   改成灰色不可点标签，信息留着、假链接没了。
                    offs.append('<span class="lk"><span class="k">%s</span>%s</span>'
                                % (inline(k2.strip()), inline(t2.strip())))
                    continue
                tgt = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
                items.append('<a href="%s"%s><span class="k">%s</span>%s</a>'
                             % (H.escape(url, quote=True), tgt, inline(k2.strip()), inline(t2.strip())))
            if offs:
                items.append('<div class="links-off" title="这些资料不在站点里（PDF、源码包、配套软件），需要自己准备">'
                             '<span class="tag2">未收录</span>%s</div>' % "\n".join(offs))
            parts.append('<div class="links"><span class="tag">本章配套资料</span>\n%s\n</div>' % "\n".join(items))

    page = TEMPLATE.format(
        title=H.escape(title), sub=inline(sub), brand=SITE_TITLE, brandsub=SITE_SUB,
        css=link_root(idx, "assets/style.css"),
        nav=nav_html(idx), crumb=crumb_html(idx), body="\n".join(parts),
        toc=toc_html(toc_items),
        js=(TOC_JS if toc_items else ""),
        prev=prev_link(idx), next=next_link(idx),
    )
    return page, {"title": title, "points": ntoc}


# ======================================================================
# 本页目录（右侧）
# ======================================================================
# 标题开头的 ①②③… 是给正文卡片用的；目录里靠顺序就够了，去掉省宽度
_CIRCLED = re.compile(r"^[\u2460-\u2473]\s*")


def toc_html(items) -> str:
    """生成右侧「本页目录」。items 是各知识点的标题（按顺序）。

    刻意不做成手写的：脚本自动生成，才能让以后每一章都自带目录、不会写漏。
    """
    if not items:
        return ""
    L = ['<div class="toc-inner">',
         '  <div class="toc-head">本页目录</div>']
    for i, t in enumerate(items, 1):
        plain = _CIRCLED.sub("", t).strip()
        L.append('  <a href="#p%d" title="%s"><span class="n">%d</span>%s</a>'
                 % (i, H.escape(plain, quote=True), i, inline(plain)))
    L.append("</div>")
    return "\n".join(L)


# 滚动时高亮当前所在的知识点。
# 用「最后一个顶部越过阈值的卡片」判断，比 IntersectionObserver 简单且不会
# 在快速滚动时出现"没有一项高亮"的空档。
TOC_JS = """<script>
(function () {
  var links = [].slice.call(document.querySelectorAll('.toc a'));
  if (!links.length) return;
  var targets = links.map(function (a) {
    return document.getElementById(a.getAttribute('href').slice(1));
  });
  var THRESHOLD = 130;   // 距视口顶部多少像素算"读到这里了"
  function update() {
    var idx = 0;
    for (var i = 0; i < targets.length; i++) {
      if (targets[i] && targets[i].getBoundingClientRect().top <= THRESHOLD) idx = i;
    }
    for (var j = 0; j < links.length; j++) {
      if (j === idx) links[j].classList.add('cur');
      else links[j].classList.remove('cur');
    }
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { update(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', update);
  window.addEventListener('load', update);
  update();
})();
</script>"""


# ======================================================================
# 导航
# ======================================================================
def nav_html(cur_idx: int) -> str:
    L = ['  <div class="brand">%s<small>%s</small></div>' % (SITE_TITLE, SITE_SUB),
         '  <h2>总览</h2>',
         '  <a href="%s"%s>需求地图</a>' % (link_root(cur_idx, "index.html"),
                                            ' class="cur"' if cur_idx < 0 else ""),
         '  <a href="%s">怎么读</a>' % link_root(cur_idx, "README.html"),
         '  <a href="%s">搜索</a>' % link_root(cur_idx, "search.html")]
    last_stage = None
    for i, c in enumerate(NAV):
        if c.get("stage") and c["stage"] != last_stage:
            last_stage = c["stage"]
            L.append('  <h2>%s</h2>' % last_stage)
        if i not in AVAILABLE:
            # 还没写的章节：灰色不可点，避免死链
            L.append('  <span class="pending">%s</span>' % c["title"])
            continue
        cur = ' class="cur"' if i == cur_idx else ' class="sub"'
        L.append('  <a href="%s"%s>%s</a>' % (link_chapter(cur_idx, i), cur, c["title"]))
    return "\n".join(L)


def crumb_html(idx: int) -> str:
    if idx < 0 or idx >= len(NAV):
        return ""
    c = NAV[idx]
    return ('<div class="crumb"><a href="%s">%s</a> › %s › <strong>%s</strong></div>'
            % (link_root(idx, "index.html"), SITE_TITLE, c.get("stage", ""),
               c["title"].split("　")[0]))


def prev_link(idx: int) -> str:
    p = prev_available(idx)
    if p is not None:
        return '<a href="%s">← %s</a>' % (link_chapter(idx, p), NAV[p]["title"])
    return '<a href="%s">← 返回需求地图</a>' % link_root(idx, "index.html")


def next_link(idx: int) -> str:
    n = next_available(idx)
    if n is not None:
        return '<a class="nxt" href="%s">%s →</a>' % (link_chapter(idx, n), NAV[n]["title"])
    return '<a class="nxt" href="%s">返回需求地图 →</a>' % link_root(idx, "index.html")


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {brand}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<div class="layout">
<nav class="sidebar">
{nav}
</nav>
<main class="main"><div class="wrap">
{crumb}
<h1>{title}</h1>
<div class="subtitle">{sub}</div>
{body}
<div class="pager">
{prev}
{next}
</div>
</div></main>
<aside class="toc">
{toc}
</aside>
</div>
{js}
<!-- 访问统计 · Vercount（不蒜子的兼容版）· 默认隐藏 -->
<!-- 想显示出来：把下面这行的 style="display:none" 删掉，然后重新构建 -->
<div class="stat" style="display:none">
  本页阅读 <span id="busuanzi_value_page_pv">-</span> 次
  · 本站访问 <span id="busuanzi_value_site_pv">-</span> 次
  · 访客 <span id="busuanzi_value_site_uv">-</span> 人
</div>
<script defer src="https://events.vercount.one/js"></script>
</body>
</html>
"""


# ======================================================================
# 主流程
# ======================================================================
def main() -> int:
    if not CONTENT.is_dir():
        print("!! 没有 content 目录：", CONTENT)
        return 1

    by_name = {s.stem: s for s in CONTENT.glob("*.md")}
    done = skipped = 0

    for i, c in enumerate(NAV):
        s = by_name.get(c["src"])
        if not s:
            print("  · 跳过（源文件缺失）: %s" % c["src"])
            skipped += 1
            continue
        page, info = render(s, i)
        out = SITE / c["dir"] / c["file"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8", newline="\n")
        print("  ✓ %-52s 知识点 %d" % ("%s/%s" % (c["dir"], c["file"]), info["points"]))
        done += 1

    # ---- 可选：同步到 KB_DEPLOY 指定的目录 ----
    import shutil
    if DEPLOY and DEPLOY.exists():
        for f in SITE.rglob("*"):
            if f.is_file():
                d = DEPLOY / f.relative_to(SITE)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)

    print()
    print("  渲染 %d 页（跳过 %d）" % (done, skipped))
    if DEPLOY and DEPLOY.exists():
        print("  已同步到 %s" % DEPLOY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
