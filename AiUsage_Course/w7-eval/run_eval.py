#!/usr/bin/env python3
"""W7 脚手架：三层断言 + trace 回放 + 对比报告。

它做三件事：
    1. 读 evalset.jsonl（20 条），逐条跑 W6 的 agent，拿回答案与 trace
    2. 三层断言：结果断言 / 轨迹断言 / 负例断言，分开记分（混在一起就没法定位）
    3. 出一份能贴进报告的 markdown，并按失败类型分类

    python3 run_eval.py --dry-run                 # 只校验 evalset，不花钱
    python3 run_eval.py --run --label baseline     # 真跑（要用 W6 的 agent）
    python3 run_eval.py --replay trace_dir         # 只回放已有 trace，验轨迹层

对比就用 label：
    python3 run_eval.py --run --label baseline
    # ... 改 description ...
    python3 run_eval.py --run --label after_desc
    # 两份 report_*.md 并排看

依赖 W6 的代码（import 进来的）。如果你改了 W6 `agent.py` 的函数签名，
这里也要跟着改 —— 这是"自己写的东西要自己维护"的第一课。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "w6-agent-loop" / "src"))

DEFAULT_REFUSE_WORDS = ["没有", "不能", "无法", "未覆盖", "只读", "不存在", "超出"]


# ---------------------------------------------------------------- evalset
def load_evalset(path: pathlib.Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"evalset 第 {i} 行不是合法 JSON: {e}")
    return rows


def validate_evalset(rows: list[dict]) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    seen = set()
    for r in rows:
        rid = r.get("id")
        if not rid:
            problems.append("有条目缺 id")
        elif rid in seen:
            problems.append(f"id 重复: {rid}")
        seen.add(rid)
        if not r.get("input"):
            problems.append(f"{rid}: 缺 input")
        if not isinstance(r.get("expect_result"), dict):
            problems.append(f"{rid}: 缺 expect_result")
        if not isinstance(r.get("expect_trace"), dict):
            problems.append(f"{rid}: 缺 expect_trace")
        if r.get("type") not in ("positive", "negative", "edge"):
            problems.append(f"{rid}: type 应为 positive/negative/edge")
        if r.get("type") == "positive" and not (r.get("expect_result") or {}).get("must_include"):
            warnings.append(f"{rid}: must_include 为空 → 结果断言恒真（假绿），请补 2–4 个关键事实")
    return problems, warnings


# ---------------------------------------------------------------- 三层断言
def assert_result(case: dict, answer: str) -> tuple[bool, str]:
    must = (case.get("expect_result") or {}).get("must_include") or []
    missing = [m for m in must if m not in answer]
    if missing:
        return False, f"答案缺关键事实 {missing}"
    if case.get("type") == "negative":
        words = case.get("refuse_keywords") or DEFAULT_REFUSE_WORDS
        if not any(w in answer for w in words):
            return False, f"负例未拒绝（未见 {words[:3]}… 任一）"
    return True, ""


def assert_trace(case: dict, rows: list[dict]) -> tuple[bool, str]:
    exp = case.get("expect_trace") or {}
    calls = [r.get("tool") for r in rows if r.get("event") == "tool_call"]
    steps = sum(1 for r in rows if r.get("event") == "llm")

    must_call = exp.get("must_call") or []
    missing = [t for t in must_call if t not in calls]
    if missing:
        return False, f"漏调 {missing}（实际调用 {calls}）"

    must_not = exp.get("must_not_call") or []
    if "*" in must_not and calls:
        return False, f"不该调任何工具，实际调用 {calls}"
    bad = [t for t in must_not if t != "*" and t in calls]
    if bad:
        return False, f"多调 {bad}（实际调用 {calls}）"

    max_steps = exp.get("max_steps")
    if max_steps and steps > max_steps:
        return False, f"步数 {steps} > 上限 {max_steps}"
    return True, ""


def assert_negative(case: dict, answer: str, rows: list[dict]) -> tuple[bool, str]:
    """负例单独一层：拒绝 + 没有破坏性调用。它和结果断言重叠，但修法不同。"""
    if case.get("type") != "negative":
        return True, ""
    calls = [r.get("tool") for r in rows if r.get("event") == "tool_call"]
    if calls:
        return False, f"负例里调用了 {calls}"
    words = case.get("refuse_keywords") or DEFAULT_REFUSE_WORDS
    if not any(w in answer for w in words):
        return False, "负例没明说拒绝"
    return True, ""


# ---------------------------------------------------------------- 执行
def run_one(case: dict, model) -> dict:
    from agent import run as agent_run   # W6 的实现

    t0 = time.time()
    trace_path = HERE / "runs" / f"_tmp_{case['id']}_{int(t0)}.jsonl"
    out = agent_run(case["input"], model, trace_path=trace_path, verbose=False)
    rows = [json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    elapsed = int((time.time() - t0) * 1000)

    answer = out.get("answer") or ""
    ok_r, msg_r = assert_result(case, answer)
    ok_t, msg_t = assert_trace(case, rows)
    ok_n, msg_n = assert_negative(case, answer, rows)

    return {
        "id": case["id"], "type": case.get("type"), "input": case["input"],
        "answer": answer, "rows": rows,
        "result_ok": ok_r, "result_msg": msg_r,
        "trace_ok": ok_t, "trace_msg": msg_t,
        "neg_ok": ok_n, "neg_msg": msg_n,
        "tokens": out.get("tokens", 0), "steps": out.get("steps", 0),
        "reason": out.get("reason"), "latency_ms": elapsed, "trace_path": str(trace_path),
    }


def replay_one(case: dict, trace_dir: pathlib.Path) -> dict | None:
    matches = sorted(trace_dir.glob(f"{case['id']}*.jsonl"))
    if not matches:
        return None
    rows = [json.loads(x) for x in matches[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    ok_t, msg_t = assert_trace(case, rows)
    return {
        "id": case["id"], "type": case.get("type"), "input": case["input"], "answer": "(replay)",
        "result_ok": None, "result_msg": "回放模式不判结果层",
        "trace_ok": ok_t, "trace_msg": msg_t,
        "neg_ok": None, "neg_msg": "回放模式不判负例层",
        "tokens": sum(int(r.get("tokens") or 0) for r in rows),
        "steps": sum(1 for r in rows if r.get("event") == "llm"),
        "reason": "replay", "latency_ms": 0, "trace_path": str(matches[-1]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="W7 评测：三层断言 + 对比报告")
    ap.add_argument("--evalset", default=str(HERE / "evalset.jsonl"))
    ap.add_argument("--run", action="store_true", help="跑 W6 的 agent（会花钱）")
    ap.add_argument("--replay", metavar="DIR", help="只回放已有 trace（只验轨迹层）")
    ap.add_argument("--label", default="baseline", help="这次配置的名字，用于报告文件名")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    es_path = pathlib.Path(args.evalset)
    if not es_path.exists():
        print(f"找不到 {es_path}。先用 seed_evalset.py 生成一个起点。")
        return 2

    cases = load_evalset(es_path)
    if args.limit:
        cases = cases[: args.limit]

    problems, warnings = validate_evalset(cases)
    print(f"evalset : {es_path.name}  {len(cases)} 条")
    print(f"分布    : positive={sum(1 for c in cases if c.get('type') == 'positive')}"
          f"  negative={sum(1 for c in cases if c.get('type') == 'negative')}"
          f"  edge={sum(1 for c in cases if c.get('type') == 'edge')}")
    if warnings:
        print(f"\n警告 {len(warnings)} 条（不阻断，但会让报告偏乐观）：")
        for w in warnings[:5]:
            print("  -", w)
        if len(warnings) > 5:
            print(f"  … 还有 {len(warnings) - 5} 条")
    if problems:
        print("\n格式问题：")
        for p in problems:
            print("  -", p)
        if args.dry_run:
            return 1
    if args.dry_run:
        print("\n校验完毕（未调用模型）。")
        return 0

    results: list[dict] = []
    if args.replay:
        d = pathlib.Path(args.replay)
        for c in cases:
            r = replay_one(c, d)
            if r is None:
                print(f"  {c['id']}: 没找到 trace，跳过")
                continue
            results.append(r)
            print(f"  {c['id']:<5} 轨迹 {'✓' if r['trace_ok'] else '✗'} {r['trace_msg']}")
    else:
        from llm_client import RealModel
        model = RealModel()
        print(f"模型    : {model.describe()}\n")
        for c in cases:
            r = run_one(c, model)
            results.append(r)
            flags = "".join([
                "R" if r["result_ok"] else "r",
                "T" if r["trace_ok"] else "t",
                "N" if r["neg_ok"] else "n",
            ])
            print(f"  {c['id']:<5} [{flags}] {r['steps']}步 {r['tokens']}tok"
                  f"  {r['result_msg'] or r['trace_msg'] or r['neg_msg'] or 'ok'}")

    report = build_report(results, args.label)
    out = HERE / f"report_{args.label}.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n报告 : {out}")
    print(report.split("## 失败分类")[0])
    return 0


def build_report(results: list[dict], label: str) -> str:
    def cnt(key: str) -> tuple[int, int]:
        vals = [r[key] for r in results if r[key] is not None]
        return sum(1 for v in vals if v), len(vals)

    r_ok, r_n = cnt("result_ok")
    t_ok, t_n = cnt("trace_ok")
    n_ok, n_n = cnt("neg_ok")
    total_ok = sum(1 for r in results if all(x is not None and x for x in
                                             [r["result_ok"], r["trace_ok"], r["neg_ok"]]))
    toks = [r["tokens"] for r in results if r["tokens"]]
    steps = [r["steps"] for r in results if r["steps"]]

    lines = [
        f"# W7 · 评测报告 · {label}",
        "",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 用例：{len(results)} 条",
        f"- 结果断言：{r_ok}/{r_n}　轨迹断言：{t_ok}/{t_n}　负例断言：{n_ok}/{n_n}",
        f"- 全绿：{total_ok}/{len(results)}",
        f"- 平均 token：{int(statistics.mean(toks)) if toks else 0}　"
        f"平均步数：{round(statistics.mean(steps), 1) if steps else 0}",
        "",
        "| id | 类型 | 结果 | 轨迹 | 负例 | 步数 | token | 失败原因 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        mark = lambda v: "—" if v is None else ("✓" if v else "✗")  # noqa: E731
        why = r["result_msg"] or r["trace_msg"] or r["neg_msg"] or ""
        lines.append(f"| {r['id']} | {r['type']} | {mark(r['result_ok'])} | {mark(r['trace_ok'])} "
                     f"| {mark(r['neg_ok'])} | {r['steps']} | {r['tokens']} | {why[:60]} |")

    lines += ["", "## 失败分类", "",
              "| 类型 | 条数 | id | 修法在哪一层 |", "|---|---|---|---|",
              f"| 结果错（事实缺失/编造） | {r_n - r_ok} | "
              f"{[r['id'] for r in results if r['result_ok'] is False]} | 检索 / 裁剪 / prompt |",
              f"| 轨迹错（漏调/多调/超步） | {t_n - t_ok} | "
              f"{[r['id'] for r in results if r['trace_ok'] is False]} | description / schema |",
              f"| 负例失守 | {n_n - n_ok} | "
              f"{[r['id'] for r in results if r['neg_ok'] is False]} | 工具权限 / 拒绝话术 |",
              "",
              "## 结论（用计划里那个句式填）",
              "",
              "> 换 ___ 后通过率从 __/__ 变成 __/__，掉的是「____」那几条，"
              "成本变化 __%，我选择 ____，因为 ____。",
              ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
