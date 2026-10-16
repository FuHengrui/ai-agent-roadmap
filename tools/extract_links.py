# -*- coding: utf-8 -*-
"""从课程章节大纲 .doc 批量抽取「阶段 → 章节 → 课时 → 链接」。

关键技术点
----------
.doc 是 OLE2 容器，正文为 UTF-16LE。超链接是 Word FIELD 结构：

    \\x13  HYPERLINK "网址"  \\n _blank  \\x01  \\x14  显示文字  \\x15
    域开始                                    域分隔           域结束

**网址在前、显示文字在后**（按直觉写成"文字在前"会一条都抽不到）。
章节名以 \\x08 开头、\\r 结尾，出现在其课时之前——因此按【位置】把课时
归给"最近一个出现在它前面的章节名"，比按编号回退可靠得多。
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
from collections import OrderedDict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ======================================================================
#  配置区 —— 按你自己的环境改
# ======================================================================
# 课程大纲 .doc 所在目录
SRC_DIR = os.environ.get("SRC_DIR", r"D:\课程资料")
# 抽取结果输出目录
OUT_DIR = Path(__file__).resolve().parent.parent / "outline"

FIELD = re.compile(r'HYPERLINK\s+"([^"]+)"[^\x13\x14\x15]{0,60}?\x14([^\x13\x15]{0,140})\x15')
CHAP  = re.compile(r"\x08([\u4e00-\u9fa5][^\r\x08\x13\x14\x15]{1,30})\r")
CTRL  = re.compile(r"[\x00-\x1f\x7f]")
JUNK  = re.compile(r"^(大语言模型基础与工程化实践|AI智能体Web系统构建实战|目录|本阶段.*)$")


def read_doc(p: str) -> str:
    return open(p, "rb").read().decode("utf-16-le", errors="ignore").replace("\x00", "")


def clean(s: str) -> str:
    s = CTRL.sub(" ", s).replace("\\n", " ").replace("_blank", " ")
    s = re.sub(r"\\[a-z]+\b", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" \x01：:·-—_ ")


def classify(url: str, label: str) -> str:
    if "资料下载" in label:
        return "resource"          # 本章资料（含网盘）下载页
    if "course/id/" in url:
        return "video"             # 课程视频（课程到期后失效）
    if "training/write/" in url:
        return "homework"          # 章节作业
    if "example.com" in url:   # 按你实际的大纲站点改
        return "site"
    return "external"              # 站外（官网等，长期有效）


def parse(path: str):
    s = read_doc(path)
    stage = os.path.splitext(os.path.basename(path))[0]

    # 章节名 + 位置
    chapters = []
    for m in CHAP.finditer(s):
        name = clean(m.group(1))
        if len(name) >= 2 and not JUNK.match(name) and name not in [c[0] for c in chapters]:
            chapters.append((name, m.start()))
    chapters.sort(key=lambda x: x[1])

    # 链接 + 位置
    links = []
    for m in FIELD.finditer(s):
        url, lab = m.group(1), clean(m.group(2))
        if not lab or lab.startswith(("_blank", "HYPERLINK", "http")):
            continue
        mm = re.match(r"^(\d{1,3})\s*[:：]\s*(.+)$", lab)
        no, title = (int(mm.group(1)), mm.group(2).strip()) if mm else (None, lab)
        links.append({"pos": m.start(), "no": no, "title": title, "url": url})

    # 按位置归属章节
    for L in links:
        cur = ""
        for name, pos in chapters:
            if pos < L["pos"]:
                cur = name
            else:
                break
        L["chapter"] = cur
        L["kind"] = classify(L["url"], L["title"])

    return stage, chapters, links


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    docs = [os.path.join(SRC_DIR, f) for f in sorted(os.listdir(SRC_DIR))
            if f.lower().endswith(".doc")] if os.path.isdir(SRC_DIR) else []
    if not docs:
        print("!! 没找到 .doc：", SRC_DIR); return 1

    outline = OrderedDict()
    all_rows = []
    for p in docs:
        stage, chapters, links = parse(p)
        grouped = OrderedDict()
        for name, _ in chapters:
            grouped[name] = []
        for L in links:
            grouped.setdefault(L["chapter"] or "(未归章)", []).append(L)
        outline[stage] = {"chapters": [{"name": k, "lessons": v} for k, v in grouped.items()]}
        for L in links:
            all_rows.append({"stage": stage, "chapter": L["chapter"], "no": L["no"] or "",
                             "kind": L["kind"], "title": L["title"], "url": L["url"]})
        print("  %-36s 章节 %2d 个（有内容的 %d），链接 %3d 条"
              % (os.path.basename(p), len(chapters),
                 sum(1 for v in grouped.values() if v), len(links)))

    json.dump(outline, open(os.path.join(OUT_DIR, "course_outline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    fn = ["stage", "chapter", "no", "kind", "title", "url"]
    with open(os.path.join(OUT_DIR, "links_all.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(all_rows)

    keep = [r for r in all_rows if r["kind"] != "video"]
    with open(os.path.join(OUT_DIR, "links_keep.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(keep)

    # ---- markdown 报告 ----
    L = ["# 课程大纲与链接抽取", ""]
    for stage, data in outline.items():
        L += ["## %s" % stage, ""]
        for ch in data["chapters"]:
            if not ch["lessons"]:
                continue
            L += ["### %s" % ch["name"], ""]
            for les in ch["lessons"]:
                K = {"video": "视频", "homework": "作业", "resource": "资料",
                     "site": "站内", "external": "站外"}[les["kind"]]
                L.append("- `%s` %s  \n  %s" % (K, les["title"], les["url"]))
            L.append("")
    open(os.path.join(OUT_DIR, "links_report.md"), "w", encoding="utf-8").write("\n".join(L))

    print()
    print("  全部 %d 条 → outline/links_all.csv" % len(all_rows))
    print("  非视频 %d 条 → outline/links_keep.csv" % len(keep))
    print("  分类：", dict(Counter(r["kind"] for r in all_rows)))
    print()
    print("  ═══ 阶段1 章节结构 ═══")
    st1 = list(outline.items())[0]
    for ch in st1[1]["chapters"]:
        if not ch["lessons"]:
            continue
        kinds = Counter(l["kind"] for l in ch["lessons"])
        print("   %-22s %3d 课时  %s" % (ch["name"][:22], len(ch["lessons"]), dict(kinds)))
    print()
    print("  ═══ 全部「资料下载地址」（非视频，可保留）═══")
    for r in keep:
        if r["kind"] in ("resource", "external"):
            print("   %-14s %-28s %s" % (r["chapter"][:14], r["title"][:28], r["url"][:62]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
