# Agentic Lab

一个**可直接运行**的 Agentic 框架（Python），参考了：

- CoreCoder 的“最小可运行 coding agent 主循环 + 工具系统”思路；
- Clowder AI 的“多角色协作（plan/execute/review）、可持续记忆、团队化协作”思路。

> 目标：不只做 coding agent，而是做一个可扩展到“分析、运营、研究、自动化任务”的通用 Agentic 骨架。

---

## 1. 这个框架解决什么问题

很多项目有以下痛点：

1. 只有“LLM + prompt”，没有可观测结构；
2. 工具调用和任务规划混在一起，不可维护；
3. 一轮对话结束后没有可复用记忆；
4. 任务执行缺少 checkpoint 和复盘线索。

**Agentic Lab**给出一版可落地解决方案：

- Planner：先给出任务计划（可审计）；
- Executor：按工具协议执行；
- Reviewer：通过规则要求“先验证后输出”；
- Memory：跨任务可检索记忆；
- Checkpoint：每次运行落盘，支持复盘。

---

## 2. 快速开始

### 2.1 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2.2 配置

可用 `.env` 或环境变量：

```bash
export OPENAI_API_KEY=你的key
export OPENAI_BASE_URL=https://api.openai.com/v1
export AGENTIC_MODEL=gpt-4.1-mini
```

> 不配置 `OPENAI_API_KEY` 也能跑（offline mode），用于验证流程与框架连通性。

### 2.3 运行

```bash
agentic run "阅读项目并提出架构优化建议"
```

输出包括：

- 终端最终结果；
- `.agentic/memory.jsonl` 记忆；
- `.agentic/checkpoints/run-*.json` 执行快照。

---

## 3. 架构说明（核心）

```text
User Task
   ↓
HeuristicPlanner (显式计划)
   ↓
AgenticOrchestrator
   ├─ Memory Recall (历史经验检索)
   ├─ LLM chat loop (支持 tool calls)
   ├─ ToolRegistry.execute(...)
   ├─ Result synthesis
   └─ Checkpoint + Memory writeback
```

### 3.1 为什么这是对 CoreCoder 思路的延展

CoreCoder 非常强在“最小主循环 + 工具调用闭环”。
本项目延展点：

1. **显式 Planner 层**（新增）
   - 让主循环更可解释，便于多人协作和审核。
2. **跨任务 Memory**（新增）
   - 不是只依赖当前 context，而是可累积经验。
3. **Checkpoint 机制**（新增）
   - 每次运行有 JSON 轨迹，利于排障和治理。

### 3.2 为什么这是对 Clowder 思路的轻量落地

Clowder 强调“团队化协作、共享记忆、纪律性流程”。
本项目以单进程轻量实现了其中关键能力：

- shared memory（MemoryStore）；
- SOP-like流程（plan → execute → verify）；
- 可继续扩展到多 agent（见 roadmap）。

---

## 4. 目录结构

```text
src/agentic_lab/
├── cli.py              # CLI 入口
├── config.py           # 环境变量与运行参数
├── llm.py              # OpenAI-compatible 客户端（含离线兜底）
├── memory.py           # append-only 记忆存储 + 关键词检索
├── orchestrator.py     # 框架主循环与checkpoint
├── planner.py          # 任务规划器
├── schemas.py          # 数据结构（消息、tool call、plan、review）
└── tools/
    ├── base.py         # 工具基类 + 注册器
    ├── fs.py           # read/write/replace 工具
    ├── shell.py        # 安全shell工具（denylist + timeout）
    └── __init__.py
```

---

## 5. 可扩展点（重点给你后续“碰撞思路”）

### 5.1 多 Agent 团队化（推荐下一步）

在 `orchestrator.py` 上层增加 `TeamCoordinator`：

- ArchitectAgent：负责分解任务与设计；
- BuilderAgent：负责执行工具；
- CriticAgent：负责审查风险与测试覆盖；
- Router：根据任务类型分发（coding/analysis/ops）。

### 5.2 从“关键词记忆”升级到“语义记忆”

当前 `MemoryStore.recall()` 是关键词 overlap，简单但稳定。
可升级为：

- embedding + 向量检索；
- 记忆 TTL 与置信度；
- 决策日志（decision record）单独索引。

### 5.3 更强安全与治理

- Shell 工具从 denylist 升级为 allowlist；
- 工具权限按任务动态下发（policy engine）；
- 审批门禁（高风险操作需人工确认）。

### 5.4 更真实的 Reviewer

当前 Reviewer 通过 system rules 约束。
可升级为：

- 独立 reviewer 模型调用；
- 自动生成“验证计划 + 执行证据 + 结论”；
- 不通过时自动回流到 Planner 重规划。

---

## 6. 与常见 agent 框架的差异

- 比“纯 prompt agent”更工程化（可审计、可回放）；
- 比“大而全平台”更轻量，能快速改造；
- 对 coding 场景友好，但天然支持非 coding 工作流。

---

## 7. 直接可用示例

### 示例 1：代码改造任务

```bash
agentic run "读取 src/app.py，找出重复逻辑并重构"
```

### 示例 2：非 coding 任务

```bash
agentic run "基于 docs/ 的内容输出一份对外发布说明和风险清单"
```

---

## 8. 后续建议（我建议你优先做）

1. 增加 `team.py`，实现双 agent（Builder + Reviewer）最小闭环；
2. 给 `memory.py` 增加 embeddings 后端接口；
3. 给每个工具加 `risk_level`，执行前策略判断；
4. 新增 `examples/` 放 3 个端到端任务样例。

这样你就从“单 agent 框架”升级到“可演进的 agentic platform 雏形”。
