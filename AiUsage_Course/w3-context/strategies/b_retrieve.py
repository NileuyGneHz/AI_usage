"""策略 B · 关键词检索 top-k。

做法：用 shared/corpus.search() 取 k 个小节，带上 `文件:行号` 定位，拼进上下文。
这是最便宜、也最容易被高估的一招：它能省 90% 的 token，也能漏掉 30% 的答案。

用法：由 run_compare.py 调用。
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from shared import corpus  # noqa: E402

NAME = "B 关键词检索"

SYSTEM = (
    "你是一名机器学习课程的助教。只依据用户提供的材料回答问题。"
    "材料里没有的内容，直接说「材料未覆盖」，不要补充外部知识。"
    "回答末尾另起一行写「来源：<文件名>:<行号>」。"
)

# TODO(你): 这里留了三个旋钮，README 的实验 2 会让你逐个扫。
# 默认 0 = 整节全文。这才是「检索」的本来面目：只挑哪些节，不裁剪节内内容。
# 改成 600 就变成「检索 + 片段裁剪」，B 和 C 的差距会立刻缩水 —— 这个对比值得亲手做一次。
SNIPPET_CHARS = 0     # 每个小节最多给多少字（0 = 给全文）
MAX_SECTIONS = 3      # 相当于 top-k


def build(question: str, *, scope: str = "subset", k: int = MAX_SECTIONS, budget: int = 60_000) -> dict:
    files = corpus.scope_files(scope) or sorted(p.name for p in corpus.notes_dir().glob("*.md"))
    allowed = set(files)

    hits = [(s, score) for s, score in corpus.search(question, k=k * 3) if s.file in allowed][:k]

    if not hits:
        material = "（没有检索到相关材料）"
        used: list[dict] = []
    else:
        blocks = []
        used = []
        for sec, score in hits:
            text = sec.text if SNIPPET_CHARS == 0 else corpus.snippet(sec, question, radius=SNIPPET_CHARS // 2)
            blocks.append(f"[{sec.cite()}] {sec.heading}\n{text}")
            used.append({"file": sec.file, "id": sec.id, "heading": sec.heading,
                         "score": score, "chars": len(text)})
        material = "\n\n".join(blocks)

    est = corpus.est_tokens(material)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"材料：\n\n{material}\n\n问题：{question}"},
        ],
        "meta": {
            "strategy": NAME,
            "sections": used,
            "chars": len(material),
            "est_tokens": est,
            "over_budget": est > budget,
            "note": f"k={k}，整节全文" if SNIPPET_CHARS == 0 else f"k={k}，每段 ≤{SNIPPET_CHARS} 字",
        },
    }
