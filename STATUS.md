# STATUS

> 最后更新：2026-11-05（骨架已推送至 private 仓库 `AI_usage`，分支 `main`）

## 骨架进度

| skill | 类型 | stage | 说明 |
|---|---|---|---|
| tech-mcp-mechanism | tech | skeleton | 正文待补 |
| role-research-librarian | role | skeleton | 正文待补 |
| role-translator | role | skeleton | 正文待补 |
| role-business-lens | role | skeleton | 正文待补 |
| role-synthesis-editor | role | skeleton | 正文待补 |
| biz-problem-reframing | biz | skeleton | adapter 已通，依赖本机 vendor |
| biz-jtbd | biz | skeleton | adapter 已通，依赖本机 vendor |
| biz-benchmark | biz | skeleton | adapter 已通，依赖本机 vendor |

其余骨架文件：`.gitignore`、`AGENTS.md`、`README.md`、`SKILLS.md`、
`docs/decisions.md`、两份模板、`references/` 两份、`scripts/` 三个、软链一条。

## 已解决

- **2026-11-05**：`vendor/dbskill` 已安装，`v3.2.3` @ `eacbecf`（浅克隆、detached HEAD）。
  35 个 `SKILL.md`、`shared/manifest.json`、`知识库/`、`LICENSE` 齐全。
  三个 `biz-*` adapter 指向的上游文件均已验证存在。
  该目录被 `.gitignore` 的 `vendor/*` 排除，不入库。
- **2026-11-05**：`AI_usage_repo_design/` 已加入 `.gitignore`（含中文文件名，本机自留）。
- **2026-11-05**：`ml-course/Coursera-ML-AndrewNg-Notes/` 已加入 `.gitignore`。
  它是 `fengdu78/Coursera-ML-AndrewNg-Notes` 的上游 clone（自带 `.git`，1.5G），
  若入库会被 git 收成悬空 gitlink，clone 后是空目录。本机语料保留，不影响 W2–W4 学习。
  `ml-course/ml-ng/` 的 6 个自有文件仍正常入库。
- **2026-11-05**：SSH 密钥诊断通过。本地 ED25519 公钥与 GitHub 账号
  `NileuyGneHz` 上注册的那把完全一致；走 `ssh.github.com:443` 认证成功，
  `git ls-remote` 返回 0（远端为空仓库）。密钥未过期、未轮换。

## 待定决策

1. 「首次推送」已解决：用户 2026-11-05 选 `main`，已推送至
   `git@github.com:NileuyGneHz/AI_usage.git`（private）。
2. `private` 是否长期保持。若计划公开，`biz-*` 与 `outputs/public_content/` 需先做许可复核。
3. 是否把 `AiUsage_Course/` 迁进本仓库的 `outputs/technical_notes/`。
   当前不迁（迁移要改 16 处路径），见 `docs/decisions.md` 第 7 条。
4. 上游更新方式：当前是浅克隆 + tag 的 detached HEAD。
   将来若要升级，直接重新 `git clone --depth 1 --branch <tag>` 覆盖，
   不要用 `git pull`（无完整历史）。

## 下一步

- 补 8 个 skill 的正文，从 `tech-mcp-mechanism` 开始。
- 写第一段 `outputs/technical_notes/`，用 `scripts/new-note.sh` 生成。
- 首次提交已完成；后续提交的时点由用户决定。
