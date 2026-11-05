# HANDOVER · AI_usage 骨架落地

> 本文件是**给另一个 agent 的执行说明**，不是给人读的设计稿。
> 读完之后，你只需要做第 5 节列出的动作，然后按第 8 节汇报。

---

## 0. 你的任务（一句话）

在 `/home/nileuy/Algothrim_proj` 下，建出第 4 节的目录结构与其中的**骨架文件**，使
WorkBuddy 与 DeepSeek Harness 两个宿主都能从这个仓库加载 skill。

你**不负责**写内容（学习笔记、科普稿、dbskill 正文）。骨架里的正文一律留 `TODO`，不要编。

启动指令（用户会这样对你说）：

```
读 /home/nileuy/Algothrim_proj/HANDOVER.md，按第 5 节执行，完成后按第 8 节汇报。
```

---

## 1. 环境事实（已核实，不要重新调查）

| 项 | 值 |
|---|---|
| 仓库根 | `/home/nileuy/Algothrim_proj`（已 `git init`，**零提交**，无 remote） |
| 已有目录 | `AiUsage_Course/`（8 周课程，**不要动**）、`ml-course/`（语料，**不要动**）、`.workbuddy/{memory,tmp,crash-backup}` |
| WorkBuddy 项目级 skill 目录 | `<repo>/.workbuddy/skills/`（本机其它项目 `bbFish-dev`、`AIC_cv-dev` 已在用） |
| DSH 的 skill 根 | `<repo>/.agents/skills`（rank 200），文档明确支持软链目录 |
| 两个宿主都只扫**一层**：`<name>/SKILL.md`，不支持 `a/b/SKILL.md` | |
| 两个宿主都读 `<repo>/AGENTS.md` | |
| dbskill 仓库 | 已 clone 在 `/tmp/dbskill`（只在用户本机，可能已被清理）；**你不要去 clone、不要复制它的内容** |

---

## 2. 硬约束（违反任意一条即失败）

1. **不要动** `AiUsage_Course/`、`ml-course/`、`.workbuddy/memory/`、`.workbuddy/tmp/`、`.workbuddy/crash-backup/`。
2. **不要** `git add`、`git commit`、`git push`。只允许 `git status --short` 查看。
3. **不要** 复制 `dbskill` 的任何正文进仓库；`vendor/` 必须被 `.gitignore` 忽略。
4. **不要**用 emoji，不要用「震惊 / 必看 / 颠覆 / 赋能 / 闭环」这类词。
5. **不要**创建 `skills/` 目录，也不要把 skill 放进两层以上子目录。
6. **不要**改文件名大小写或加中文名；文件名一律全小写 ASCII kebab-case。
7. **不要**在 `AGENTS.md` 里写超过 120 行。
8. **不要**编造 skill 正文；正文只写结构骨架 + `TODO`。
9. 所有新建文件用 UTF-8、LF 换行。
10. 遇到不确定的事，**停下来问**，不要猜着做。

---

## 3. 已完成的设计决策（不要重新讨论）

| # | 决策 | 一句话理由 |
|---|---|---|
| 1 | 实体 skill 放在 `.workbuddy/skills/`，不再有 `skills/` 目录 | 宿主只扫一层；"源即宿主"少一次同步 |
| 2 | DSH 通过软链 `.agents/skills -> ../.workbuddy/skills` 读取 | DSH 文档明确支持软链目录 |
| 3 | 不建 `agents/` 目录，角色写成 `role-*` skill | 两宿主都没有 agents 加载入口；skill 存盘即生效 |
| 4 | 来源用前缀编码：`tech-` / `biz-` / `role-` | 平面目录下仍能分组，且名字全局唯一 |
| 5 | `biz-*` 只放**薄壳 adapter**，正文指向 `vendor/dbskill` | dbskill LICENSE 4.1/4.4 禁止再分发 |
| 6 | `vendor/` 与 `.workbuddy/memory` 等不进 git | 合规 + 体积 |
| 7 | 不迁移 `AiUsage_Course/` | 迁移要改 16 处路径，本次不做 |
| 8 | 仓库保持 private，内容自留 | 用户决定 |

---

## 4. 目标结构

```text
/home/nileuy/Algothrim_proj/
├── HANDOVER.md                     # 本文件，完成后可删
├── README.md                       # 新建
├── AGENTS.md                       # 新建
├── STATUS.md                       # 新建
├── SKILLS.md                       # 新建（能力清单）
├── .gitignore                      # 新建
│
├── .workbuddy/
│   ├── skills/                     # 新建
│   │   ├── tech-mcp-mechanism/SKILL.md
│   │   ├── role-research-librarian/SKILL.md
│   │   ├── role-translator/SKILL.md
│   │   ├── role-business-lens/SKILL.md
│   │   ├── role-synthesis-editor/SKILL.md
│   │   ├── biz-problem-reframing/SKILL.md
│   │   ├── biz-jtbd/SKILL.md
│   │   └── biz-benchmark/SKILL.md
│   ├── memory/                     # 已存在，不动
│   ├── tmp/                        # 已存在，不动
│   └── crash-backup/               # 已存在，不动
│
├── .agents/
│   └── skills -> ../.workbuddy/skills      # 软链
│
├── docs/
│   ├── decisions.md
│   └── templates/
│       ├── SKILL.template.md
│       └── ROLE.template.md
│
├── outputs/
│   ├── technical_notes/.gitkeep
│   └── public_content/
│       ├── drafts/.gitkeep
│       └── published/.gitkeep
│
├── references/
│   ├── dbskill-manifest.yaml
│   └── glossary.md
│
├── vendor/.gitkeep                 # 被 .gitignore 忽略，只留占位
│
├── scripts/
│   ├── link-agent.sh
│   ├── new-note.sh
│   └── check.sh
│
├── AiUsage_Course/                 # 已存在，不动
└── ml-course/                      # 已存在，不动
```

---

## 5. 执行步骤

### Step 1 · 建目录

```bash
cd /home/nileuy/Algothrim_proj
mkdir -p .workbuddy/skills .agents docs/templates outputs/technical_notes \
         outputs/public_content/drafts outputs/public_content/published \
         references vendor scripts
touch outputs/technical_notes/.gitkeep outputs/public_content/drafts/.gitkeep \
      outputs/public_content/published/.gitkeep vendor/.gitkeep
```

### Step 2 · 写 `.gitignore`

文件：`.gitignore`

```gitignore
# 宿主状态（只保留 skills）
.workbuddy/*
!.workbuddy/skills/

# 依赖与缓存
.venv/
venv/
__pycache__/
*.pyc
*.pyo

# 密钥与环境
.env
.env.*
!.env.example

# 第三方正文（dbskill 许可证 4.1 / 4.4）
vendor/*
!vendor/.gitkeep

# 系统噪声
.DS_Store
Thumbs.db
*.tmp
*.swp
```

### Step 3 · 建软链

```bash
cd /home/nileuy/Algothrim_proj
ln -s ../.workbuddy/skills .agents/skills
ls -l .agents/skills
```

期望：`.agents/skills -> ../.workbuddy/skills`。
若已存在同名真实目录，**停下来问**，不要删。

### Step 4 · 写三个脚本

**`scripts/link-agent.sh`**

```bash
#!/usr/bin/env bash
# 维护 .agents/skills -> ../.workbuddy/skills 这条桥。
# 实体只在 .workbuddy/skills，链接只是让 DSH 看得见。
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p .agents
target="../.workbuddy/skills"

if [ -L .agents/skills ]; then
  rm -f .agents/skills
elif [ -e .agents/skills ]; then
  echo "错误：.agents/skills 是真实目录，先人工确认再处理" >&2
  exit 1
fi

ln -s "$target" .agents/skills
echo "已建立：.agents/skills -> $target"
ls -l .agents/skills
```

**`scripts/new-note.sh`**

```bash
#!/usr/bin/env bash
# 按规范生成文件名，杜绝手敲拼写错误。
# 用法：./scripts/new-note.sh <technical_notes|public_content> <slug>
set -euo pipefail
cd "$(dirname "$0")/.."

kind="${1:?usage: new-note.sh <technical_notes|public_content> <slug>}"
raw="${2:?slug required}"
if printf '%s' "$raw" | grep -q '[^A-Za-z0-9 -]'; then
  echo "slug 只允许 ASCII 字母、数字、空格、连字符：$raw" >&2
  exit 1
fi
slug="$(printf '%s' "$raw" | tr '[:upper:] ' '[:lower:]-' | tr -s '-' | sed 's/^-//; s/-$//')"
[ -n "$slug" ] || { echo "slug 为空" >&2; exit 1; }
day="$(date +%F)"

case "$kind" in
  technical_notes) out="outputs/technical_notes/${day}__${slug}.md" ;;
  public_content)  out="outputs/public_content/drafts/${day}__${slug}__v1.md" ;;
  *) echo "unknown kind: $kind" >&2; exit 1 ;;
esac

mkdir -p "$(dirname "$out")"
[ -e "$out" ] && { echo "已存在：$out" >&2; exit 1; }
printf '# %s\n\n> created: %s | status: draft\n\n## 一句话\n\nTODO\n' "$slug" "$day" > "$out"
printf '%s\n' "$out"
```

**`scripts/check.sh`**

```bash
#!/usr/bin/env bash
# 骨架体检：命名 / frontmatter / 层级 / 许可证边界。
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0
note() { printf '%s\n' "$*"; }
bad()  { printf '[FAIL] %s\n' "$*"; fail=1; }

# 1) skill 必须是一层目录 + SKILL.md
while IFS= read -r f; do
  rel="${f#./}"
  if ! printf '%s' "$rel" | grep -Eq '^\.workbuddy/skills/[^/]+/SKILL\.md$'; then
    bad "路径不合规（只允许一层）：$rel"
  fi
done < <(find .workbuddy/skills -name 'SKILL.md' -print 2>/dev/null)

# 2) frontmatter：name 必须等于目录名，description 非空
for d in .workbuddy/skills/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  f="${d}SKILL.md"
  if [ ! -f "$f" ]; then bad "$name 缺 SKILL.md"; continue; fi
  head -1 "$f" | grep -q '^---$' || bad "$name 缺 frontmatter"
  fm_name="$(sed -n '2,12p' "$f" | grep -m1 '^name:' | sed 's/^name:[[:space:]]*//')"
  [ "$fm_name" = "$name" ] || bad "$name 的 name 字段是 '$fm_name'，与目录名不一致"
  sed -n '2,12p' "$f" | grep -q '^description:.\+' || bad "$name 缺 description"
done

# 3) 软链
[ -L .agents/skills ] || bad ".agents/skills 不是软链（需要 scripts/link-agent.sh）"

# 4) 命名：仓库内新增文件不得含中文
git ls-files 2>/dev/null | grep -P '[\x{4e00}-\x{9fff}]' && bad "有中文文件名入库"

# 5) 许可证边界：vendor 不得入库
git ls-files 2>/dev/null | grep -E '^vendor/.+' | grep -v '^vendor/.gitkeep$' && bad "vendor/ 被提交了"

# 汇总
n=0
for d in .workbuddy/skills/*/; do [ -d "$d" ] && n=$((n+1)); done
note "skills 数量：$n"
if [ "$fail" -eq 0 ]; then note "OK"; exit 0; else note "有问题，见上"; exit 1; fi
```

写完执行：

```bash
chmod +x scripts/*.sh
```

### Step 5 · 写 `AGENTS.md`（≤120 行）

必须包含这六节，内容按下面要点写，不要扩写：

1. **这是什么仓库**：私有，单人使用；两宿主共用；不是分发物。
2. **目录约定**：`.workbuddy/skills/<name>/SKILL.md` 是唯一实体；`.agents/skills` 是软链；`outputs/` 放产出；`vendor/` 不进库。
3. **命名规范**：全小写 kebab-case；skill 目录名必须等于 frontmatter `name`；三种前缀 `tech-` / `biz-` / `role-`；产出文件名 `YYYY-MM-DD__<slug>[__v<N>].md`。
4. **事实来源优先级**：`references/` 与 `outputs/` 里的证据 > 模型记忆；不确定的标「推断」。
5. **禁区**：不复制 dbskill 正文；不把 `vendor/` 入库；不用 emoji；不用营销腔。
6. **提交前**：跑 `./scripts/check.sh`，通过再 `git status --short` 人工看一遍。

### Step 6 · 写 8 个 skill

统一规则：

- 目录名 = frontmatter `name`（前面 `check.sh` 会校验）。
- 只允许一层。
- 正文只写骨架，每节留 `TODO`，**不要编内容**。
- 角色类用 `ROLE` 骨架，能力类用 `SKILL` 骨架（见 Step 7 的模板）。

**frontmatter 取值表**（照抄，逐条替换）

| 目录 | name | description（一句话，症状式） |
|---|---|---|
| `tech-mcp-mechanism` | tech-mcp-mechanism | 当需要解释 MCP 的三类原语、initialize 能力协商，或排查「模型不调用我的工具」时用 |
| `role-research-librarian` | role-research-librarian | 当需要为一个概念收集可引用的事实与出处时用；只给带路径或链接的事实卡，不给观点 |
| `role-translator` | role-translator | 当需要把已确认的技术笔记降维成非技术读者能读的骨架时用；不适用于查资料或成稿润色 |
| `role-business-lens` | role-business-lens | 当需要给一个技术话题补一节商业或经济学解释时用；只解释机制，不做预测 |
| `role-synthesis-editor` | role-synthesis-editor | 当需要把技术笔记与商业视角合成一篇面向非技术读者的稿子并统一语气时用 |
| `biz-problem-reframing` | biz-problem-reframing | 当需要把「用户要什么功能」重新表述成「要解决什么问题」时用（adapter，指向 vendor 里的 dbskill） |
| `biz-jtbd` | biz-jtbd | 当需要判断「用户雇佣这个产品去完成什么任务」时用（adapter，指向 vendor 里的 dbskill） |
| `biz-benchmark` | biz-benchmark | 当需要把一个产品放到同类里做对标、找出差异点位置时用（adapter，指向 vendor 里的 dbskill） |

公共可选字段（每个文件都加，值照抄）：

```yaml
metadata:
  origin: self          # biz-* 写 dbskill@3.2.3
agent_created: true
```

`role-*` 额外加：

```yaml
whenToUse: 需要扮演<角色名>时
metadata:
  role: <角色中文名>
```

`biz-*` 额外加：

```yaml
metadata:
  origin: dbskill@3.2.3
  upstream_skill: dbs-<名字>
```

**`biz-*` 的正文**统一用这段（把 `<名字>` 换掉即可）：

```markdown
# 用法

1. 读 `~/AI_usage/vendor/dbskill/skills/dbs-<名字>/SKILL.md`，按其流程执行。
2. 只取结论与框架名，不复制原文段落进 `outputs/`。
3. 输出用本仓库的三段式，不用上游格式。

## 前提

`vendor/dbskill` 需在本机安装（见 `references/dbskill-manifest.yaml`）。未安装时直接说明，不要凭记忆编造框架。
```

### Step 7 · 写两份模板与其余文档

**`docs/templates/SKILL.template.md`**：含 frontmatter（name / description / metadata / agent_created）与五节正文：
`# 一句话` / `# 什么时候用、什么时候别用` / `# 输入与输出` / `# 执行步骤` / `# 判据与失败模式`。

**`docs/templates/ROLE.template.md`**：含 frontmatter（name / description / whenToUse / metadata.role）与四节正文：
`# 角色` / `# 能力` / `# 流程` / `# 边界`。

**`docs/decisions.md`**：把第 3 节的 8 条决策逐条写成「决策 / 理由 / 代价」三行小表。

**`README.md`**：六十行以内，包含：仓库定位、两宿主怎么读、三条常用命令
（`./scripts/check.sh`、`./scripts/new-note.sh`、`./scripts/link-agent.sh`）、目录速查表。

**`STATUS.md`**：进度表（8 个 skill 的 `stage` 全填 `skeleton`）、待定决策三条
（vendor 何时安装、`private` 是否长期、是否迁移课程目录）。

**`SKILLS.md`**：一张表，列为 `name / 类型 / 状态 / 关联产出`，8 行，状态填 `skeleton`。

**`references/dbskill-manifest.yaml`**：

```yaml
upstream:
  repo: https://github.com/dontbesilent2025/dbskill
  pinned_version: 3.2.3
  license_checked: 2026-11-05
  local_path: ~/AI_usage/vendor/dbskill
policy:
  commit_original_files: false
  publish_modified_version: false
  quote_original_text: false
  share_link_allowed: true
dependencies:
  shared: [shared/manifest.json, shared/references/]
adapters:
  - name: biz-problem-reframing
    targets: [dbs-diagnosis, dbs-good-question]
  - name: biz-jtbd
    targets: [dbs-jtbd]
  - name: biz-benchmark
    targets: [dbs-benchmark]
```

**`references/glossary.md`**：三列表头 `术语 / 大白话 / 一个类比`，先留 5 行 `TODO`。

`dbs-<名字>` 的对应关系：`biz-jtbd` → `dbs-jtbd`，`biz-benchmark` → `dbs-benchmark`，
`biz-problem-reframing` → 主要指向 `dbs-diagnosis`（`dbs-good-question` 作为辅助）。

### Step 8 · 自检

```bash
cd /home/nileuy/Algothrim_proj
./scripts/check.sh
find .workbuddy/skills -name SKILL.md | wc -l
git status --short | head -40
```

期望：`check.sh` 输出 `OK`，skill 数量为 `8`，`git status` 里**没有** `vendor/` 下的文件、没有 `AiUsage_Course/` 的改动。

---

## 6. 验收清单（逐条打勾后再汇报）

- [ ] `.agents/skills` 是软链，指向 `../.workbuddy/skills`
- [ ] `find .workbuddy/skills -name SKILL.md | wc -l` 输出 `8`
- [ ] 8 个目录名与各自 `name` 字段完全一致
- [ ] `./scripts/check.sh` 输出 `OK` 且退出码为 0
- [ ] `git status --short` 不含 `vendor/` 下的文件、不含 `AiUsage_Course/` 或 `ml-course/` 的改动
- [ ] `AGENTS.md` 不超过 120 行（`wc -l AGENTS.md`）
- [ ] 所有 skill 正文里没有编造的技术结论，只有骨架与 `TODO`
- [ ] 没有 emoji，没有营销词

---

## 7. 禁止事项（再强调一次）

| 不要做 | 因为 |
|---|---|
| `git add` / `commit` / `push` | 首次提交由用户决定 |
| 复制 dbskill 的 SKILL.md 正文 | 许可证 4.1 禁止再分发 |
| 安装 dbskill（`npx skills add`） | 需要网络，且由用户手工完成 |
| 修改 `AiUsage_Course/` 里的任何文件 | 那是另一条工作线 |
| 创建 `skills/`、`agents/` 目录 | 已废弃，会造成两条真相 |
| 把 skill 放进二级目录 | 两个宿主都只扫一层 |
| 用中文文件名 | 跨平台与 tab 补全问题 |
| 自己决定新增文件 | 先问 |

---

## 8. 汇报格式

完成后，用下面格式回复，不要贴大段文件内容：

```
完成情况：<全部完成 / 部分完成>
已创建：<文件数> 个文件，<目录数> 个目录
自检：
  check.sh   -> <OK / FAIL: 原因>
  skill 数   -> <n>
  git status -> <干净 / 列出了 n 条，主要是 ...>
偏离说明：<没有 / 哪一条为什么偏离>
待用户决定：<最多三条，例如 vendor 何时安装>
```

---

## 9. 卡住时

按这个顺序处理，不要猜：

1. 某个文件已存在且内容不同 → 停下来问，不要覆盖。
2. `ln -s` 失败 → 记录错误原文，停下来问（不要退化成复制）。
3. `check.sh` 报错但你看不懂 → 把命令与完整输出贴出来。
4. 需要联网（装 dbskill、push）→ 一律停下，交给用户。
