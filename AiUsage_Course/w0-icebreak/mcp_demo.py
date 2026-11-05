"""W0 最小 MCP server：一个 tool，一个 resource。

两类原语各来一个，是为了让你看清它们的差别：
  tool     —— 模型自己决定什么时候调，参数由 JSON Schema 约束
  resource —— 只读上下文，由 client（不是模型）决定何时注入

注意版本：这里用的是 mcp 2.x 的 API。网上大量教程还在用 1.x 的
`from mcp.server.fastmcp import FastMCP`，2.x 已改名为 MCPServer。
装的时候务必锁版本（见 requirements.txt），否则抄来的代码会直接 ImportError。

跑起来（stdio 模式，一般由 client 拉起，不要手动跑）：
    python mcp_demo.py

看报文（W0 唯一要拿到的感觉）：
    npx @modelcontextprotocol/inspector python mcp_demo.py
    然后在 Inspector 里点 tools/list、tools/call、resources/list
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("demo")


@mcp.tool()
def count_lines(path: str) -> int:
    """统计一个文本文件的行数。

    什么时候用：需要快速判断文件规模时，例如决定要不要把整篇读进上下文。
    什么时候别用：需要看文件内容时，直接读文件，不要用本工具试探。
    参数 path 用绝对路径。
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


@mcp.resource("demo://about")
def about() -> str:
    """这个 server 是干什么的，供 client 按需注入到上下文。"""
    return "W0 破冰用的最小 MCP server，只提供行数统计。"


if __name__ == "__main__":
    mcp.run()  # 默认 transport="stdio"
