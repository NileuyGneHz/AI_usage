#!/usr/bin/env python3
"""W6 · 主循环（骨架：能跑，但有一个**故意的**缺陷）

这一版做了什么：
    - 发起请求、拿 tool_calls、执行、把结果 append 回 messages、再发起
    - 记录 trace（每一步一行）
    - 有 max_steps 兜底

这一版**故意没做**什么（三个 TODO，就是本周的作业）：
    - TODO 1：token 预算。TOKEN_BUDGET 定义了，但循环里没人检查它。
    - TODO 2：工具结果裁剪。现在把整个返回塞回上下文，正是 W3 说的"第一成本杀手"。
    - TODO 3：状态外置。计划、已完成步骤全靠 messages 隐式携带，中断后无法恢复。

先跑一次 `--fixture loop_trap`，你会亲眼看到它烧完 12 步、预算超三倍，
而且**退出时只有一个 "max_steps"，说不清为什么停下**。这就是缺终止条件的真实后果。

    python3 src/agent.py --fixture fixtures/good_run.json
    python3 src/agent.py --fixture fixtures/loop_trap.json
    python3 src/agent.py --real --question "4.6 节的正规方程是什么？"

写完之后，`--real` 模式才对你有意义：那时你要做的是计划里那道验收题
（读一章 → 找 2 个公式 → 出 3 道题 → 自查 → 输出 markdown），以及"找第 99 章"的优雅失败。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from llm_client import RealModel, ScriptedModel   # noqa: E402
from tools import TOOLS, execute                  # noqa: E402
from trace import Trace, digest                   # noqa: E402

MAX_STEPS = 12
TOKEN_BUDGET = 20_000

SYSTEM = (
    "你是一个会用工具的课程助教。回答只能依据工具返回的材料，并在末尾标注 `文件:行号`。\n"
    "如果工具返回 error，读 hint 决定下一步，不要重复同样的调用。\n"
    "确认信息足够后，直接给出最终答案，不要再调用工具。"
)


def run(question: str, model, *, trace_path: pathlib.Path, verbose: bool = True) -> dict:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    trace = Trace(trace_path)
    spent = 0

    try:
        for step in range(1, MAX_STEPS + 1):
            r = model.complete(messages, TOOLS)
            if not r["ok"]:
                trace.add(event="error", step=step, detail=r["error"])
                return {"answer": None, "steps": step, "tokens": spent, "reason": "model_error",
                        "detail": r["error"]}

            spent += int((r["usage"] or {}).get("total_tokens") or 0)
            trace.add(event="llm", step=step, tokens=(r["usage"] or {}).get("total_tokens"),
                      latency_ms=r["latency_ms"], content_digest=digest(r["content"] or "", 120))
            if verbose:
                print(f"[step {step}] 模型返回：{len(r['tool_calls'])} 个 tool_call"
                      f"  累计 token={spent}")

            # 模型说完了 —— 终止条件之一
            if not r["tool_calls"]:
                return {"answer": r["content"], "steps": step, "tokens": spent, "reason": "model_done"}

            # 把 assistant 这一轮原样放回历史（tool_calls 必须带上，否则下一轮对不上 id）
            messages.append({
                "role": "assistant",
                "content": r["content"] or "",
                "tool_calls": r["tool_calls"],
            })

            for call in r["tool_calls"]:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {}
                result = execute(name, args)

                trace.add(event="tool_call", step=step, tool=name, args=args,
                          result_digest=digest(result), tokens=0)

                # TODO 2: 这里把整个 result 塞回去了。W3 说过这是第一成本杀手。
                #   改法提示：只回 digest + 定位（file/行号），让模型自己决定要不要再读。
                #   注意：改得太狠会让模型没法继续，这条线要自己试出来。
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
                if verbose:
                    print(f"           └ {name}({json.dumps(args, ensure_ascii=False)[:60]}) → "
                          f"{digest(result, 80)}")

            # TODO 1: 预算检查。现在这里什么都没有。
            #   if spent > TOKEN_BUDGET: return {... "reason": "budget_exceeded"}
            #   同时想清楚：预算和步数同时超了，哪个原因优先？退出原因要能区分。

            # TODO 3: 状态外置。现在 plan / done / facts 全在 messages 里。
            #   改法提示：维护一个 dict，每步更新，最后连同 trace 一起落盘。
    finally:
        summary = trace.summary()
        trace.close()

    # 走到这里 = 步数用尽。缺陷：没有更细的原因，也说不清"还差什么没做完"。
    return {"answer": None, "steps": MAX_STEPS, "tokens": spent, "reason": "max_steps",
            "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description="W6 agent 循环骨架")
    ap.add_argument("--fixture", default=str(HERE.parent / "fixtures" / "good_run.json"))
    ap.add_argument("--real", action="store_true", help="用真模型（默认用剧本回放）")
    ap.add_argument("--question", default="4.6 节的正规方程是什么？")
    ap.add_argument("--trace", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    model = RealModel() if args.real else ScriptedModel(pathlib.Path(args.fixture))
    trace_path = pathlib.Path(args.trace) if args.trace else (
        HERE.parent / "trace" / f"{time.strftime('%Y%m%d-%H%M%S')}.jsonl")

    print(f"模型 : {model.describe()}")
    print(f"问题 : {args.question}")
    print(f"预算 : max_steps={MAX_STEPS}  token_budget={TOKEN_BUDGET}\n")

    out = run(args.question, model, trace_path=trace_path, verbose=not args.quiet)

    print("\n=== 结果 ===")
    print(f"退出原因 : {out['reason']}")
    print(f"步数     : {out['steps']}")
    print(f"累计token: {out['tokens']}  ({'超预算 ' + str(out['tokens'] - TOKEN_BUDGET) if out['tokens'] > TOKEN_BUDGET else '在预算内'})")
    print(f"trace    : {trace_path}")
    if out.get("answer"):
        print("\n--- 答案 ---")
        print(out["answer"][:800])
    else:
        print("\n没有产出答案。看 trace 里最后几步在干什么。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
