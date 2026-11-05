#!/usr/bin/env python3
"""W4 的工具函数库：把「语料」变成三个可以被 MCP 包起来的能力。

它本身不是 server —— 它是 server 里那几个函数要调的东西。
把它和 `server.py` 分开，是为了让你这周只思考一件事：**MCP 那一层怎么写**，
而不是同时纠结"检索怎么排"（W3 已经定了）。

    python3 notes_index.py list
    python3 notes_index.py search 正规方程 --k 3
    python3 notes_index.py search 梯度下降 --chapter week1.md
    python3 notes_index.py read week2.md --start 146 --end 160

在 server.py 里直接 import：

    from notes_index import list_chapters, search_notes, read_section

三个返回值都是 dict，可以直接 `json.dumps` 或塞进 tool 的返回值。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from shared import corpus  # noqa: E402

MAX_LINES_PER_CALL = 120      # read_section 的硬上限：超过就报错，而不是默默返回全文
MAX_SNIPPET_CHARS = 240       # search_notes 每段片段的字数上限


# ---------------------------------------------------------------- 安全边界
def _safe_path(path: str) -> pathlib.Path:
    """只允许读 NOTES_DIR 下的 .md 文件。

    这条检查必须写在这里，不能写在 tool 的 description 里靠模型自觉 ——
    模型可以被诱导，代码不会。
    """
    root = corpus.notes_dir().resolve()
    p = (root / pathlib.Path(path).name).resolve()
    if root not in p.parents or p.suffix != ".md":
        raise ValueError(f"只能读取 {root} 下的 .md 文件，收到: {path}")
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在: {p.name}")
    return p


# ---------------------------------------------------------------- 三个能力
def list_chapters() -> dict:
    """章节清单：文件名 + 每节标题 + 行号范围。给模型"先看地图"用的。"""
    chapters: dict[str, list] = {}
    for sec in corpus.load_sections():
        chapters.setdefault(sec.file, []).append(
            {"id": sec.id, "title": sec.title, "start_line": sec.line_start, "end_line": sec.line_end}
        )
    return {
        "chapters": [
            {"file": f, "sections": sorted(v, key=lambda x: x["start_line"])}
            for f, v in sorted(chapters.items())
        ]
    }


def search_notes(query: str, chapter: str | None = None, k: int = 3) -> dict:
    """检索：只返回片段 + 精确定位，绝不返回全文。

    W3 的结论在这里落地：3 段 × 240 字 + `文件:行号`，比 5000 字有用得多 ——
    而且给了行号，模型才能自己决定"要不要再读一段"。
    """
    hits = corpus.search(query, k=k * 3)
    if chapter:
        hits = [(s, sc) for s, sc in hits if s.file == chapter]
    hits = hits[:k]

    return {
        "query": query,
        "k": k,
        "hits": [
            {
                "file": sec.file,
                "section": sec.heading,
                "start_line": sec.line_start,
                "end_line": sec.line_end,
                "snippet": corpus.snippet(sec, query, radius=MAX_SNIPPET_CHARS // 2)[:MAX_SNIPPET_CHARS],
                "score": score,
            }
            for sec, score in hits
        ],
        "note": "片段是截断的。需要完整上下文时，用 read_section 按行号读。",
    }


def read_section(path: str, start_line: int, end_line: int) -> dict:
    """按行读：必须给行号范围，且一次不超过 MAX_LINES_PER_CALL 行。"""
    p = _safe_path(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)

    if start_line < 1 or end_line < start_line:
        raise ValueError(f"行号不合法: {start_line}-{end_line}")
    if end_line > total:
        raise ValueError(f"文件只有 {total} 行，请求到 {end_line}")
    if end_line - start_line + 1 > MAX_LINES_PER_CALL:
        raise ValueError(
            f"一次最多 {MAX_LINES_PER_CALL} 行，本次请求 {end_line - start_line + 1} 行。"
            f" 请缩小范围 —— 这条限制就是为了防止你把整篇塞进上下文。"
        )

    return {
        "path": p.name,
        "start_line": start_line,
        "end_line": end_line,
        "total_lines": total,
        "text": "\n".join(lines[start_line - 1:end_line]),
    }


def index_tree() -> str:
    """给 resource `notes://index` 用的目录树（纯文本，人看得懂，模型也看得懂）。"""
    lines = [f"笔记库: {corpus.notes_dir().name}"]
    cur = None
    for sec in corpus.load_sections():
        if sec.file != cur:
            cur = sec.file
            lines.append(f"\n{cur}")
        lines.append(f"  {sec.id:<6} {sec.title}  (L{sec.line_start}-{sec.line_end})")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def _main() -> int:
    ap = argparse.ArgumentParser(description="W4 语料工具（server 的可复用内核）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="章节清单")

    sp = sub.add_parser("search", help="检索片段")
    sp.add_argument("query")
    sp.add_argument("--k", type=int, default=3)
    sp.add_argument("--chapter", default=None)

    rp = sub.add_parser("read", help="按行读")
    rp.add_argument("path")
    rp.add_argument("--start", type=int, required=True)
    rp.add_argument("--end", type=int, required=True)

    sub.add_parser("tree", help="目录树（notes://index 的内容）")

    args = ap.parse_args()
    try:
        if args.cmd == "list":
            out = list_chapters()
        elif args.cmd == "search":
            out = search_notes(args.query, chapter=args.chapter, k=args.k)
        elif args.cmd == "read":
            out = read_section(args.path, args.start, args.end)
        else:
            print(index_tree())
            return 0
    except (ValueError, FileNotFoundError) as e:
        # 注意这里的错误形态：可读、带下一步。W5 会把这条规则用在 tool 返回里。
        print(json.dumps({"error": str(e), "hint": "检查参数或缩小行号范围"}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
