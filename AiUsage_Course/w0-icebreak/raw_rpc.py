"""不装 Inspector，直接看 MCP 的 JSON-RPC 报文。

原理：stdio 传输就是"父进程写一行 JSON、子进程回一行 JSON"。
没有 HTTP、没有 SSE、没有魔法——这个脚本就是最小 client。

用法（在 w0-icebreak 目录下）：
    .venv/bin/python raw_rpc.py

它做的事，和 Inspector 点按钮做的事完全一样：
    initialize → notifications/initialized → tools/list → tools/call
"""

import json
import subprocess
import sys
from pathlib import Path

SERVER = [sys.executable, "mcp_demo.py"]
TARGET = str(Path("mcp_demo.py").resolve())


def send(proc: subprocess.Popen, obj: dict) -> None:
    line = json.dumps(obj, ensure_ascii=False)
    proc.stdin.write(line + "\n")
    proc.stdin.flush()
    print("--> " + line)


def recv(proc: subprocess.Popen) -> dict | None:
    line = proc.stdout.readline()
    if not line:
        print("<-- (连接已关闭)")
        return None
    print("<-- " + line.rstrip())
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def main() -> None:
    proc = subprocess.Popen(
        SERVER,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    send(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "raw-rpc-client", "version": "0.1"},
        },
    })
    init = recv(proc)
    if init and "result" in init:
        print(f"\n[协商结果] 服务端声明的能力: {list(init['result'].get('capabilities', {}))}\n")

    send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    print("\n=== tools/list ===")
    send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    recv(proc)

    print("\n=== tools/call ===")
    send(proc, {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "count_lines", "arguments": {"path": TARGET}},
    })
    recv(proc)

    print("\n=== resources/list ===")
    send(proc, {"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
    recv(proc)

    proc.stdin.close()
    proc.wait(timeout=5)
    err = proc.stderr.read()
    if err.strip():
        print("\n[stderr]\n" + err.strip())


if __name__ == "__main__":
    main()
