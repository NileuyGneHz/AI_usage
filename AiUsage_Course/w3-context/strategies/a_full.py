"""策略 A · 全文塞入（基线，也是最贵的那个）。

做法：把选定范围内的所有 md 原文拼进 user 消息，不加检索、不裁剪。
它存在的意义是**给另外两套策略一个参照系**——没有 A 的账单，B/C 的"省了 80%"
是一句没有分母的话。

用法：由 run_compare.py 调用；也可以单独 import 试。
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from shared import corpus  # noqa: E402

NAME = "A 全文塞入"

SYSTEM = (
    "你是一名机器学习课程的助教。只依据用户提供的材料回答问题。"
    "材料里没有的内容，直接说「材料未覆盖」，不要补充外部知识。"
    "回答末尾另起一行写「来源：<文件名>:<行号>」。"
)


def build(question: str, *, scope: str = "subset", k: int = 3, budget: int = 60_000) -> dict:
    files = corpus.scope_files(scope) or sorted(p.name for p in corpus.notes_dir().glob("*.md"))
    parts, used = [], []
    for name in files:
        text = corpus.read_file(name)
        parts.append(f"===== {name} =====\n{text}")
        used.append({"file": name, "chars": len(text)})

    material = "\n\n".join(parts)
    est = corpus.est_tokens(material)

    # TODO(你): 超预算时怎么办？
    #   现在：仍然拼出 messages，但 meta 里标 over_budget，由 run_compare 决定发不发。
    #   另一条路是截断到 budget，但"截哪一段"本身就是一次策略选择，想清楚再改。
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"材料：\n\n{material}\n\n问题：{question}"},
        ],
        "meta": {
            "strategy": NAME,
            "files": used,
            "chars": len(material),
            "est_tokens": est,
            "over_budget": est > budget,
            "note": f"{len(used)} 个文件全文",
        },
    }
