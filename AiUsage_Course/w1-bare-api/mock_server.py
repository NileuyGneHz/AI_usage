"""W1 的可运行脚手架：一个"假"的 OpenAI 兼容服务，让你在没 API key 的情况下把客户端逻辑跑通。

它只做一件事：按 OpenAI 的 /v1/chat/completions 协议回话，支持 stream 与非 stream，
返回里带 usage。用途是**验证你的代码逻辑**，不是评估模型。

跑起来（另开一个终端）：
    python mock_server.py

然后让调用方指向它：
    LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_API_KEY=mock LLM_MODEL=mock-model \
        python raw_http.py

它故意做得"很笨"：回答是固定的。但协议字段、SSE 分块顺序、usage 结构都是真的，
所以你的解析代码可以在这里调通，再换成真 key 一把过。
"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSWER = (
    "这是 mock 服务生成的固定回答，用来验证你的流式解析与 usage 读取是否正确。"
    "它不包含任何真实推理内容，请不要用它评估模型质量。"
)

JSON_ANSWER = json.dumps(
    {"category": "TypeError", "severity": "high", "root_cause": "mock 服务返回的固定结构"},
    ensure_ascii=False,
)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[mock] " + fmt % args)

    def _json(self, code: int, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            self._json(200, {"object": "list", "data": [{"id": "mock-model", "object": "model"}]})
        else:
            self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._json(404, {"error": {"message": "not found"}})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        # 校验一下鉴权头，让你能顺手看到"key 没传"时的真实报错形态
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            self._json(401, {"error": {"message": "Missing Authorization: Bearer <key>"}})
            return

        model = body.get("model", "mock-model")
        want_json = body.get("response_format") is not None
        text = JSON_ANSWER if want_json else ANSWER
        prompt_tokens = len(json.dumps(body.get("messages", []), ensure_ascii=False)) // 3
        completion_tokens = len(text) // 2

        if not body.get("stream"):
            self._json(200, {
                "id": "mock-1", "object": "chat.completion", "created": int(time.time()), "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                          "total_tokens": prompt_tokens + completion_tokens},
            })
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def chunk(delta: dict, finish=None) -> None:
            payload = {
                "id": "mock-1", "object": "chat.completion.chunk", "created": int(time.time()), "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            self.wfile.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        chunk({"role": "assistant", "content": ""})
        for i in range(0, len(text), 6):
            chunk({"content": text[i:i + 6]})
            time.sleep(0.01)
        chunk({}, "stop")

        # 关键：流式下的 usage 只在开了 stream_options.include_usage 时才单独发一块
        if body.get("stream_options", {}).get("include_usage"):
            usage_chunk = {
                "id": "mock-1", "object": "chat.completion.chunk", "created": int(time.time()), "model": model,
                "choices": [],
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                          "total_tokens": prompt_tokens + completion_tokens},
            }
            self.wfile.write(f"data: {json.dumps(usage_chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    print("mock OpenAI-compatible server on http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
