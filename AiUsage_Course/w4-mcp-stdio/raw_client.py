#!/usr/bin/env python3
"""W4 脚手架：最小 MCP client，把线路上每一行 JSON-RPC 打出来。

它和 Inspector 做的事完全一样，区别是**不帮你隐藏任何东西**：
    initialize → notifications/initialized → tools/list → resources/list → tools/call

用法：
    # 1) 先对着 W0 的 demo 跑一遍（零成本，确认你懂报文）
    python3 raw_client.py --server "../w0-icebreak/.venv/bin/python ../w0-icebreak/mcp_demo.py"

    # 2) 写好自己的 server 之后
    python3 raw_client.py
    python3 raw_client.py --call search_notes --args '{"query": "正规方程", "k": 3}'
    python3 raw_client.py --call read_section --args '{"path": "week2.md", "start_line": 146, "end_line": 160}'

    # 3) 把 tools/list 的结果存下来，W5 的 probe.py 要用
    python3 raw_client.py --dump ../w5-mcp-http/tools.json

为什么先手工跑报文再接 LLM：接上 LLM 之后，你同时面对两个黑箱（协议 + 模型），
出问题时无法定位。先让报文这一层变成白箱，剩下的就只有一个黑箱了。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import queue
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
PROTOCOL_VERSION = "2025-06-18"


class Client:
    def __init__(self, cmd: list[str], timeout: float = 10.0):
        self.timeout = timeout
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self.q: queue.Queue[str] = queue.Queue()
        self.log: list[str] = []
        threading.Thread(target=self._pump, daemon=True).start()
        self._id = 0

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.q.put(line)
        self.q.put("")  # 结束哨兵

    def send(self, obj: dict) -> None:
        assert self.proc.stdin is not None
        line = json.dumps(obj, ensure_ascii=False)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        self.log.append("--> " + line)
        print("--> " + line)

    def recv(self) -> dict | None:
        try:
            line = self.q.get(timeout=self.timeout)
        except queue.Empty:
            print(f"<-- (超时 {self.timeout}s：server 没回。看下面的 stderr)")
            return None
        if not line:
            print("<-- (连接已关闭)")
            return None
        line = line.rstrip("\n")
        self.log.append("<-- " + line)
        print("<-- " + line)
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            print("    ^ 不是合法 JSON —— 多半是 print() 打到 stdout 了（见 README 坑 1）")
            return None

    def call(self, method: str, params: dict | None = None, *, notify: bool = False) -> dict | None:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        self.send(msg)
        return None if notify else self.recv()

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        if self.proc.stderr:
            err = self.proc.stderr.read()
            if err.strip():
                print("\n[stderr]\n" + err.strip()[:2000])


def default_cmd() -> list[str]:
    server = HERE / "server" / "server.py"
    if server.exists():
        venv = HERE / ".venv" / "bin" / "python"
        py = str(venv) if venv.exists() else sys.executable
        return [py, str(server)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="最小 MCP client（打印原始 JSON-RPC）")
    ap.add_argument("--server", help='启动命令，例如 "python3 ../w0-icebreak/mcp_demo.py"')
    ap.add_argument("--call", help="额外执行的 tools/call 工具名")
    ap.add_argument("--args", default="{}", help="tools/call 的参数（JSON 字符串）")
    ap.add_argument("--dump", help="把 tools/list 的结果写入该文件（W5 用）")
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    if args.server:
        cmd = args.server.split()
    else:
        cmd = default_cmd()
        if not cmd:
            print("还没写 server/server.py。两条路：")
            print("  1) 先对着 W0 的 demo 看报文：")
            print('     python3 raw_client.py --server "../w0-icebreak/.venv/bin/python ../w0-icebreak/mcp_demo.py"')
            print("  2) 按 README 把 server/server.py 写出来，再直接跑 python3 raw_client.py")
            return 2

    print(f"[启动] {' '.join(cmd)}\n")
    c = Client(cmd, timeout=args.timeout)
    try:
        print("=== initialize ===")
        init = c.call("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "w4-raw-client", "version": "0.1"},
        })
        if init and "result" in init:
            r = init["result"]
            print(f"\n[协商] protocolVersion={r.get('protocolVersion')}  "
                  f"capabilities={list(r.get('capabilities', {}))}  "
                  f"serverInfo={r.get('serverInfo')}\n")

        c.call("notifications/initialized", notify=True)

        print("=== tools/list ===")
        tools = c.call("tools/list", {})
        if tools and "result" in tools:
            for t in tools["result"].get("tools", []):
                print(f"\n[tool] {t['name']}")
                print(f"  description: {(t.get('description') or '')[:160]}")
                print(f"  inputSchema: {json.dumps(t.get('inputSchema'), ensure_ascii=False)}")

        print("\n=== resources/list ===")
        c.call("resources/list", {})

        if args.call:
            print(f"\n=== tools/call {args.call} ===")
            payload = json.loads(args.args)
            c.call("tools/call", {"name": args.call, "arguments": payload})

        if args.dump and tools and "result" in tools:
            out = pathlib.Path(args.dump)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(tools["result"], ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n[已保存] {out}（W5 的 probe.py 直接读它）")
    finally:
        c.close()

    print("\n三个必须看懂的点：")
    print("1. initialize 是能力协商，不是握手寒暄：服务端在这里声明自己提供什么。")
    print("2. tools/list 里，description 决定「调不调」，inputSchema 决定「怎么调」。")
    print("3. tools/call 有一对 id：请求 id 和工具名前缀，没有别的魔法。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
