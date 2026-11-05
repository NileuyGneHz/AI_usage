# W0 · 破冰：一个晚上，两个最小件

目的不是学会，是**消除"这东西很神秘"**。两件事各 30 分钟，都不许加功能。

为什么不是三件：prompt 你其实写过几百次（跟 AI 对话就是写 prompt），只是没有验收标准，那是 W2 的事。MCP 和 skill 才是真零基础。

---

## A. 写一个 MCP server（30 分钟）

### 1. 建环境

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w0-icebreak
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

不加镜像时国内直连 pypi 大概率超时，这不是你配错了。

### 2. 先撞一次版本墙（故意的）

打开 `mcp_demo.py`，把 import 改回你会在网上看到的那种写法：

```python
from mcp.server.fastmcp import FastMCP   # 1.x 的写法
mcp = FastMCP("demo")
```

跑一下，你会得到：

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'.
This is mcp 2.x, where FastMCP was renamed to MCPServer
```

这就是 90% 的 LLM 教程会坑你的地方——**它们不写版本**。记住这个手感：W8 那道"你怎么判断一个 skill 过期了"的题，考的是同一种能力。

改回去（`from mcp.server.mcpserver import MCPServer`），继续。

### 3. 看报文（这一步是关键）

**路 A（推荐，不依赖 npm）：看原始 JSON-RPC**

```bash
.venv/bin/python raw_rpc.py
```

它就是一个 60 行的最小 client，做的事和 Inspector 点按钮完全一样，但把线路上每一行都打出来了。实测输出（节选）：

```
--> {"jsonrpc": "2.0", "id": 1, "method": "initialize", ...}
<-- {"result":{"capabilities":{"prompts":...,"resources":...,"tools":...},
     "protocolVersion":"2025-06-18","serverInfo":{"name":"demo","version":""}}}
```

```
<-- {"id":2,"result":{"tools":[{
      "name":"count_lines",
      "description":"统计一个文本文件的行数。\n\n什么时候用：...\n参数 path 用绝对路径。\n",
      "inputSchema":{"properties":{"path":{"title":"Path","type":"string"}},"required":["path"]},
      "outputSchema":{"properties":{"result":{"title":"Result","type":"integer"}}}
    }]}}
```

```
<-- {"id":3,"result":{"content":[{"text":"43","type":"text"}],"isError":false,
     "structuredContent":{"result":43}}}
```

**四个必须看出来的点**

1. `initialize` 不是握手寒暄，是**能力协商**：服务端在这里声明自己提供 `prompts / resources / tools` 三样。
2. `tools/list` 里，`description` 是你 docstring 的**全文**，`inputSchema` 是从类型标注**自动生成**的。模型判断"调不调"主要看 `description`，判断"怎么调"主要看 `inputSchema`。
3. `tools/call` 返回两套内容：`content`（给模型看的文本）和 `structuredContent`（给程序用的数据）。**两者可以不一致**——W7 做评测时你会感谢这个设计。
4. 盯住 `"path": {"title": "Path", "type": "string"}`：**参数本身一句说明都没有**。你 docstring 里写的"用绝对路径"落在工具说明里，不在参数说明里。W5 会教怎么补。

**路 B：官方 Inspector（需要 npm 能联网）**

```bash
npx @modelcontextprotocol/inspector .venv/bin/python mcp_demo.py
```

界面更友好，但看不到原始报文。真想理解协议，路 A 的信息量更大。

### 4. 记一句

在 `NOTES.md` 写下：`tools/list` 返回里，哪个字段决定"调不调"，哪个字段决定"怎么调"？（答案是两个不同的字段）

---

## B. 写一个 skill（30 分钟）

### 1. 先读一遍形状

`skill-template/SKILL.md` 是一个完整例子（ROS 2 话题排查，54 行）。读的时候注意两件事：

- **frontmatter 的 `description` 写的是"症状"和"触发场景"，不是功能简介。** 它是唯一常驻上下文的字段，决定这个 skill 会不会被想起来用。写"用于 ROS2 话题调试"是失败的；写"echo 无输出、hz 为 0、话题在 list 里但没数据"才会被命中。
- **正文写的是判断顺序，不是知识介绍。** "先看 A，A 正常再看 B，B 异常说明问题在 C"——这个结构 agent 才能照着执行。写成"ROS 2 的 QoS 有几种"就是在写教材。

### 2. 换成你自己的

```bash
cp -r skill-template ~/.workbuddy/skills/<你的skill名>
```

然后改三处：`name`、`description`、正文。选题标准：**你每周都在做、步骤固定 ≥3 步、每次都得想一下顺序**的事。想不到就先用这个：

> 「提交前检查工作区：有没有忘记 add 的文件、有没有误提交大文件、commit message 是否为空」

### 3. 验收（比写更难，也更重要）

开一个**新的** WorkBuddy 会话，**不提 skill 的名字**，只描述你遇到的问题，看它会不会自动加载你刚写的那个。

- 没命中 → 改 `description`，把症状写得更具体、更像你的原话
- 命中了但执行顺序乱 → 改正文，把步骤改成"先…再…若…则…"

反复三四轮。这个手感（**description 决定召回率**）是写 skill 最核心的技能，比正文写法重要十倍，而且只能靠试出来。

---

## 完成标志

- [x] 撞过一次版本墙，能说出为什么不能直接抄教程里的 import
- [x] 能从 `tools/list` 的返回里指出：哪个字段决定"调不调"，哪个字段决定"怎么调"
- [x] `~/.workbuddy/skills/` 下有一个你自己写的、被成功召回过的 skill
- [x] 能一句话说清 tool 和 resource 的区别（谁决定调用）

四条都过了再进 W1。W1 开始就是真代码，不再是玩具。
