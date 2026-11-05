# AGENTS.md · 运行契约

## 1. 这是什么仓库

私有、单人使用的项目仓库。用于学习 AI 应用工程（MCP / Agent / Skills），
并产出技术笔记与面向非技术读者的科普文稿。

两个宿主共用同一份能力定义：WorkBuddy 读 `.workbuddy/skills/`，
DeepSeek Harness 经软链 `.agents/skills` 读同一目录。本仓库不是分发物。

## 2. 目录约定

| 路径 | 职责 |
|---|---|
| `.workbuddy/skills/<name>/SKILL.md` | 唯一的能力实体，只有一层目录 |
| `.agents/skills` | 软链，指向 `../.workbuddy/skills`，不要改成真实目录 |
| `docs/templates/` | 新建 skill / role 的模板 |
| `docs/decisions.md` | 已定决策与代价 |
| `outputs/technical_notes/` | 硬核学习笔记 |
| `outputs/public_content/{drafts,published}/` | 科普稿草稿与定稿 |
| `references/` | 外部依赖清单与术语表，只存元数据 |
| `vendor/` | 本机安装的第三方依赖，不进 git |
| `scripts/` | 链路维护、命名、自检 |

不要创建 `skills/` 或 `agents/` 目录：两个宿主都没有对应加载入口，
会形成两份真相。角色一律写成 `role-*` skill。

## 3. 命名规范

- 文件名全小写 ASCII kebab-case，不用中文名，不改大小写。
- skill 目录名必须等于 frontmatter 的 `name` 字段，`check.sh` 会校验。
- 前缀即来源，也是分组：`tech-`（自己写的技术能力）、
  `biz-`（指向 dbskill 的薄壳 adapter）、`role-*`（协作角色）。
- 产出文件名：`YYYY-MM-DD__<slug>[__v<N>].md`，双下划线分隔。
- 用 `./scripts/new-note.sh` 生成文件，不手敲长文件名；路径用 Tab 补全。

## 4. 事实来源优先级

1. `references/` 与 `outputs/` 里有出处的证据
2. 仓库内代码与配置的实际内容
3. 模型记忆

前一级与后一级冲突时，以前一级为准。查不到证据的结论标注「推断」，
不要写成事实。引用格式用 `<path>:<line>`，不用「据文档所述」。

## 5. 禁区

- 不复制 `dbskill` 的 SKILL.md 正文进仓库：其 LICENSE 4.1 禁止再分发、
  4.4 禁止公开发布修改版。`biz-*` 只写调用路径与接口。
- 不把 `vendor/` 下的任何文件提交进 git。
- 不用 emoji，不用「震惊 / 必看 / 颠覆 / 赋能 / 闭环」这类词。
- 不编造技术结论；骨架正文只写结构与 `TODO`。
- 不改动 `AiUsage_Course/`、`ml-course/`、`.workbuddy/memory/`、
  `.workbuddy/tmp/`、`.workbuddy/crash-backup/`。

## 6. 提交前

```bash
./scripts/check.sh        # 必须为 OK
git status --short        # 人工再看一遍
```

`check.sh` 校验：skill 层级、`name` 与目录名一致、`description` 非空、
软链存在、无中文文件名入库、`vendor/` 未入库。

首次提交由用户在 2026-11-05 明确授权完成，分支为 `main`。
后续提交沿用 `type(scope): 简述`，提交时点由用户决定；
Agent 不擅自执行 `git add` / `commit` / `push`，除非当次会话得到明确授权。
沙箱内 `HOME` 可能为空，提交前需 `export HOME=/home/nileuy`，否则读不到全局 git 身份。
