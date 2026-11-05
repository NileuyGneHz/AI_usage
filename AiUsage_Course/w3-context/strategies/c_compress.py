"""策略 C · 检索 + 压缩。

做法：先检索，再把每节压成「与问题最相关的几句」，最后拼起来。
它想证明的一件事：**压缩省下的 token，值不值得丢掉的那些句子。**

压缩方式有两类，本周只用第一类：

1. **抽取式**（当前实现）：按查询词给句子打分，保留 top 句。便宜、可控、不花钱。
2. **生成式**（TODO）：让模型先写摘要，再拿摘要回答问题。多一次调用，可能丢细节。

用法：由 run_compare.py 调用。
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from shared import corpus  # noqa: E402

NAME = "C 检索+压缩"

SYSTEM = (
    "你是一名机器学习课程的助教。只依据用户提供的材料回答问题。"
    "材料里没有的内容，直接说「材料未覆盖」，不要补充外部知识。"
    "回答末尾另起一行写「来源：<文件名>:<行号>」。"
)

K = 3
MAX_CHARS = 900  # 压缩后总预算
SENT_SPLIT = re.compile(r"(?<=[。！？!?\n])")


def _score_sentence(sent: str, qterms: set[str]) -> float:
    hits = sum(1 for t in corpus.terms(sent) if t in qterms)
    return hits / (len(sent) ** 0.5 + 1)


def compress(sec: corpus.Section, question: str, max_chars: int) -> tuple[str, int]:
    """抽取式压缩：保留与问题最相关的句子，按原文顺序拼回。"""
    qterms = set(corpus.terms(question))
    sents = [s.strip() for s in SENT_SPLIT.split(sec.text) if len(s.strip()) > 12]
    if not sents:
        return sec.text[:max_chars], len(sents)

    ranked = sorted(range(len(sents)), key=lambda i: _score_sentence(sents[i], qterms), reverse=True)
    keep: list[int] = []
    total = 0
    for i in ranked:
        if total >= max_chars:
            break
        keep.append(i)
        total += len(sents[i])
    keep.sort()

    out = "\n".join(sents[i] for i in keep)
    if len(out) > max_chars * 1.4:          # 高相关短句太多时兜底
        out = out[:max_chars]
    return out, len(keep)


def build(question: str, *, scope: str = "subset", k: int = K, budget: int = 60_000) -> dict:
    files = corpus.scope_files(scope) or sorted(p.name for p in corpus.notes_dir().glob("*.md"))
    allowed = set(files)
    hits = [(s, sc) for s, sc in corpus.search(question, k=k * 3) if s.file in allowed][:k]

    per_section = max(200, MAX_CHARS // max(1, len(hits)))
    blocks, used = [], []
    for sec, score in hits:
        text, kept = compress(sec, question, per_section)
        blocks.append(f"[{sec.cite()}] {sec.heading}\n{text}")
        used.append({"file": sec.file, "id": sec.id, "heading": sec.heading,
                     "score": score, "chars_in": sec.chars, "chars_out": len(text), "sentences": kept})

    material = "\n\n".join(blocks) if blocks else "（没有检索到相关材料）"
    est = corpus.est_tokens(material)

    # TODO(你): 生成式摘要版。
    #   在 build() 里先调一次 chat() 让它把每节压成 3 句，再拼给正式回答。
    #   然后记账时把两次调用的 token 都算进 C 的成本 —— 否则你会高估 C 的性价比。
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
            "note": f"k={k}，压缩到 ≤{MAX_CHARS} 字",
        },
    }
