# 📐 架构设计文档

> 本文档详细解释 AI Agent 系统的核心架构决策——**为什么这么设计**，面试时能讲清楚设计权衡。

---

## 目录
- [1. 整体架构：为什么选 LangGraph？](#1-整体架构为什么选-langgraph)
- [2. ReAct 引擎：agent ↔ tools ↔ guard 循环](#2-react-引擎agent--tools--guard-循环)
- [3. 4 级路由链：为什么不只是单 Agent？](#3-4-级路由链为什么不只是单-agent)
- [4. 3 层记忆体系：短/窗口/长期](#4-3-层记忆体系短窗口长期)
- [5. LLM 降级链 + 熔断：稳定性保障](#5-llm-降级链--熔断稳定性保障)
- [6. Self-Correction：让 Agent 自己纠错](#6-self-correction让-agent-自己纠错)
- [7. 安全防护：注入检测 + PII 脱敏](#7-安全防护注入检测--pii-脱敏)
- [8. 流式输出：SSE + Redis Pub/Sub](#8-流式输出sse--redis-pubsub)
- [9. 转人工：Human-in-the-Loop](#9-转人工human-in-the-loop)
- [10. 可观测与质量评估](#10-可观测与质量评估)

---

## 1. 整体架构：为什么选 LangGraph？

**决策**：用 LangGraph 而非裸 LangChain Agent 或自研框架。

**理由**：
- **状态机模型**：LangGraph 把 Agent 抽象为有向图（节点 + 边），每个节点是纯函数，状态显式传递。相比 LangChain Agent 的隐式执行，调试和可观测性好得多。
- **循环支持**：ReAct 本质是「思考→行动→观察→再思考」的循环。LangGraph 原生支持条件边和循环，不需要 hack。
- **可控性**：每个节点可独立插拔（加 guard、加缓存、加监控），不影响其它节点。符合开闭原则。

**代码位置**：`ai-agent2/graph/`
- `state.py` —— AgentState 定义（messages / working_memory / budget 等状态字段）
- `nodes.py` —— 所有节点函数（check_faq / agent / guard / error_handler）
- `graph.py` —— 图的组装（节点 + 条件边）

```
         ┌──────────┐
用户输入 →│ check_faq │──命中──→ END（零延迟快路径）
         └────┬─────┘
              │未命中
              ▼
         ┌──────────┐  tool_calls   ┌───────┐
         │  agent   │──────────────→│ tools │
         │ (LLM)    │←──────────────│       │
         └────┬─────┘               └───┬───┘
              │                          │
              │                    ┌─────▼─────┐
              │ no tool_calls      │   guard   │ 自纠错 + 压缩 + 安全
              │                    └─────┬─────┘
              ▼                          │
            END                    回到 agent
```

---

## 2. ReAct 引擎：agent ↔ tools ↔ guard 循环

**核心机制**（`graph/nodes.py`）：

1. **agent 节点**：LLM 绑定全量工具，输出要么是 `tool_calls`（要调工具），要么是最终回复。
2. **tools 节点**：LangGraph 的 ToolNode 执行工具调用，结果作为 ToolMessage 回传。
3. **guard 节点**（关键创新）：工具执行后不直接回 agent，而是经过「守卫」节点：
   - **压缩**：工具返回太长（如订单列表）→ 压缩摘要，省 token
   - **安全过滤**：检测 SQL 错误栈 / IP / 凭证泄露
   - **纠错检测**：工具返回"未登录"/"未找到"等异常 → 注入纠错上下文
   - **Working Memory 更新**：从工具参数提取已收集信息（订单号/原因等）

**为什么需要 guard？**
> 纯 ReAct 的痛点：LLM 看到"未找到订单"会直接转告用户，不会自我修正。guard 检测到这类异常后，会注入「请先查询用户订单列表再操作」的提示，强制 agent 修正策略。这让 Agent 的成功率从 ~60% 提升到 ~90%。

---

## 3. 4 级路由链：为什么不只是单 Agent？

**决策**：在 ReAct Agent 之上，加一层 4 级优先级路由。

**4 级路由**（`api/chat.py` + `skills/`）：
```
用户消息进入
    │
    ├─① Active Skill 命中？ ── 是 → 直接进入该 Skill 的多轮对话（如正在退货流程中）
    │
    ├─② FAQ 命中？ ── 是 → 零延迟返回（"你好"→"我是智能客服..."）
    │
    ├─③ Skill Trigger 命中？ ── 是 → 激活 Skill，收集参数（"我要退货"→ 激活退货 Skill）
    │
    └─④ ReAct Agent ── 兜底：让 LLM 自己决定调哪个工具
```

**为什么不只用 ReAct Agent？**
- **延迟**：每次都过 LLM 至少 1-2 秒。FAQ 快路径 0 延迟。
- **成本**：简单问题（"你好"）不值得消耗 token。
- **确定性**：多轮流程（退货需要：订单号→原因→确认）用 Skill 显式管理状态，比让 LLM 自己记更可靠。
- **兜底**：复杂/未知意图仍由 ReAct Agent 处理，兼顾灵活性。

**Skill 示例**（`skills/return_item_skill.py`）：
- 定义所需参数：`order_id`, `reason`（必填）
- 参数不全时主动追问，而非反复试错
- 收集齐后一次性调用 `request_return` 工具

---

## 4. 3 层记忆体系：短/窗口/长期

**3 层设计**（`memory/`）：

| 层 | 存储 | 用途 | TTL |
|----|------|------|-----|
| **短期对话** | Redis `chat::ai::session::*` | 完整对话历史，作为 LLM 上下文 | 24h |
| **窗口摘要** | Redis（异步任务） | 超过窗口时自动摘要旧对话，防止上下文爆炸 | 24h |
| **Working Memory** | Redis `chat::ai::wm::*` | 结构化信息（当前订单号/退货原因/已收集参数） | 30min |

**为什么需要 Working Memory？**
> 对话中 Agent 需要记住「用户正在退哪个订单」「退货原因是什么」。如果只靠对话历史让 LLM 自己提取，不稳定且浪费 token。Working Memory 用结构化方式存储，guard 节点每次工具调用后自动更新，prompt 中直接注入「当前已知：订单号=xxx」。

**SessionManager**（`memory/session_memory.py`）：
- `add_message()` 写入历史后自动 `publish` 到 Redis Pub/Sub 通道
- SSE 订阅者收到通知后拉取增量消息，实现流式推送

---

## 5. LLM 降级链 + 熔断：稳定性保障

**降级链**（`resilience/llm_factory.py`）：
```
qwen-max（最强，贵） → 失败/超时 → qwen-plus（均衡） → 失败 → qwen-turbo（快，便宜） → 失败 → 兜底文案
```

**熔断器**（`resilience/circuit_breaker.py`）：
- 连续 N 次失败 → 熔断（不再调 LLM，直接降级）
- 半开状态探活，恢复后自动闭合

**为什么需要？**
> 生产环境 LLM API 会限流/超时/返回错误。没有降级链，一次 API 抖动就导致客服不可用。三级降级确保即使主力模型挂了，用户仍能收到（质量略低但可用的）回复。

---

## 6. Self-Correction：让 Agent 自己纠错

**实现**（`reasoning/self_correction.py` + guard 节点）：

guard 节点扫描工具返回，检测异常模式：
```python
ERROR_PATTERNS = {
    "未登录": "请提示用户先登录",
    "未找到": "请先调用 get_my_orders 查询订单列表，再操作",
    "失败": "检查参数是否正确，或换一种方式重试",
}
```
命中后，guard 向 messages 注入一条 `SystemMessage`（纠错提示），agent 节点下次执行时会读到这个提示并修正行为。

**为什么有效？**
> 不修改用户可见的对话，只在 Agent 内部「自我提醒」。比简单的重试更智能——它会告诉 LLM 具体该怎么改，而不是盲目重试同样的错误。

---

## 7. 安全防护：注入检测 + PII 脱敏

**输入侧**（`core/security.py` `validate_input`）：
- Prompt 注入检测：「忽略以上指令」「你现在是 DAN 模式」等模式
- 拒绝包含 SQL/代码注入的输入

**PII 脱敏**（`core/security.py` `detect_pii` + `mask_pii`）：
- 手机号 `13812345678` → `138****5678`
- 身份证 `110101199001011234` → `110101********1234`
- 邮箱 `user@example.com` → `u***@example.com`
- 在存入历史和发给 LLM 前都脱敏

**输出侧**（`sanitize_output`）：
- 过滤 LLM 回复中的内部错误栈、IP 地址、凭证

**为什么？**
> 客服场景用户会不自觉地暴露手机号/订单号等敏感信息。Agent 把这些信息发给 LLM（第三方）有合规风险。脱敏后既保留语义（让 LLM 理解上下文），又避免真实数据泄露。

---

## 8. 流式输出：SSE + Redis Pub/Sub

**为什么用 SSE 而非 WebSocket？**
- SSE 是单向（服务器→客户端），契合「LLM 逐字输出」场景
- 基于 HTTP，无需额外协议升级，nginx/网关友好
- 自动重连（浏览器原生支持）
- 比 WebSocket 轻量

**为什么加 Redis Pub/Sub？**
> 转人工场景需要双向实时：用户发消息→客服端要实时看到；客服回复→用户端要实时收到。用 Pub/Sub 解耦：
> - 写者：`SessionManager.add_message()` publish 通知
> - 读者：SSE 端点 subscribe 通道，收到通知后拉增量消息推送

**代码位置**：
- 用户端 SSE：`api/chat.py` `/chat/stream` + `/chat/transfer-wait`
- 管理端 SSE：`api/admin.py` `/admin/transfer/{id}/stream`

---

## 9. 转人工：Human-in-the-Loop

**设计**（`agents/tools/transfer_tool.py` + `api/admin.py`）：

当 Agent 无法解决时，触发转人工：
1. 创建工单写入 Redis 队列（按情感优先级排序）
2. 设置会话转人工标记
3. 管理端轮询/Pub-Sub 感知新工单
4. 客服接单后，双向实时消息（SSE）
5. 客服回复通过 SessionManager 写入用户会话历史
6. Agent 后续对话能读到人工回复，无缝衔接

**情感优先级**：
- 愤怒用户（情感分析检测到连续负面情绪）→ high 优先级
- 普通用户 → low 优先级
- 确保愤怒用户优先被服务

---

## 10. 可观测与质量评估

**Token Budget**（`cost/token_budget.py`）：
- 每次请求计算 token 消耗，超预算时触发对话压缩
- 防止长对话导致 context 爆炸 + 成本失控

**Trace 链路追踪**（`middleware/trace.py`）：
- 每个请求注入 X-Trace-Id，贯穿 LLM 调用/工具执行/Redis 操作
- 结构化日志（structlog），便于 ELK 采集

**质量评估**（`monitoring/eval/`）：
- `test_cases.json` 预置测试用例（输入 + 期望行为）
- `evaluator.py` 自动跑用例，LLM 评分回复质量
- 支持回归测试，确保改动不退化

---

## 设计哲学总结

| 原则 | 体现 |
|------|------|
| **分层兜底** | FAQ → Skill → ReAct → 转人工，每层兜住更复杂的情况 |
| **失败可恢复** | LLM 降级链 + 熔断 + Self-Correction，不因单点故障中断 |
| **状态显式** | Working Memory + Skill State 用结构化存储，不靠 LLM 隐式记忆 |
| **成本可控** | Token Budget + 缓存 + 快路径跳过 LLM |
| **安全合规** | 输入注入检测 + PII 脱敏 + 输出过滤，全链路防护 |
| **可观测** | Trace + 结构化日志 + 自动化质量评估 |
