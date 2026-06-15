"""LangGraph 节点定义 — 所有节点函数、路由函数、辅助函数

节点职责：
    check_faq:       匹配问候语和功能介绍（零延迟快路径）
    agent:           LLM 调用（绑定全量工具 + 统一 Prompt + WM/Budget 上下文）
    guard:           工具输出守卫（压缩 → 安全过滤 → 纠错 → WM 更新 → 指标记录）
    mark_failed:     标记 LLM 失败（触发降级）
    error_handler:   错误兜底回复

路由函数：
    _route_after_faq:   FAQ 匹配后 → END / agent
    _route_after_agent: agent 后 → tools / mark_failed / error_handler / END
"""

import time
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from graph.state import AgentState
from resilience.llm_factory import mark_llm_failed, LLMFallbackException
from agents.tools import ALL_TOOLS
from agents.tools.constants import ERROR_KEYWORDS
from agents.faq import match_greeting, match_feature_query
from reasoning.prompts import build_unified_prompt
from reasoning.self_correction import apply_guard_and_correct
from reasoning.compressor import compress_tool_output
from memory.working_memory import get_working_memory, Phase
from langgraph.graph import END
import structlog

logger = structlog.get_logger(__name__)


# Working Memory — 工具参数提取映射
WM_TOOL_ARG_MAP = {
    "cancel_order":     {"order_id": "order_id"},
    "request_refund":   {"order_id": "order_id", "reason": "reason", "amount": "amount"},
    "request_return":   {"order_id": "order_id", "reason": "reason", "return_type": "return_type"},
    "submit_complaint":  {"order_id": "order_id", "complaint_type": "complaint_type", "detail": "detail"},
    "cancel_refund":    {"refund_id": "refund_id"},
    "remind_delivery":  {"order_id": "order_id"},
    "check_refund_status": {"refund_id": "refund_id"},
    "track_logistics":  {"order_id": "order_id"},
    "get_my_orders":    {"productKeyword": "product_keyword"},
}

# 调用成功后自动标记任务完成的工具（执行类操作）
WM_COMPLETION_TOOLS = {
    "cancel_order", "request_refund", "request_return",
    "submit_complaint", "cancel_refund", "remind_delivery",
}


# ============================================================
# 节点函数
# ============================================================

def check_faq_node(state: AgentState) -> dict:
    """匹配问候语和功能介绍（零延迟快路径）"""
    messages = state["messages"]
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break
    reply = match_greeting(last_user_msg) or match_feature_query(last_user_msg)
    return {"faq_reply": reply or ""}


def guard_node(state: AgentState) -> dict:
    """工具输出守卫 + 自纠错 + Working Memory 更新
    职责：
    ① 压缩长输出（减少 token 消耗）
    ② 安全过滤（检测 SQL 异常栈/IP/凭证泄露）
    ③ 纠错检测（未登录/未找到/操作失败/资源不足）
    ④ 纠错上下文注入（强制 LLM 修正策略）
    ⑤ Working Memory 更新（从工具调用参数中提取已收集信息）
    ⑥ 记录工具调用明细（Dashboard）
    """
    messages = state["messages"]
    t0 = time.monotonic()
    guarded_msgs = []
    tool_count = 0
    corrections_injected = 0

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_count += 1
            tool_name = getattr(msg, "name", "")
            # ① 压缩长输出
            original_content = str(msg.content or "")
            compressed_content = compress_tool_output(original_content, tool_name)
            if compressed_content != original_content:
                msg = ToolMessage(content=compressed_content, tool_call_id=msg.tool_call_id, name=tool_name)
            # ② 安全过滤 + 纠错检测
            guarded, needs_correction, correction_ctx = apply_guard_and_correct(msg)
            guarded_msgs.insert(0, guarded)
            if needs_correction:
                corrections_injected += 1
        elif guarded_msgs:
            break

    if tool_count == 0:
        return {}

    elapsed = (time.monotonic() - t0) * 1000

    # ⑤ Working Memory 更新
    session_id = state.get("session_id", "")
    if session_id:
        try:
            _update_working_memory(messages, session_id, guarded_msgs)
        except Exception as e:
            logger.warning("wm_update_failed", error=str(e))

    # ⑥ 记录工具调用明细
    try:
        from monitoring.dashboard import record_tool_detail_sync
        for msg in guarded_msgs:
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", "unknown")
                content = str(msg.content or "")
                has_error = any(kw in content for kw in ERROR_KEYWORDS)
                per_tool_ms = elapsed / max(tool_count, 1)
                record_tool_detail_sync(tool_name, per_tool_ms, not has_error)
    except Exception:
        pass

    if corrections_injected > 0:
        logger.info("guard_corrections_injected", count=corrections_injected)

    return {"messages": guarded_msgs}


def mark_failed_node(state: AgentState) -> dict:
    """标记 LLM 失败（触发降级）并重建图"""
    mark_llm_failed()
    # 降级后重建图，使新 LLM 实例生效
    try:
        from core.execution import rebuild_graph
        rebuild_graph()
    except Exception as e:
        logger.warning("rebuild_graph_failed", error=str(e))
    logger.warning("llm_marked_failed", retry_count=state.get("retry_count", 0))
    return {"retry_count": state.get("retry_count", 0) + 1, "last_error": "", "is_fatal_error": False}


def error_handler_node(state: AgentState) -> dict:
    """错误兜底回复"""
    error_msg = "抱歉，处理您的请求时出现了问题，请稍后重试。"
    if state.get("is_fatal_error"):
        error_msg = state.get("last_error", error_msg)
    return {"messages": [AIMessage(content=error_msg)]}


# ============================================================
# 路由函数
# ============================================================

def route_after_faq(state: AgentState) -> str:
    """FAQ 匹配后路由"""
    return END if state.get("faq_reply") else "agent"


def route_after_agent(state: AgentState) -> str:
    """agent 节点后路由：检查错误 → mark_failed / error_handler，否则检查 tool_calls"""
    if state.get("last_error"):
        if state.get("is_fatal_error"):
            return "error_handler"
        if state.get("retry_count", 0) < 3:
            return "mark_failed"
        return "error_handler"
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ============================================================
# 工厂函数
# ============================================================

def make_call_model(llm):
    """创建 agent 节点的 call_model 函数（闭包捕获 llm 实例）

    单 Agent 架构：绑定全量工具 + 统一 System Prompt
    """

    def _is_llm_error(error_str: str) -> bool:
        error_lower = error_str.lower()
        return any(kw in error_lower for kw in [
            'timeout', 'connection', 'rate limit', 'service unavailable',
            'internal server error', 'bad gateway', '503', '502', '504',
            'quota', 'capacity', 'overloaded'
        ])

    def call_model(state: AgentState):
        summary = state.get("summary", "")
        dialog_context = state.get("dialog_context", "")
        sentiment_context = state.get("sentiment_context", "")
        wm_context = state.get("working_memory_context", "")
        budget_context = state.get("budget_context", "")

        # 统一 Prompt：合并所有领域的工具说明和流程提示
        system_content = build_unified_prompt(summary, dialog_context, sentiment_context)
        if wm_context:
            system_content += "\n\n" + wm_context
        if budget_context:
            system_content += "\n\n" + budget_context
        system_msg = SystemMessage(content=system_content)

        # 绑定全量工具（单 Agent 拥有所有能力）
        llm_with_tools = llm.bind_tools(ALL_TOOLS)

        messages = state["messages"]
        full_messages = [system_msg] + list(messages)
        t0 = time.monotonic()

        try:
            response = llm_with_tools.invoke(full_messages)

            logger.debug("agent_call", tool_count=len(ALL_TOOLS),
                         has_tool_calls=bool(getattr(response, "tool_calls", None)))
            return {"messages": [response], "last_error": "", "is_fatal_error": False}
        except LLMFallbackException as e:
            logger.error("llm_all_exhausted_in_agent", error=str(e)[:200])
            return {"last_error": str(e), "is_fatal_error": True}
        except Exception as e:
            error_str = str(e)
            if _is_llm_error(error_str):
                logger.warning("llm_error_in_agent", error=error_str[:200],
                               retry_count=state.get("retry_count", 0))
                return {"last_error": error_str, "is_fatal_error": False}
            else:
                logger.error("agent_call_error", error=error_str[:200])
                return {"last_error": error_str, "is_fatal_error": True}

    return call_model


# ============================================================
# 辅助函数
# ============================================================

def _update_working_memory(messages: list, session_id: str, tool_msgs: list):
    """从工具调用中提取信息，更新 Working Memory。

    策略：
    1. 找到最近的 AIMessage（包含 tool_calls 和参数）
    2. 对每个 tool_call，根据 WM_TOOL_ARG_MAP 提取参数 → wm.collect()
    3. 如果工具输出不含错误关键词且是执行类工具 → 标记任务完成
    4. 如果工具输出含错误关键词 → 记录错误到 WM
    """
    wm = get_working_memory(session_id)
    state = wm.get_state()

    if not state.task_type or state.phase == Phase.COMPLETED:
        return

    ai_msg = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            ai_msg = msg
            break

    if not ai_msg:
        return

    tool_output_map = {}
    for msg in tool_msgs:
        if isinstance(msg, ToolMessage):
            tool_output_map[msg.tool_call_id] = str(msg.content or "")

    any_success = False
    any_error = False

    for tc in ai_msg.tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", "")

        arg_map = WM_TOOL_ARG_MAP.get(tool_name, {})
        for arg_key, wm_key in arg_map.items():
            value = tool_args.get(arg_key)
            if value is not None and value != "" and value != 0:
                wm.collect(wm_key, value)

        output = tool_output_map.get(tool_call_id, "")
        has_error = any(kw in output for kw in ERROR_KEYWORDS)

        if has_error:
            any_error = True
            wm.mark_error(f"{tool_name}: {output[:100]}")
        else:
            any_success = True

    if any_success and not any_error:
        executed_tools = {tc.get("name") for tc in ai_msg.tool_calls}
        if executed_tools & WM_COMPLETION_TOOLS:
            wm.advance_phase(Phase.EXECUTION)
            wm.complete()
            logger.info("wm_auto_completed", session_id=session_id,
                        tools=list(executed_tools))
        elif not state.pending:
            wm.advance_phase(Phase.EXECUTION)
    elif any_error:
        logger.info("wm_error_recorded", session_id=session_id,
                    error=state.error[:80] if state.error else "")
