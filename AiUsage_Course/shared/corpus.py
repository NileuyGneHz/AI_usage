"""笔记语料的最小工具集：切分、按标题取、朴素关键词检索、token 估算。

W2 用它取「某一节」喂给 prompt，W3 用它做检索对比，W4 用它实现 search_notes。
语料是 `ml-course/Coursera-ML-AndrewNg-Notes/markdown/*.md`：15 个 md、约 500 KB、
116 个以 `### x.y 标题` 开头的小节。

这份实现是**故意朴素**的：中文按二字滑窗切词、TF 打分、无 IDF、无向量。
W3 的结论本来就是「先算账再决定要不要上检索」，所以朴素版本正好是那个对照基线。
想换成 embedding，只需要替换 `search()`，调用方一行不用改。

命令行自检：
    python -m shared.corpus list
    python -m shared.corpus show 6.2
    python -m shared.corpus search 正规方程 --k 3
"""

from __future__ import annotations

import math
import os
import pathlib
import re
from dataclasses import dataclass

COURSE_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_NOTES_DIR = (
    COURSE_ROOT.parent
    / "ml-course"
    / "Coursera-ML-AndrewNg-Notes"
    / "markdown"
)

HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
ID_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*(.*)$")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-.]{1,}")


def notes_dir() -> pathlib.Path:
    """允许用 NOTES_DIR 环境变量指向别处（W5 的 mcp.json 也是这么配的）。"""
    env = os.getenv("NOTES_DIR")
    return pathlib.Path(env).expanduser() if env else DEFAULT_NOTES_DIR


@dataclass
class Section:
    id: str          # "6.2"
    file: str        # "week3.md"
    heading: str     # "6.2 假说表示"
    title: str       # "假说表示"
    line_start: int  # 1-based，指向 ### 那一行
    line_end: int    # 1-based，含
    text: str

    @property
    def chars(self) -> int:
        return len(self.text)

    @property
    def tokens(self) -> int:
        return est_tokens(self.text)

    def cite(self) -> str:
        """给模型看的定位串，W4 的 search_notes 返回值里必须有这一类东西。"""
        return f"{self.file}:{self.line_start}-{self.line_end}"


SUBSET_FILES = [f"week{i}.md" for i in range(1, 6)]


def scope_files(scope: str = "subset") -> list[str] | None:
    """语料范围：subset = week1..week5；all = 全部 15 个 md。"""
    if scope == "all":
        return None
    return list(SUBSET_FILES)


def read_file(name: str, notes: pathlib.Path | None = None) -> str:
    path = (notes or notes_dir()) / name
    return path.read_text(encoding="utf-8", errors="replace")


def est_tokens(text: str) -> int:
    """粗估 token 数：中文约 0.65 token/字，英文约 1 token / 3.5 字符。

    只用于「三个策略谁更贵」的相对比较。真实账单以 API 返回的 usage 为准 ——
    这正是 W3 要求同时记「估算」和「实测」两列的原因。
    """
    cjk = len(CJK_RE.findall(text))
    other = len(text) - cjk
    return int(cjk * 0.65 + other / 3.5) + 1


def load_sections(notes: pathlib.Path | None = None, files: list[str] | None = None) -> list[Section]:
    """按 `### ` 切小节。周文件的章标题是 `----` 下划线式，不用管。"""
    root = notes or notes_dir()
    out: list[Section] = []
    paths = sorted(root.glob("*.md"))
    if files:
        wanted = set(files)
        paths = [p for p in paths if p.name in wanted]

    for path in paths:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        starts = [i for i, ln in enumerate(lines) if HEADING_RE.match(ln)]
        for n, i in enumerate(starts):
            end = (starts[n + 1] - 1) if n + 1 < len(starts) else len(lines) - 1
            heading = HEADING_RE.match(lines[i]).group(1)  # type: ignore[union-attr]
            m = ID_RE.match(heading)
            sec_id, title = (m.group(1), m.group(2) or heading) if m else (heading, heading)
            out.append(
                Section(
                    id=sec_id,
                    file=path.name,
                    heading=heading,
                    title=title,
                    line_start=i + 1,
                    line_end=end + 1,
                    text="\n".join(lines[i:end + 1]).strip(),
                )
            )
    return out


def get(sec_id: str, file: str | None = None, notes: pathlib.Path | None = None) -> Section | None:
    for s in load_sections(notes):
        if s.id == sec_id and (file is None or s.file == file):
            return s
    return None


def terms(text: str) -> list[str]:
    """中文二字滑窗 + 英文词。够用，且你能一眼看懂它为什么朴素。"""
    text = text.lower()
    cjk = "".join(CJK_RE.findall(text))
    grams = [cjk[i:i + 2] for i in range(len(cjk) - 1)]
    words = [w.lower() for w in WORD_RE.findall(text)]
    return grams + words


def search(query: str, k: int = 3, notes: pathlib.Path | None = None) -> list[tuple[Section, float]]:
    """TF 打分 + 长度归一。查询词在标题里出现的，额外加权。"""
    q = terms(query)
    if not q:
        return []
    qset = set(q)
    scored: list[tuple[Section, float]] = []
    for sec in load_sections(notes):
        body = terms(sec.text)
        if not body:
            continue
        hits = sum(1 for t in body if t in qset)
        title_hits = sum(1 for t in terms(sec.heading) if t in qset)
        score = hits / math.sqrt(len(body)) + title_hits * 0.8
        if score > 0:
            scored.append((sec, round(score, 4)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


SNIPPET_RADIUS = 90


def snippet(sec: Section, query: str, radius: int = SNIPPET_RADIUS) -> str:
    """截一段围绕首个查询词的窗口。这是 W4「别返回全文」的最小可行实现。"""
    text = sec.text
    q = [t for t in terms(query) if len(t) >= 2]
    pos = -1
    for t in q:
        pos = text.lower().find(t)
        if pos >= 0:
            break
    if pos < 0:
        return text[: radius * 2].replace("\n", " ").strip()
    lo = max(0, pos - radius)
    hi = min(len(text), pos + radius)
    piece = text[lo:hi].replace("\n", " ").strip()
    return ("…" if lo > 0 else "") + piece + ("…" if hi < len(text) else "")


def _main() -> None:
    import sys

    argv = sys.argv[1:]
    if not argv or argv[0] == "list":
        secs = load_sections()
        print(f"语料目录: {notes_dir()}")
        print(f"小节数  : {len(secs)}   总字符: {sum(s.chars for s in secs):,}"
              f"   估算 token: {sum(s.tokens for s in secs):,}")
        cur = None
        for s in secs:
            if s.file != cur:
                cur = s.file
                print(f"\n[{cur}]")
            print(f"  {s.id:<6} {s.title[:34]:<36} L{s.line_start}-{s.line_end}")
        return
    if argv[0] == "show" and len(argv) > 1:
        sec = get(argv[1])
        if not sec:
            print(f"找不到小节 {argv[1]}")
            return
        print(f"{sec.heading}   ({sec.cite()})  {sec.chars} 字 / ~{sec.tokens} token")
        print("-" * 60)
        print(sec.text)
        return
    if argv[0] == "search" and len(argv) > 1:
        k = 3
        if "--k" in argv:
            k = int(argv[argv.index("--k") + 1])
        for sec, score in search(argv[1], k=k):
            print(f"{score:>6}  {sec.heading[:40]:<42} {sec.cite()}")
            print("        " + snippet(sec, argv[1])[:150])
        return
    print(__doc__)


if __name__ == "__main__":
    _main()
