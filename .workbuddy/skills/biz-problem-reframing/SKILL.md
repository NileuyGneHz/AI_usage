---
name: biz-problem-reframing
description: 当需要把「用户要什么功能」重新表述成「要解决什么问题」时用（adapter，指向 vendor 里的 dbskill）
metadata:
  origin: dbskill@3.2.3
  upstream_skill: dbs-diagnosis
agent_created: true
---

# 用法

1. 读 `vendor/dbskill/skills/dbs-diagnosis/SKILL.md`（相对仓库根），按其流程执行。
2. 只取结论与框架名，不复制原文段落进 `outputs/`。
3. 输出用本仓库的三段式，不用上游格式。

## 前提

`vendor/dbskill` 需在本机安装（见 `references/dbskill-manifest.yaml`）。未安装时直接说明，不要凭记忆编造框架。
