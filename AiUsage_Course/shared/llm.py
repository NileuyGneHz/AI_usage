"""共用的最小 LLM 客户端（纯标准库，零第三方依赖）。

为什么会有这个文件：
    W2–W7 每一周都要发同一个 POST。抄六遍的代价不是行数，是「你读代码时
    要多看六份一样的拼接逻辑」。所以把「拼 body / 发请求 / 取 text+usage」
    抽到这里，各周的脚本只写自己那一周真正要判断的东西。

它刻意不做的事：
    - 不重试、不降级、不管并发。那些是框架的活，而你正在学的就是不靠框架。
    - 不隐藏请求体。`chat(..., dry_run=True)` 会把要发的 JSON 原样还给你。

用法：
    from shared.llm import Config, chat

    cfg = Config.from_env()
    r = chat([{"role": "user", "content": "你好"}], cfg=cfg)
    print(r["text"], r["usage"], r["latency_ms"])

环境变量（第一次配置读 `AiUsage_Course/.env`，或直接 export）：
    LLM_BASE_URL   默认 http://127.0.0.1:8000/v1   （默认指向 w1 的 mock_server.py）
    LLM_API_KEY    默认 mock
    LLM_MODEL      默认 mock-model
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

COURSE_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _candidate_env_files() -> list[pathlib.Path]:
    """找 .env 的顺序：显式指定 > 当前目录 > 课程根目录 > W1 目录。"""
    out: list[pathlib.Path] = []
    explicit = os.getenv("LLM_ENV_FILE")
    if explicit:
        out.append(pathlib.Path(explicit).expanduser())
    out.append(pathlib.Path.cwd() / ".env")
    out.append(COURSE_ROOT / ".env")
    out.append(COURSE_ROOT / "w1-bare-api" / ".env")
    return out


def load_dotenv(path: pathlib.Path | None = None) -> pathlib.Path | None:
    """极简 .env 读取：只认 KEY=VALUE，不覆盖已存在的环境变量。"""
    files = [path] if path else _candidate_env_files()
    for f in files:
        if not f or not f.is_file():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        return f
    return None


@dataclass
class Config:
    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        return cls(
            base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
            api_key=os.getenv("LLM_API_KEY", "mock"),
            model=os.getenv("LLM_MODEL", "mock-model"),
        )

    @property
    def is_mock(self) -> bool:
        return "127.0.0.1" in self.base_url or "localhost" in self.base_url

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def describe(self) -> str:
        tag = "MOCK（只能验证管线，不能评估质量）" if self.is_mock else "真实模型"
        return f"{self.model} @ {self.endpoint}  [{tag}]"


def build_body(
    messages: list[dict[str, Any]],
    cfg: Config,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """把 Python 参数翻成 HTTP body。想看清楚"你发出去的是什么"，调它。"""
    body: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if response_format is not None:
        body["response_format"] = response_format
    if tools:
        body["tools"] = tools
    if tool_choice:
        body["tool_choice"] = tool_choice
    return body


def chat(
    messages: list[dict[str, Any]],
    cfg: Config | None = None,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    response_format: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    timeout: int = 90,
    dry_run: bool = False,
) -> dict[str, Any]:
    """发一次非流式请求，返回归一化结果。

    返回字段（无论成功失败都齐全）：
        ok / text / message / tool_calls / usage / latency_ms / error / body
    """
    cfg = cfg or Config.from_env()
    body = build_body(
        messages, cfg, temperature=temperature, max_tokens=max_tokens,
        response_format=response_format, tools=tools, tool_choice=tool_choice,
    )
    result: dict[str, Any] = {
        "ok": False, "text": "", "message": None, "tool_calls": [],
        "usage": {}, "latency_ms": 0, "error": None, "body": body,
    }
    if dry_run:
        result["error"] = "dry_run"
        return result

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        cfg.endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        },
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        result["error"] = f"HTTP {e.code}: {detail}"
        result["latency_ms"] = int((time.time() - t0) * 1000)
        return result
    except Exception as e:  # 连接失败 / 超时 / DNS
        result["error"] = f"{type(e).__name__}: {e}"
        result["latency_ms"] = int((time.time() - t0) * 1000)
        return result

    result["latency_ms"] = int((time.time() - t0) * 1000)
    result["ok"] = True
    result["usage"] = payload.get("usage") or {}
    choice = (payload.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    result["message"] = msg
    result["text"] = msg.get("content") or ""
    result["tool_calls"] = msg.get("tool_calls") or []
    return result


def main() -> None:
    """自检：`python -m shared.llm` 看当前配置，`--dry-run` 只看请求体。"""
    import sys

    cfg = Config.from_env()
    print("配置 :", cfg.describe())
    print("模型 :", cfg.model)
    if "--dry-run" in sys.argv:
        body = build_body([{"role": "user", "content": "你好"}], cfg)
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return
    r = chat([{"role": "user", "content": "用一句话说明你收到了这条消息。"}], cfg=cfg)
    if not r["ok"]:
        print("失败 :", r["error"])
        if cfg.is_mock:
            print("提示 : mock 没起？先跑  python3 w1-bare-api/mock_server.py")
        return
    print("回答 :", r["text"][:200])
    print("usage:", r["usage"])
    print("延迟 :", r["latency_ms"], "ms")


if __name__ == "__main__":
    main()
