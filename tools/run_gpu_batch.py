# -*- coding: utf-8 -*-
"""跨平台批量真跑：把一批章跑一遍，输出「章 → 通过/报错/跳过」汇总。

用法（在云主机或本机都能跑）：
    python tools/run_gpu_batch.py                 # 跑默认的 torch 相关章
    python tools/run_gpu_batch.py --all           # 跑全书（会很久）
    python tools/run_gpu_batch.py --stage 21      # 只跑某阶段
    python tools/run_gpu_batch.py --json out.json # 顺带存一份结果

判据沿用 run_chapter：缺依赖记「跳过」，其余异常记「报错」。
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "覆盖台账.md"
RUNNER = ROOT / "tools" / "run_chapter.py"


def chapters():
    out = []
    for ln in LEDGER.read_text(encoding="utf-8").split("\n"):
        if not ln.startswith("|"):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 7 and c[1].endswith(".md"):
            out.append((c[0], c[1]))
    return out


def needs_torch(name: str) -> bool:
    p = ROOT / "content" / name
    return p.exists() and "torch" in p.read_text(encoding="utf-8")


def run_one(name: str):
    r = subprocess.run([sys.executable, str(RUNNER), name],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout or ""
    m = re.search(r"通过 (\d+) / 报错 (\d+) / 跳过 (\d+)", out)
    ok, bad, skip = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)
    errs = [l.strip() for l in out.split("\n") if "[ERR]" in l][:3]
    return {"chapter": name, "ok": ok, "bad": bad, "skip": skip, "errors": errs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="全书都跑")
    ap.add_argument("--stage", help="只跑某阶段，如 21")
    ap.add_argument("--json", help="把结果写到这个文件")
    a = ap.parse_args()

    items = chapters()
    if a.stage:
        items = [x for x in items if x[0].replace("阶段 ", "") == a.stage]
    elif not a.all:
        items = [x for x in items if needs_torch(x[1])]

    print("将跑 %d 章" % len(items))
    results = []
    for i, (stage, name) in enumerate(items, 1):
        r = run_one(name)
        results.append({"stage": stage, **r})
        flag = "OK" if r["bad"] == 0 else "ERR"
        print("[%2d/%d] %-8s %-46s %s (通过%d 报错%d 跳过%d)"
              % (i, len(items), stage, name[:46], flag, r["ok"], r["bad"], r["skip"]))
        for e in r["errors"]:
            print("        %s" % e[:100])

    bad = [r for r in results if r["bad"]]
    print("\n== 汇总：%d 章，全通过 %d，有报错 %d" % (len(results), len(results) - len(bad), len(bad)))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
        print("结果已写入 %s" % a.json)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())