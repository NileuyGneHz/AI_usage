# 双宿主技能结构（WorkBuddy + DeepSeek Harness）

> 适用版本：WorkBuddy（codebuddy CLI，2026-11）、dsh 0.2.x。
> 结论全部来自 2026-11-05 在一台 Linux/Windows 双系统机上的实测；标「推断」的地方没有源码或日志佐证，用之前先验一次。
> 目的：换任何工程，照第 4 节五步走，就能让两边的 agent 都调得到同一份技能。

---

## 0. 三十秒版

| 问题 | 答案 |
|---|---|
| 技能内容放哪 | 工程内 `skills/<name>/SKILL.md`，这是唯一事实来源 |
| WorkBuddy 怎么看到 | 在 `~/.workbuddy/skills/` 建一条**软链**指向它 |
| DSH 怎么看到 | 工程根 `.agents/skills` 一条软链，指向同一批目录 |
| 能不能只靠仓库内目录 | **不能**。两个宿主都不扫工程内 `.workbuddy/skills/` |
| 有没有注册 API | 没有。放软链就是全部动作 |

---

## 1. 两个宿主各自枚举哪里

```
WorkBuddy（已证实）
  ~/.workbuddy/skills/<name>/SKILL.md     ← 唯一被证实的加载根
  ~/.workbuddy/plugins/cache/...          ← 已安装插件里的 skills（走 SkillExtensionLoader）
  ⨯ <workspace>/.workbuddy/skills/        ← 不枚举（2026-11-05 两次实测）

DeepSeek Harness（文档写明）
  <projectRoot>/.dsh/skills        rank 100
  <projectRoot>/.agents/skills     rank 200   ← 推荐用这个
  <customSkillDirs>                rank 300
  <dshHome>/skills                 rank 400   （≈ ~/.dsh/skills）
  <agentsHome>/skills              rank 500   （≈ ~/.agents/skills）
```

两条关键差异，直接决定结构：

| | WorkBuddy | DSH |
|---|---|---|
| 作用域 | **全局**（所有工程共享） | **按工程**（projectRoot = 最近的 `.git` 祖先） |
| 同名冲突 | 全局唯一命名空间 | 按 rank 覆盖，低 rank 优先 |
| 软链 | 跟随（已证实） | 跟随（文档明写：符号链接目录按普通文件处理） |
| 层级 | 只扫一层 | 只扫一层，**明确不支持嵌套 `**/SKILL.md`** |
| 热更新 | 监听目录，建链后当前会话即可用（对方实测） | 监听目录，增删改名无需重启 |
| 清单文本 | 系统提示里的 `<available_skills>` 是**启动快照** | 同属快照类行为 |

---

## 2. 推荐结构

```
<repo>/
├── skills/                        # 唯一事实来源，平铺一层
│   ├── my-deploy/SKILL.md
│   │   ├── scripts/               # 确定性步骤
│   │   └── references/            # 长资料，按需读
│   └── my-audit/SKILL.md
├── .agents/skills -> ../skills    # DSH 入口（一条软链，不复制）
└── .workbuddy/                    # 不参与发现，只放 memory/tmp 之类
```

宿主侧：

```
~/.workbuddy/skills/
├── my-deploy -> <repo>/skills/my-deploy      # 软链
└── my-audit  -> <repo>/skills/my-audit
```

为什么不是反过来（实体放宿主、仓库放链）：

- 多工程共享一个全局命名空间，实体放宿主就没有"哪个仓库的"这个概念了；
- 仓库里链到宿主，`git clone` 到另一台机器全是断链。

---

## 3. 命名规则（三条，破一条就会静默失效）

1. **目录名 = frontmatter `name` = 链接名**，三者必须逐字相同。
   宿主按名字建映射，不一致时**不报错，只是加载不到**。
2. **全小写 kebab-case，ASCII**。同一台机器上同时有 Windows 与 Linux 时，大小写与中文文件名都会咬人。
3. **跨项目加前缀**：`cut-deploy`、`aic-deploy`、`rm-deploy`。
   因为 user-level 是全局命名空间，你不能靠"注册时改名"来隔离——那会违反第 1 条。前缀只能加在**工程侧目录名**上。

```yaml
---
name: cut-deploy                 # ← 必须等于目录名
description: >
  把 cut 服务部署到测试环境并回读健康检查。
  当用户说「发一版」「部署到 test」或要核对部署状态时使用。
  触发词：部署、发版、deploy、健康检查。
---
```

`description` 是宿主判断"要不要加载"的唯一依据，缺了**不报错、不加载**。写法：做什么 + 何时用 + 触发词，60–300 字。

---

## 4. 五步接入（新工程照做）

### 第 1 步 · 建源目录

```bash
cd <repo>
mkdir -p skills/my-deploy
$EDITOR skills/my-deploy/SKILL.md      # 按第 3 节的 frontmatter
```

正文控制在一屏内（≤120 行），长表放 `references/`，固定命令放 `scripts/`。

### 第 2 步 · 建 DSH 入口（仓库内，可提交）

```bash
mkdir -p .agents
ln -s ../skills .agents/skills
```

验证：DSH 里问"当前有哪些技能"，或看 `skill` 工具返回的目录。

### 第 3 步 · 注册到 WorkBuddy（用户级，软链）

把 `scripts/register_skills.sh`（第 5 节）放进工程，然后：

```bash
bash scripts/register_skills.sh --check    # 先看
bash scripts/register_skills.sh            # 再建
```

### 第 4 步 · 验收（顺序不能反）

```bash
# 1) 磁盘侧
bash scripts/register_skills.sh --check          # 期望：全部 [ok]
# 2) 宿主侧热重载
grep -h "HotReload.*skills" ~/.workbuddy/logs/$(date +%F)/nileuy__*.log | tail -3
# 3) 真打一次
#    在对话里：Skill("my-deploy")
```

**判断能不能调，只能靠第 3 步**。系统提示里的清单文本是启动快照，建链后它不会更新，但运行时注册表已经更新——照文本判断会误判成"必须新开会话"。

### 第 5 步 · 日常维护

```bash
bash scripts/register_skills.sh --check     # 加了新技能后先看
bash scripts/register_skills.sh             # 幂等补链
bash scripts/register_skills.sh --unlink    # 卸载（只删链）
```

---

## 5. 脚本配方

`scripts/register_skills.sh`：幂等、不覆盖、可回滚。三个判断都用 `readlink -f` 解析到真实路径，避免"同一个技能经软链进来被当成两个"。

```bash
#!/usr/bin/env bash
# 把工程内技能注册到 WorkBuddy 用户级目录（唯一被枚举的位置）。
#   bash scripts/register_skills.sh [--check|--unlink] [--src DIR]... [--exclude NAME]...
set -uo pipefail
cd "$(dirname "$0")/.."

MODE="link"; SRC_DIRS=(); EXCLUDE=()
while [ $# -gt 0 ]; do
  case "$1" in
    --check)   MODE="check"; shift ;;
    --unlink)  MODE="unlink"; shift ;;
    --src)     SRC_DIRS+=("$2"); shift 2 ;;
    --exclude) shift; while [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; do EXCLUDE+=("$1"); shift; done ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done
[ ${#SRC_DIRS[@]} -eq 0 ] && SRC_DIRS=("skills")

HOST="$HOME/.workbuddy/skills"
[ -d "$HOST" ] || { echo "宿主目录不存在: $HOST" >&2; exit 1; }

is_excluded() { local n="$1" e; for e in ${EXCLUDE[@]+"${EXCLUDE[@]}"}; do [ "$e" = "$n" ] && return 0; done; return 1; }

rc=0; n_ok=0; n_new=0; n_skip=0; n_bad=0
for src in "${SRC_DIRS[@]}"; do
  [ -d "$src" ] || { echo "源不存在: $src" >&2; rc=1; continue; }
  abs="$(cd "$src" && pwd)"
  for d in "$abs"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    d="${d%/}"
    real="$(cd "$d" && pwd -P)"
    n="$(basename "$d")"
    is_excluded "$n" && continue
    link="$HOST/$n"
    case "$MODE" in
      check)
        if [ -L "$link" ] && [ "$(readlink -f "$link")" = "$real" ]; then echo "[ok]     $n"; n_ok=$((n_ok+1))
        elif [ -e "$link" ] || [ -L "$link" ]; then echo "[冲突]   $n"; n_bad=$((n_bad+1)); rc=1
        else echo "[未注册] $n"; n_new=$((n_new+1)); fi ;;
      link)
        if [ -L "$link" ]; then
          if [ "$(readlink -f "$link")" = "$real" ]; then n_skip=$((n_skip+1)); continue; fi
          echo "[冲突] $n 已指向别处，不动" >&2; n_bad=$((n_bad+1)); rc=1; continue
        fi
        [ -e "$link" ] && { echo "[冲突] $n 是真实目录，不动" >&2; n_bad=$((n_bad+1)); rc=1; continue; }
        ln -s "$real" "$link" && echo "[注册]   $n"; n_new=$((n_new+1)) ;;
      unlink)
        if [ -L "$link" ] && [ "$(readlink -f "$link")" = "$real" ]; then rm -f "$link"; echo "[卸载]   $n"; fi ;;
    esac
  done
done
echo "----"
case "$MODE" in
  check)  echo "已注册 $n_ok / 未注册 $n_new / 冲突 $n_bad" ;;
  link)   echo "新注册 $n_new / 已存在 $n_skip / 冲突 $n_bad" ;;
  unlink) echo "完成" ;;
esac
[ "$n_bad" -gt 0 ] && echo "有冲突：先人工确认同名条目" >&2
exit "$rc"
```

配套体检（把"宿主真正枚举的目录"也纳入，否则磁盘全绿也没意义）：

```python
# scripts/skill_doctor.py 的根目录列表
ROOTS = [
    Path.home() / ".workbuddy" / "skills",           # 宿主枚举的位置
    ROOT / ".agents" / "skills",                     # DSH 入口（若无软链则指仓库 skills/）
]
```

检查项：断链、缺 `SKILL.md`、缺 `description`、`name` 与目录名不一致、`description: |` 块标量解析。

---

## 6. 多工程共存

| 场景 | 做法 |
|---|---|
| 两个工程都有 `deploy` | 工程侧目录分别叫 `cut-deploy` / `aic-deploy`，`name` 同步改 |
| 一个工程废弃 | `register_skills.sh --unlink`，源文件不动 |
| 仓库搬家/换盘符 | 重跑 `--check` 找到断链，`--unlink` 后重新注册 |
| 临时禁用某个技能 | 卸载链接即可，不要改 frontmatter（`disable` 类字段各宿主支持不一） |

**软链目标要稳**。指向 `/media/<挂载点>/...` 的链，盘没挂就是断的。长期用就把仓库放固定路径，或让链指向一个固定位置的中间软链。

---

## 7. 反模式（都踩过）

| 别做 | 后果 |
|---|---|
| 在工程里放 `.workbuddy/skills/` 指望被发现 | 宿主不扫，改了也没用（两次实测） |
| 把技能复制进 `~/.workbuddy/skills/` | 仓库与宿主两份，改一边另一边不动 |
| 注册时改名加前缀 | `name ≠ 目录名`，静默不加载 |
| 技能放进二级目录 `skills/a/b/SKILL.md` | 两个宿主都只扫一层 |
| 靠 `<available_skills>` 文本判断能不能调 | 那是启动快照，会误判 |
| 一个技能里塞 300 行手册 | 命中后整篇进上下文（每轮都付费） |
| `description` 只写"用于 XX" | 召回率接近 0，且不报错 |

---

## 8. 迁移 checklist

```
[ ] 源：skills/<name>/SKILL.md，目录名 = name，kebab-case
[ ] DSH：.agents/skills -> ../skills（仓库根，且该根有 .git）
[ ] WB ：register_skills.sh --check 全绿
[ ] 热重载日志出现 HotReload ... skills
[ ] 对话里 Skill("<name>") 实际返回正文
[ ] 卸载路径可用：--unlink 只删链
[ ] 断链扫描：find . -xtype l 无输出
```

---

## 9. 附录：什么时候才用插件路线

WorkBuddy 还有一条路：把工程做成插件（`.codebuddy-plugin/plugin.json` + `skills: [...]`），注册进 `~/.workbuddy/plugins/`，走 `SkillExtensionLoader`。

| | 用户级软链（本文主推） | 插件包 |
|---|---|---|
| 适用 | 单人、本机、快速迭代 | 要分发给别人、要版本号、要市场安装 |
| 维护 | 一条命令 | plugin.json + 版本 + 安装记录 |
| 风险 | 全局命名空间被占 | 宿主可能只信任"市场安装"，手工登记会被覆盖 |

本机有一次尝试把插件手工登记进 `installed_plugins.json` 的实践，但**未验证宿主是否认**；日常开发用软链足够。要分发再切插件，两者可以并存（技能内容仍是同一份）。

---

## 10. 排查表

| 症状 | 先查 |
|---|---|
| 宿主说 `Can not find skill` | `~/.workbuddy/skills/<name>` 是否存在、是否软链、`readlink -f` 是否可解析 |
| 链接在，但清单里没有 | 是否只是没重开窗口；再打一次调用看运行时；查 HotReload 日志 |
| 能调，但内容是旧的 | 链指向的是副本不是源；`readlink -f` 看真实路径 |
| DSH 看不到 | `.agents/skills` 是否在 `.git` 根；是否嵌套；名字是否 kebab-case |
| 改了 SKILL.md 没生效 | 两个宿主都在监听，通常即时；先确认改的是 `readlink -f` 指向的那个文件 |
