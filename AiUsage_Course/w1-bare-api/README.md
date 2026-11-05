# W1 · 裸调用：先看见 HTTP 里的东西

**先读 [`LECTURE.md`](LECTURE.md) 再动手**：概念拆解、你 W0 笔记里那道题的订正、以及和 C++ / ROS 2 / 洛谷刷题的对照都在里面。本文件是操作手册与实验清单。

目标不是"跑通一个 demo"，是**让一次请求和一次响应完全透明**。这一周任何框架都不许碰。

三个脚本，各管一件事：

| 文件 | 角色 | 依赖 |
|---|---|---|
| `raw_http.py` | 手写 HTTP + 手工解析 SSE，什么都不藏 | 无（纯标准库） |
| `hello_llm.py` | 同一个任务用官方 SDK 再写一遍，用来对照 | `openai` |
| `mock_server.py` | 假的 OpenAI 兼容服务，没有 key 也能把逻辑跑通 | 无 |

---

## 三条路，按顺序走

### 路 1：先不联网，把请求体看明白（5 分钟，零成本）

```bash
cd /home/nileuy/Algothrim_proj/AiUsage_Course/w1-bare-api
python3 raw_http.py --dry-run
```

输出里有一段 `--- body ---` 和一段 `--- 等价 curl ---`。**这就是全部的魔法**：一个 POST，一个 JSON，一个 Authorization 头。你现在已经知道大模型应用是怎么回事了，剩下的都是在这上面加东西。

注意 `"stream": true` 旁边那个 `"stream_options": {"include_usage": true}`。删掉它，流式返回里就没有 usage —— 这是最常被误解的一条，实验 1 会让你亲眼看到。

### 路 2：没有 key，用假服务把代码跑通（10 分钟）

```bash
# 终端 A
python3 mock_server.py

# 终端 B
LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_API_KEY=mock LLM_MODEL=mock-model \
    python3 raw_http.py
```

你会看到 SSE 的原始行 `data: {...}`，逐块拼回来的正文，以及最后那一块单独携带 `usage` 的响应。

再跑一次 SDK 版本对照：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
LLM_BASE_URL=http://127.0.0.1:8000/v1 LLM_API_KEY=mock LLM_MODEL=mock-model \
    python hello_llm.py stream
```

两个输出应该几乎一样。**差别在于：一个你什么都能看见，一个你什么都看不见。**这就是框架的本质——它没替你做事，它替你藏事。

### 路 3：换成真模型（准备好再走）

去 `platform.deepseek.com` 拿 key（充 10 元够你这八周所有实验），然后：

```bash
cp .env.example .env
# 编辑 .env，填 LLM_API_KEY
set -a; source .env; set +a
python raw_http.py
python hello_llm.py structured
```

没有条件付费也行：硅基流动（`.env.example` 方案 C）有免费额度，同样是 OpenAI 兼容协议，代码一行不用改。**这正是"协议统一"的价值**——你会亲手体会到为什么大家都要兼容 OpenAI 格式。

---

## 五个实验（这一周真正的功夫在这里）

每个都改一行、跑一次、记一句结论。别跳过。

**实验 1 · 删掉 `stream_options`**
把 `raw_http.py` 里那行注释掉，重跑。usage 变成 `无`。结论：流式默认不报 token 数，**要显式索取**。

**实验 2 · temperature 扫一遍**
`temperature` 改成 0，同一问题跑 5 次，记输出是否完全一致；再改成 1.5 跑 5 次。结论：0 接近确定但仍不保证逐字相同；高温下"同一个 prompt"会给出结构不同的答案。**这就是为什么评测必须跑多次取分布。**

**实验 3 · 指令冲突**
system 里写"只回答英文"，user 里写"用中文回答"。看谁赢。结论决定了你把约束写在哪个位置。

**实验 4 · 故意写错模型名**
`LLM_MODEL=deepseek-chat-xxx`，看报错长什么样。结论：错误信息是可读的、带建议的。**这个认知在 W5 会变成设计原则**——工具的错误也要写成这样，模型才能自我修正。

**实验 5 · 前缀缓存**
同一个 prompt 连发两次，对比第二次 usage 里的缓存字段（DeepSeek 返回 `prompt_cache_hit_tokens`）。结论：**前缀不变 = 省钱**。这是 W3 的地基，现在先看一眼。

---

## 交付物

`w1-bare-api/NOTES.md`：

1. 一张对照表：`raw_http.py` 与 `hello_llm.py` 各自让你看见了什么、藏了什么
2. 五个实验，每个一行结论 + 你认为的原因
3. 一句话回答：为什么 `--dry-run` 看到的 body，和 SDK 实际发出去的一样？

## 验收

- 能画出链路：字符串 → messages 数组 → JSON body → HTTP → SSE 分块 → 拼回来的字符串
- 能说出：`usage` 里三个字段分别对应什么、流式下为什么默认没有
- 能解释：为什么"请输出 JSON"不如 schema 约束可靠（提示：看 `hello_llm.py structured` 里 `json.loads` 失败那条分支）

## 坑

- `pip install openai` 不加镜像会超时，这不是你配错了。
- 别在 `.env` 里写 key 后 commit。`.gitignore` 加上 `.env`。
- 流式下 `chunk.choices` 可能是**空数组**（最后那块只带 usage 的 chunk 就是），直接索引 `[0]` 会 IndexError。`hello_llm.py` 里那句 `if not chunk.choices: continue` 就是为它写的。
