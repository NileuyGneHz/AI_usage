"""W6 · agent 的手脚：三个工具 + 一个分发器。

本周用**本地函数**而不是 MCP server，是刻意的：
    W4/W5 已经证明工具能被模型调起来，这一周要学的是**循环**，不是协议。
    等循环写通了，把 execute() 换成 MCP client 调用，其余代码一行不用动。
    （这也是 W4 把业务逻辑放 notes_index.py、server 只做适配的回报。）

工具定义里的 description 沿用 W5 的手感：先说什么时候用，再说什么时候别用。
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from shared import corpus  # noqa: E402

MAX_LINES = 120
MAX_SNIPPET = 240


def _safe(path: str) -> pathlib.Path:
    root = corpus.notes_dir().resolve()
    p = (root / pathlib.Path(path).name).resolve()
    if root not in p.parents or p.suffix != ".md":
        raise ValueError(f"只能读 {root} 下的 .md，收到 {path}")
    return p


def search_notes(query: str, chapter: str | None = None, k: int = 3) -> dict:
    hits = corpus.search(query, k=k * 3)
    if chapter:
        hits = [(s, sc) for s, sc in hits if s.file == chapter]
    hits = hits[:k]
    return {
        "hits": [
            {"file": s.file, "section": s.heading, "start_line": s.line_start, "end_line": s.line_end,
             "snippet": corpus.snippet(s, query, radius=MAX_SNIPPET // 2)[:MAX_SNIPPET], "score": sc}
            for s, sc in hits
        ],
        "note": "片段是截断的；需要上下文时用 read_section 按行号读。",
    }


def read_section(path: str, start_line: int, end_line: int) -> dict:
    p = _safe(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if start_line < 1 or end_line < start_line:
        raise ValueError("行号不合法")
    if end_line > len(lines):
        raise ValueError(f"文件只有 {len(lines)} 行")
    if end_line - start_line + 1 > MAX_LINES:
        raise ValueError(f"一次最多 {MAX_LINES} 行，请缩小范围")
    return {"path": p.name, "start_line": start_line, "end_line": end_line,
            "text": "\n".join(lines[start_line - 1:end_line])}


def list_chapters() -> dict:
    out: dict[str, list] = {}
    for s in corpus.load_sections():
        out.setdefault(s.file, []).append({"id": s.id, "title": s.title,
                                           "start_line": s.line_start, "end_line": s.line_end})
    return {"chapters": [{"file": f, "sections": v} for f, v in sorted(out.items())]}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": (
                "在机器学习课程笔记里按关键词检索小节，返回片段和 `文件:行号`。\n"
                "什么时候用：想不起某个概念在哪一节时。\n"
                "什么时候别用：已知具体文件与行号时，直接用 read_section。\n"
                "返回：最多 3 条命中，每条含 file / section / start_line / end_line / snippet。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "关键词，尽量短"},
                    "k": {"type": "integer", "description": "返回条数，1-5，默认 3"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_section",
            "description": (
                "按行号读取笔记原文，一次最多 120 行。\n"
                "什么时候用：已经从检索结果拿到 `文件:行号`，需要看细节时。\n"
                "什么时候别用：不知道在哪时，先用 search_notes。\n"
                "返回：path / start_line / end_line / text。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件名，如 week3.md"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path", "start_line", "end_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_chapters",
            "description": (
                "列出全部笔记文件与小节标题。\n"
                "什么时候用：冷启动，连该查哪个文件都不知道时。\n"
                "什么时候别用：已经知道文件名时——它很贵（约 3000 token）。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_FUNCS = {"search_notes": search_notes, "read_section": read_section, "list_chapters": list_chapters}


def execute(name: str, args: dict) -> dict:
    """执行工具，永远返回 dict（不抛异常给循环）。

    错误格式沿用 W5 定下的约定：{"error": 原因, "hint": 下一步}。
    模型靠这个自我修正；堆栈只会让它放弃。
    """
    fn = _FUNCS.get(name)
    if not fn:
        return {"error": f"没有这个工具: {name}", "hint": f"可用工具: {list(_FUNCS)}"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": f"参数不对: {e}", "hint": "检查必填参数与类型"}
    except (ValueError, FileNotFoundError) as e:
        return {"error": str(e), "hint": "缩小范围，或先用 search_notes 定位"}


if __name__ == "__main__":
    # 自检：不经过模型，直接跑一遍三个工具
    print(json.dumps(execute("search_notes", {"query": "正规方程", "k": 2}), ensure_ascii=False, indent=2)[:800])
    print(json.dumps(execute("read_section", {"path": "week2.md", "start_line": 146, "end_line": 152}),
                     ensure_ascii=False)[:300])
    print(json.dumps(execute("read_section", {"path": "week2.md", "start_line": 1, "end_line": 999}),
                     ensure_ascii=False))
