# W2 · Prompt 契约化 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约与待定决策在 [`BRIEF.md`](BRIEF.md)。
本文件只回答一件事：**今天坐下来，按顺序点哪些命令。**

目标不是"写出一个好 prompt"，是**用 10 条固定输入，把三个版本量出差距**。

---

## 0. 先看骨架（2 分钟）

```
w2-prompt/
├── cases.jsonl              # 10 条固定输入（章节定位），已备
├── prompts/v1.txt           # 自然语言版，已备
├── prompts/v2.txt           # 五槽位版，已备
├── prompts/v3.template.txt  # v3 骨架，5 处「待填」← 你的活
├── schema/cards.schema.json # 唯一判分尺子（三版共用）
├── schema_check.py          # 极小 JSON Schema 校验器，可单独跑
├── run.py                   # 管道：渲染 / 请求 / 判分 / 出报告
└── runs/                    # 每次运行的明细（自动生成，别删）
```

关键是 `run.py` 已经**替你写好管道，但没有替你写 v3**。这个分工不是偷懒：
管道是可复用的，判断才是本周要长出来的东西。

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w2-prompt
```

---

## 1. 零成本：先看渲染结果（5 分钟）

```bash
python3 run.py --dry-run --only v1
```

你会看到 v1 渲染后的完整 prompt，以及一个 token 估算。做两件事：

1. 确认 `{heading}` / `{content}` 都被替换掉了（模板里没有残留花括号占位符）
2. 记下 token 量级——它是你 tok 预算的基准

再看 v2:

```bash
python3 run.py --dry-run --only v2
```

**对比两份渲染结果的长度差**。v2 长出来的部分全是契约，没有一句是废话。这就是本周
第一次"看见"契约化的成本。

---

## 2. 没 key 也能跑：用 W1 的 mock 验管线（10 分钟）

```bash
# 终端 A
cd ../w1-bare-api && python3 mock_server.py

# 终端 B
cd ../w2-prompt
python3 run.py --only v1 --limit 2
```

**预期结果：2 条全是「JSON 不合法」。**

这不是 bug，是 mock 的固定回答本来就是一段中文说明。它证明了两件事：
判分器真的在工作；**mock 不能用来评质量**——三版在它面前都会一样烂。

这一步的目的只有一个：确认"取语料 → 渲染 → 请求 → 判分 → 出报告"这条链路通。

---

## 3. 换成真模型（准备好再走）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course
cp w1-bare-api/.env.example .env    # 填 LLM_API_KEY（DeepSeek 充 10 元够八周）
# .env 放在课程根目录，W2–W7 所有脚本都会自动找到它
```

自检：

```bash
python3 -m shared.llm
```

看到回答就说明通道好了。然后先小样本试水：

```bash
cd w2-prompt
python3 run.py --only v1 --limit 3
```

第一次真跑会给你一个基线：v1 的合规率大概是 3/10 到 7/10 之间（取决于模型）。
**记住这个数**，它就是你后面两版要打败的对手。

---

## 4. 写 v3（本周真正的活，1–2 小时）

```bash
cp prompts/v3.template.txt prompts/v3.txt
```

打开 `v3.txt`，五处「待填」逐条填。填之前先回答模板里夹着的三个问题：

1. 为什么字段清单要从正文搬进 schema？（提示：正文是给模型看的，schema 是给**解码器**看的）
2. 你 W1 亲眼见过的那个失败形态是什么？把它写成负例。
3. 任务段和 v2 **一字不改**——你能做到吗？做不到，说明你其实还在改任务。

填完先 dry-run，确认没有残留「待填」：

```bash
python3 run.py --dry-run --only v3 | head -40
```

然后跑：

```bash
python3 run.py --only v3
```

`--format auto` 会先试 `json_schema`，服务商不认就自动降级成 `json_object` 并在结果里
标 `(降级)`。**看一下你的报告里有没有降级**——如果有，说明你实际测的是 json_object，
v3 的"schema 约束"这一半根本没生效。这个坑很深，报告里那一列就是为它准备的。

---

## 5. 三版一起跑，出报告（15 分钟）

```bash
python3 run.py --repeat 3
```

10 条 × 3 次 × 3 版 = 90 次调用。用 DeepSeek 大约几分钱，慢的话十几分钟。

输出 `report.md`，长这样：

| 版本 | 合规 | 拒答 | 坏 JSON | 坏结构 | 合规率 | 平均 input | 平均 output | 平均延迟 |
|---|---|---|---|---|---|---|---|---|

**读表的三条规矩**：

1. 先看 `坏 JSON` 与 `坏结构` 的**比例**，别只看合规率总数——它们修法不同。
2. 再看 token：v3 相对 v1 涨了多少？涨的部分买到的是"确定性"，值不值由你判断。
3. 最后才看内容可用率（这一列得你自己填进 `report.md` 的归因段）。

---

## 6. 有余力：拆 v3a / v3b（推荐）

v3 同时动了两个变量（schema + 负例），所以你现在**无法归因**。二十分钟就能补上：

```bash
cp prompts/v3.txt prompts/v3a.txt   # 只留 schema，负例段清空
cp prompts/v3.txt prompts/v3b.txt   # 只留负例，去掉 response_format（用 --format none）
python3 run.py --only v3a
python3 run.py --only v3b
```

| 版本 | 变量 | 合规率 |
|---|---|---|
| v2 | 基线 | |
| v3a | 只加 schema | |
| v3b | 只加负例 | |
| v3 | 两个都加 | |

这张表就是 W7 单变量回归的预演。**如果 v3 没有明显好于 v3a 和 v3b 中较强的那个，
说明两个改动互相抵消了**——这种情况比你想象的多。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `prompts/v3.txt` | 填完的五槽位 + schema + 负例 |
| `report.md` | 由 `run.py` 生成，**归因段必须你亲手写** |
| `runs/*.jsonl` | 原始明细，别删（W7 会需要真实失败样本） |
| `NOTES.md` | 200 字以内：失败什么样、成本在哪、别人会卡在哪 |

---

## 验收

- [ ] v3 合规 **10/10**（`report.md` 第一行就是证据）
- [ ] 总 token **≤ v1 的 1.5 倍**
- [ ] 能指着失败明细说清：这条是格式失败还是结构失败，该改哪一槽
- [ ] 做了消融（至少 v3a 或 v3b 其一），能说出"负例/schema 各值多少"

---

## 坑

- **`--dry-run` 没跑就先花钱**。渲染错了（比如 `{content}` 没替换）会白跑 90 次。
- **三个版本用不同温度**。这是最常见的"不可比"，报告里温度只显示一次，改了就骗自己。
- **只跑 1 次就下结论**。模型有随机性，W1 实验 2 已经证过；`--repeat 3` 是下限。
- **报告只有表没有归因**。表是 `run.py` 给的，归因只能你写；没有归因，这周等于没做。
- **`report.md` 被覆盖**。每次跑都会覆盖同名文件，想留档就 `--out report_v1.md`。
- **把 mock 的数字当真**。mock 忽略 prompt，三版在它面前没有区别。
