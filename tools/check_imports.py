# -*- coding: utf-8 -*-
"""查「代码块用了某个库，但这一块没有 import」。

这是这轮自查里最高频的一类「照抄就炸」：`torch.randn` 没 import torch、`os.getenv` 没 import os、
`@tool` 没 import tool、`uvicorn.run` 没 import uvicorn……

做法：
  1. 抽每个 ```python 块，用 ast 拿到「本块 import 了哪些名字」和「用到了哪些顶层名字」；
  2. 用到的名字如果属于「常见第三方库的顶层名」，而本块又没 import 它，就报一条；
  3. 只报「疑似」，因为片段可能承接上文——所以默认只打印，加 --check 才当错（且允许文件级白名单）。

用法：
  python tools/check_imports.py            # 只看报告
  python tools/check_imports.py --check    # CI 用：命中即退出码 1
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

STRICT = "--strict" in sys.argv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 顶层名 → 装了哪个包才能 import（只列书里常用的）
KNOWN = {
    "torch": "torch", "np": "numpy", "pd": "pandas", "plt": "matplotlib",
    "sns": "seaborn", "cv2": "opencv-python", "jieba": "jieba",
    "chromadb": "chromadb", "faiss": "faiss-cpu", "ollama": "ollama",
    "requests": "requests", "httpx": "httpx", "aiohttp": "aiohttp",
    "uvicorn": "uvicorn", "fastapi": "fastapi", "openai": "openai",
    "dashscope": "dashscope", "transformers": "transformers", "peft": "peft",
    "datasets": "datasets", "trl": "trl", "accelerate": "accelerate",
    "os": "标准库", "sys": "标准库", "json": "标准库", "re": "标准库",
    "asyncio": "标准库", "time": "标准库", "datetime": "标准库",
    "logging": "标准库", "pathlib": "标准库", "typing": "标准库",
    "subprocess": "标准库", "random": "标准库", "math": "标准库",
    "statistics": "标准库", "sqlite3": "标准库", "base64": "标准库",
    "hashlib": "标准库", "uuid": "标准库", "collections": "标准库",
    "itertools": "标准库", "functools": "标准库", "dataclasses": "标准库",
    "abc": "标准库", "contextlib": "标准库", "threading": "标准库",
    "queue": "标准库", "csv": "标准库", "io": "标准库", "glob": "标准库",
    "shutil": "标准库", "tempfile": "标准库", "traceback": "标准库",
    "warnings": "标准库", "unittest": "标准库", "sklearn": "scikit-learn",
    "langchain": "langchain", "langchain_core": "langchain-core",
    "langgraph": "langgraph", "pymilvus": "pymilvus", "tortoise": "tortoise-orm",
    "pydantic": "pydantic", "pydantic_settings": "pydantic-settings",
    "dotenv": "python-dotenv", "streamlit": "streamlit", "gradio": "gradio",
    "rank_bm25": "rank-bm25", "sentence_transformers": "sentence-transformers",
}

FENCE = re.compile(r"^```(\w*)\s*$")


def blocks(text: str):
    lines = text.split("\n")
    lang, body, start = None, [], 0
    for i, ln in enumerate(lines, 1):
        m = FENCE.match(ln.strip())
        if m:
            if lang is None:
                lang, body, start = (m.group(1) or "text").lower(), [], i + 1
            else:
                yield lang, start, "\n".join(body)
                lang, body = None, []
            continue
        if lang is not None:
            body.append(ln)


def imported_names(src: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        # 片段常常语法不全：退回正则
        for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+))", src, re.M):
            if m.group(1):
                names.add(m.group(1).split(".")[0])
            if m.group(2):
                for part in m.group(2).split(","):
                    part = part.strip().split(" as ")[-1].strip()
                    if part:
                        names.add(part.split(".")[0])
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def used_names(src: str, imports: set[str]) -> set[str]:
    used = set()
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.", src):
        name = m.group(1)
        if name in KNOWN and name not in imports:
            used.add(name)
    return used


def main() -> int:
    hits = []
    checked = 0
    for p in sorted(CONTENT.glob("*.md")):
        if p.name.startswith("_"):
            continue
        text = p.read_text(encoding="utf-8")
        for lang, start, body in blocks(text):
            if lang not in ("python", "py"):
                continue
            if STRICT and "完整示例" not in body:
                continue   # --strict 只查「自称完整示例」的块，普通片段不冤枉它
            checked += 1
            imps = imported_names(body)
            for name in sorted(used_names(body, imps)):
                hits.append((p.name, start, name, KNOWN[name]))
    print("检查了 %d 个 python 代码块" % checked)
    if not hits:
        print("✓ 没有发现「用了却没 import」的块")
        return 0
    print("疑似缺 import：%d 处" % len(hits))
    for name, line, var, pkg in hits:
        print("  %s:%d  用了 %s（需要 %s）" % (name, line, var, pkg))
    return 1 if "--check" in sys.argv else 0


if __name__ == "__main__":
    raise SystemExit(main())