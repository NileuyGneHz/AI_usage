#!/usr/bin/env python3
"""W2 脚手架：三版 prompt × 10 个固定输入 → 一张能说话的对比表。

它负责的是**管道**：取语料、渲染模板、发请求、按同一把尺子判分、算账、出报告。
它不负责**判断**：v3 长什么样、哪条负例该加、数据说明什么 —— 那些是你的活。

    python3 run.py --dry-run               # 零成本：只渲染 + 估 token，不联网
    python3 run.py --only v1               # 只跑一版（有真 key 时先这样试水）
    python3 run.py --limit 3               # 只跑前 3 个 case
    python3 run.py --repeat 3              # 每个 case 跑 3 次，看稳定性
    python3 run.py --out report.md         # 出报告（默认也是 report.md）

环境（默认指向 w1 的 mock_server.py）：
    LLM_BASE_URL / LLM_API_KEY / LLM_MODEL   —— 见 ../../shared/llm.py

判分标准对三版完全一样（同一份 cards.schema.json），这正是"控制变量"：
v3 的差别只在"请求里是否带 schema"和"正文里的负例"，不在判分器。
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
from schema_check import validate   # noqa: E402

VERSIONS = ("v1", "v2", "v3")
STATUS_LABEL = {
    "ok": "合规",
    "insufficient": "拒答(合规)",
    "bad_json": "JSON 不合法",
    "bad_schema": "结构不符",
    "request_failed": "请求失败",
}


def load_schema() -> dict:
    return json.loads((HERE / "schema" / "cards.schema.json").read_text(encoding="utf-8"))


def load_cases(path: pathlib.Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def render(tpl: str, heading: str, content: str) -> str:
    """不用 str.format：讲义里的数学公式含 `{}`，format 会炸。"""
    return tpl.replace("{heading}", heading).replace("{content}", content)


def strip_fences(text: str) -> str:
    """v1 最典型的死法：```json ... ```。这里只做最小清理，并在报告里记一笔。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def classify(text: str, schema: dict) -> tuple[str, dict | None, list[str]]:
    """把一次输出归到四类之一。三版共用，保证尺子一致。"""
    cleaned = strip_fences(text)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return "bad_json", None, [f"json.loads 失败: {e.msg} (pos {e.pos})"]
    errs = validate(obj, schema)
    if errs:
        return "bad_schema", obj, errs
    if isinstance(obj, dict) and obj.get("error") == "insufficient":
        return "insufficient", obj, []
    return "ok", obj, []


def format_for(cfg_mode: str, schema: dict) -> dict | None:
    if cfg_mode == "none":
        return None
    if cfg_mode == "json_object":
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {"name": "review_cards", "strict": True, "schema": schema},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="W2：三版 prompt 对比 runner")
    ap.add_argument("--cases", default=str(HERE / "cases.jsonl"))
    ap.add_argument("--only", choices=VERSIONS, help="只跑某一版")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个 case")
    ap.add_argument("--repeat", type=int, default=1, help="每个 case 重复次数（评测建议 3）")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--format", default="auto", choices=["auto", "json_schema", "json_object", "none"],
                    help="structured output 模式。auto = 先 json_schema，400 时降级 json_object")
    ap.add_argument("--out", default=str(HERE / "report.md"))
    ap.add_argument("--dry-run", action="store_true", help="只渲染与估算，不联网")
    args = ap.parse_args()

    schema = load_schema()
    cases = load_cases(pathlib.Path(args.cases))
    if args.limit:
        cases = cases[: args.limit]
    versions = [args.only] if args.only else list(VERSIONS)

    templates: dict[str, str] = {}
    for v in versions:
        p = HERE / "prompts" / f"{v}.txt"
        if not p.exists():
            print(f"[缺少] {p}")
            if v == "v3":
                print("        cp prompts/v3.template.txt prompts/v3.txt  # 然后填完 5 处「待填」")
            return 2
        templates[v] = p.read_text(encoding="utf-8")

    cfg = Config.from_env()
    print(f"模型   : {cfg.describe()}")
    print(f"用例   : {len(cases)} 条 × {args.repeat} 次 × {len(versions)} 版")
    print(f"温度   : {args.temperature}")

    if args.dry_run:
        print("\n=== dry-run：只看第一例渲染结果，不发请求 ===")
        c = cases[0]
        sec = corpus.get(c["id"], c["file"])
        if not sec:
            print(f"语料里找不到 {c['file']} #{c['id']}")
            return 2
        for v in versions:
            prompt = render(templates[v], c["heading"], sec.text)
            print(f"\n--- {v} ---  {len(prompt)} 字 / 约 {corpus.est_tokens(prompt)} token")
            print(prompt[:700] + ("\n…（截断）" if len(prompt) > 700 else ""))
        print("\n下一步：起 mock 跑管线，或配好 key 直接跑真模型。")
        return 0

    rows: list[dict] = []
    run_id = time.strftime("%Y%m%d-%H%M%S")
    for v in versions:
        fmt_mode = args.format
        for case in cases:
            sec = corpus.get(case["id"], case["file"])
            if not sec:
                print(f"[跳过] 语料里没有 {case['file']} #{case['id']}")
                continue
            prompt = render(templates[v], case["heading"], sec.text)
            for rep in range(args.repeat):
                rf = None
                degraded = False
                if v == "v3":
                    mode = "json_schema" if fmt_mode == "auto" else fmt_mode
                    rf = format_for(mode, schema)
                r = chat(
                    [{"role": "user", "content": prompt}],
                    cfg=cfg, temperature=args.temperature, response_format=rf,
                )
                # auto 降级：服务商不认 json_schema 时退回 json_object
                if v == "v3" and fmt_mode == "auto" and not r["ok"] and "400" in (r["error"] or ""):
                    r = chat(
                        [{"role": "user", "content": prompt}],
                        cfg=cfg, temperature=args.temperature,
                        response_format={"type": "json_object"},
                    )
                    degraded = True

                if not r["ok"]:
                    status, obj, errs = "request_failed", None, [r["error"] or "unknown"]
                else:
                    status, obj, errs = classify(r["text"], schema)

                usage = r.get("usage") or {}
                rows.append({
                    "run_id": run_id, "version": v, "case": case["id"], "file": case["file"],
                    "rep": rep, "status": status, "errors": errs[:3],
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "latency_ms": r["latency_ms"],
                    "degraded": degraded,
                    "raw": r["text"][:1200],
                })
                print(f"  {v}  case {case['id']:<5} rep{rep}  {STATUS_LABEL[status]:<8}"
                      f"  {r['latency_ms']:>5}ms  in={usage.get('prompt_tokens')}"
                      f"  {'(降级 json_object)' if degraded else ''}")

    if not rows:
        print("没有产生任何结果。")
        return 1

    runs_dir = HERE / "runs"
    runs_dir.mkdir(exist_ok=True)
    raw_path = runs_dir / f"{run_id}.jsonl"
    raw_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")

    report = build_report(rows, cfg, args, len(cases))
    pathlib.Path(args.out).write_text(report, encoding="utf-8")
    print(f"\n明细 : {raw_path}")
    print(f"报告 : {args.out}")
    print("\n" + "\n".join(report.splitlines()[:24]))
    return 0


def build_report(rows: list[dict], cfg: Config, args, n_cases: int) -> str:
    def agg(v: str) -> dict:
        sub = [r for r in rows if r["version"] == v]
        total = len(sub) or 1
        ok = sum(1 for r in sub if r["status"] == "ok")
        insuf = sum(1 for r in sub if r["status"] == "insufficient")
        bad_json = sum(1 for r in sub if r["status"] == "bad_json")
        bad_schema = sum(1 for r in sub if r["status"] == "bad_schema")
        failed = sum(1 for r in sub if r["status"] == "request_failed")
        def avg(key: str) -> int:
            vals = [r[key] for r in sub if r.get(key) is not None]
            return int(sum(vals) / len(vals)) if vals else 0
        return {
            "n": len(sub), "ok": ok, "insuf": insuf, "bad_json": bad_json,
            "bad_schema": bad_schema, "failed": failed,
            "in": avg("prompt_tokens"), "out": avg("completion_tokens"), "ms": avg("latency_ms"),
            "rate": f"{ok}/{total}" if sub else "-",
        }

    lines = [
        "# W2 · 三版 prompt 对比（自动生成）",
        "",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 模型：`{cfg.model}`（{'mock，数字无质量意义' if cfg.is_mock else '真实模型'}）",
        f"- 温度：{args.temperature}　重复：{args.repeat} 次/例　用例：{n_cases} 条",
        f"- 判分：`schema/cards.schema.json`（三版同一把尺子）",
        "",
        "| 版本 | 合规 | 拒答 | 坏 JSON | 坏结构 | 请求失败 | 合规率 | 平均 input | 平均 output | 平均延迟 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v in VERSIONS:
        if not any(r["version"] == v for r in rows):
            continue
        a = agg(v)
        lines.append(
            f"| {v} | {a['ok']} | {a['insuf']} | {a['bad_json']} | {a['bad_schema']} | {a['failed']} "
            f"| {a['rate']} | {a['in']} | {a['out']} | {a['ms']}ms |"
        )

    fails = [r for r in rows if r["status"] in ("bad_json", "bad_schema", "request_failed")]
    lines += ["", "## 失败明细", ""]
    if fails:
        lines += ["| 版本 | case | 状态 | 第一条错误 |", "|---|---|---|---|"]
        for r in fails[:20]:
            err = (r["errors"] or [""])[0].replace("|", "/")[:90]
            lines.append(f"| {r['version']} | {r['case']} | {STATUS_LABEL[r['status']]} | {err} |")
    else:
        lines.append("全部通过。")

    lines += [
        "",
        "## 归因（这一栏必须由你来写）",
        "",
        "1. v2 相对 v1 的差值，来自「槽位化」还是「碰巧」？——看失败类型分布，不看总分。",
        "2. v3 相对 v2 的差值，混了 `schema` 与「负例」两个变量。要不要拆成 v3a / v3b？",
        "3. token 涨了多少？涨的部分买到了什么？（schema 本身也占 token，这是要计入的成本）",
        "",
        "> 验收线：v3 合规 10/10，且总 token ≤ v1 的 1.5 倍。达不到就回去改模板，不是改判分器。",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
