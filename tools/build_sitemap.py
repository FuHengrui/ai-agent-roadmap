# -*- coding: utf-8 -*-
"""生成 sitemap.xml 与 robots.txt —— 给搜索引擎一张「我家有哪些页」的清单。

为什么需要
----------
GitHub Pages 不发 sitemap，搜索引擎只能顺着链接慢慢爬：238 章分布式目录，爬全要很久，
而且漏了也不知道。主动递一张清单，收录快、也方便在 Search Console 里看每页的曝光。
（这也是判断「要不要加强站内搜索」的唯一真数据来源。）

注意两点：
  · 路径里有中文，**必须 percent-encode**，否则部分爬虫会把整行判为无效 URL
  · 不写 <lastmod>：写了就得每天变，CI 的「站点一致性」检查会天天报红

不收录 `stats.html`（访问数据页，只有作者知道地址）。

用法：
    python tools/build_sitemap.py     # 写 site/sitemap.xml + site/robots.txt
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "tools"))

from build_site import NAV  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

BASE = "https://fuhengrui.github.io/ai-agent-roadmap/"

# 根目录下要收录的页面（stats.html 故意不放）
ROOT_PAGES = ["index.html", "README.html", "search.html"]


def url_for(path: str) -> str:
    return BASE + quote(path, safe="/")


def main() -> int:
    pages = [p for p in ROOT_PAGES if (SITE / p).is_file()]
    pages += ["%s/%s" % (c["dir"], c["file"])
              for c in NAV if (SITE / c["dir"] / c["file"]).is_file()]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        lines.append("  <url><loc>%s</loc></url>" % url_for(p))
    lines.append("</urlset>")

    (SITE / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (SITE / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: %s\n" % url_for("sitemap.xml"),
        encoding="utf-8", newline="\n")

    print("  ✓ sitemap.xml：%d 个页面" % len(pages))
    print("  ✓ robots.txt：指向 sitemap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())