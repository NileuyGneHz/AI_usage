"""W6 · trace：每一步都落一行盘。

为什么值得单独一个文件：
    出问题的时候你需要的是**回放**，不是重跑。重跑会遇到"这次又是另一个错"，
    而 trace 里那一行还在原地等你。
    W7 的轨迹断言（该调的调了没有、有没有多余步骤）直接读这些文件。

字段是刻意设计过的 —— `step / tool / args / result_digest / tokens / latency_ms`
就是 W7 断言要用到的全部信息。现在多写一个字段，W7 就少改一次代码。
"""

from __future__ import annotations

import json
import pathlib
import time


def digest(obj, limit: int = 240) -> str:
    """把工具返回值压成一行摘要。trace 里不存全文，否则文件会爆炸（W3 的教训）。"""
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    text = " ".join(text.split())
    return text[:limit] + ("…" if len(text) > limit else "")


class Trace:
    def __init__(self, path: pathlib.Path | str, run_id: str | None = None):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
        self.rows: list[dict] = []
        self.fh = self.path.open("a", encoding="utf-8")

    def add(self, **kw) -> dict:
        row = {"run_id": self.run_id, "ts": round(time.time(), 3), **kw}
        self.rows.append(row)
        self.fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.fh.flush()
        return row

    def close(self) -> None:
        self.fh.close()

    def summary(self) -> dict:
        tools = [r.get("tool") for r in self.rows if r.get("event") == "tool_call"]
        return {
            "run_id": self.run_id,
            "steps": sum(1 for r in self.rows if r.get("event") == "llm"),
            "tool_calls": tools,
            "tokens": sum(int(r.get("tokens") or 0) for r in self.rows),
            "latency_ms": sum(int(r.get("latency_ms") or 0) for r in self.rows),
        }


def load(path: pathlib.Path | str) -> list[dict]:
    """读回一份 trace（W7 用）。"""
    return [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
