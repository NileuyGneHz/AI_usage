#!/usr/bin/env python3
"""W8 L1 工具：把你继承的那 18 个 skill 摊开看一遍（只读，不改动任何文件）。

它回答的是 L1 的第一层问题：**这批文件到底有多重、有没有脚本、常驻成本是多少。**
不回答"哪句是错的"——那要靠人读。

    python3 audit_skills.py                          # 默认扫 ~/.workbuddy/skills
    python3 audit_skills.py --dir /path/to/skills
    python3 audit_skills.py --json out.json          # 机读版，方便排序筛选
    python3 audit_skills.py --sort lines

输出里的「常驻」= frontmatter 的 name+description 估算 token：
这部分**每次请求都在 system 里**，18 个 skill 加起来就是你每天在付的固定成本。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from dataclasses import dataclass, asdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.corpus import est_tokens  # noqa: E402

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)
CODE_BLOCK_RE = re.compile(r"```")
ABS_PATH_RE = re.compile(r"/home/[\w.-]+/")

FLAG_RULES = [
    ("body>200", "正文超过 200 行：命中后一次性灌进上下文，成本高"),
    ("no-scripts", "有可执行步骤却没有 scripts/：模型每次都要逐行照着敲"),
    ("huge-code", "正文里嵌了超长代码块：本应是脚本或 references/"),
    ("abs-path", "正文里写死了绝对路径：换机器/换目录就失效"),
    ("desc-short", "description 太短：召回率会低"),
    ("desc-long", "description 太长：每次请求都在为它付钱"),
    ("todo", "正文里有 TODO/TBD/待补：这文件自己都没写完"),
]


@dataclass
class Skill:
    name: str
    dir: str
    lines: int
    desc_chars: int
    desc_tokens: int
    scripts: int
    references: int
    code_blocks: int
    flags: list[str]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FM_RE.match(text)
    if not m:
        return {}, text
    block, body = m.group(1), text[m.end():]
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def inspect(skill_dir: pathlib.Path) -> Skill | None:
    f = skill_dir / "SKILL.md"
    if not f.is_file():
        return None
    text = f.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)
    lines = len(text.splitlines())
    desc = (meta.get("description") or "").strip()
    scripts = len([p for p in (skill_dir / "scripts").glob("*")]) if (skill_dir / "scripts").is_dir() else 0
    refs = len([p for p in (skill_dir / "references").glob("*")]) if (skill_dir / "references").is_dir() else 0
    code_blocks = CODE_BLOCK_RE.findall(body).__len__() // 2

    flags = []
    if lines > 200:
        flags.append("body>200")
    has_cmd_lines = sum(1 for ln in body.splitlines() if ln.strip().startswith(("$", "sudo", "python", "pip", "npm", "ros2", "git ")))
    if scripts == 0 and has_cmd_lines >= 5:
        flags.append("no-scripts")
    if code_blocks >= 1 and any(len(b.splitlines()) > 30 for b in re.findall(r"```.*?```", body, re.S)):
        flags.append("huge-code")
    if ABS_PATH_RE.search(body):
        flags.append("abs-path")
    if len(desc) < 20:
        flags.append("desc-short")
    if len(desc) > 400:
        flags.append("desc-long")
    if re.search(r"\bTODO\b|\bTBD\b|待补", body):
        flags.append("todo")

    return Skill(
        name=meta.get("name") or skill_dir.name,
        dir=str(skill_dir),
        lines=lines,
        desc_chars=len(desc),
        desc_tokens=est_tokens(desc),
        scripts=scripts,
        references=refs,
        code_blocks=code_blocks,
        flags=flags,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="审计一批 skill（只读）")
    ap.add_argument("--dir", default=os.path.expanduser("~/.workbuddy/skills"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--sort", default="lines", choices=["lines", "desc", "scripts"])
    args = ap.parse_args()

    root = pathlib.Path(args.dir).expanduser()
    if not root.is_dir():
        print(f"目录不存在: {root}")
        return 2

    skills = [s for p in sorted(root.iterdir()) if p.is_dir() and (s := inspect(p))]
    if not skills:
        print(f"{root} 下没有找到 SKILL.md")
        return 1

    key = {"lines": lambda s: -s.lines, "desc": lambda s: -s.desc_chars,
           "scripts": lambda s: s.scripts}[args.sort]
    skills.sort(key=key)

    print(f"目录: {root}   共 {len(skills)} 个 skill\n")
    print(f"{'skill':<38}{'行数':>5}{'desc字':>7}{'常驻tok':>8}{'脚本':>5}{'refs':>5}  标记")
    print("-" * 100)
    for s in skills:
        print(f"{s.name[:36]:<38}{s.lines:>5}{s.desc_chars:>7}{s.desc_tokens:>8}"
              f"{s.scripts:>5}{s.references:>5}  {','.join(s.flags) or 'ok'}")

    total_resident = sum(s.desc_tokens for s in skills)
    total_lines = sum(s.lines for s in skills)
    print("-" * 100)
    print(f"合计: {total_lines} 行   常驻约 {total_resident} token / 次请求")
    print(f"      （这就是你每天开机就在付的固定成本，和用不用得上无关）")

    from collections import Counter
    c = Counter(f for s in skills for f in s.flags)
    if c:
        print("\n标记分布：")
        for flag, n in c.most_common():
            desc = dict(FLAG_RULES).get(flag, "")
            print(f"  {flag:<12} {n:>2} 个  — {desc}")

    print("\n输出全是事实，判断留给你：")
    print("  - 哪个文件的 description 写的是功能而不是症状？")
    print("  - 哪个文件的正文里有可以直接变成 scripts/ 的步骤？")
    print("  - 哪个文件的路径/命令已经过期？（这个工具看不出来，要人去验证）")

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps([asdict(s) for s in skills], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n机读版: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
