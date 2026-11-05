# W6 · 手写 Agent 循环 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
**本周不许引入任何 agent 框架。** 顺序：先跑通剧本 → 再看它翻车 → 再补三个 TODO → 最后接真模型。

---

## 0. 骨架（3 分钟）

```
w6-agent-loop/
├── src/
│   ├── agent.py        # 主循环（能跑，但故意缺三样东西 ← 你的活）
│   ├── llm_client.py   # RealModel（真模型） + ScriptedModel（剧本回放）
│   ├── tools.py        # 三个工具 + execute()，错误走 {"error","hint"}
│   └── trace.py        # 每步一行，W7 直接读它
├── fixtures/
│   ├── good_run.json   # 3 轮正常剧本：搜 → 读 → 答
│   └── loop_trap.json  # 10 轮死循环剧本：用来暴露没有预算检查的后果
└── trace/              # 每次运行的 jsonl
```

`ScriptedModel` 是本周最值得注意的设计：它让**模型这一侧变成确定的**。
调循环逻辑时，你不再需要区分"是模型抽风还是我写错了"——这个问题会消耗掉你一半的时间。

---

## 1. 零成本跑通（5 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w6-agent-loop
python3 src/agent.py --fixture fixtures/good_run.json
```

预期：

```
[step 1] 模型返回：1 个 tool_call  累计 token=758
[step 2] 模型返回：1 个 tool_call  累计 token=1783
[step 3] 模型返回：0 个 tool_call  累计 token=3499
退出原因 : model_done
```

打开 `trace/<时间戳>.jsonl`，逐行看：`event / step / tool / args / result_digest / tokens`。
**这就是 W7 要读的东西**，先熟悉它的形状。

---

## 2. 看它翻车（5 分钟，本周最重要的一步）

```bash
python3 src/agent.py --fixture fixtures/loop_trap.json --quiet
```

预期：

```
退出原因 : max_steps
步数     : 12
累计token: 22560  (超预算 2560)
```

三条信息同时出现，正好对应三个 TODO：

1. **超预算了还在跑** → TODO 1（预算检查）
2. **12 步里每步都在塞更多工具结果** → TODO 2（裁剪）
3. **退出只告诉你 max_steps，说不清它想干嘛** → TODO 3（状态外置）

**先别改代码。** 把这三个现象抄进 `NOTES.md`，再动手——这周的价值在于你能描述问题，
不在于你能写循环。

---

## 3. 补 TODO 1：预算 + 退出原因（20 分钟）

在 `agent.py` 里 `# TODO 1` 那行，做三件事：

```python
if spent > TOKEN_BUDGET:
    return {"answer": None, "steps": step, "tokens": spent,
            "reason": "budget_exceeded", "last_tool": name}
```

- 位置：**每步结束**检查，不是循环开头（否则会多跑一步）
- 原因：要和 `max_steps` 区分开，W7 才能分别断言
- 附带：记录 `last_tool`，人看 trace 时才不用翻十行

改完再跑 `loop_trap`，预期变成：

```
退出原因 : budget_exceeded
步数     : 11
```

**如果步数没变，说明你检查的位置不对。** 这种"差一步"的 bug，trace 一眼就能看出来。

---

## 4. 补 TODO 2：裁剪工具结果（30 分钟）

现在每步都 append 完整 `result`。改成"摘要 + 定位"：

```python
messages.append({
    "role": "tool",
    "tool_call_id": call["id"],
    "content": json.dumps(compact(result), ensure_ascii=False),
})
```

`compact()` 你自己写。两个参考方向（都试一下，看 token 差多少）：

| 方案 | 回什么 | 预期效果 |
|---|---|---|
| 温和 | 原样，但 `snippet` 截到 120 字 | token 降 30%，行为基本不变 |
| 激进 | 只回 `file` / `start_line` / `end_line` / 标题 | token 降 70%，但模型会更频繁调 `read_section` |

**跑完对比 `good_run` 的累计 token**：3499 是基线。降了多少？答案质量变了吗？

这就是 W3 的那笔账，在 agent 场景里重演一遍。

---

## 5. 补 TODO 3：状态外置（40 分钟）

在 `run()` 里维护一个 dict，并在每步更新：

```python
state = {"goal": question, "plan": [], "done": [], "facts": {}, "budget": {"spent": 0, "limit": TOKEN_BUDGET}}
```

硬要求（W7 会检查）：

- 每次工具调用后，把"我得到了什么"写进 `facts`（带 `file:行号`）
- 每步往 `trace` 里加一行 `event="state"`，内容是这个 dict 的快照
- 退出时把 `state` 一起返回并落盘

**验证方式**：拿 `trace` 里的 state 快照，能不能仅凭它复述"它做到哪一步、下一步打算干什么"？
不能，说明状态还是虚的。

---

## 6. 接真模型（20 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course && python3 -m shared.llm   # 确认通道
cd w6-agent-loop
python3 src/agent.py --real --question "6.2 节的假说表示是什么意思？"
```

跑通之后做计划里那道验收任务（多步）：

> 读一章笔记 → 找 2 个核心公式 → 生成 3 道题 → 自查答案与笔记是否一致 → 输出 markdown

把它写成 `--task formulas` 之类的模式也行，直接改 `--question` 也行。
**要求：≤120 行（不含工具实现），带 `max_steps` 与 token 预算，超限有明确退出原因。**

---

## 7. 优雅失败实验（20 分钟，不能砍）

```bash
python3 src/agent.py --real --question "找第 99 章的内容。"
```

判定标准（三条都要满足）：

- [ ] 在有限步内停下（`reason` 不是 `max_steps`）
- [ ] 明确说"没有这一章 / 材料未覆盖"，**没有编造**
- [ ] `trace` 里能看到它试过 `list_chapters` 或 `search_notes`，且没有重复同样的调用

只要出现"空转到 12 步"或"编出一章内容"，就回去改终止逻辑和错误提示，别改 prompt 措辞。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `src/agent.py` | ≤120 行，三个 TODO 全部补完 |
| `trace/*.jsonl` | 至少 3 份：good_run、loop_trap（改后）、真模型任务 |
| `NOTES.md` | 200 字以内：失败长什么样、成本在哪、别人会卡在哪 |

---

## 验收

- [ ] `loop_trap` 现在以 `budget_exceeded` 停下，步数 < 12
- [ ] `good_run` 的累计 token 比基线（3499）低，且答案没变差
- [ ] `state` 快照能独立复述"做到哪、下一步"
- [ ] 「找第 99 章」优雅失败，三条全过
- [ ] `agent.py` ≤120 行（不含 `tools.py`）

---

## 坑

- **assistant 消息没带 `tool_calls` 就 append**：下一轮 `tool_call_id` 对不上，模型会开始胡言乱语。
- **`tool` 消息的 `tool_call_id` 写成工具名**：协议要求是 `call_xxx` 那个 id，不是 `search_notes`。
- **一次返回多个 `tool_calls` 时只处理第一个**：剩下的 id 永远没有对应回填，下一轮直接报错。
- **预算检查放在循环开头**：会多跑一步，正好在你最想省钱的时候多花一次钱。
- **裁剪裁到模型没法继续**：只回行号不给内容，它会反复 `read_section`，反而更贵。
- **用框架"省事"**：你会在 W7 发现，所有断言都得穿透框架的抽象去拿 trace，比手写还慢。
