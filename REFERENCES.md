# 参考项目与借鉴点

本文档列出本仓在设计和实现中参考过的项目，并说明“借鉴了什么”。

---

## 1) he-yufeng/CoreCoder
- 项目地址：https://github.com/he-yufeng/CoreCoder
- 项目定位：轻量、可读、最小可运行的 coding agent 框架。

### 借鉴内容
1. **主循环范式**：`用户输入 -> LLM -> tool call -> tool结果回填 -> 再问LLM`
2. **工具优先**：通过统一工具协议扩展能力，而不是堆 prompt
3. **工程最小闭环**：能跑、能改、能复盘，优先可维护性

---

## 2) zts212653/clowder-ai
- 项目地址：https://github.com/zts212653/clowder-ai
- 项目定位：更偏“团队协作/多角色”的 Agent 系统思路。

### 借鉴内容
1. **角色化流程**：Plan / Execute / Review 分工思想
2. **共享记忆**：任务过程沉淀可被后续任务利用
3. **体系化扩展**：支持从单 agent 进化到多 agent 协作

---

## 3) claude-code-best/claude-code
- 项目地址：https://github.com/claude-code-best/claude-code
- 项目定位：Claude Code 相关工程实践与结构化实现参考。

### 借鉴内容
1. **模块边界清晰**：配置、编排、工具、运行入口解耦
2. **可演进架构**：便于后续接入权限、钩子、技能体系
3. **工程落地导向**：强调可执行、可迭代而非纯概念

---

## 4) shareAI-lab/learn-claude-code
- 项目地址：https://github.com/shareAI-lab/learn-claude-code
- 项目定位：面向 Claude Code 的学习和拆解路径。

### 借鉴内容
1. **从最小到系统化**的学习路线
2. **结构化理解 Agent Harness**（循环、工具、上下文、权限）
3. **强调“可解释设计”**，便于团队知识传递

---

## 5) lintsinghua/claude-code-book
- 项目地址：https://github.com/lintsinghua/claude-code-book
- 项目定位：对 Agent Harness（尤其 Claude Code 架构思想）进行系统化分析。

### 借鉴内容（本次优化重点）
1. **上下文预算治理**：新增 `context.py`，在长对话时压缩上下文
2. **权限管线思维**：新增 `security.py`，命令执行采用四阶段评估
3. **Harness 化组织**：强化 orchestrator 作为“承载层”的职责边界
4. **设计可迁移性**：将具体模型/工具实现与运行时框架分离

---

## 说明
- 本项目为“借鉴架构思想 + 自主实现代码”。
- 若后续继续扩展（Hook、子代理、MCP、Plan Mode），会持续补充本文件。
