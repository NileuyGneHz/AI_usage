"""W6 · 模型适配层：一个真实客户端 + 一个剧本回放器。

为什么要有"剧本回放器"（ScriptedModel）：
    写循环逻辑时，如果每次都调真模型，你会在"模型这次为什么这么答"和"我的循环写对没写对"
    之间反复横跳。剧本回放把模型这一侧变成确定的：给定同样的输入，永远返回同样的输出。
    于是 --fixture 模式可以零成本复现 bug，真模型模式只用来验收。

两个类接口一样：
    .complete(messages, tools) -> {"ok", "content", "tool_calls", "usage", "latency_ms", "error"}
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from shared.llm import Config, chat  # noqa: E402


class RealModel:
    def __init__(self, cfg: Config | None = None, temperature: float = 0.0):
        self.cfg = cfg or Config.from_env()
        self.temperature = temperature

    def describe(self) -> str:
        return self.cfg.describe()

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        r = chat(messages, cfg=self.cfg, temperature=self.temperature, tools=tools, tool_choice="auto")
        return {
            "ok": r["ok"], "content": r["text"], "tool_calls": r["tool_calls"],
            "usage": r["usage"], "latency_ms": r["latency_ms"], "error": r["error"],
        }


class ScriptedModel:
    """按剧本逐轮返回。剧本用完就返回最后一条的 content（模拟"模型说完了"）。"""

    def __init__(self, path: pathlib.Path):
        self.turns = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        self.i = 0

    def describe(self) -> str:
        return f"ScriptedModel({len(self.turns)} 轮剧本)"

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        time.sleep(0.01)  # 让 trace 的时间戳有点区分度
        turn = self.turns[min(self.i, len(self.turns) - 1)]
        self.i += 1
        calls = turn.get("tool_calls") or []
        return {
            "ok": True,
            "content": turn.get("content", ""),
            "tool_calls": calls,
            "usage": {"prompt_tokens": turn.get("prompt_tokens", 800),
                      "completion_tokens": turn.get("completion_tokens", 60),
                      "total_tokens": turn.get("prompt_tokens", 800) + turn.get("completion_tokens", 60)},
            "latency_ms": 10,
            "error": None,
        }
