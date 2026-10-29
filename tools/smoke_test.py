# -*- coding: utf-8 -*-
"""冒烟测试：把书里最容易被照抄的 4 个示例真跑一遍。

跑什么：
  1) FastAPI 最小应用 + TestClient（书里"hello world"那段）
  2) Tortoise ORM + SQLite 的增查改删（书里模型/查询那段）
  3) Pandas 读写 + 分组 + 日期（书里数据分析主路径）
  4) LangGraph 最小图（书里 State/Node/Edge 那段）——没装就跳过

不跑什么：
  vLLM / CUDA / Spark / Docker——这些要么要 GPU、要么要集群，本机跑不了。

用法：python tools/smoke_test.py
结果写进 docs/冒烟测试.md（--doc）。
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "冒烟测试.md"

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

results: list[tuple[str, bool, str]] = []


def record(name: str, fn):
    try:
        detail = fn() or ""
        results.append((name, True, str(detail)))
        print("✓ %s %s" % (name, detail))
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc().strip().split("\n")[-1]
        results.append((name, False, tb))
        print("✗ %s —— %s" % (name, tb))


# 模型必须定义在模块层（Tortoise 要按模块路径找它）
from tortoise import fields, models  # noqa: E402


class Note(models.Model):
    id = fields.IntField(pk=True)
    text = fields.CharField(max_length=50)

    class Meta:
        table = "notes"


# ---------------- 1) FastAPI ----------------
def smoke_fastapi():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/hello")
    def hello():
        return {"msg": "hello"}

    c = TestClient(app)
    r = c.get("/hello")
    assert r.status_code == 200, r.status_code
    assert r.json() == {"msg": "hello"}, r.text
    return "GET /hello → 200"


# ---------------- 2) Tortoise + SQLite ----------------
def smoke_tortoise():
    from tortoise import Tortoise

    async def run():
        await Tortoise.init(db_url="sqlite://:memory:",
                            modules={"models": ["__main__"]})
        await Tortoise.generate_schemas()
        n = await Note.create(text="hello")
        got = await Note.get(id=n.id)
        found = await Note.filter(text__contains="hell").first()
        got.text = "changed"
        await got.save()
        cnt = await Note.all().count()
        await Tortoise.close_connections()
        return cnt, found is not None

    cnt, found = asyncio.run(run())
    assert cnt == 1 and found
    return "建表/插入/查询/更新 → OK"


# ---------------- 3) Pandas ----------------
def smoke_pandas():
    import pandas as pd

    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-01", "2026-01-02"],
        "city": ["北京", "上海", "北京"],
        "sales": [100, 200, 300],
    })
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby("city", as_index=False)["sales"].sum()
    assert set(g["city"]) == {"北京", "上海"}
    assert int(g.loc[g.city == "北京", "sales"].iloc[0]) == 400
    monthly = df.set_index("date").resample("ME")["sales"].sum()
    assert len(monthly) == 1
    return "groupby / resample('ME') → OK"


# ---------------- 4) LangGraph ----------------
def smoke_langgraph():
    from typing import TypedDict

    from langgraph.graph import END, START, StateGraph

    class S(TypedDict):
        n: int

    def inc(state: S):
        return {"n": state["n"] + 1}

    b = StateGraph(S)
    b.add_node("inc", inc)
    b.add_edge(START, "inc")
    b.add_edge("inc", END)
    g = b.compile()
    out = g.invoke({"n": 1})
    assert out["n"] == 2, out
    return "START→inc→END → OK"


def main() -> int:
    record("FastAPI 最小应用", smoke_fastapi)
    record("Tortoise + SQLite", smoke_tortoise)
    record("Pandas 读写/分组/重采样", smoke_pandas)
    try:
        import langgraph  # noqa: F401
        record("LangGraph 最小图", smoke_langgraph)
    except ImportError:
        results.append(("LangGraph 最小图", False, "未安装 langgraph，跳过"))
        print("- LangGraph 最小图：未安装，跳过")

    if "--check" in sys.argv:
        bad = [n for n, ok, _ in results if not ok]
        if bad:
            print("失败：%s" % "、".join(bad))
            return 1
        print("全部通过")
        return 0

    if "--doc" in sys.argv:
        ok = sum(1 for _, p, _ in results if p)
        lines = ["# 冒烟测试", "",
                 "> `python tools/smoke_test.py --doc` 生成。跑的是书里最容易被照抄的示例。",
                 "> 环境：本机 Python，" + sys.version.split()[0] + "；**没有 GPU / 没有 Docker / 没有 Spark**，",
                 "> 所以 vLLM、CUDA、Spark、Docker 的示例**没有**被真跑验证。", "",
                 "| 用例 | 结果 | 说明 |", "|---|---|---|"]
        for name, p, d in results:
            lines.append("| %s | %s | %s |" % (name, "通过" if p else "失败/跳过", d))
        lines += ["", "合计：**%d/%d 通过**。" % (ok, len(results))]
        DOC.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("已写 %s" % DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())