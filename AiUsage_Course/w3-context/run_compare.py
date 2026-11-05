#!/usr/bin/env python3
"""W3 脚手架：三套上下文策略 × 5 个固定问题 → 一张 token / 延迟 / 得分 的表。

分工：
    管道（取语料、拼上下文、发请求、记账、出表）—— 本文件
    判断（k 取多少、压缩到多少字、哪套更划算）—— 你

    python3 run_compare.py --dry-run                 # 零成本：只算三套的 token 账
    python3 run_compare.py --scope subset            # 5 章语料跑三套
    python3 run_compare.py --scope all --force       # 全量（A 很可能超预算）
    python3 run_compare.py --k 5                     # B/C 的 top-k
    python3 run_compare.py --repeat 3                # 每问每策略跑 3 次

得分不在这里出：人工判分表在 questions.md 里，跑完自己填。
"""

from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from shared import corpus                                    # noqa: E402
from shared.llm import Config, chat                          # noqa: E402

STRATEGIES = {"a": "strategies.a_full", "b": "strategies.b_retrieve", "c": "strategies.c_compress"}


def load_questions(path: pathlib.Path) -> list[str]:
    """从 questions.md 的「## 固定问题」段里抓 `1. xxx` 这样的行。"""
    text = path.read_text(encoding="utf-8")
    body = text.split("## 固定问题", 1)[-1]
    qs = []
    for line in body.splitlines():
        m = re.match(r"^\s*\d+\.\s+(.*\S)\s*$", line)
        if m:
            qs.append(m.group(1))
    return qs


def main() -> int:
    ap = argparse.ArgumentParser(description="W3：三策略对比")
    ap.add_argument("--strategies", default="a,b,c", help="要跑哪几套，例如 a,c")
    ap.add_argument("--scope", default="subset", choices=["subset", "all"])
    ap.add_argument("--k", type=int, default=3, help="B/C 的 top-k")
    ap.add_argument("--budget", type=int, default=60_000, help="单次请求的估算 token 上限")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--questions", default=str(HERE / "questions.md"))
    ap.add_argument("--dry-run", action="store_true", help="只算 token 账，不发请求")
    ap.add_argument("--force", action="store_true", help="即使超预算也发")
    args = ap.parse_args()

    wanted = [s.strip().lower() for s in args.strategies.split(",") if s.strip()]
    mods = {s: importlib.import_module(STRATEGIES[s]) for s in wanted if s in STRATEGIES}

    questions = load_questions(pathlib.Path(args.questions))
    if not questions:
        print("没有从 questions.md 解析出问题。检查「## 固定问题」段是不是被改了。")
        return 2

    n_files = len(corpus.scope_files(args.scope) or list(corpus.notes_dir().glob("*.md")))
    print(f"语料 : {corpus.notes_dir()}  ({args.scope} = {n_files} 个文件)")
    print(f"问题 : {len(questions)} 条   策略: {', '.join(m.NAME for m in mods.values())}")

    # ---- 第一遍：只拼上下文，算账（不花钱） ----
    plans = []
    for key, mod in mods.items():
        for qi, q in enumerate(questions, 1):
            p = mod.build(q, scope=args.scope, k=args.k, budget=args.budget)
            plans.append({"key": key, "q": qi, "question": q, **p})

    print("\n=== 估算账（不花钱） ===")
    print(f"{'策略':<14}{'题':<4}{'材料字数':>10}{'估算token':>12}{'预算':>8}  备注")
    for p in plans:
        m = p["meta"]
        flag = "超预算" if m["over_budget"] else "ok"
        print(f"{m['strategy']:<14}Q{p['q']:<3}{m['chars']:>10,}{m['est_tokens']:>12,}{flag:>8}  {m['note']}")

    if args.dry_run:
        print("\n干跑结束。这一步已经把「A 到底装不装得下」回答了一半。")
        return 0

    cfg = Config.from_env()
    print(f"\n模型 : {cfg.describe()}")

    rows = []
    run_id = time.strftime("%Y%m%d-%H%M%S")
    for p in plans:
        m = p["meta"]
        if m["over_budget"] and not args.force:
            rows.append({"run_id": run_id, "strategy": m["strategy"], "q": p["q"],
                         "question": p["question"], "status": "over_budget", "meta": m,
                         "answer": "", "usage": {}, "latency_ms": 0})
            print(f"  {m['strategy']:<14}Q{p['q']}  跳过（估算 {m['est_tokens']:,} > 预算 {args.budget:,}）")
            continue
        for rep in range(args.repeat):
            r = chat(p["messages"], cfg=cfg, temperature=args.temperature)
            rows.append({
                "run_id": run_id, "strategy": m["strategy"], "q": p["q"],
                "question": p["question"], "status": "ok" if r["ok"] else "failed",
                "meta": m, "answer": r["text"], "usage": r["usage"],
                "latency_ms": r["latency_ms"], "error": r["error"], "rep": rep,
            })
            u = r["usage"]
            print(f"  {m['strategy']:<14}Q{p['q']} r{rep}  in={u.get('prompt_tokens')}"
                  f"  out={u.get('completion_tokens')}  {r['latency_ms']}ms")

    runs = HERE / "runs"
    runs.mkdir(exist_ok=True)
    out = runs / f"{run_id}.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")

    print("\n=== 实测账（按策略汇总） ===")
    print(f"{'策略':<14}{'次数':>6}{'平均input':>11}{'平均output':>12}{'平均延迟':>10}")
    for name in {r["strategy"] for r in rows}:
        sub = [r for r in rows if r["strategy"] == name and r["status"] == "ok"]
        if not sub:
            print(f"{name:<14}{0:>6}{'-':>11}{'-':>12}{'-':>10}   （全部跳过/失败）")
            continue
        ai = sum(r["usage"].get("prompt_tokens", 0) for r in sub) // len(sub)
        ao = sum(r["usage"].get("completion_tokens", 0) for r in sub) // len(sub)
        al = sum(r["latency_ms"] for r in sub) // len(sub)
        print(f"{name:<14}{len(sub):>6}{ai:>11,}{ao:>12,}{al:>10}ms")

    print(f"\n明细 : {out}")
    print("下一步：把 5 个问题的人工得分填进 questions.md 的表格，再填 report.template.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
