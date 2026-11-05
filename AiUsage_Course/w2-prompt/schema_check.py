"""极小 JSON Schema 校验器（够 W2 用，也够你看懂"schema 校验"到底在做什么）。

支持的关键字：type / properties / required / additionalProperties / items /
enum / const / minItems / maxItems / minLength / maxLength / pattern / oneOf / $ref。

故意不实现：format、依赖、外部 $ref、递归环。真实项目里用 `jsonschema` 库，
这里自己写一遍的价值在于：跑失败时你能指着某一行说"是这条规则拦下的"。

    from schema_check import validate
    errs = validate({"cards": []}, schema)
"""

from __future__ import annotations

import json
from typing import Any


def _resolve(ref: str, root: dict) -> dict:
    """只支持本地引用 "#/$defs/name"。"""
    if not ref.startswith("#/"):
        raise ValueError(f"只支持本地 $ref，收到 {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate(instance: Any, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """返回错误列表，空列表 = 通过。"""
    root = root or schema
    errs: list[str] = []

    if "$ref" in schema:
        return validate(instance, _resolve(schema["$ref"], root), root, path)

    if "oneOf" in schema:
        branches = schema["oneOf"]
        results = [validate(instance, b, root, path) for b in branches]
        passes = [r for r in results if not r]
        if len(passes) == 0:
            errs.append(f"{path}: 不匹配 oneOf 的任何一支；" + " | ".join(r[0] for r in results if r))
        elif len(passes) > 1:
            errs.append(f"{path}: 同时匹配 oneOf 的多支（应恰好一支）")
        return errs

    # type
    t = schema.get("type")
    if t:
        ok = {
            "object": isinstance(instance, dict),
            "array": isinstance(instance, list),
            "string": isinstance(instance, str),
            "integer": isinstance(instance, int) and not isinstance(instance, bool),
            "number": isinstance(instance, (int, float)) and not isinstance(instance, bool),
            "boolean": isinstance(instance, bool),
            "null": instance is None,
        }.get(t, True)
        if not ok:
            return [f"{path}: 期望 {t}，实际是 {type(instance).__name__}"]

    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: 期望常量 {schema['const']!r}，实际 {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} 不在枚举 {schema['enum']} 里")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: 字符串长度 {len(instance)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: 字符串长度 {len(instance)} > maxLength {schema['maxLength']}")
        if "pattern" in schema:
            import re
            if not re.search(schema["pattern"], instance):
                errs.append(f"{path}: 不匹配 pattern {schema['pattern']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: 元素数 {len(instance)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: 元素数 {len(instance)} > maxItems {schema['maxItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs.extend(validate(item, schema["items"], root, f"{path}[{i}]"))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: 缺少必填字段 {key!r}")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in instance:
                errs.extend(validate(instance[key], sub, root, f"{path}.{key}"))
        extra = [k for k in instance if k not in props]
        if extra and schema.get("additionalProperties") is False:
            errs.append(f"{path}: 多出未声明字段 {extra}")

    return errs


def _main() -> None:
    import pathlib
    import sys

    here = pathlib.Path(__file__).resolve().parent
    schema = json.loads((here / "schema" / "cards.schema.json").read_text(encoding="utf-8"))
    sample = {
        "cards": [
            {"q": "什么是监督学习？", "a": "给定带标签数据学习映射。", "point": "定义", "difficulty": "easy"},
            {"q": "代价函数的作用？", "a": "衡量预测与真值差距。", "point": "目标函数", "difficulty": "medium"},
            {"q": "梯度下降何时收敛？", "a": "学习率合适且梯度趋零。", "point": "收敛条件", "difficulty": "hard"},
        ]
    }
    if "--bad" in sys.argv:
        sample["cards"] = sample["cards"][:2]
        sample["cards"][0]["difficulty"] = "简单"
    errs = validate(sample, schema)
    print("通过" if not errs else "\n".join(errs))


if __name__ == "__main__":
    _main()
