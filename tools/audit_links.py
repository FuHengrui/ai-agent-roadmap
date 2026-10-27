# -*- coding: utf-8 -*-
"""外链体检：把正文里 400 多条「去别人家」的链接挨个敲一遍，看还活着没。

为什么要做
----------
`@@links` 里的官方文档、论文、GitHub 仓库，都会过期：项目改名、文档改版、
仓库归档。页面本身不会报错，读者点进去才发现 404 —— 这种烂掉是**静默的**。

怎么判
------
  ok       2xx
  moved    3xx（跟到最后还是 2xx 就算 ok）
  dead     404 / 410
  blocked  403 / 429（多半是反爬，不代表链接坏了）
  error    连接失败 / 超时 / TLS 证书问题

⚠️ 超时和 403 不要直接当死链：这台机器访问外网本来就慢（GitHub raw 长期不通），
   报告要人看一眼再决定改不改。

用法：
    python tools/audit_links.py               # 全量（约 2–5 分钟）
    python tools/audit_links.py --limit 20    # 先试 20 条
    python tools/audit_links.py --md out.md   # 顺便写一份报告
"""

from __future__ import annotations

import argparse
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_site import CONTENT, NAV  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# 只关心状态码，不校验证书（这台机器对部分站点的证书链本来就不通）
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
TIMEOUT = 12


def collect() -> dict:
    """{url: [章节…]}"""
    found: dict[str, list[str]] = {}
    for c in NAV:
        p = CONTENT / (c["src"] + ".md")
        if not p.exists():
            continue
        for ln in p.read_text(encoding="utf-8").split("\n"):
            m = re.match(r"^[^|]+\|[^|]*\|(\S+)\s*$", ln.strip())
            if m and m.group(1).startswith("http"):
                found.setdefault(m.group(1), []).append(c["file"])
    return found


def probe(url: str) -> tuple[str, str]:
    # 有些链接带中文路径（比如中文博客），http.client 只收 ASCII —— 先转成百分号编码，
    # 已经编码过的（含 %）不要二次编码，所以把 % 放进 safe。
    url = quote(url, safe=":/?#[]@!$&'()*+,;=%")
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                return ("ok" if r.status < 400 else "blocked", str(r.status))
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue          # 有的站不认 HEAD，换 GET 再试
            if e.code in (404, 410):
                return "dead", str(e.code)
            if e.code in (403, 429):
                return "blocked", str(e.code)
            return "error", "HTTP %d" % e.code
        except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as e:
            if method == "HEAD":
                continue
            return "error", type(e).__name__
    return "error", "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--md", default="")
    args = ap.parse_args()

    urls = collect()
    items = sorted(urls.items())
    if args.limit:
        items = items[: args.limit]

    results: list[tuple[str, str, str, list[str]]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(probe, u): (u, owners) for u, owners in items}
        for i, (fut, (u, owners)) in enumerate(futures.items(), 1):
            try:
                kind, detail = fut.result()
            except Exception as e:  # noqa: BLE001 —— 单条炸了不许拖垮整轮
                kind, detail = 'error', type(e).__name__
            results.append((u, kind, detail, owners))
            if i % 50 == 0:
                print("  …%d/%d" % (i, len(items)))

    buckets: dict[str, list] = {}
    for r in results:
        buckets.setdefault(r[1], []).append(r)

    print()
    for k in ("ok", "dead", "blocked", "error"):
        print("  %-8s %d" % (k, len(buckets.get(k, []))))
    print("  合计 %d 条（去重后）" % len(results))

    for k in ("dead", "blocked", "error"):
        rows = buckets.get(k, [])
        if not rows:
            continue
        print("\n  == %s ==" % k)
        for u, _k, detail, owners in rows[:25]:
            print("    [%s] %s  ← %s" % (detail, u, owners[0] if owners else "?"))
        if len(rows) > 25:
            print("    …… 还有 %d 条" % (len(rows) - 25))

    if args.md:
        out = [Path(args.md).stem, ""]
        out.append("体检时间：见文件时间；共 %d 条唯一链接\n" % len(results))
        out.append("| 结果 | 条数 |")
        out.append("|---|---|")
        for k in ("ok", "dead", "blocked", "error"):
            out.append("| %s | %d |" % (k, len(buckets.get(k, []))))
        out.append("")
        for k in ("dead", "blocked", "error"):
            rows = buckets.get(k, [])
            if not rows:
                continue
            out.append("## %s（%d）\n" % (k, len(rows)))
            out.append("| 链接 | 状态 | 出处 |")
            out.append("|---|---|---|")
            for u, _k, detail, owners in rows:
                out.append("| %s | %s | %s |" % (u, detail, "、".join(sorted(set(owners))[:3])))
            out.append("")
        Path(args.md).write_text("\n".join(out), encoding="utf-8", newline="\n")
        print("\n  报告已写入 %s" % args.md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())