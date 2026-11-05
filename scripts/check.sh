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
# LC_ALL=C + 非 ASCII 字节范围，避免 GNU grep -P 的 \x{...} 兼容问题；
# 不用 grep -q，防止 pipefail 下提前退出返回 SIGPIPE 而漏报
non_ascii="$(git ls-files 2>/dev/null | LC_ALL=C grep -n '[^ -~]' || true)"
[ -n "$non_ascii" ] && bad "有非 ASCII 文件名入库：$non_ascii"

# 5) 许可证边界：vendor 不得入库
git ls-files 2>/dev/null | grep -E '^vendor/.+' | grep -v '^vendor/.gitkeep$' && bad "vendor/ 被提交了"

# 汇总
n=0
for d in .workbuddy/skills/*/; do [ -d "$d" ] && n=$((n+1)); done
note "skills 数量：$n"
if [ "$fail" -eq 0 ]; then note "OK"; exit 0; else note "有问题，见上"; exit 1; fi
