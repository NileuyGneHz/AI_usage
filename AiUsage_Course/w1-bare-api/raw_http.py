"""W1 主课：不借助任何 SDK，手写一次 HTTP 请求，手工解析 SSE 流。

为什么不用 openai 库：SDK 会替你补默认参数（system、重试、超时），还会把 SSE 解析藏起来。
W1 的目标是"让一次请求和一次响应完全透明"，所以这里只用标准库。

用法：
    python raw_http.py                # 真发一次流式请求
    python raw_http.py --dry-run      # 只打印请求体，不联网、不花钱（没有 key 也能跑）
    python raw_http.py --no-stream    # 关掉流式，看非流式的返回长什么样

先跑 --dry-run，把请求体看明白，再去配 key。
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"


def load_cfg() -> tuple[str, str, str]:
    base = os.environ.get("LLM_BASE_URL", DEFAULT_BASE).rstrip("/")
    key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL).strip()
    return base, key, model


def build_body(model: str, stream: bool) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是简洁的助教，回答不超过三句话。"},
            {"role": "user", "content": "用一句话解释什么是 KV cache。"},
        ],
        "temperature": 0.7,
        "max_tokens": 200,
        "stream": stream,
    }
    if stream:
        # 不加这个字段，流式返回里就没有 usage —— 你会以为"流式拿不到 token 数"
        body["stream_options"] = {"include_usage": True}
    return body


def show_request(url: str, headers: dict, body: dict) -> None:
    print("=== 请求 ===")
    print(f"POST {url}")
    for k, v in headers.items():
        print(f"  {k}: {'Bearer ***' if k.lower() == 'authorization' else v}")
    print("--- body ---")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print("--- 等价 curl ---")
    flat = json.dumps(body, ensure_ascii=False).replace("'", "'\\''")
    print(f"curl -N {url} -H 'Content-Type: application/json' "
          f"-H 'Authorization: Bearer $LLM_API_KEY' -d '{flat}'")
    print()


def do_stream(url: str, headers: dict, body: dict) -> None:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    started = time.perf_counter()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {e.read().decode(errors='replace')}")
        sys.exit(1)

    print("=== 响应头 ===")
    for k, v in resp.headers.items():
        print(f"  {k}: {v}")

    print("=== 流式片段（原样打印前 3 块，之后只显示解析结果）===")
    first_token_at = None
    pieces: list[str] = []
    usage = None
    raw_shown = 0

    for raw in resp:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            continue
        if raw_shown < 3:
            print(f"  raw> {line[:160]}", flush=True)
            raw_shown += 1
            if raw_shown == 3:
                print("=== 正文开始 ===", flush=True)
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if chunk.get("usage"):
            usage = chunk["usage"]
        for choice in chunk.get("choices") or []:
            text = (choice.get("delta") or {}).get("content")
            if text:
                if first_token_at is None:
                    first_token_at = time.perf_counter() - started
                pieces.append(text)
                sys.stdout.write(text)
                sys.stdout.flush()

    elapsed = time.perf_counter() - started
    print("\n\n=== 统计 ===")
    print(f"  首 token 延迟: {first_token_at:.2f}s" if first_token_at else "  首 token 延迟: 未取到")
    print(f"  总耗时:       {elapsed:.2f}s")
    print(f"  字符数:       {len(''.join(pieces))}")
    if usage:
        print(f"  usage:        {usage}")
    else:
        print("  usage:        无（检查 body 里有没有 stream_options.include_usage）")


def do_no_stream(url: str, headers: dict, body: dict) -> None:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {e.read().decode(errors='replace')}")
        sys.exit(1)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n总耗时: {time.perf_counter() - started:.2f}s")


def main() -> None:
    args = set(sys.argv[1:])
    base, key, model = load_cfg()
    url = f"{base}/chat/completions"
    stream = "--no-stream" not in args
    body = build_body(model, stream)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}

    show_request(url, headers, body)

    if "--dry-run" in args:
        print("dry-run：只打印请求体，没有联网。")
        return
    if not key:
        print("没有 LLM_API_KEY。三条路：\n"
              "  1) 纯离线练逻辑：另开终端跑 python mock_server.py，然后\n"
              "     LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_API_KEY=mock LLM_MODEL=mock-model python raw_http.py\n"
              "  2) 真模型：去 platform.deepseek.com 拿 key，写进 .env 后 source 一下\n"
              "  3) 先只跑 --dry-run，把请求体看懂再说")
        sys.exit(2)

    if stream:
        do_stream(url, headers, body)
    else:
        do_no_stream(url, headers, body)


if __name__ == "__main__":
    main()
