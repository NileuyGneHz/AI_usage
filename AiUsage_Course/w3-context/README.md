# W3 · Context 预算 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
本周产出**不是代码，是一张有数字的表**。

---

## 0. 骨架（3 分钟）

```
w3-context/
├── questions.md          # 5 个固定问题 + 判分标准（改一条，数据全废）
├── strategies/
│   ├── a_full.py         # A 全文塞入
│   ├── b_retrieve.py     # B 检索 top-k（默认整节）
│   └── c_compress.py     # C 检索 + 抽取式压缩
├── run_compare.py        # 三套 × 5 问，记账出表
├── cache_probe.py        # 前缀缓存实验
├── report.template.md    # 三角对比表 + 拐点表（人填）
└── runs/                 # 每次运行的明细（含完整材料，别删）
```

三套策略的 `build()` 签名一致：`build(question, scope, k, budget) -> {messages, meta}`。
**想加第四套策略，写一个同签名的模块就行**，runner 不用动——这是刻意的设计，
因为你这周真正会想试的是"k 取 5 会怎样""压缩到 300 字会怎样"。

---

## 1. 先算账，不花钱（5 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w3-context
python3 run_compare.py --dry-run
```

看两件事：

1. A 的材料量是 B 的多少倍、C 的多少倍
2. `--scope all` 时 A 会不会超预算

```bash
python3 run_compare.py --dry-run --scope all
```

**如果这一步你已经惊讶了，说明你已经懂了 60%。**

---

## 2. 跑三套（需要 key，约 5 分钟）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course
python3 -m shared.llm        # 确认通道；不行先回去配 .env
cd w3-context
python3 run_compare.py --scope subset
```

5 问 × 3 套 = 15 次调用。DeepSeek 上大概几分钱。

跑完会打印：

```
策略                次数    平均input    平均output      平均延迟
A 全文塞入            5      46,3xx          3xx          8s
B 关键词检索          5       2,9xx          3xx          3s
C 检索+压缩           5         5xx          3xx          2s
```

**注意 A 的延迟**。它不只是贵，它慢——因为服务端要处理 4.6 万 token 的输入。
在 agent 场景里（W6），这个延迟会被乘以步数。

---

## 3. 人工判分（30 分钟，这周最累的部分）

打开 `questions.md`，把 5 题 × 3 套的答案逐条判分（2/1/0）。

纪律：**按题号横向判，不要按策略纵向判**。先判完 Q1 的三套，再判 Q2。
纵向判会不自觉地给后判的那套抬分。

判完把得分填进 `questions.md` 的表格，合计满分为 10。

---

## 4. 拐点实验（15 分钟）

```bash
python3 run_compare.py --scope all --force
```

- `--force` 是故意的：不拦你，让你亲眼看到"发出去的 token 数"和"窗口上限"撞车的样子
  （也可能只是很慢很贵——两种结果都是结论）
- 如果 provider 直接报错（超过上下文），**把错误原文抄进 report**，这比任何解释都有力

把 5 章与全量两行的 token 数填进 `report.template.md` 的拐点表。

---

## 5. 前缀缓存实验（10 分钟）

```bash
python3 cache_probe.py
python3 cache_probe.py --timestamp
```

两次对照，回答三个问题（脚本末尾会再问一遍）：

1. 第二次的哪个字段变小了？
2. 加时间戳后它还小吗？
3. 你写的 system 里，哪些内容该放前面、哪些必须挪到最后？

> mock 不实现缓存，字段一定是平的——这本身也是个结论：**缓存是服务商行为，不是协议行为**。

---

## 6. 扫 k（可选，20 分钟）

```bash
python3 run_compare.py --strategies b,c --k 5
python3 run_compare.py --strategies b,c --k 1
```

记录：k 变大时 token 怎么涨、正确率怎么变、有没有出现"多召回的段落反而干扰答案"。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `runs/*.jsonl` | 每次运行的完整记录（含材料原文，W4/W7 会用） |
| `questions.md` | 填完的人工得分表 |
| `report.template.md` → `report.md` | 三角对比表 + 拐点表 + 结论三问 |
| `NOTES.md` | 200 字以内 |

---

## 验收

- [ ] `report.md` 里三套策略的 token 是**实测值**（来自 usage），不是估算
- [ ] 能一句话说清：**在我的语料规模下哪套最优，为什么**
- [ ] 能说出拐点：语料涨到多少、或问题变成什么类型时，该换策略
- [ ] 能给出 W4 `search_notes` 的返回规格（字数 / 条数 / 是否带行号），并有数据支撑
- [ ] `cache_probe.py` 两组数据都看过，能解释时间戳为什么毁缓存

---

## 坑

- **C 比 B 还贵**。如果你把 `MAX_CHARS` 调大、或 B 用片段裁剪，C 可能不再便宜。
  那时候的正确结论是"压缩在这个规模下没有收益"，不是"我实现错了"。
- **硬截断切断句子**。`out[:max_chars]` 会把一句话劈成两半，去 `runs/*.jsonl` 里搜一下
  `material`，看有没有。修法：按句边界截断。
- **只判总分不看错因**。5 题里错了哪题、错在检索没召回还是模型没理解，这一列比总分重要。
- **拿 mock 的延迟当真**。mock 是本地进程，延迟≈0，没有参考意义。
- **把 A 跑全量当"有毅力"**。如果 provider 报超限，那是正确结果，不是失败；记下来。
