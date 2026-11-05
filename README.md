# AI_usage

私有、单人使用的项目仓库。用于学习 AI 应用工程（MCP / Agent / Skills），
并产出技术笔记与面向非技术读者的科普文稿。不是分发物。

## 两个宿主怎么读

WorkBuddy 与 DeepSeek Harness 共用一份能力定义：

```text
.workbuddy/skills/<name>/SKILL.md     ← 唯一实体，两个宿主都只扫一层
.agents/skills -> ../.workbuddy/skills ← 软链，只让 DSH 看得见
AGENTS.md                             ← 两个宿主都读的运行契约
```

实体只存一份。不要新建 `skills/` 或 `agents/` 目录，那会形成两份真相。
角色以 `role-*` skill 存放，来源用前缀区分：`tech-`、`biz-`、`role-`。

`biz-*` 是薄壳 adapter，只指向本机 `vendor/dbskill`，不含上游正文
（dbskill LICENSE 4.1 / 4.4）。详见 `references/dbskill-manifest.yaml`。

## 三条常用命令

```bash
./scripts/check.sh                                      # 骨架体检，须输出 OK
./scripts/new-note.sh public_content mcp-context-boundary  # 按规范建产出文件
./scripts/link-agent.sh                                 # 重建 DSH 软链
```

`new-note.sh` 第一个参数只能是 `technical_notes` 或 `public_content`。
文件名格式为 `YYYY-MM-DD__<slug>[__v<N>].md`，不要手敲。

## 目录速查

| 路径 | 内容 |
|---|---|
| `.workbuddy/skills/` | 8 个能力实体（骨架状态） |
| `docs/templates/` | `SKILL.template.md` / `ROLE.template.md` |
| `docs/decisions.md` | 8 条已定决策与代价 |
| `outputs/technical_notes/` | 硬核学习笔记 |
| `outputs/public_content/drafts/` | 科普稿草稿 |
| `outputs/public_content/published/` | 定稿 |
| `references/` | 依赖清单、术语表（只存元数据） |
| `vendor/` | 本机第三方依赖，不进 git |
| `scripts/` | 链路维护、命名、自检 |
| `SKILLS.md` | 能力清单 |
| `STATUS.md` | 进度与待定决策 |

## 规则

- 文件名全小写 ASCII kebab-case，不用中文名。
- skill 目录名必须等于 frontmatter 的 `name`。
- 事实来源优先级：`references/` 与 `outputs/` 的证据 > 代码 > 模型记忆；查不到标「推断」。
- 不用 emoji，不用营销词。
- 提交前 `./scripts/check.sh` 通过，再看 `git status --short`。

完整约束见 `AGENTS.md`。本仓库当前零提交，首次提交由用户决定。
