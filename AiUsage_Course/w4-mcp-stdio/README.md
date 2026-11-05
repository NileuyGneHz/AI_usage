# W4 · MCP 协议与第一个 server — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
本周节奏：**先看报文 → 再写契约 → 最后写代码**。顺序反了一定返工。

---

## 0. 骨架（3 分钟）

```
w4-mcp-stdio/
├── raw_client.py             # 最小 MCP client：打印每一行 JSON-RPC（已给）
├── notes_index.py            # 语料内核：list / search / read（已给，可直接 import）
├── tools.spec.template.md    # 契约工作表（先填这个）
├── server/                   # 你写 server.py 的地方（空的）
└── NOTES.md
```

**已经给你的**：客户端、语料能力、安全检查。
**没给你的**：`server.py` —— 也就是本周真正要学的"MCP 那一层"。

这不是藏私。`notes_index.py` 是可复用内核，`raw_client.py` 是观测工具；
而"把一个函数变成模型能调用的工具"这件事，只能你亲手做一遍。

---

## 1. 环境（10 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w4-mcp-stdio
python3 -m venv .venv
.venv/bin/pip install "mcp>=2,<3" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

版本必须锁 `mcp<3`。W0 已经让你撞过一次 `FastMCP → MCPServer` 的改名墙，
这次别再抄教程里的 import。

验证：

```bash
.venv/bin/python -c "from mcp.server.mcpserver import MCPServer; print('ok')"
```

---

## 2. 先看报文，零成本（15 分钟）

对着 W0 的 demo 跑一遍，确认你认得每一行：

```bash
python3 raw_client.py --server "../w0-icebreak/.venv/bin/python ../w0-icebreak/mcp_demo.py"
```

逐行看，重点看三处：

1. `initialize` 的响应里 `capabilities` 有哪三样
2. `tools/list` 里 `inputSchema` 长什么样——**注意 `path` 参数没有 description**
3. `resources/list` 里那个 `demo://about`——它不在 `tools/list` 里，模型不会调它

再手动发一次调用：

```bash
python3 raw_client.py \
  --server "../w0-icebreak/.venv/bin/python ../w0-icebreak/mcp_demo.py" \
  --call count_lines --args "{\"path\": \"$(pwd)/notes_index.py\"}"
```

**这一步过不了就不要往下走。** 报文没看懂就写 server，等于闭着眼睛改代码。

---

## 3. 先填契约，别先写代码（40 分钟）

```bash
cp tools.spec.template.md tools.spec.md
```

按表逐格填。填的时候只有一个标准：**读者是一个从没见过你这个库的人，他只有 30 秒。**

三个工具的 description 里，最容易漏的是"什么时候**别**用"。补上它，W5 的误调用率
会明显下降——这不是玄学，是给模型划边界。

填完先自检一遍文末那六条，再动代码。

---

## 4. 写 server.py（1–2 小时）

放 `server/server.py`。结构大概是：

```python
from mcp.server.mcpserver import MCPServer
from notes_index import list_chapters, search_notes, read_section, index_tree

mcp = MCPServer("ml-notes")

@mcp.tool()
def search_notes_tool(query: str, chapter: str | None = None, k: int = 3) -> dict:
    """（把你 tools.spec.md 里写的那段 description 抄进来）"""
    return search_notes(query, chapter=chapter, k=k)

# ... read_section / list_chapters 同理

@mcp.resource("notes://index")
def notes_index_resource() -> str:
    """笔记目录树，供 client 按需注入。"""
    return index_tree()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

四个容易出错的细节：

1. **`notes_index` 的 import 路径**。`server/` 是子目录，需要
   `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`，或者把
   `notes_index.py` 复制进去。前者更干净。
2. **类型标注就是 schema**。`k: int = 3` 会生成 `{"type": "integer"}`，
   `chapter: str | None = None` 会变成可选。**想要 `enum` 就自己写 JSON Schema，
   或者干脆不收这个参数**——W5 会告诉你为什么。
3. **docstring 就是 description**。它会**原样**进 system prompt，包括缩进和空行。
   写之前先想：这段话值多少 token？
4. **别 `print()`**。日志用 `print(..., file=sys.stderr)`。

---

## 5. 用 raw_client 验（20 分钟）

```bash
# 默认会找 server/server.py，并用 .venv/bin/python 起它
python3 raw_client.py
```

逐条过：

```bash
python3 raw_client.py --call search_notes --args '{"query": "正规方程", "k": 2}'
python3 raw_client.py --call read_section --args '{"path": "week2.md", "start_line": 146, "end_line": 160}'
python3 raw_client.py --call list_chapters
```

**错误路径也要跑**（这比成功路径重要）：

```bash
python3 raw_client.py --call read_section --args '{"path": "nope.md", "start_line": 1, "end_line": 5}'
python3 raw_client.py --call read_section --args '{"path": "week2.md", "start_line": 1, "end_line": 900}'
```

看到的是**可读错误 + 下一步建议**才对。如果看到 `isError: true` 加一坨 Python 堆栈，
回去把异常改成返回值——W5 的模型靠这个自我修正，而堆栈只会让它放弃。

---

## 6. 存一份 tools.json 给 W5（1 分钟）

```bash
python3 raw_client.py --dump ../w5-mcp-http/tools.json
```

W5 的 `probe.py` 直接读它，对着真实的 schema 测"模型会不会选错工具"。

---

## 7. 可选：Inspector（需要 npm 能联网）

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server/server.py
```

界面好看，但**看不到原始报文**。你已经用 `raw_client.py` 看过了，这里只是交叉验证。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `tools.spec.md` | 填完的契约工作表（这是设计文档，别删） |
| `server/server.py` | 三个 tool + 一个 resource |
| `tools.json` | `tools/list` 的快照（W5 要用） |
| `NOTES.md` | 200 字以内 |

---

## 验收

- [ ] `python3 raw_client.py` 打出完整的 `initialize → tools/list → resources/list`
- [ ] `search_notes` 的返回里**有 `file` 和行号**，不是只有文本
- [ ] 传不存在的文件给 `read_section`，得到可读错误 + 建议，不是堆栈
- [ ] 一次要 900 行会被**代码**拦住（不是靠 description 请求模型别这么做）
- [ ] 能不看文档说出三大原语的控制权归属

---

## 坑

- **`print()` 打到 stdout**：协议流被污染，client 报 `Expecting value`。用 `sys.stderr`。
- **`mcp` 装成了 3.x 或 1.x**：`ImportError` 或 API 全变。`pip show mcp` 确认版本。
- **server 用系统 python 起，用 venv 装的包**：报 `No module named mcp`。
  `raw_client.py` 会优先用 `.venv/bin/python`，但 `mcp.json` 里要写绝对路径（W5）。
- **返回 `str` 还是 `dict`**：`dict` 会进 `structuredContent`，`str` 只进 `content`。
  W7 做断言时 `structuredContent` 更好用，所以本周统一返回 `dict`。
- **在 `server.py` 里写业务逻辑**：逻辑放 `notes_index.py`，server 只做协议适配。
  这样 W5 换传输方式时，业务代码一行不用动。
