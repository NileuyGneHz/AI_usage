# W4 讲义 · MCP 上：协议、原语、和第一个 server

> 配合 `w4-mcp-stdio/` 使用。先读这份，再跑 `raw_client.py` 对着 W0 的 demo 看报文，
> 最后才写 `server/server.py`。
> 本周不接 LLM。**先让协议这一层变成白箱，再接模型**——顺序反了你会同时调两个黑箱。

---

## 0. 一句话

MCP 就是 **JSON-RPC 2.0 + 三个原语 + 一个生命周期 + 两种传输**。
你在 W0 已经见过它的报文，这周要做的是**自己造一个**，并且知道每一行是谁写的。

---

## 1. 你已经在 W0 见过它了

W0 的 `raw_rpc.py` 打出来的东西，你当时看到的是"哦，原来是这样"。现在换个问法：

| 报文 | 谁生成的 | 你要写的代码在哪 |
|---|---|---|
| `initialize` 的响应 | **框架**（`MCPServer` 自动回） | 你不用写 |
| `tools/list` 的 `description` | **框架**从你的 docstring 抄的 | 你写 docstring |
| `tools/list` 的 `inputSchema` | **框架**从你的类型标注生成的 | 你写类型标注 |
| `tools/call` 的执行 | **你的函数** | 你写函数体 |

**结论**：本周你写的东西，影响力集中在两个地方——**docstring 和类型标注**。
这两样东西在模型眼里就是"这个工具是什么、怎么用"。写错这两处，代码再漂亮也没用。

---

## 2. 三个原语，区别只在"谁决定"

这是本周唯一必须记牢、且会一直用到 W8 的知识：

| 原语 | 谁决定何时用 | 有副作用？ | 典型用途 |
|---|---|---|---|
| `tools` | **模型**（model-controlled） | 可以 | 搜索、读文件、执行命令 |
| `resources` | **应用/Host**（application-controlled） | 只读 | 目录树、配置、当前打开的文件 |
| `prompts` | **用户**（user-controlled） | 无 | 斜杠命令模板 |

为什么这个区别重要：**它决定了 W8 的三选一判据**。你现在做的笔记检索，如果由模型
主动决定"该搜了"，那是 tool；如果由 client 在会话开始时把目录树注入进去，那是 resource。
同一个能力，两种形态，成本与可控性完全不同。

> 一句话记法：**tool 是模型伸手，resource 是宿主递过来。**

---

## 3. 生命周期：initialize 不是寒暄

```
client → initialize(protocolVersion, capabilities, clientInfo)
server → result(protocolVersion, capabilities, serverInfo)
client → notifications/initialized        （注意：通知，没有 id，不期待回复）
client → tools/list
client → tools/call
```

三件事要看清：

1. **能力协商是双向的**。服务端声明自己提供 `tools/resources/prompts` 中的哪些，
   客户端声明自己支持什么（比如 sampling、roots）。双方都只承诺自己声明过的。
2. **版本号不匹配时要做降级**。`protocolVersion` 是日期字符串（如 `2025-06-18`），
   不匹配时客户端应选一个双方都支持的版本，而不是硬上。
3. **`notifications/initialized` 没有 id**。它是通知，不是请求——没有响应。
   发完它，会话才算"就绪"。很多手写 client 漏这一步，然后奇怪为什么 server 不回。

`raw_client.py` 里这三步是分开打印的，跑一次就能对上。

---

## 4. 传输：stdio 的物理形态

stdio 传输极其朴素：**父进程写一行 JSON 到子进程 stdin，子进程回一行 JSON 到 stdout。**

```
client ──stdin──> server
client <─stdout── server
       （stderr 是日志通道，不属于协议）
```

由此推出本周**头号坑**：

> **绝对不能在 server 里 `print()`。** 任何打到 stdout 的东西都会被当成协议消息，
> 轻则 `json.loads` 报错，重则连接断开。日志一律 `print(..., file=sys.stderr)`。

这不是洁癖，是物理约束：stdout 是数据通道，不是控制台。

另一条：2025-03 版规范已经用 **Streamable HTTP** 取代了早期的 **HTTP+SSE**。
W5 会碰它，本周只在脑子里留个位置：**stdio 是本地子进程，HTTP 是远程服务**，
能力集一样，差别在部署形态与鉴权。

---

## 5. inputSchema 是 JSON Schema，不是"参数说明"

`{"path": {"title": "Path", "type": "string"}}` 这段是**机器可读的契约**，不是给人看的注释。
三个关键字分工明确：

| 关键字 | 作用 | 松了会怎样 |
|---|---|---|
| `required` | 哪些参数必须给 | 模型漏参数，你的函数收到 `None` |
| `enum` | 取值只能在这些里面 | 模型自由发挥（`week2` / `第2周` / `week 2`） |
| `description`（参数级） | 每个参数是什么意思 | 模型猜参数含义，猜错不报错 |

W0 那个 demo 里，`path` 参数的说明是空的——你 docstring 里写的"用绝对路径"落在
**工具说明**里，不在**参数说明**里。补上它，是本周唯一需要额外动手的 schema 细节。

> 记住这条因果：**schema 越松，模型越自由，你的错误处理代码越忙。**

---

## 6. 怎么读 spec（别通读）

`modelcontextprotocol.io` 的规范有几十页。你要读的只有四块，按顺序，两小时够：

1. **Lifecycle**（initialize / 能力协商 / 版本）
2. **Tools**（tools/list、tools/call、返回结构 `content` vs `structuredContent`）
3. **Resources**（uri、mimeType、谁注入）
4. **Transports**（stdio 与 Streamable HTTP 的差别）

读完的标准不是"看完了"，是**能不看文档说出：一次 `tools/call` 的完整报文长什么样**。
你 W0 已经跑过一次，现在只是把经验对上规范条文。

---

## 7. 三个设计判断（这周真正要长出来的东西）

### 7.1 返回片段，不返回全文

W3 算过账：整节返回 ~700 token，一次工具调用就能吃掉一次问答的预算。
所以 `search_notes` 返回 **3 段 × 240 字 + `文件:行号`**。

**但裁剪必须和定位一起给。** 只给片段、不给行号，等于把书合上——模型没法"再读一段"。
`read_section` 的存在就是为了补这个能力。

### 7.2 一个 tool 一件事

`search_notes` 只在"我不知道在哪"时用；`read_section` 只在"我知道在哪、要看细节"时用；
`list_chapters` 只在"连该查哪个文件都不知道"时用。

描述里堆功能（"可以搜索、读取、列目录、统计……"）会让模型分不清何时用哪个——
W5 的误调用统计会把这件事量化。

### 7.3 权限边界写在代码里

`notes_index.py` 的 `_safe_path()` 只允许读 `NOTES_DIR` 下的 `.md`。这条检查**不能**写成
description 里的一句"请只读笔记目录"。模型可以被诱导，代码不会。

---

## 8. 和你已有能力的对照

| 你已经会的 | MCP 里的对应物 |
|---|---|
| ROS 2 的节点发现 + 接口声明 | `initialize` 能力协商 + `tools/list` 自省 |
| ROS 2 service（一问一答，带请求 id） | `tools/call`（JSON-RPC 的 id 就是请求 id） |
| `ros2 run` 拉起一个子进程 | stdio 传输：client 起 server，管道通信 |
| ROS 2 的 topic（持续发布） | 有点像 `notifications/*`：单向、不等回复 |
| CMake 的 `install()` 声明导出什么 | `capabilities`：只承诺声明过的东西 |

最后一行值得多想一秒：**ROS 里一个节点没声明的东西，别人不会去调它**。MCP 也是——
server 没在 `capabilities` 里声明 `resources`，client 就不该去 `resources/list`。

---

## 9. 常见失败清单（照着你大概率会踩的顺序排的）

1. **server 里 `print()` 了**。协议流被污染，client 报 `Expecting value`。
2. **initialize 之前就发 `tools/list`**。规范要求先协商，手写 client 最容易漏。
3. **`notifications/initialized` 带了 id**。它是通知，带 id 就变成了非法请求。
4. **把 resource 当 tool 用**。`resources/list` 里有的东西，模型不会"调用"它。
5. **`inputSchema` 的 `required` 和 `properties` 对不上**。框架通常能校验住，但报错信息难读。
6. **返回全文**。功能对，成本错，W5 会立刻显形。
7. **异常直接抛出协议层**。模型收到的是一条 `isError: true` 的原始堆栈，它不会自我修正。

---

## 10. 验收怎么读

- `python3 raw_client.py` 能打印出完整的 `initialize → tools/list → resources/list`
- `--call search_notes --args '{"query":"正规方程"}'` 返回里**必须有 `file` 和行号**
- 故意传一个不存在的文件给 `read_section`，返回的是**可读错误 + 下一步建议**，不是堆栈
- 你能不看文档说出：`description` 决定什么、`inputSchema` 决定什么、resource 由谁注入

四条都过了再进 W5。W5 开始，你要让**模型**来调这些东西——那时错误会以你意想不到的方式出现。
