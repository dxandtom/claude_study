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

1. 引入 TeamCoordinator：Builder / Critic / Researcher 多 Agent 编排。
2. `MemoryStore` 升级为向量检索与时间衰减策略。
3. Shell 工具从 denylist 进化到 allowlist + policy gate。
4. 增加 E2E regression tests（含 tool-call replay）。
