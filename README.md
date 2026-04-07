# CoreCoder 代码阅读笔记（基于 he-yufeng/CoreCoder）

> 目标仓库：<https://github.com/he-yufeng/CoreCoder>
>
> 这份文档不是官方 README 的翻译，而是面向“快速读懂实现”的技术解读。

## 1. 项目定位（一句话）

CoreCoder 是一个“最小可运行”的 AI Coding Agent：把 Claude Code 的一些核心模式压缩成一个小体量 Python 工程，重点是**可读性与可二次开发**。

---

## 2. 整体架构

从目录和实现上看，核心由 4 层组成：

1. **CLI 层（`cli.py`）**
   - 提供交互式 REPL + one-shot 模式。
   - 支持 `/model`、`/compact`、`/save`、`/sessions`、`/diff` 等命令。

2. **Agent 循环层（`agent.py`）**
   - 主循环是：`用户输入 -> LLM -> 工具调用 -> 回填工具结果 -> 再问 LLM`。
   - 当模型不再返回 tool calls 时，表示本轮任务完成。
   - 支持多工具并行执行（线程池）。

3. **LLM 抽象层（`llm.py`）**
   - 基于 OpenAI 兼容接口封装，统一调用不同模型提供方。
   - 支持流式 token 输出、tool call 聚合、重试机制、粗略成本估算。

4. **Tools 工具层（`tools/*.py`）**
   - 包含 bash/read/write/edit/glob/grep/agent 七类工具。
   - 通过统一 Tool 基类暴露 schema，让模型可以函数调用。

---

## 3. Agent 主循环：这个项目最关键的逻辑

`corecoder/agent.py` 的设计非常“直白”：

- 每次 `chat()` 会把用户消息追加到历史。
- 调用 `ContextManager.maybe_compress()`，避免上下文爆掉。
- 把 `system prompt + history + tool schemas` 一起喂给 LLM。
- 若返回普通文本：结束本轮。
- 若返回 tool calls：执行工具，把结果以 `role=tool` 追加，再继续下一轮。
- 默认 `max_rounds=50`，防止死循环。

这个结构非常适合二次开发：你只要改 tools 或 prompt，就能明显改变 agent 行为。

---

## 4. 上下文压缩策略（实用）

`corecoder/context.py` 实现了 3 层压缩（按 token 使用比例触发）：

1. **snip（50%）**：先截断超长工具输出（保留首尾信息）。
2. **summarize（70%）**：对较早对话做 LLM 摘要，只保留最近窗口。
3. **hard collapse（90%）**：紧急压缩，只保留摘要 + 最近少量消息。

这套策略的价值是：

- 不依赖复杂缓存系统，也能把“长任务对话”跑得比较稳。
- 相比简单“截断前文”，它尽量保留任务状态（改了哪些文件、遇到什么错误）。

---

## 5. 工具系统（为什么可扩展）

工具注册在 `tools/__init__.py`，核心工具职责如下：

- `read_file`：按行号读取文件（鼓励先读后改）。
- `write_file`：整文件覆盖写。
- `edit_file`：**精确字符串替换**（要求 `old_string` 在文件中唯一匹配），并返回 unified diff。
- `glob`：按模式查文件。
- `grep`：正则检索内容。
- `bash`：执行 shell，含危险命令拦截、超时控制、输出截断、`cd` 路径跟踪。
- `agent`：拉起“子代理”处理复杂子任务，返回摘要给父代理（并限制输出长度，防止上下文污染）。

其中 `edit_file` 的唯一匹配约束非常关键：可以显著降低“改错位置”风险，也更容易 code review。

---

## 6. LLM 层实现亮点

`corecoder/llm.py` 里有几个工程化细节值得学习：

- **流式解析**：边收 token 边打印，同时累积工具调用参数。
- **tool calls 聚合**：处理分片返回的函数参数 JSON，再统一解析。
- **重试机制**：对限流、超时、连接异常做指数退避。
- **成本估算**：内置部分模型单价表，基于累计 token 粗估成本。

这让它在“很小代码量”下，具备了接近生产可用的基本鲁棒性。

---

## 7. 配置与会话

- `config.py`：
  - 支持 `.env` 与环境变量读取。
  - 兼容常见变量名（如 `OPENAI_API_KEY` / `OPENAI_BASE_URL`）。
- `session.py`：
  - 会话持久化到 `~/.corecoder/sessions/*.json`。
  - 可列出历史会话并恢复上下文继续做任务。

这个设计很“本地优先”：简单、可调试、几乎零额外依赖。

---

## 8. 我对这个项目的评价（读码结论）

### 优点

1. **结构清晰**：单文件职责边界明显，适合学习 agent 架构。
2. **最小可用**：实现了真实可运行的循环，而不只是 demo。
3. **扩展成本低**：新增 Tool 基本是“小类 + schema + execute”。
4. **安全意识在线**：bash 工具带危险命令检测与超时机制。

### 局限

1. **复杂任务能力上限受限**：缺少更深层规划器/记忆系统。
2. **并发工具是线程池级别**：适合轻量任务，不是高吞吐调度框架。
3. **安全策略是正则黑名单**：实用但非完备沙箱。
4. **成本表需要持续维护**：模型价格变化快，可能过时。

---

## 9. 适合怎么用

我建议把 CoreCoder 当成：

- 学习 AI Coding Agent 的“骨架项目”；
- 自己做内部 coding assistant 的起点；
- 快速实验“提示词 + 工具设计 + 上下文压缩”组合的实验场。

如果你要做企业级版本，可以在它上面逐步加：

- 权限更细的命令执行沙箱；
- 更强的任务规划/回滚机制；
- 更稳定的长上下文记忆（向量库或结构化状态存储）；
- 更完备的可观测性（trace、tool latency、失败原因统计）。

---

## 10. 快速上手（参考）

```bash
pip install corecoder

# 以 OpenAI 兼容接口为例
export OPENAI_API_KEY=your_key
# 如需第三方兼容网关可设置 OPENAI_BASE_URL

corecoder -m gpt-4o
```

进入交互后，可先试：

- `read README.md，列出待改进点并直接修改`
- `/tokens` 查看 token 使用
- `/compact` 主动压缩上下文
- `/save` 保存当前会话

---

## 11. 你如果想继续深入，我建议下一步看什么

1. 先读 `tools/base.py` + `tools/__init__.py`（理解工具协议）。
2. 再读 `agent.py`（理解主循环）。
3. 再读 `context.py`（理解长任务稳定性）。
4. 最后读 `llm.py`（理解流式 + 函数调用落地细节）。

这样能最快把“一个 coding agent 怎么跑起来”建立成完整心智模型。
