# Agentic Lab

一个可运行的 Agentic 框架（Python），吸收了以下项目思路并落地为可执行代码：

- [claude-code-best/claude-code](https://github.com/claude-code-best/claude-code)：强调工程化、模块化、可构建与可调试。
- [zts212653/clowder-ai](https://github.com/zts212653/clowder-ai)：强调多角色协作、共享记忆、流程纪律。
- [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)：强调从最小循环到完整 agent harness 的演进学习路径。

> 目标：不仅是 coding agent，还可扩展为 research / ops / analysis 等多场景 agentic runtime。

---

## 核心能力

1. **Plan-Execute-Review 主循环**
   - 显式 Planner 输出计划；
   - Orchestrator 负责工具循环与验证导向输出；
   - 全流程 checkpoint 可复盘。

2. **Anthropic Skills 支持（新增）**
   - 内置 `skills/*/SKILL.md`；
   - 自动按 task 触发或通过 `--skills` 显式指定；
   - 将 skill 内容注入系统上下文，形成可组合工作流。

3. **双 Provider 支持**
   - `AGENTIC_PROVIDER=openai`：支持 tool-calls。
   - `AGENTIC_PROVIDER=anthropic`：走 Anthropic Messages API。

4. **可选的精美 Web UI（新增）**
   - 本地启动 `agentic ui`；
   - 渐变视觉 + 任务输入 + 技能输入 + 结果面板；
   - 适合演示和非技术用户协作。

---

## 快速开始

### 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### OpenAI 模式

```bash
export AGENTIC_PROVIDER=openai
export OPENAI_API_KEY=xxx
export AGENTIC_MODEL=gpt-4.1-mini
agentic run "审查项目并提出重构方案"
```

### Anthropic 模式

```bash
export AGENTIC_PROVIDER=anthropic
export ANTHROPIC_API_KEY=xxx
export AGENTIC_MODEL=claude-3-7-sonnet-latest
agentic run "基于文档输出一份执行计划"
```

### Skills

```bash
agentic skills
agentic run "重构这段 Python 代码" --skills coding
```

### Web UI

```bash
agentic ui --host 127.0.0.1 --port 8765
# 浏览器打开 http://127.0.0.1:8765
```

---

## 目录结构

```text
src/agentic_lab/
├── cli.py
├── config.py
├── llm.py
├── memory.py
├── orchestrator.py
├── planner.py
├── schemas.py
├── skills_engine.py
├── webui.py
├── tools/
│   ├── base.py
│   ├── fs.py
│   └── shell.py
└── skills/
    ├── coding/SKILL.md
    └── research/SKILL.md
```

---

## 设计上的进一步优化建议


### 合并与运行稳定性修复

- OpenAI 工具调用链已对齐 `tool_call_id` 回传要求，避免 tool round-trip 400。
- 默认 skills 路径改为包内绝对路径，安装后在任意工作目录都能识别内置技能。
- checkpoint 文件名加入微秒与随机后缀，避免并发运行覆盖。


1. 引入 TeamCoordinator：Builder / Critic / Researcher 多 Agent 编排。
2. `MemoryStore` 升级为向量检索与时间衰减策略。
3. Shell 工具从 denylist 进化到 allowlist + policy gate。
4. 增加 E2E regression tests（含 tool-call replay）。


---

## 合并冲突说明（这次你提到的“合入冲突”）

常见原因：

1. 多个分支同时修改了 `README.md`/`pyproject.toml` 同一区域；
2. 文件换行符不一致（CRLF/LF）；
3. 同时新增目录结构和文档目录树，造成同段落冲突。

我已在仓库增加 `.gitattributes`：

- 统一文本文件为 `LF`；
- 对 `*.md`（尤其 `README.md`）使用 `merge=union`，降低文档冲突概率；
- 代码文件保持普通文本合并，避免错误自动拼接。

如果你愿意，我下一步可以再补一个 `CONTRIBUTING.md`，把分支合并顺序和 release 流程标准化，进一步减少冲突。
