"""W1 的工程写法：同一个任务，用官方 SDK 再写一遍，和 raw_http.py 对照。

区别只有一个：SDK 把 SSE 解析、重试、超时、默认参数都藏起来了。
藏起来不等于不存在——你在 raw_http.py 里见过的东西，这里全都在，只是看不见。

三个子命令：
    python hello_llm.py stream       # 流式 + token 计量
    python hello_llm.py structured   # JSON Schema 约束输出（带 json_object 降级）
    python hello_llm.py --dry-run    # 只打印将要发送的参数，不联网

和 raw_http.py 一起跑一遍，然后回答：SDK 到底替你省了什么、又瞒了你什么。
"""

import json
import os
import sys
import time

from openai import OpenAI

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

# 出错样例：W1 的任务是把它结构化，而不是让人读
SAMPLE_ERROR = """
Traceback (most recent call last):
  File "train.py", line 42, in <module>
    x = torch.tensor(data, dtype=torch.float32)
TypeError: expected TensorOptions(dtype=float, device=cpu, layout=Strided, requires_grad=False)
but got TensorOptions(dtype=float64, device=cpu, layout=Strided, requires_grad=False)
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["TypeError", "RuntimeError", "ImportError", "LogicError", "Unknown"]},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "root_cause": {"type": "string"},
    },
    "required": ["category", "severity", "root_cause"],
    "additionalProperties": False,
}


def cfg() -> tuple[str, str, str]:
    return (
        os.environ.get("LLM_BASE_URL", DEFAULT_BASE).rstrip("/"),
        os.environ.get("LLM_API_KEY", "").strip(),
        os.environ.get("LLM_MODEL", DEFAULT_MODEL).strip(),
    )


def run_stream(cli: OpenAI, model: str) -> None:
    started = time.perf_counter()
    first = None
    usage = None

    stream = cli.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是简洁的助教，回答不超过三句话。"},
            {"role": "user", "content": "用一句话解释什么是 KV cache。"},
        ],
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        if chunk.usage:
            usage = chunk.usage
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if text:
            if first is None:
                first = time.perf_counter() - started
            print(text, end="", flush=True)

    print("\n")
    print(f"首 token: {first:.2f}s" if first else "首 token: 未取到")
    print(f"总耗时:  {time.perf_counter() - started:.2f}s")
    print(f"usage:   {usage}")


def run_structured(cli: OpenAI, model: str) -> None:
    base = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": "你是错误分类器。只输出 JSON，字段严格按 schema。信息不足时 category 填 Unknown，不要猜。"},
            {"role": "user", "content": SAMPLE_ERROR},
        ],
        "temperature": 0,
    }

    # 先试严格 schema 模式（OpenAI 支持），不支持就降级到 json_object
    try:
        resp = cli.chat.completions.create(
            **base,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "error_classification", "strict": True, "schema": SCHEMA},
            },
        )
        print("[模式] json_schema（严格）")
    except Exception as e:
        print(f"[降级] json_schema 不可用（{type(e).__name__}），改用 json_object + prompt 内嵌 schema")
        resp = cli.chat.completions.create(
            **base,
            response_format={"type": "json_object"},
        )

    raw = resp.choices[0].message.content or ""
    print("[原始返回]")
    print(raw)
    print("[解析结果]")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        print("  解析失败：模型没给出合法 JSON —— 这正是'用自然语言要求 JSON'的失败形态")
        return

    print(json.dumps(obj, ensure_ascii=False, indent=2))
    missing = [k for k in SCHEMA["required"] if k not in obj]
    print(f"必填缺失: {missing or '无'}")
    if obj.get("category") not in SCHEMA["properties"]["category"]["enum"]:
        print("  category 不在枚举内 —— schema 约束失效")
    print(f"usage: {resp.usage}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "stream"
    base, key, model = cfg()

    print(f"base_url={base}  model={model}  key={'已设置' if key else '未设置'}\n")

    if mode == "--dry-run":
        print("dry-run：下面就是 SDK 最终会发出去的 body（stream 模式）")
        print(json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": "你是简洁的助教，回答不超过三句话。"},
                         {"role": "user", "content": "用一句话解释什么是 KV cache。"}],
            "stream": True,
            "stream_options": {"include_usage": True},
        }, ensure_ascii=False, indent=2))
        print("\n对比 raw_http.py --dry-run 的输出：字段一样，只是这里你看不到它。")
        return

    if not key:
        print("没有 LLM_API_KEY。先跑 --dry-run，或按 README 起 mock_server.py。")
        sys.exit(2)

    cli = OpenAI(base_url=base, api_key=key)
    if mode == "stream":
        run_stream(cli, model)
    elif mode == "structured":
        run_structured(cli, model)
    else:
        print(f"未知模式 {mode}，可用: stream | structured | --dry-run")
        sys.exit(1)


if __name__ == "__main__":
    main()
