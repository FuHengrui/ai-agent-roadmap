# -*- coding: utf-8 -*-
"""发布前安全扫描 —— 扫 git 已跟踪的全部文件，找不该公开的东西。

用法：
    python tools/check_publish.py

退出码：0 = 干净，1 = 有问题。
建议放进 git pre-push 钩子，或者推之前手动跑一次。
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# ======================================================================
#  ★ 换成你自己的 —— 这里默认是空的，请填上
# ======================================================================
# 这些词一旦进了公开仓库，就会被搜索引擎和 AI 抓走，删都删不干净。
#
# 格式：  "说明": "要拦的词"
#
# 至少填这几类（把下面注释掉的改成你自己的）：
#   · 你的真名、常用昵称
#   · 你的设备型号、手机序列号（adb devices 能查）
#   · 你买过的课 / 服务名（写出来等于告诉别人你买了什么）
#   · 公司或学校的内网地址、内部项目代号
#
# ⚠️ 注意：别拿"张三""李四"这种当测试词 ——
#    它们是中文内容里通用的示例人名，会满屏误报。
#
BANNED: dict[str, str] = {
    "课程来源站": "itbaizhan",
    "课程品牌":   "百战",
    # "真名":       "你的名字",
    # "设备型号":    "你的笔记本型号",
    # "手机序列号":  "adb devices 查出来的那串",
    # "买的课程":    "课程名",
}

# 这些是"谁都不该写进公开内容"的，不用改
BANNED_ALWAYS: list[str] = [
    "已购",          # "已购课程" 会暴露你买过什么
    "我的账号是",     # 具体账号名不该出现
]

# 密钥类（正则）
SECRETS: dict[str, str] = {
    "OpenAI 风格 Key": r"sk-[A-Za-z0-9]{20,}",
    "阿里云 AccessKey": r"LTAI[A-Za-z0-9]{12,}",
    "Bearer Token": r"Bearer\s+[A-Za-z0-9._\-]{20,}",
    "JWT": r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.",
    "私钥文件": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
}

# 不该出现在仓库里的文件名
BANNED_FILES = [
    r"\.pdf$", r"\.docx?$", r"\.ipynb$", r"\.env$", r"\.p12$", r"\.key$",
    r"_资料索引/", r"_阶段\d+提取/", r"id_ed25519",
]

# 合法占位符（命中这些不算泄露）
SAFE = re.compile(
    r"(?:你的|your|xxx|XXX|张三|ABCD|<|>|\$\{|os\.environ|getenv|"
    r"CHANGE_ME|placeholder|示例|例如|\.\.\.|…)"
)


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8").stdout
    return [f for f in out.split("\n") if f.strip()]


def main() -> int:
    files = tracked_files()
    if not files:
        print("  !! 这不是一个 git 仓库，或者还没有任何文件被跟踪")
        return 1

    print("  扫描 %d 个已跟踪文件…" % len(files))
    print()

    problems = 0

    # ---- 1. 不该有的文件 ----
    bad_files = []
    for f in files:
        for pat in BANNED_FILES:
            if re.search(pat, f):
                bad_files.append(f)
                break
    if bad_files:
        problems += len(bad_files)
        print("  ★ 不该提交的文件：")
        for f in bad_files[:20]:
            print("       %s" % f)
    else:
        print("  ✓ 文件类型检查通过")

    # ---- 2. 违禁词 ----
    print()
    hit_words = 0
    all_banned = dict(BANNED)
    all_banned.update({("通用·%s" % w): w for w in BANNED_ALWAYS})

    # 跳过"定义这些词"的检查器自己 —— 否则它们会自己举报自己
    SELF = {"tools/check_publish.py", "tools/check_content.py"}

    for f in files:
        if f in SELF:
            continue
        p = ROOT / f
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for label, word in all_banned.items():
            if not word:
                continue
            for m in re.finditer(re.escape(word), t):
                line = t[:m.start()].count("\n") + 1
                print("  ★ %-40s 第%d行  【%s】%s" % (f, line, label, word))
                hit_words += 1
                break
    problems += hit_words
    if not hit_words:
        n = len(BANNED)
        print("  ✓ 违禁词检查通过（你自己填了 %d 个词 + %d 个通用词）"
              % (n, len(BANNED_ALWAYS)))

    # ---- 3. 密钥 ----
    print()
    hit_sec = 0
    for f in files:
        p = ROOT / f
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for label, pat in SECRETS.items():
            for m in re.finditer(pat, t):
                seg = t[max(0, m.start() - 60):m.end() + 20]
                if SAFE.search(seg):
                    continue          # 是占位符，放过
                line = t[:m.start()].count("\n") + 1
                print("  ★ %-40s 第%d行  【%s】" % (f, line, label))
                hit_sec += 1
                break
    problems += hit_sec
    if not hit_sec:
        print("  ✓ 密钥检查通过（%d 类）" % len(SECRETS))

    # ---- 结论 ----
    print()
    if problems:
        print("  ══ 发现 %d 处问题，先处理再推 ══" % problems)
        return 1
    print("  ══ ✓ 干净，可以推 ══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
