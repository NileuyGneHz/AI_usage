#!/usr/bin/env python3
"""W3 实验：前缀缓存的账，亲手记一次。

它做一件很笨的事：同一段**长前缀**连发两次，第二次把 usage 里的缓存字段打出来。
然后往 system 里塞一个时间戳，再发两次，看那些字段掉不掉。

    python3 cache_probe.py                 # 稳定前缀：第 2 次应该便宜
    python3 cache_probe.py --timestamp     # 前缀里塞时间戳：第 2 次白搭
    python3 cache_probe.py --prefix-chars 4000

不同服务商字段名不一样（DeepSeek 是 prompt_cache_hit_tokens / prompt_cache_miss_tokens，
OpenAI 是 prompt_tokens_details.cached_tokens）。这里不猜字段，**把 usage 原样打出来**，
你自己认。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from shared import corpus          # noqa: E402
from shared.llm import Config, chat  # noqa: E402

RULES = (
    "你是课程助教。回答必须：1) 只用材料内容；2) 结论先行；3) 末尾标来源。"
    "以下是课程规范，请严格遵守，不要复述本段内容。"
)


def make_prefix(chars: int, timestamp: bool) -> str:
    """用真实语料拼一段长前缀。前缀越长，缓存收益越明显。"""
    text = corpus.read_file("week1.md")[:chars]
    head = RULES
    if timestamp:
        head += f"\n（本次会话时间：{time.strftime('%Y-%m-%d %H:%M:%S')}）"
    return f"{head}\n\n===== 材料 =====\n{text}"


def once(cfg: Config, prefix: str, question: str) -> dict:
    r = chat(
        [{"role": "system", "content": prefix}, {"role": "user", "content": question}],
        cfg=cfg,
    )
    return {"ok": r["ok"], "usage": r["usage"], "latency_ms": r["latency_ms"], "error": r["error"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix-chars", type=int, default=3000)
    ap.add_argument("--timestamp", action="store_true", help="在 system 前缀里塞时间戳")
    args = ap.parse_args()

    cfg = Config.from_env()
    print("模型 :", cfg.describe())
    prefix = make_prefix(args.prefix_chars, args.timestamp)
    print(f"前缀 : {len(prefix):,} 字 / 约 {corpus.est_tokens(prefix):,} token"
          f"  {'（含时间戳）' if args.timestamp else '（稳定）'}")

    rows = []
    for i in (1, 2):
        r = once(cfg, prefix, "用一句话概括这段材料在讲什么。")
        rows.append(r)
        print(f"\n第 {i} 次  {r['latency_ms']} ms  ok={r['ok']}")
        print("usage:", json.dumps(r["usage"], ensure_ascii=False))
        if not r["ok"]:
            print("error:", r["error"])
            if cfg.is_mock:
                print("提示: mock 不实现缓存，字段一定是空的 —— 这本身就是个结论。")
            return 1

    a, b = rows
    print("\n=== 对照 ===")
    print(f"延迟: {a['latency_ms']} ms → {b['latency_ms']} ms")
    print(f"usage: {json.dumps(a['usage'], ensure_ascii=False)}")
    print(f"   →   {json.dumps(b['usage'], ensure_ascii=False)}")
    print("\n要回答的三件事：")
    print("1. 第二次的哪个字段变小了（或没变）？")
    print("2. 加时间戳后，那个字段还在吗？")
    print("3. 你自己写 system 时，哪些内容该放前面、哪些必须挪到最后？")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
