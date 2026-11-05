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
