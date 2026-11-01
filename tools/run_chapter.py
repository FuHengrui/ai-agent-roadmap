# -*- coding: utf-8 -*-
"""把一章的 ```python 代码块按顺序真跑一遍，报告哪块报错。

为什么要它：**「读着对」和「能跑」是两件事**。
二轮复核 238 章靠读，抓不到「boxplot(labels=) 改名 tick_labels」「数据定义在最后一个代码块」
「Chroma 返回的是 distance 不是 score」这类——只有执行才知道。

用法：
    python tools/run_chapter.py "09-第九章-NumPy计算统计与进阶.md"
    python tools/run_chapter.py --list              # 列出清单里验证过的章
    python tools/run_chapter.py <章> --keep-flags   # 保留 matplotlib 缺库时的跳过行为

行为：
- 抽取 ```python 块，**按顺序在同一命名空间里执行**（模拟读者边看边敲，变量会累积）
- 无头环境：matplotlib 用 Agg；plt.show() / uvicorn.run() 置空
- 缺依赖（matplotlib/seaborn/torch/transformers）记为「跳过」，不算失败
- 每块只报 traceback 最后一行，不中断后续块

退出码：0 = 没有「报错」块；1 = 有报错块。
"""
import argparse
import contextlib
import io
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

SOFT_MISSING = ("matplotlib", "seaborn", "torch", "transformers", "gensim")


def blocks(text: str):
    """抽出所有 ```python 代码块的内容。"""
    out, cur, fence = [], None, None
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("```"):
            if fence is None:
                fence = s[3:].strip().lower()
                if fence == "python":
                    cur = []
                continue
            if cur is not None:
                out.append("\n".join(cur))
                cur = None
            fence = None
            continue
        if cur is not None:
            cur.append(ln)
    return out


def run(name: str) -> int:
    p = CONTENT / name
    if not p.exists():
        print("找不到 %s（用 --list 看看有哪些）" % p)
        return 2
    bs = blocks(p.read_text(encoding="utf-8"))
    print("== %s：%d 个 python 块" % (name, len(bs)))
    ns = {"__name__": "__main__"}
    ok = bad = skip = 0
    for i, code in enumerate(bs, 1):
        if not code.strip():
            skip += 1
            continue
        code = code.replace("plt.show()", "pass").replace("uvicorn.run(", "pass  # uvicorn.run(")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(code, "<块%d>" % i, "exec"), ns)
            ok += 1
            print("  块%-2d [OK]" % i)
            continue
        except ModuleNotFoundError as e:
            if any(m in str(e) for m in SOFT_MISSING):
                skip += 1
                print("  块%-2d [SKIP 缺依赖] %s" % (i, str(e)[:60]))
                continue
            err = e
        except Exception as e:  # noqa: BLE001 - 就是要抓所有异常
            err = e
        bad += 1
        last = [x for x in traceback.format_exc().strip().split("\n") if x.strip()][-1]
        print("  块%-2d [ERR] %s" % (i, last[:110]))
    print("== 结果：通过 %d / 报错 %d / 跳过 %d" % (ok, bad, skip))
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="逐块真跑某章的 python 代码")
    ap.add_argument("chapter", nargs="?", help="content/ 下的文件名，如 09-第九章-xxx.md")
    ap.add_argument("--list", action="store_true", help="列出 docs/代码验证清单.md 里验证过的章")
    a = ap.parse_args()
    if a.list:
        doc = ROOT / "docs" / "代码验证清单.md"
        for ln in doc.read_text(encoding="utf-8").split("\n"):
            if ln.startswith("| 阶段"):
                print(ln.split("|")[1].strip())
        return 0
    if not a.chapter:
        ap.print_help()
        return 2
    return run(a.chapter)


if __name__ == "__main__":
    sys.exit(main())