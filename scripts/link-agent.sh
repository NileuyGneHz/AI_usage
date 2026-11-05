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
