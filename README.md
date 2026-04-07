# Agentic Lab（可运行的 Agent Harness 框架）

Agentic Lab 是一个面向 **工程化 Agent 系统** 的 Python 框架：
它不只做“问答”，而是强调 **计划（Plan）—执行（Execute）—审查（Review）**、工具调用、技能注入、上下文治理、权限护栏与可复盘运行记录。

> 设计目标：让这个仓库从“概念验证”进化为“可持续演进的 Agent Harness”。

---

## 一、总体介绍（先看全貌）

### 1.1 系统流程

```text
用户任务
  ↓
Planner（任务拆解）
  ↓
SkillManager（技能匹配/注入）
  ↓
Orchestrator 主循环
  ├─ ContextManager（上下文预算压缩）
  ├─ LLM Adapter（OpenAI / Anthropic）
  ├─ ToolRegistry（文件/命令等工具）
  ├─ PermissionPipeline（命令权限四阶段）
  └─ Memory + Checkpoint（持久化与复盘）
  ↓
最终输出
```

### 1.2 当前支持能力

- 双 Provider：`openai` + `anthropic`
- 工具调用：OpenAI 兼容 tool-calls（含 `tool_call_id` 回传）
- 技能系统：`skills/*/SKILL.md` 自动加载与触发
- 上下文治理：超预算时压缩历史消息
- 安全执行：Shell 四阶段权限管线
- 可观测性：运行 checkpoint 与 memory 持久化
- 运行方式：CLI + 本地 Web UI

---

## 二、按模块介绍（逐个解释职责）

### 2.1 `config.py` — 配置中心

- 统一读取环境变量（provider/model/key/base_url 等）
- 默认 skills 目录使用包内绝对路径，避免“安装后换目录就找不到技能”

### 2.2 `schemas.py` — 协议数据结构

- `ChatMessage`：统一消息结构
- `ToolCall`：函数调用结构，支持 `call_id`
- `LLMResponse` / `TaskPlan` / `ReviewReport`

### 2.3 `llm.py` — 模型适配层

- `OpenAICompatLLM`：OpenAI 兼容接口，支持 tool-calls
- `AnthropicLLM`：Anthropic Messages API
- `build_llm()`：provider 工厂
- 无 key 时自动 offline fallback，便于本地流程调试

### 2.4 `planner.py` — 计划器

- 当前为启发式 Planner，输出可审计步骤
- 后续可替换为分层规划器或多 Agent Planner

### 2.5 `skills_engine.py` — 技能系统

- 扫描 `skills/*/SKILL.md`
- 支持显式技能（`--skills`）与触发词自动匹配
- 将技能内容注入系统上下文，形成可复用 SOP

### 2.6 `context.py` — 上下文治理

- 控制上下文预算
- 对历史内容进行 snip + summary + keep_recent
- 避免长任务因上下文膨胀导致质量下降

### 2.7 `security.py` + `tools/shell.py` — 安全护栏

- 引入四阶段权限管线：parse → classify → policy → final
- Shell 工具先过权限评估，再执行命令
- 阻断高风险命令模式，降低误操作风险

### 2.8 `tools/` — 工具体系

- `base.py`：Tool 抽象与注册表
- `fs.py`：读写文件、唯一替换
- `shell.py`：安全命令执行

### 2.9 `memory.py` — 记忆系统

- append-only 存储
- 关键词召回
- 为跨任务连续工作提供“弱长期记忆”

### 2.10 `orchestrator.py` — 运行时核心

- 串联计划、技能、上下文、模型、工具、记忆、checkpoint
- 负责每轮 tool-calls 的执行与消息回填
- checkpoint 文件名含微秒 + 随机后缀，避免并发覆盖

### 2.11 `cli.py` / `webui.py` — 交互入口

- CLI：
  - `agentic run "..."`
  - `agentic skills`
  - `agentic ui`
- Web UI：本地可选控制台，便于演示与业务协作

---

## 三、快速使用

### 3.1 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3.2 OpenAI 模式

```bash
export AGENTIC_PROVIDER=openai
export OPENAI_API_KEY=xxx
agentic run "审查仓库并输出重构建议"
```

### 3.3 Anthropic 模式

```bash
export AGENTIC_PROVIDER=anthropic
export ANTHROPIC_API_KEY=xxx
agentic run "基于文档输出执行计划"
```

### 3.4 Skills 与 UI

```bash
agentic skills
agentic run "重构 Python 代码" --skills coding
agentic ui --host 127.0.0.1 --port 8765
```

---

## 四、下一步建议（高优先级）

1. 增加单元测试（LLM mock、tool call round-trip、permission pipeline）
2. 引入语义记忆（embedding）替代关键词召回
3. 增加 Reviewer 子代理，实现“自动回流重规划”
4. 增加 Hook 系统（before_tool/after_tool/on_error）
