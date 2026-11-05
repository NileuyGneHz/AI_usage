#!/usr/bin/env python3
"""W8 L2/L3 工具：给一个 skill 做体检。

检查的都是**这条计划里定过的硬规则**，不是我的审美：
    - frontmatter 有 name / description
    - description 写症状不写功能（粗略启发式：有没有"当/如果/出现/失败/报错"这类词）
    - 正文 ≤120 行（L2 硬要求）
    - scripts/ 下至少 1 个文件（L2 硬要求）
    - 正文里点名的脚本真的存在
    - 没有写死绝对路径、没有 TODO

    python3 lint_skill.py skill-src/my-skill
    python3 lint_skill.py ~/.workbuddy/skills/nuedc-topic-research

退出码 0 = 通过，1 = 有错误。警告不阻断。
注意：它**判不了"这个 skill 有没有用"**。那只由 5 个真实场景的命中率说了算。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.corpus import est_tokens  # noqa: E402

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
SYMPTOM_WORDS = ["当", "如果", "一旦", "出现", "失败", "报错", "卡", "无法", "没有", "症状", "when", "if "]
MAX_BODY_LINES = 120


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill", help="skill 目录（含 SKILL.md）")
    ap.add_argument("--max-lines", type=int, default=MAX_BODY_LINES)
    args = ap.parse_args()

    d = pathlib.Path(args.skill).expanduser()
    f = d / "SKILL.md" if d.is_dir() else d
    if not f.is_file():
        print(f"找不到 {f}")
        return 2

    text = f.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    warns: list[str] = []

    m = FM_RE.match(text)
    if not m:
        errors.append("缺 frontmatter（--- name/description ---）")
        meta, body = {}, text
    else:
        meta, body = {}, text[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        if not meta.get("name"):
            errors.append("frontmatter 缺 name")
        if not meta.get("description"):
            errors.append("frontmatter 缺 description（它决定召回率）")

    desc = meta.get("description", "")
    if desc:
        if len(desc) < 60:
            warns.append(f"description 只有 {len(desc)} 字，召回率会低（建议 60–300 字，写症状）")
        if len(desc) > 400:
            warns.append(f"description {len(desc)} 字偏长：它常驻上下文，每次请求都付钱")
        if not any(w in desc.lower() for w in SYMPTOM_WORDS):
            warns.append("description 里没有『当/如果/出现/失败』这类触发词，可能在写功能简介")

    body_lines = len(body.splitlines())
    if body_lines > args.max_lines:
        errors.append(f"正文 {body_lines} 行 > {args.max_lines} 行（L2 硬要求；L1 读现有 skill 时忽略）")

    scripts = sorted((d / "scripts").glob("*")) if (d / "scripts").is_dir() else []
    if not scripts:
        errors.append("scripts/ 下没有任何文件（L2 要求；L1 读现有 skill 时忽略这条）")

    for s in scripts:
        if s.name not in body and f"scripts/{s.name}" not in body:
            warns.append(f"scripts/{s.name} 没有在正文里被点名，模型不会去读它")

    seen = set()
    for ref in re.findall(r"scripts/([\w.\-]+)", body):
        if ref in seen:
            continue
        seen.add(ref)
        if not (d / "scripts" / ref).exists():
            warns.append(f"正文提到 scripts/{ref}，但本 skill 的 scripts/ 下没有"
                         f"（若那是项目里的路径而非 skill 自带脚本，忽略这条）")

    if re.search(r"/home/[\w.-]+/", body):
        warns.append("正文里有写死的绝对路径：换机器就失效")

    if re.search(r"\bTODO\b|\bTBD\b|待补", body):
        warns.append("正文里有 TODO/TBD/待补：这还不是成品")

    resident = est_tokens(meta.get("name", "") + " " + desc)
    print(f"skill      : {meta.get('name') or d.name}")
    print(f"路径       : {f}")
    print(f"常驻成本   : 约 {resident} token（name+description，每次请求都在）")
    print(f"正文       : {body_lines} 行（上限 {args.max_lines}）  ~{est_tokens(body)} token（命中后一次性）")
    print(f"scripts    : {len(scripts)} 个")
    print()

    for w in warns:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[错误] {e}")

    if errors:
        print(f"\n不通过：{len(errors)} 个错误，{len(warns)} 个警告")
        return 1
    print(f"\n通过（{len(warns)} 个警告）")
    print("但体检通过 ≠ 有用：去 5 个真实场景里试命中率（scenarios.template.md）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
