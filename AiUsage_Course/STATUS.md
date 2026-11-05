# STATUS · 进度与可调整点

> 本文件是**骨架的目录**，不是又一份计划。每周细节看各自的 `BRIEF.md`，总讲解看 `README.md`。
> 最后更新：2026-11-05（W0 完成 / W1 进行中 / W2–W8 已升级为可跑脚手架）

---

## 一、每周三件套（2026-11-05 起统一）

每个周目录现在都有三份**角色不同**的文档，照着顺序读：

| 文件 | 回答的问题 | 你什么时候读 |
|---|---|---|
| `LECTURE.md` | 为什么要有这一周？概念怎么拆？ | 开工前，一次读完 |
| `README.md` | 今天坐下先点哪条命令？ | 动手时，对着做 |
| `BRIEF.md` | 交什么、怎么算过、哪些还没定 | 定目标 / 收尾验收时 |

W0 只有 `README.md`（它本来就是动手手册），W1 是 `LECTURE + README` 的起点，
W2–W8 在 2026-11-05 补齐了这个形状。

---

## 二、进度

| 周 | 主题 | 状态 | 现在目录里有什么 |
|---|---|---|---|
| W0 | 破冰 | 已完成 | 可跑脚本 + 完整 README |
| W1 | 裸调用 | **进行中** | 讲义 + 操作手册 + 3 个可跑脚本 |
| W2 | Prompt 契约化 | 脚手架就绪 | LECTURE + README + `run.py` + schema 校验器；**v3 待写** |
| W3 | Context 预算 | 脚手架就绪 | LECTURE + README + 三策略 + `run_compare.py` + `cache_probe.py`；数据待跑 |
| W4 | MCP 协议 | 脚手架就绪 | LECTURE + README + `raw_client.py` + `notes_index.py`；**server 待写** |
| W5 | MCP 工程化 | 脚手架就绪 | LECTURE + README + `probe.py` + 10 问；**改动待做** |
| W6 | Agent 循环 | 脚手架就绪 | LECTURE + README + 循环骨架（含 3 个 TODO）+ 剧本回放 |
| W7 | 评测 | 脚手架就绪 | LECTURE + README + `run_eval.py` + `seed_evalset.py`；**evalset 待填** |
| W8 | 封装接管 | 脚手架就绪 | LECTURE + README + `audit_skills.py` + `lint_skill.py`；三级任务待做 |

「脚手架就绪」的意思是：**管道都给了，判断留给你。** 每周的 `BRIEF.md` 交付物表里
标着哪些是「已建」、哪些是「待写」——照那张表看，不用猜。

---

## 三、公共模块（W2 起共用）

| 文件 | 作用 | 被谁用 |
|---|---|---|
| `shared/llm.py` | 最小 OpenAI 兼容客户端（纯标准库）+ `.env` 自动查找 | W2–W7 全部 |
| `shared/corpus.py` | 笔记切节 / 朴素检索 / token 估算 | W2 / W3 / W4 / W6 |

自检：

```bash
python3 -m shared.llm --dry-run     # 看当前配置与请求体
python3 -m shared.corpus list       # 125 个小节 / 27.5 万字 / ≈12.4 万 token
python3 -m shared.corpus search 正规方程 --k 3
```

`.env` 查找顺序：`$LLM_ENV_FILE` → `./.env` → 课程根目录 `.env` → `w1-bare-api/.env`。
填一次，后面几周都认。

---

## 四、待定决策汇总（进每一周之前，先看这几条）

| 周 | 最该先定的一条 | 影响面 |
|---|---|---|
| W2 | provider 用真模型还是 mock（**mock 不能评质量**） | 决定 W2 全部数字有没有意义 |
| W2 | 任务是否沿用「ML 笔记出题器」 | 会带到 W6 的验收任务、W7 的 evalset |
| W3 | 语料用 5 章子集还是 15 个文件全量（全量 ≈12.4 万 token） | 决定 W4 `search_notes` 的裁剪策略 |
| W4 | server 语言 Python / Node；tool 粒度 3 个够不够 | 决定 W5 能否直接复用 |
| W5 | 是否真做 HTTP（最安全的压缩点） | 只影响 W5 自身 |
| W6 | 子 agent 本周写不写（**建议不写**） | 影响 W7 轨迹断言的粒度 |
| W7 | 20 条从 W2/W5 真实提问转，还是新写 | 决定评测是否偏袒当前实现 |
| W8 | L3 只改一个变量，改哪个 | 决定「能不能安全改不完全理解的文件」有无证据 |

---

## 五、改一处会牵动谁（调整前看这张表）

```
W1 的 NOTES.md ──> W2 的 runner、W3 的缓存实验、W7 的「跑 3 次」约定
W2 的任务/语料 ──> W3 的固定问题 ──> W6 验收任务 ──> W7 evalset
W3 的裁剪结论 ──> W4 search_notes 返回格式 ──> W5 上下文增量测量
W4 的 tool 契约 ──> W5 description 优化 ──> W6 可用工具集 ──> W7 轨迹断言
W6 的 trace ─────> W7 回放能力
W0 的 skill ─────> W8 L2 的写法
W7 的单变量纪律 ─> W8 L3 的受控改动
```

**任何一周的决策改了，顺着箭头往下检查一遍**就够了，不必重读整份计划。
更细的旋钮清单（可调什么、调大调小的后果）在 `ADAPT.md` 第 4 节。

---

## 六、三处不能砍

1. **W3 不能跳** —— 后面成本与稳定性的全部依据
2. **W5 的「接进真实 client 实测 10 问」不能砍** —— 唯一能验证 description 写得好不好的环节
3. **W8 不能跳** —— 唯一产出可复用资产的一周

补充两条（W6/W7 新增）：

4. **W6 的「找第 99 章」优雅失败实验不能砍** —— 唯一能证明终止逻辑正确
5. **W7 的「改一处前后对比」不能砍** —— 唯一一次把优化变成可验证动作

压缩方案（4 周 × 18 h）在 `README.md` 第七节；每个 `BRIEF.md` 的「可调整 / 压缩」写了该周具体怎么砍、砍了会失去什么证据。

---

## 七、事实核对（2026-11-05 现算，会随环境变化）

| 项 | 数值 | 怎么复核 |
|---|---|---|
| 笔记语料 | 15 个 md / 27.5 万字 / 125 小节 / ≈12.4 万 token | `python3 -m shared.corpus list` |
| W3 三策略（5 章子集） | A ≈46k / B ≈1.7–4.9k / C ≈0.55–0.6k token | `python3 run_compare.py --dry-run`（在 w3-context） |
| 继承的 skill | 21 个 / 3,488 行 / 常驻 ≈2,684 token / 19 个无脚本 | `python3 audit_skills.py`（在 w8-skill-pack） |
| W6 骨架的死循环样本 | 12 步 / 22,560 token（预算 20,000 却跑满） | `python3 src/agent.py --fixture fixtures/loop_trap.json` |

> 原 `README.md` 里写的「22 个 md」「18 个 skill」是 2026-11-03 的旧数，已在 v6 修正为
> 「按工具现算」的口径。数字会变，方法是稳定的：**能跑一条命令复核的，就别写死。**

---

## 八、一处待核实

`w5-mcp-http/mcp.json.example` 里的 `url` 字段是标准 MCP 客户端约定，但本机
`~/.workbuddy/mcp.json` 尚不存在，**WorkBuddy 的确切写法未经本机验证**（推断）。
进 W5 时按官方配置文档核对一次再改。stdio 版本已给出，不依赖这一点。
