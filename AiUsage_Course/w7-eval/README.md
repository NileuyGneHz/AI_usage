# W7 · 评测与回归 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
本周产物是**两份报告 + 一句话结论**，不是测试框架。

---

## 0. 骨架（3 分钟）

```
w7-eval/
├── evalset.jsonl           # 20 条（seed 脚本生成 10 条骨架，你再补 10 条）
├── seed_evalset.py         # 把 W5 的 10 个真实提问转成 evalset 起点
├── run_eval.py             # 三层断言 + 报告；支持 --run / --replay / --dry-run
├── report.template.md      # 人工结论表（官方模板）
└── runs/                   # 临时 trace（每次跑自动生成）
```

`run_eval.py` 直接 import W6 的 `agent.py`。**你改 W6 的函数签名，这里也会跟着坏**——
这不是设计缺陷，是"自己维护自己的工具链"的第一课。坏了就修，两行的事。

---

## 1. 造一个起点（10 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w7-eval
python3 seed_evalset.py
```

它会读 `../w5-mcp-http/questions.md`，生成 10 条骨架：7 正例 + 3 负例，
`must_call` 已按期望工具填好，`must_include` **留空**（那是你的活）。

---

## 2. 补 `must_include`（40 分钟，本周最累）

每条的判据：**2–4 个关键事实**，不是整句答案。

```json
"must_include": ["正规方程", "X^T X", "不可逆"]
```

判据要满足两个条件：

1. 正确答案**一定**包含它（否则假红）
2. 错误答案**通常不**包含它（否则测不出东西）

> 别写 `"必须"` 这种太常见的词，也别写一整句公式——模型换个写法就假红。

再补 10 条自己的。建议分布：

| 类型 | 条数 | 例子 |
|---|---|---|
| 真实提问（W5 转） | 7 | 已生成 |
| 负例 / 越界 | 3 | 已生成 |
| **多步任务** | 4 | "读 6.2 节 → 出 3 题 → 自查" |
| **歧义 / 材料未覆盖** | 3 | "讲讲第 99 章"、"解释一下 SVM"（笔记里没有） |
| **格式边界** | 3 | "用表格列出三种梯度下降变体" |

---

## 3. 先验格式，不花钱（2 分钟）

```bash
python3 run_eval.py --dry-run
```

会打印分布、格式问题、以及 **"假绿"警告**（`must_include` 为空的那几条）。
把警告清零再往下走——不然你跑出来的全绿是假的。

---

## 4. 跑基线（20–40 分钟，要花钱）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course
python3 -m shared.llm          # 先确认通道
cd w7-eval
python3 run_eval.py --run --label baseline
```

每条会打印 `[RtN]` 三面小旗：大写=通过，小写=失败。

```
E01   [RTn] 4步 3201tok  漏调 ['search_notes']
```

跑完看 `report_baseline.md`：

- **全绿几条**（这是你的起点，不要期待 20/20）
- **结果 / 轨迹 / 负例** 三层分别几条
- 失败分类表里，哪一类最多

**先别修。** 先把失败分类抄进 `report.template.md`。

---

## 5. 改一处，再跑（30 分钟）

选一个**轨迹层**失败（最有价值的那种），只改一处：

| 失败 | 改什么 | 改在哪 |
|---|---|---|
| 漏调 | description 的"什么时候用"写具体 | `w6-agent-loop/src/tools.py` |
| 多调 | 加"什么时候别用" | 同上 |
| 步数超 | `max_steps` 或裁剪策略 | `w6-agent-loop/src/agent.py` |

```bash
python3 run_eval.py --run --label after_desc
```

并排看两份报告：

```bash
diff <(sed -n '1,40p' report_baseline.md) <(sed -n '1,40p' report_after_desc.md)
```

预期：**轨迹层变好，结果层基本不动**。如果结果层也变了，说明你改动的不止一处。

---

## 6. 换模型（可选，20 分钟）

```bash
LLM_MODEL=<小模型名> python3 run_eval.py --run --label small_model
```

这一组的意义是给你一个**成本-质量的对照点**，报告里那句结论就靠它。

---

## 7. 回放（不花钱，验证 trace 可用）

```bash
python3 run_eval.py --replay runs --label replay_check
```

它只验轨迹层（trace 里没有最终答案）。用途：确认你的 trace 格式**足够**支撑断言。
如果回放时断言不出东西，说明 W6 的 trace 字段不够——现在补还来得及。

---

## 8. 写结论（20 分钟）

打开 `report.template.md`，把三组数据填进去，然后用计划里那个句式写一句话：

> 换 ___ 后通过率从 __/20 变成 __/20，掉的是「____」那几条，成本变化 __%，
> 我选择 ____，因为 ____。

**这句话就是本周的唯一产出。** 表是工具给的，判断只能你写。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `evalset.jsonl` | 20 条，`must_include` 全部填好 |
| `report_baseline.md` / `report_after_*.md` | 至少两份 |
| `report.template.md` → 填完 | 三组对比 + 失败分类 + 一句话结论 |
| `runs/*.jsonl` | trace 存档 |
| `NOTES.md` | 200 字以内 |

---

## 验收

- [ ] 20 条里至少 3 条是"当前一定失败"的（用来标定天花板）
- [ ] 报告分三层记分，不是只报总分
- [ ] 至少一条失败是**轨迹层**的，且你能说清修在哪
- [ ] 能用计划里那个句式说出一句完整结论
- [ ] 能说出这套 evalset **测不到**什么

---

## 坑

- **`must_include` 写整句**：模型换个措辞就假红。写关键词。
- **只跑 1 次**：随机性会把 17/20 变成 14/20。`--repeat` 在 `run_eval` 里没有，
  正确做法是跑三次 `--label r1/r2/r3` 再取均值（或自己在脚本外加循环）。
- **一边改 prompt 一边改 evalset**：你在给自己出符合答案的题。**evalset 先冻结**。
- **只测 happy path**：20 条全是"能答对"的题，跑出 20/20 也说明不了什么。
- **忽略 `--dry-run` 的假绿警告**：`must_include` 空的条目会让结果层永远绿。
- **拿 mock 跑评测**：mock 不返回 `tool_calls`，轨迹层会全红，纯浪费时间。
