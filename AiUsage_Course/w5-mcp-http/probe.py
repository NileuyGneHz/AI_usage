#!/usr/bin/env python3
"""W5 脚手架：不接宿主，直接问模型「这 10 个问题，你会调哪个工具？」

原理很简单，但很有用：把 W4 的 `tools/list` 结果翻成 OpenAI 的 tools 数组，
连同问题一起发给模型，看它选谁。**这比在 WorkBuddy 里点十次快得多，也更容易做 A/B。**

    # 基线（W4 跑完 raw_client.py --dump ../w5-mcp-http/tools.json 之后）
    python3 probe.py --tools tools.json

    # 改完 description 后，重新 dump 一份，对比
    python3 probe.py --tools tools_b.json --out report_b.md

    python3 probe.py --tools tools.json --repeat 3     # 看稳定性

它测不了的：真实宿主里的多轮、工具返回后的自我修正、上下文增量。
那些在 measure.template.md 里人工记。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from shared import corpus          # noqa: E402
from shared.llm import Config, chat  # noqa: E402

SYSTEM = "你可以使用工具，也可以不使用。只在确实需要时才调用，参数必须符合 schema。"


def load_questions(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## ") and rows:
            break          # 只读第一张表，后面还有「结果表」之类的模板表
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() == "id":
            continue
        if all(set(c) <= set("-: ") for c in cells if c):
            continue  # 分隔线
        rows.append({"id": cells[0], "question": cells[1], "expect": cells[2],
                     "note": cells[3] if len(cells) > 3 else ""})
    return rows


def to_openai_tools(tools: list[dict]) -> list[dict]:
    out = []
    for t in tools:
        schema = t.get("inputSchema") or {"type": "object", "properties": {}}
        schema.setdefault("type", "object")
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": (t.get("description") or "").strip(),
                "parameters": schema,
            },
        })
    return out


def check_args(call: dict, tools_by_name: dict[str, dict]) -> tuple[bool, str]:
    name = call["function"]["name"]
    raw = call["function"].get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as e:
        return False, f"arguments 不是合法 JSON: {e.msg}"
    schema = (tools_by_name.get(name, {}).get("inputSchema") or {})
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing:
        return False, f"缺必填参数 {missing}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="W5：description / schema 的 A/B 探针")
    ap.add_argument("--tools", default=str(HERE / "tools.json"), help="W4 的 tools/list 快照")
    ap.add_argument("--questions", default=str(HERE / "questions.md"))
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--out", default=None, help="把结果写成 markdown 报告")
    args = ap.parse_args()

    tools_path = pathlib.Path(args.tools)
    if not tools_path.exists():
        print(f"找不到 {tools_path}")
        print("先在 W4 跑： python3 ../w4-mcp-stdio/raw_client.py --dump ../w5-mcp-http/tools.json")
        return 2

    payload = json.loads(tools_path.read_text(encoding="utf-8"))
    tools = payload.get("tools", payload if isinstance(payload, list) else [])
    if not tools:
        print("tools 快照是空的。")
        return 2
    tools_by_name = {t["name"]: t for t in tools}
    oa_tools = to_openai_tools(tools)

    resident = corpus.est_tokens(json.dumps(oa_tools, ensure_ascii=False))
    print(f"工具   : {', '.join(tools_by_name)}")
    print(f"常驻成本: 约 {resident} token —— 这段定义每次请求都在 system 里，改长一点都要付钱")

    questions = load_questions(pathlib.Path(args.questions))
    if not questions:
        print("没解析出问题。检查 questions.md 的表格格式。")
        return 2

    cfg = Config.from_env()
    print(f"模型   : {cfg.describe()}")
    print(f"问题   : {len(questions)} 条 × {args.repeat} 次\n")

    rows = []
    run_id = time.strftime("%Y%m%d-%H%M%S")
    for q in questions:
        for rep in range(args.repeat):
            r = chat(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q["question"]}],
                cfg=cfg, temperature=args.temperature, tools=oa_tools, tool_choice="auto",
            )
            if not r["ok"]:
                rows.append({**q, "actual": "ERROR", "correct": False, "args_ok": False,
                             "detail": r["error"], "rep": rep, "usage": {}, "latency_ms": r["latency_ms"]})
                print(f"  {q['id']:<4} 请求失败: {r['error']}")
                continue

            calls = r["tool_calls"]
            if calls:
                actual = calls[0]["function"]["name"]
                args_ok, detail = check_args(calls[0], tools_by_name)
                shown = calls[0]["function"].get("arguments") or "{}"
            else:
                actual, args_ok, detail, shown = "none", True, "", ""

            correct = actual == q["expect"]
            rows.append({**q, "actual": actual, "correct": correct, "args_ok": args_ok,
                         "detail": detail, "args": shown, "rep": rep,
                         "usage": r["usage"], "latency_ms": r["latency_ms"]})

            mark = "✓" if correct else "✗"
            print(f"  {q['id']:<4} {mark}  期望 {q['expect']:<13} 实际 {actual:<13}"
                  f"{'' if args_ok else '参数不合法: ' + detail}")

    # ---- 汇总 ----
    n = len(rows)
    correct = sum(1 for x in rows if x["correct"])
    arg_ok = sum(1 for x in rows if x["args_ok"])
    fp = [x for x in rows if x["expect"] == "none" and x["actual"] != "none"]
    fn = [x for x in rows if x["expect"] != "none" and x["actual"] == "none"]
    wrong_tool = [x for x in rows if x["expect"] not in ("none", x["actual"]) and x["actual"] != "none"]

    print("\n=== 汇总 ===")
    print(f"选择正确 : {correct}/{n}")
    print(f"参数合法 : {arg_ok}/{n}")
    print(f"误调(本该 none) : {len(fp)}  {[x['id'] for x in fp]}")
    print(f"漏调(本该调却 none) : {len(fn)}  {[x['id'] for x in fn]}")
    print(f"调错工具 : {len(wrong_tool)}  {[x['id'] for x in wrong_tool]}")
    print(f"常驻定义 : ~{resident} token")

    runs = HERE / "runs"
    runs.mkdir(exist_ok=True)
    out = runs / f"{run_id}.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows), encoding="utf-8")
    print(f"明细     : {out}")

    if args.out:
        pathlib.Path(args.out).write_text(build_report(rows, tools_path.name, resident), encoding="utf-8")
        print(f"报告     : {args.out}")

    print("\n下一步：只改一处（description 或 schema），重新 dump、再跑一遍，对比两张表。")
    return 0 if correct == n else 1


def build_report(rows: list[dict], tools_name: str, resident: int) -> str:
    lines = [
        "# W5 · 工具选择探针结果",
        "",
        f"- tools 快照：`{tools_name}`",
        f"- 工具定义常驻成本：约 {resident} token",
        f"- 用例：{len(rows)} 条",
        "",
        "| id | 期望 | 实际 | 选择 | 参数 | 备注 |",
        "|---|---|---|---|---|---|",
    ]
    for x in rows:
        lines.append(
            f"| {x['id']} | {x['expect']} | {x['actual']} | {'✓' if x['correct'] else '✗'} "
            f"| {'✓' if x['args_ok'] else '✗'} | {(x.get('detail') or x.get('note') or '')[:40]} |"
        )
    ok = sum(1 for x in rows if x["correct"])
    lines += ["", f"**选择正确 {ok}/{len(rows)}**", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
