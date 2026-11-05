#!/usr/bin/env python3
"""W7 脚手架：把 W5 的 10 个真实提问转成 evalset 的起点。

为什么要有这一步：
    "20 条从哪来"是本最容易卡住的地方。凭空编 20 条，一定会偏袒你当前的实现。
    从 W5 的真实提问转，这些输入已经被真实使用过，天然更中立。

它只生成**骨架**：`must_include`（关键事实）留空给你填，因为只有你知道什么算答对。

    python3 seed_evalset.py                      # 生成 evalset.jsonl（已存在则拒绝）
    python3 seed_evalset.py --force              # 覆盖
    python3 seed_evalset.py --out evalset_v1.jsonl

生成后你必须做的三件事：
    1. 给每条填 `expect_result.must_include`（2–4 个关键事实，别写整句）
    2. 把 `max_steps` 按任务复杂度调（检索题 6，多步题 8–10，负例 2）
    3. 再补 10 条自己的（边界、歧义、多步），凑够 20
"""

from __future__ import annotations

import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_Q = HERE.parent / "w5-mcp-http" / "questions.md"


def parse_questions(path: pathlib.Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## ") and rows:
            break
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() == "id":
            continue
        if all(set(c) <= set("-: ") for c in cells if c):
            continue
        rows.append({"id": cells[0], "question": cells[1], "expect": cells[2]})
    return rows


def to_case(q: dict, idx: int) -> dict:
    expect = q["expect"]
    negative = expect == "none"
    case = {
        "id": f"E{idx:02d}",
        "type": "negative" if negative else "positive",
        "input": q["question"],
        "expect_result": {
            "must_include": [],          # ← 你来填
            "judge": "human",
            "_todo": "填 2-4 个关键事实；负例可留空，但建议填「拒绝」类关键词",
        },
        "expect_trace": {
            "must_call": [] if negative else [expect],
            "must_not_call": ["*"] if negative else [],
            "max_steps": 2 if negative else (8 if "读" in q["question"] else 6),
        },
        "_source": f"w5-questions:{q['id']}",
    }
    if negative:
        case["expect_behavior"] = "拒绝，并说明工具只读 / 材料未覆盖"
    return case


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(DEFAULT_Q))
    ap.add_argument("--out", default=str(HERE / "evalset.jsonl"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    if out.exists() and not args.force:
        print(f"{out} 已存在。用 --force 覆盖，或换个 --out。")
        return 1

    qs = parse_questions(pathlib.Path(args.questions))
    if not qs:
        print("没解析出问题，检查 questions.md 表格格式。")
        return 2

    cases = [to_case(q, i) for i, q in enumerate(qs, 1)]
    out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cases), encoding="utf-8")

    print(f"已生成 {out}  ({len(cases)} 条)")
    print(f"  正例 {sum(1 for c in cases if c['type'] == 'positive')} / "
          f"负例 {sum(1 for c in cases if c['type'] == 'negative')}")
    print("\n必须补的三件事：")
    print("  1. 每条填 expect_result.must_include（2-4 个关键事实）")
    print("  2. 按任务复杂度调 max_steps")
    print("  3. 再补 10 条自己的，凑够 20 —— 尤其是「该拒但容易答」的边界样本")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
