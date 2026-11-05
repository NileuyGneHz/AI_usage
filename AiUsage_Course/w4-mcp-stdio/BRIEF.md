# W4 · MCP 协议与第一个 server — 任务卡

> 状态：骨架已升级为可跑脚手架（2026-11-05）
> 入口顺序：`LECTURE.md`（为什么）→ `README.md`（怎么做）→ 本文件（交什么、怎么算过）。

## 目标

不抄教程，读 spec 写一个能用的 `ml-notes-mcp`。**先手工跑通 JSON-RPC 报文，再接 LLM。**

## 依赖

- W0 的 `raw_rpc.py`：报文格式已经见过，本周是把它变成一个真的 server
- W3 的结论：`search_notes` 该返回多少字、怎么给定位
- 同一份笔记语料（15 个 md，`shared/corpus.py` 已能切节）
- `mcp` 2.x：注意是 `MCPServer` 不是 `FastMCP`（W0 已撞过这个版本墙）

## 交付物清单

| 文件 | 内容 | 状态 |
|---|---|---|
| `server/server.py` | `ml-notes-mcp` 主程序（MCP 那一层） | **待写（本周核心）** |
| `notes_index.py` | 语料索引与切分逻辑（可复用内核） | 已建 |
| `tools.spec.template.md` | 3 个 tool + 1 个 resource 的契约工作表 | 已建，**待填成 `tools.spec.md`** |
| `raw_client.py` | 最小 MCP client，打印原始 JSON-RPC（含 `--dump`） | 已建 |
| `tools.json` | `tools/list` 快照，W5 的 probe 会读它 | 跑完即生成 |
| `NOTES.md` | 本周踩坑记录 | 模板已建 |

> 分工：**客户端、语料能力、安全边界已给**；`server.py`（MCP 适配层）与契约设计**必须自己写**。
> 理由见 README 第 0 节：本周要学的就是「一个普通函数怎么变成模型能调用的工具」。

工具契约（计划原文）：
- `search_notes(query, chapter?)` → 命中片段 + 文件路径 + 行号
- `read_section(path, start_line, end_line)` → 按行读
- `list_chapters()` → 章节清单
- resource：`notes://index` → 目录树

## 验收

用 Inspector 或 `raw_client.py` 手工发 `tools/list`、`tools/call`，看到完整 JSON-RPC 报文。
**先跑通报文，再接 LLM** —— 顺序反了会同时调试两个黑箱。

## 待定决策

1. **语言**：Python（`mcp` 2.x，W0 已验证）还是 Node？建议 Python，你 W0–W3 全是 Python，且 `mcp` 2.3.0 已在隔离环境跑通。
2. **tool 粒度**：3 个够不够？`search_notes` 和 `read_section` 是否会职责重叠？**先按 3 个写，跑起来再拆**。
3. **索引方式**：每次调用现扫 15 个文件，还是启动时建一次索引？本周语料小，现扫即可，别过早优化
   （`notes_index.py` 默认现扫，一次约 40 ms，可接受）。
4. **resource 的 uri 设计**：`notes://index` 只是计划里的建议值，可改。
5. **是否现在读 spec 原文**：计划要求「读 spec 不读博客」。若 W3 学得吃力，允许先写 server 再回头补 spec，但**不要跳过**。

## 可调整 / 压缩

4 周方案里 W4 + W5 合并为 1 周，做法是**只做 stdio、不做 HTTP**。这是最安全的压缩点。

## 坑

- `search_notes` 别返回全文：3 段 × 200 字 + 精确定位，比 5000 字有用得多。
- 三大原语的**控制权归属**最容易记混：tools 模型决定 / resources 应用决定 / prompts 用户决定。
- 别在 tool 定义里堆功能清单，一个 tool 一件事。
