# -*- coding: utf-8 -*-
"""知识库内容自检：六块结构、need 覆盖率、密钥泄露、个人信息、渲染一致性。

用法：python check_content.py            → 检查全部章节
      python check_content.py 05 06      → 只检查阶段 05、06
"""

from __future__ import annotations

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

DEPLOY = ROOT / "site"      # 质检时扫描构建产物

SIX = ["@@why", "@@map", "@@summary", "@@quiz", "@@links"]

# ★ 密钥类：发现任何一条就是事故，必须立刻处理
KEYPATS = [
    ("sk-开头的Key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("api_key 硬编码", re.compile(r"api[_-]?key\s*[=:]\s*[\"'][^\"']{12,}[\"']", re.I)),
    ("Bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.")),
    ("明文密码", re.compile(r"(?:pass(?:word)?|pwd)\s*[=:]\s*[\"'][^\"']{4,}[\"']", re.I)),
]

# 合法占位符：出现这些不算泄露
SAFE = re.compile(
    r"(?:你的|your|xxx|XXX|<|>|\$\{|os\.environ|getenv|CHANGE_ME|"
    r"placeholder|示例|例如|\.\.\.|…|sk-xxx)",
)

# ======================================================================
#  ★ 个人信息黑名单 —— 请换成你自己的
# ======================================================================
# 这个检查器会扫所有章节，命中这些词就报警。
#
# 至少要放进去：
#   · 你的真名 / 常用昵称
#   · 你的设备型号、手机序列号
#   · 任何"只有你才有"的标识（订单号、内部项目代号、公司内网地址）
#
# 为什么值得花两分钟填这个：
#   内容一旦公开，这些词会被搜索引擎和 AI 抓走，删都删不干净。
#
PERSONAL: list[str] = [
    # ---- 通用：谁都不该写进公开内容 ----
    "已购",        # "已购课程" 会暴露你买过什么
    "itbaizhan",    # 课程来源站域名
    "百战",         # 课程品牌
    "baizhan",      # 课程品牌（拼音）
    "我的账号",     # 具体账号名不该出现
    # ---- ★ 把你自己的加在下面（示例格式）----
    # "张三",                  # 真名
    # "ThinkPad X1",          # 设备型号
    # "ABCD1234567890",       # 手机序列号（adb devices 查）
]


def main() -> int:
    want = set(sys.argv[1:])
    files = sorted(CONTENT.glob("*.md"))
    files = [f for f in files if f.stem != "_模板"]

    print("=" * 80)
    print("  %-34s %4s %5s %5s   %s" % ("章节", "知识", "need", "trap", "问题"))
    print("=" * 80)

    problems = []
    for f in files:
        t = f.read_text(encoding="utf-8")
        np_ = t.count("@@point")
        nn = t.count("@@need")
        nt = t.count("@@trap")
        flags = []

        miss = [k for k in SIX if k not in t]
        if miss:
            flags.append("★缺块:" + ",".join(miss))
        if np_ and nn < np_:
            flags.append("★need只覆盖 %d/%d" % (nn, np_))
        if np_ and not (8 <= np_ <= 16):
            flags.append("★知识点%d个(应8-16)" % np_)

        for name, pat in KEYPATS:
            for m in pat.finditer(t):
                s = m.group(0)
                if SAFE.search(s):
                    continue
                flags.append("★★【%s】%s" % (name, s[:34]))

        per = [x for x in PERSONAL if x in t]
        if per:
            flags.append("★个人信息:" + ",".join(per))

        vid = len(re.findall(r"course/id/\d+", t))
        if vid:
            flags.append("★视频链接%d条" % vid)

        if flags:
            problems.append((f.name, flags))
        print("  %-34s %4d %5d %5d   %s" % (f.stem[:32], np_, nn, nt,
                                            " ".join(flags) if flags else "✓"))

    # ---------------- 渲染层 ----------------
    print()
    print("=" * 80)
    print("  渲染层：目录条目数 / 标题残留")
    print("=" * 80)
    for dp, _dn, fn in os.walk(DEPLOY):
        if not os.path.basename(dp).startswith("阶段"):
            continue
        for f in sorted(fn):
            if not f.endswith(".html"):
                continue
            t = (Path(dp) / f).read_text(encoding="utf-8")
            npt = t.count('class="point" id=')
            ntc = len(re.findall(r'<a href="#p\d+"', t))
            leak = len(re.findall(r"<p>#{1,6}\s", t))
            ok = npt == ntc and leak == 0 and npt > 0
            if not ok:
                problems.append((f, ["渲染异常 点%d 目录%d 残留%d" % (npt, ntc, leak)]))
            print("  %s %-46s 点 %3d | 目录 %3d | 残留 %d"
                  % ("✓" if ok else "✗", f[:44], npt, ntc, leak))

    print()
    print("=" * 80)
    if problems:
        print("  ⚠️ 发现 %d 个问题：" % len(problems))
        for name, flags in problems:
            print("     %s" % name)
            for x in flags:
                print("        %s" % x)
        return 1
    print("  ✓ 全部通过（%d 个章节）" % len(files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
