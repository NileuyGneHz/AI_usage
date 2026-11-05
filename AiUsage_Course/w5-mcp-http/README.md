# W5 · MCP 工程化 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
本周的活是**改文字 + 量数据**，不是写代码。如果你在写代码，多半走偏了。

---

## 0. 骨架（3 分钟）

```
w5-mcp-http/
├── questions.md              # 10 个真实提问 + 期望工具（已给，可改）
├── probe.py                  # 不接宿主，直接问模型「你会调哪个」（已给）
├── tools.json                # W4 的 tools/list 快照（你自己 dump 出来的）
├── measure.template.md       # 人工度量表：成功率 / 误调 / 上下文增量
├── mcp.json.example          # Streamable HTTP 注册模板（字段待核对）
├── mcp.stdio.example.json    # stdio 注册模板（压缩方案用）
└── runs/                     # 每次 probe 的明细
```

`probe.py` 用的是**同一个模型 + 同一组问题 + 不同版本的 tools 定义**，
所以它测出来的差异，可以归因到你改的那一句话上。

---

## 1. 造一份基线（10 分钟）

W4 结束时应该留下了 `server/server.py`。没留就先回去做 W4，别跳。

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w4-mcp-stdio
python3 raw_client.py --dump ../w5-mcp-http/tools.json    # 确认 server 起得来
```

然后：

```bash
cd ../w5-mcp-http
python3 probe.py --tools tools.json --out baseline.md
```

看三行输出就够：

```
选择正确 : x/10
参数合法 : x/10
误调(本该 none) : x  ['Q6']
```

**这就是你的基线。** 把它记下来，后面每次改动都和它比。

> 如果模型全都不调（`0/10`，全是 none），先别改 description——检查
> `tools.json` 里的 schema 是不是 `type: object` 缺失，或者参数全是 required。

---

## 2. 只改一句 description（30 分钟）

从基线里挑**一个**失败类型下手，别贪多：

| 失败类型 | 改哪句 | 例 |
|---|---|---|
| 漏调（Q1/Q5/Q8 没调） | 「什么时候用」太抽象 | 改成用户会说的话："想不起某个概念在哪一节时" |
| 误调（Q6/Q7 调了） | 缺「什么时候别用」 | "闲聊、天气、与课程无关的问题不要调用" |
| 调错工具 | 两个描述的边界重叠 | 在 `search_notes` 里写"已知行号时请用 read_section" |
| 参数错 | 不是 description 的问题 | 去改 schema（第 3 节） |

改完，**重新 dump、重新 probe**：

```bash
cd ../w4-mcp-stdio
python3 raw_client.py --dump ../w5-mcp-http/tools_b.json
cd ../w5-mcp-http
python3 probe.py --tools tools_b.json --out after_desc.md
```

对比 `baseline.md` 与 `after_desc.md`。**如果没变好，把改动退回去**——
这不是浪费，这是证明"这句话不影响决策"，本身就是一条结论。

---

## 3. 再动 schema（30 分钟，可选但推荐）

只做一件事：把 `chapter` 改成 `enum`（15 个文件名）。

```python
# server.py 里
from typing import Literal
Chapter = Literal["week1.md", "week2.md", ..., "math.md"]

@mcp.tool()
def search_notes_tool(query: str, chapter: Chapter | None = None, k: int = 3) -> dict:
    ...
```

重新 dump → probe → `after_schema.md`。

这次要回答的是：**参数合法率变了吗？常驻 token 涨了多少？**（`probe.py` 会打印后者）

---

## 4. 接进真实宿主（40 分钟，不能砍）

前面三步是"离线测量"，这一步是"真实战场"。

```bash
cp mcp.stdio.example.json ~/.workbuddy/mcp.json   # 注意先看下面两条
```

改两个地方：

1. `command` 必须是**绝对路径**，指向 `w4-mcp-stdio/.venv/bin/python`
2. `args` 指向 `server/server.py` 的绝对路径；`env.NOTES_DIR` 指向语料目录

⚠️ 本机 `~/.workbuddy/mcp.json` 此前不存在，**字段名是按 MCP 客户端惯例推断的**，
进这一节时按官方配置文档核对一次。stdio 版不依赖 HTTP，先跑通它。

重启宿主，然后问：

```
线性回归的正规方程是什么？
```

验收点：**答案里带文件名 + 行号**。没有行号，说明它没用你的工具，或者工具返回被裁剪掉了。

> 想验证"到底调没调"，去宿主的日志/调试面板看 `tools/call`。看不到就去
> `runs/` 里找 probe 的记录——两者能对上，说明你的离线测量是可信的。

---

## 5. Streamable HTTP（可选，最安全的压缩点）

只有在时间富余时做。改法很小：`mcp.run(transport="streamable-http")`，
然后按 `mcp.json.example` 用 `url` 注册。

做完记一句：**stdio 与 HTTP 的差别在部署形态，不在能力集**。
如果你发现两者行为不一致，那多半是鉴权或会话管理的问题，不是协议问题。

---

## 6. 人工度量（20 分钟）

`probe.py` 测的是"选不选得对"，测不了"调完之后上下文涨了多少"。这一列要人工记：

```bash
cp measure.template.md measure.md
```

在真实宿主里跑那 10 个问题，每条记：调了几次工具、上下文增量 token、答案有没有出处。
**不用很精确，量级对就行。**

---

## 交付物

| 文件 | 内容 |
|---|---|
| `tools.json` / `tools_b.json` | 改动前后的 `tools/list` 快照 |
| `baseline.md` / `after_desc.md` / `after_schema.md` | 三次 probe 报告 |
| `measure.md` | 真实宿主里的 10 问度量 |
| `mcp.json`（实际是 `~/.workbuddy/mcp.json`） | 注册配置 |
| `NOTES.md` | 200 字以内 |

---

## 验收

- [ ] `probe.py` 选择正确 **≥ 8/10**，参数合法 10/10
- [ ] 误调 ≤ 1，且能指出改的是哪一句
- [ ] 真实宿主里问「正规方程」，答案带**文件名 + 行号**
- [ ] 能说出：`search_notes` 与 `read_section` 的边界在哪一句
- [ ] 能说出：这次改动让常驻 token 涨了多少（`probe.py` 的最后一行）

---

## 坑

- **一次改两处**。description 和 schema 一起动，数据就废了——W2 的 v3a/v3b 纪律，这里原样复用。
- **拿 mock 跑 probe**。mock 不会返回 `tool_calls`，永远是 `0/10`，只会浪费你的时间。
- **`~/.workbuddy/mcp.json` 写相对路径**。宿主的工作目录不是你的项目目录，server 起不来。
- **改完 description 忘了重新 dump**。`probe.py` 读的是 json 文件，不是你的 server。
  这个坑我踩过：改了半天 server，测的还是旧快照。
- **只看准确率不看误调**。10/10 里如果有 2 次误调，那在真实使用中会表现成"它老是乱查"。
- **在 description 里堆功能清单**。"可以搜索、读取、列目录"会让模型分不清何时用哪个。
