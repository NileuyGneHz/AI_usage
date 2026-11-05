# W8 · 封装与接管 — 操作手册

先读 [`LECTURE.md`](LECTURE.md)。任务契约在 [`BRIEF.md`](BRIEF.md)。
三级任务，**前一级不过不进入下一级**：L1 读 → L2 写 → L3 改。

---

## 0. 骨架（3 分钟）

```
w8-skill-pack/
├── audit_skills.py        # L1：扫描一批 skill，出行数/脚本/常驻成本/标记
├── lint_skill.py          # L2/L3：给单个 skill 做体检（含硬规则）
├── skill-src/SKILL.template.md   # 写新 skill 的起点
├── review.template.md     # L1 五问 + L3 受控改动记录
├── scenarios.template.md  # 5 个场景（3 命中 + 2 不该命中）
├── dist/                  # 加分项：可分发包
└── NOTES.md
```

---

## L1 · 读（2 小时）

### 1. 先看账

```bash
python3 audit_skills.py
```

你会看到 21 个 skill、3,488 行、**常驻约 2,684 token**。这个数字是"负债"的量化：
每次请求都在付，和你用不用无关。

### 2. 挑两个极端样本

```bash
wc -l ~/.workbuddy/skills/nuedc-topic-research/SKILL.md        # 60 行
wc -l ~/.workbuddy/skills/rm-nav-dev-push-decision/SKILL.md     # 371 行
```

各读一遍，**读的时候手里拿一支笔**，把每一条"照这个命令敲"的句子标出来。

### 3. 回答五问

```bash
cp review.template.md review.md
```

五问里最容易糊弄过去的是第 4、5 问。给个提示：

- 第 4 问"你怎么判断它过期了" → 找**断言点**：`test -d`、`command -v`、`--version`、
  输出字段名。找不到断言点的句子，就是最容易沉默失败的那句。
- 第 5 问"能定位到哪一句" → 如果它执行错了，你是靠日志、靠行号、还是只能靠猜？

**验收：五问里每条答案后面都得跟一个行号或原句引用。** 没有证据的答案不算。

### 4. 顺手用 lint 看一眼

```bash
python3 lint_skill.py ~/.workbuddy/skills/nuedc-topic-research
python3 lint_skill.py ~/.workbuddy/skills/rm-nav-dev-push-decision
```

注意：**lint 不通过不代表这个 skill 是坏的**，只代表它不符合"可维护"的形状。
用它来校准你的判断，而不是当作判决。

---

## L2 · 写（4 小时）

### 1. 选题

必须满足三条：**你每周都在做、步骤 ≥5、每次都得想一下顺序**。

候选（从你的实际生活里挑一个）：

- 提交前的工作区检查（漏 add、误提交大文件、message 为空）
- 洛谷题解归档（命名、目录、README 索引）
- Lumerical / ROS 2 项目的仿真脚本排错

> 不要选"看起来高大上"的题。**选你做得最多、最烦、最容易漏一步的那件事。**

### 2. 写

```bash
mkdir -p skill-src/<your-skill>/scripts
cp skill-src/SKILL.template.md skill-src/<your-skill>/SKILL.md
```

三个硬要求：

| 要求 | 为什么 |
|---|---|
| 正文 ≤120 行 | 命中后一次性进上下文，超了就是 W3 说的成本失控 |
| ≥1 个 `scripts/` | 模型执行 1 个脚本，比执行 10 行命令可靠 |
| description 写症状 | 它决定召回率，写功能简介等于隐形 |

脚本的要求：能独立跑、有退出码、输出可读（人看得懂，模型也看得懂）。

### 3. 体检

```bash
python3 lint_skill.py skill-src/<your-skill>
```

错误清零。警告可以留一条，但要知道为什么留。

### 4. 测命中率（比写更难）

```bash
cp scenarios.template.md scenarios.md
```

装进 `~/.workbuddy/skills/`（或你的宿主要求的目录），**开新会话，不提 skill 名字**，
只描述你遇到的问题。

- 3 条该命中的 → 至少命中 3 条（计划要求 ≥4/5 含负例）
- 2 条不该命中的 → **一条都不许误触发**

没命中就改 `description`，把症状写得更像你的原话。反复三四轮。
这个手感（description 决定召回）是写 skill 最核心的技能，比正文写法重要十倍。

---

## L3 · 改（2 小时）

挑一个 AI 写的 skill（**建议 `rm-nav-dev-push-decision`**，它标记最多），做一次受控改动：

| 选项 | 改什么 | 观察什么 |
|---|---|---|
| A | 只改 `description` | 5 个场景的命中/误命中变化 |
| B | 只把长案例拆进 `references/` | 加载后一次性进上下文的字数变化 |

**一次只能动一个变量。** 改完用同一张 `scenarios.md` 复测，填进"改动—复测"表。

验收的关键一句：**你能指出差异来自哪一句改动**。指不出来，说明这次改动不可归因，
等于没做。

---

## 加分项：打包（时间够再做）

把 W4–W7 的产物（MCP server + 评测集 + agent）打包成 `dist/`，写一个 20 分钟能跑完的
README，让一个没参与的同学独立跑通。

**不要在旁邊解释。** 他卡住的地方，就是你的文档缺的那一句。

---

## 交付物

| 文件 | 内容 |
|---|---|
| `review.md` | L1 五问（带行号证据） |
| `skill-src/<your-skill>/` | L2 成品：SKILL.md + scripts/ |
| `scenarios.md` | 5 场景 + 命中结果 + L3 前后对比 |
| `NOTES.md` | 200 字以内 |
| `dist/`（可选） | 加分项 |

---

## 验收

- [ ] `audit_skills.py` 跑过，能说出 21 个 skill 的常驻成本量级
- [ ] L1 五问每条都有行号/原句证据
- [ ] L2 `lint_skill.py` 通过，正文 ≤120 行，≥1 个脚本
- [ ] 5 个场景命中 ≥4/5，且两条"不该命中"零误触发
- [ ] L3 改动前后数据都在，能指出差异来自哪一句

---

## 坑

- **description 写成功能简介**（"用于 ROS2 调试"）。这是最常见、也最致命的错。
- **正文写成教材**（"ROS 2 的 QoS 有几种"）。手册写的是**判断顺序**，不是知识。
- **脚本写得太聪明**。它要能独立跑、失败有明确退出码，不要依赖对话上下文。
- **5 个场景全是该命中的**。没有负例，你测不出误召回——而误召回比漏召回更烦人。
- **L3 一次改两个变量**。改了 description 又拆了 references，差异就归因不了。
- **只信 `lint_skill.py`**。它只查形状，不查有用性；有用性只能靠 5 个场景。
