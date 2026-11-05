# W5 · MCP 工程化 — 任务卡

> 状态：骨架已升级为可跑脚手架（2026-11-05）
> 入口顺序：`LECTURE.md`（为什么）→ `README.md`（怎么做）→ 本文件（交什么、怎么算过）。

## 目标

从「能跑」到「敢给别人用」。本周的产出质量几乎全由 `description` 和 `inputSchema` 两项决定，**不是由代码质量决定**——这正是 W0 订正过的那件事。

## 依赖

- W4 的 server 完整可用（stdio 报文已跑通）
- W1 实验 4（错误信息的可读性）——工具错误要写成那样，模型才会自我修正
- WorkBuddy 的 MCP 配置入口 `~/.workbuddy/mcp.json`

## 交付物清单

| 文件 | 内容 | 状态 |
|---|---|---|
| `server_http.py` | W4 server 增加 Streamable HTTP 传输 | **待写（可选，压缩点）** |
| `mcp.json.example` | 注册配置模板 | 已建（使用前核对字段名） |
| `questions.md` | 10 个真实提问 + 期望工具（7 正例 / 3 负例） | 已建 |
| `probe.py` | **description/schema 的 A/B 探针**：直接问模型调哪个 | 已建 |
| `measure.template.md` | 调用成功率 / 误调 / 上下文增量（人工） | 模板已建，**待填** |
| `NOTES.md` | 本周踩坑记录 | 模板已建 |

> 分工：探针与 10 问已给；**改哪一句、改完有没有变好，必须自己判断**。
> 本周不写新代码也能过验收——这就是它和 W4 的区别。

## 验收

问「线性回归的正规方程是什么」，agent 自动调用 `search_notes`，答案带**文件路径 + 行号**；10 问里调用正确 ≥ 8 次。
达不到就回去改 `description` 和 schema，不要去改函数体。

## 待定决策

1. **是否真做 HTTP**：最安全的压缩点。若 W4 卡得久，本周可以只做「接进 WorkBuddy」而跳过 HTTP。
2. **注册到哪**：WorkBuddy（`~/.workbuddy/mcp.json`）还是只用 Inspector？计划要求真实 client，建议 WorkBuddy，因为你要观察的是「模型会不会主动调」。
3. **10 个提问从哪来**：建议从 W2/W3 的真实提问里挑，别临时编——编出来的问题会不自觉地贴合你写的 description，测不出误调用。
4. **annotations 标哪些**：`readOnlyHint` / `destructiveHint` / `idempotentHint`。本周的 server 全只读，正好用来理解 Host 为什么要这些标记。
5. **错误返回格式**：定一个统一约定（`Error: <可读原因> | hint: <下一步>`），W6 的 agent 会靠它自我修正。

## 可调整 / 压缩

W4 + W5 合并 → 1 周，只做 stdio。**但「接进真实 client 实测 10 问」不能砍**，这是唯一能验证 description 写得好不好的环节。

## 坑

- `description` 里堆「可以搜索、读取、列目录、统计……」会让模型分不清何时用哪个。
- schema 要收紧：`enum` 优于自由字符串，`required` 要真的必填。
- 权限边界写在代码里硬约束，不要写在 description 里靠模型自觉。
- 工具返回内容是不可信输入，别让它当指令执行。
