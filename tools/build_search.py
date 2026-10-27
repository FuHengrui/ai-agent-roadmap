# -*- coding: utf-8 -*-
"""全站搜索：把 content/*.md 抽成一份索引 + 一个搜索页。

为什么这么做
------------
238 章、130 多万字，只能靠侧边栏一章章点进去 = 找不到东西。
搜索要用**纯静态**方案：不引 CDN、不上后端，双击 site/index.html 也能用。

两个关键约束决定了实现方式：
  1. **不能 fetch JSON** —— file:// 下会被 CORS 拦掉。所以索引写成
     `site/search-index.js`，用 <script src> 加载，`file://` 照样能读。
  2. **不能引入大的检索库** —— 中文用**子串匹配**已经够好（不用分词），
     匹配逻辑直接写在页面里，几十行，零依赖。

索引结构（数组形式，省掉重复的 key，控制体积）
------------------------------------------------
    window.KB_SEARCH = {
      "chapters": [
        [章节标题, 阶段名, "阶段XX-…/文件名.html", 章节级正文摘要, [
          ["1", "① 知识点标题", "知识点正文摘录"], …
        ]],
        …
      ]
    }

每个知识点带 `pN`，正好对应 build_site.py 渲染出的 `<div class="point" id="pN">`，
所以搜索结果能直接跳到那一条，而不是只跳到章首。

用法：
    python tools/build_search.py            # 生成 site/search-index.js + site/search.html
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "tools"))

# ★ 这两个模块都要 import：build_site 提供解析器，sync_index 提供侧边栏。
#   它们内部都把 stdout 重新包过一层 TextIOWrapper，两个一起 import 会把底层
#   buffer 关掉（ValueError: I/O operation on closed file），所以那边改成了
#   sys.stdout.reconfigure()，这里也就不能再自己包一层。
from build_site import CONTENT, NAV, parse  # noqa: E402
from sync_index import AVAILABLE, sidebar_html  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

# 每条结果里正文留多少字。实测：200 字漏得厉害（「向量数据库」只命中 7 处），
# 400 字能覆盖大多数知识点的前两段，索引约 2 MB（Pages 走 gzip，实际传输 ~0.5 MB）。
POINT_CHARS = 400
CHAPTER_CHARS = 240

CIRCLED = re.compile(r"^[\u2460-\u2473]\s*")


def plain(lines) -> str:
    """把 markdown 正文压成可搜索的纯文本（保留中英文与数字）。"""
    out = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("@@"):
            continue
        if re.match(r"^\|[\s:\-|]+\|$", s):          # 表格分隔行
            continue
        s = re.sub(r"`([^`]*)`", r"\1", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = s.replace("|", " ").replace("<br>", " ")
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"\s+", " ", s)
        if s:
            out.append(s)
    return " ".join(out)


def cut(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n].rstrip() + "…"


def chapter_text(blocks) -> str:
    """章节级摘要：为什么学 + 小结 + 自测题（这三块最像「别人会怎么搜」）。"""
    parts = []
    for b in blocks:
        if b["k"] in ("why", "summary", "quiz", "note"):
            parts.append(plain([b["arg"]] + b["body"]))
    return cut(" ".join(x for x in parts if x), CHAPTER_CHARS)


def point_list(blocks) -> list:
    out = []
    n = 0
    for b in blocks:
        if b["k"] != "point":
            continue
        n += 1
        title = CIRCLED.sub("", b["arg"]).strip() or "知识点 %d" % n
        lines = []
        for ln in b["body"]:
            m = re.match(r"^@@(\w+)(?:\s+(.*))?$", ln.strip())
            if m:
                if m.group(2):
                    lines.append(m.group(2))   # @@need 要解决什么 —— 这行也是正文
            else:
                lines.append(ln)
        out.append([str(n), title, cut(plain(lines), POINT_CHARS)])
    return out


def build_index() -> dict:
    chapters = []
    for i, c in enumerate(NAV):
        if i not in AVAILABLE:
            continue
        src = CONTENT / (c["src"] + ".md")
        blocks = parse(src.read_text(encoding="utf-8"))
        chapters.append([
            c["title"],
            c.get("stage", ""),
            "%s/%s" % (c["dir"], c["file"]),
            chapter_text(blocks),
            point_list(blocks),
        ])
    return {"chapters": chapters}


SEARCH_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>搜索 · {brand}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="layout">
<nav class="sidebar">
{nav}
</nav>
<main class="main"><div class="wrap">
<h1>搜索</h1>
<div class="subtitle">{nch} 章 · {npt} 个知识点，搜一句话或一个词</div>

<form class="search-form" id="sf" onsubmit="return false">
  <input id="q" type="search" name="q" autocomplete="off" autofocus
         placeholder="比如：向量数据库怎么选 / MCP 是什么 / 为什么要用 LCEL">
  <button type="submit">搜索</button>
</form>

<div class="search-stat" id="stat">输入关键词，边打边出结果（Esc 清空）</div>
<div class="hits" id="hits"></div>
<p class="search-hint">搜的是 <strong>全站正文</strong>：知识点标题、讲解、避坑、自测题都在里面。点结果直接跳到那一节。</p>
</div></main>
</div>
<script src="search-index.js"></script>
<script>
(function () {{
  var D = window.KB_SEARCH || {{ chapters: [] }};
  var MAX = 40;
  var q = document.getElementById('q');
  var hits = document.getElementById('hits');
  var stat = document.getElementById('stat');

  function esc(s) {{
    return String(s).replace(/[&<>]/g, function (c) {{
      return {{ '&': '&amp;', '<': '&lt;', '>': '&gt;' }}[c];
    }});
  }}
  function rx(t) {{
    return new RegExp(t.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'), 'gi');
  }}
  function mark(s, ts) {{
    var out = esc(s);
    ts.forEach(function (t) {{
      if (t) out = out.replace(rx(t), function (m) {{ return '<mark>' + m + '</mark>'; }});
    }});
    return out;
  }}
  function tokens(s) {{
    return String(s || '').toLowerCase().split(/\\s+/).filter(Boolean);
  }}
  function allIn(hay, ts) {{
    for (var i = 0; i < ts.length; i++) if (hay.indexOf(ts[i]) < 0) return false;
    return true;
  }}
  function snippet(text, ts) {{
    var low = text.toLowerCase(), at = -1;
    for (var i = 0; i < ts.length; i++) {{
      var k = low.indexOf(ts[i]);
      if (k >= 0 && (at < 0 || k < at)) at = k;
    }}
    if (at < 0) at = 0;
    var start = Math.max(0, at - 40);
    var seg = text.substr(start, 120);
    return (start > 0 ? '…' : '') + mark(seg, ts) + (start + 120 < text.length ? '…' : '');
  }}

  function run() {{
    var ts = tokens(q.value);
    if (!ts.length) {{
      hits.innerHTML = '';
      stat.textContent = '输入关键词，边打边出结果（Esc 清空）';
      return;
    }}
    var res = [];
    D.chapters.forEach(function (ch) {{
      var title = ch[0], stage = ch[1], url = ch[2], blob = ch[3] || '', pts = ch[4] || [];
      var head = (title + ' ' + stage).toLowerCase();
      var titleHit = allIn(head, ts);

      if (titleHit && blob) {{
        res.push({{ score: 120, url: url, ch: ch, anchor: '', text: blob, label: '章节' }});
      }}
      pts.forEach(function (p) {{
        var pid = p[0], ptitle = p[1], text = p[2] || '';
        var hay = (ptitle + ' ' + text).toLowerCase();
        if (!allIn(hay, ts)) return;
        var s = 50, low = hay, n;
        ts.forEach(function (t) {{
          if (ptitle.toLowerCase().indexOf(t) >= 0) s += 25;
          n = low.split(t).length - 1;
          s += Math.min(n, 10) * 3;
        }});
        if (titleHit) s += 20;
        res.push({{ score: s, url: url, ch: ch, anchor: '#p' + pid, text: text, label: ptitle }});
      }});
    }});

    res.sort(function (a, b) {{ return b.score - a.score; }});
    var total = res.length;
    res = res.slice(0, MAX);

    // ★ 用 DOM 拼，不拼字符串：字符串里的链接模板会被 verify_site.py 当成死链（当场被抓过一次）
    var frag = document.createDocumentFragment();
    res.forEach(function (r) {{
      var a = document.createElement('a');
      a.className = 'hit';
      a.href = r.url + r.anchor;
      a.innerHTML =
        '<div class="hit-ch">' + esc(r.ch[1]) + ' · ' + esc(r.ch[0]) + '</div>' +
        '<div class="hit-t">' + (r.label === '章节' ? '（整章）' : mark(r.label, ts)) + '</div>' +
        '<div class="hit-s">' + snippet(r.text, ts) + '</div>';
      frag.appendChild(a);
    }});
    hits.innerHTML = '';
    hits.appendChild(frag);
    stat.textContent = total
      ? ('命中 ' + total + ' 处' + (total > MAX ? '，只显示前 ' + MAX + ' 处' : '') + ' —— 点一下直接跳过去')
      : ('没搜到「' + q.value.trim() + '」；试试更短的词，比如只搜「向量」而不是整句');
  }}

  var timer = null;
  q.addEventListener('input', function () {{
    clearTimeout(timer);
    timer = setTimeout(run, 120);
  }});
  q.addEventListener('keydown', function (e) {{
    if (e.key === 'Escape') {{ q.value = ''; run(); }}
  }});

  var m = /[?&]q=([^&]*)/.exec(location.search);
  if (m) {{
    q.value = decodeURIComponent(m[1].replace(/\\+/g, ' '));
    run();
  }}
  q.focus();
}})();
</script>
</body>
</html>
"""


def main() -> int:
    data = build_index()
    chs = data["chapters"]
    npt = sum(len(c[4]) for c in chs)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    out = SITE / "search-index.js"
    out.write_text("window.KB_SEARCH=" + payload + ";\n", encoding="utf-8", newline="\n")

    page = SEARCH_HTML.format(
        brand="建立知识库", nav=sidebar_html("search.html"),
        nch=len(chs), npt=npt,
    )
    (SITE / "search.html").write_text(page, encoding="utf-8", newline="\n")

    print("  ✓ 索引 %d 章 / %d 个知识点，%.1f MB" % (len(chs), npt, out.stat().st_size / 1048576.0))
    print("  ✓ 搜索页 site/search.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())