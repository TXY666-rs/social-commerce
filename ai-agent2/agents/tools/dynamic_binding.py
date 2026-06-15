"""动态工具绑定 — 基于对话上下文的智能工具选择器

设计动机：
    当前架构在每次 LLM 调用时绑定全量 14 个工具（graph/nodes.py 第 212 行：
    ``llm.bind_tools(ALL_TOOLS)``）。这带来三个问题：

    1. **Token 浪费** — 每个工具的 name + description + args schema 会注入 System
       Prompt，而大部分对话只涉及 1-2 个领域。
    2. **选择困难** — 工具过多会增加 LLM "选错工具"的概率。
    3. **延迟增加** — 更长的 Prompt 意味着更高的推理延迟。

设计思路：
    根据用户最新消息的**领域关键词** + Working Memory 的**任务状态**，动态筛选
    出与当前意图相关的工具子集，仅将该子集绑定到 LLM 调用。

    安全策略：
    - ``transfer_to_human`` 始终包含（逃生通道，确保用户随时可以转人工）
    - 无法识别领域时回退到全量工具（safe fallback），避免因漏判而丧失能力

领域分组：
    orders     → get_my_orders, cancel_order, remind_delivery
    logistics  → track_logistics
    after_sale → request_refund, request_return, check_refund_status,
                 cancel_refund, submit_complaint
    transfer   → transfer_to_human

集成方式：
    在 ``graph/nodes.py`` 的 ``make_call_model`` 中替换::

        # 原：llm_with_tools = llm.bind_tools(ALL_TOOLS)
        # 新：
        from agents.tools.dynamic_binding import select_tools
        tools = select_tools(last_user_message, state)
        llm_with_tools = llm.bind_tools(tools)

监控：
    调用 ``get_tool_stats()`` 获取各领域被选中的次数，用于分析领域命中率、
    优化关键词表、评估 token 节省效果。
"""

from __future__ import annotations

import re
import threading
from typing import Any

import structlog
from langchain_core.tools import StructuredTool

from agents.tools import ALL_TOOLS
from agents.tools.registry import get_registry

logger = structlog.get_logger(__name__)


# ============================================================
# 1. 领域 → 工具名 映射
# ============================================================

# 每个领域包含的工具名列表（与 @register_tool 注册的 name 一致）
TOOL_DOMAINS: dict[str, list[str]] = {
    "orders": [
        "get_my_orders",
        "cancel_order",
        "remind_delivery",
    ],
    "logistics": [
        "track_logistics",
    ],
    "after_sale": [
        "request_refund",
        "request_return",
        "check_refund_status",
        "cancel_refund",
        "submit_complaint",
    ],
    "transfer": [
        "transfer_to_human",
    ],
}

# 反向映射：工具名 → 领域（用于快速查找）
_TOOL_TO_DOMAIN: dict[str, str] = {}
for _domain, _tools in TOOL_DOMAINS.items():
    for _tool_name in _tools:
        _TOOL_TO_DOMAIN[_tool_name] = _domain


# ============================================================
# 2. 领域关键词映射（用于意图识别）
# ============================================================

# 关键词 → 领域；匹配优先级：按列表顺序，先匹配先命中
# 每个关键词可以是普通字符串（子串匹配）或正则表达式
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "orders": [
        "订单", "下单", "取消订单", "催发货", "催单",
        "买了", "购买", "订单号", "待付款", "待发货",
    ],
    "logistics": [
        "物流", "快递", "发货", "到了", "配送", "运送",
        "到哪了", "派送", "签收", "在途", "物流信息",
    ],
    "after_sale": [
        "退款", "退货", "售后", "投诉", "质量问题", "破损",
        "退了", "不想要", "瑕疵", "坏了", "退货退款",
        "退款进度", "取消退款", "换货",
    ],
    "transfer": [
        "人工", "客服", "转接", "转人工", "真人",
        "找人工", "人工客服",
    ],
}

# 预编译正则（避免每次调用时重复编译）
_DOMAIN_PATTERNS: dict[str, list[re.Pattern]] = {}
for _domain, _keywords in DOMAIN_KEYWORDS.items():
    _DOMAIN_PATTERNS[_domain] = [
        re.compile(kw, re.IGNORECASE) for kw in _keywords
    ]


# ============================================================
# 3. Working Memory 任务类型 → 领域映射
# ============================================================

# Working Memory 中的 task_type 值 → 对应的工具领域
WM_TASK_TYPE_TO_DOMAIN: dict[str, str] = {
    "refund": "after_sale",
    "return": "after_sale",
    "complaint": "after_sale",
    "query_order": "orders",
    "query_logistics": "logistics",
    "cancel_order": "orders",
}


# ============================================================
# 4. 统计计数器（线程安全）
# ============================================================

_stats_lock = threading.Lock()
_domain_selection_counts: dict[str, int] = {
    domain: 0 for domain in TOOL_DOMAINS
}
_total_selections: int = 0
_fallback_count: int = 0


# ============================================================
# 5. 核心选择逻辑
# ============================================================

def _detect_domains_from_message(message: str) -> set[str]:
    """根据用户消息关键词检测匹配的领域集合。

    遍历所有领域的关键词正则列表，命中即加入集合。
    一条消息可能同时命中多个领域（如"我的订单退款了"同时命中 orders 和 after_sale）。

    Args:
        message: 用户最新消息内容

    Returns:
        匹配到的领域名称集合（可能为空）
    """
    if not message:
        return set()

    matched: set[str] = set()
    for domain, patterns in _DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                matched.add(domain)
                break  # 该领域已命中，跳过剩余关键词
    return matched


def _detect_domain_from_wm_state(state: dict) -> set[str]:
    """根据 Working Memory 的任务状态推断应包含的工具领域。

    当 WM 中已有活跃任务（task_type 非空且 phase 不是 completed）时，
    将该任务类型对应的领域纳入选择范围，确保多轮对话中工具不会"丢失"。

    Args:
        state: AgentState 字典，可包含 session_id 等字段

    Returns:
        推断出的领域集合（可能为空）
    """
    session_id = state.get("session_id", "")
    if not session_id:
        return set()

    try:
        from memory.working_memory import get_working_memory, Phase
        wm = get_working_memory(session_id)
        task_state = wm.get_state()

        # 仅在有活跃且未完成的任务时才推断
        if task_state.task_type and task_state.phase != Phase.COMPLETED:
            domain = WM_TASK_TYPE_TO_DOMAIN.get(task_state.task_type)
            if domain:
                logger.debug("wm_domain_hint",
                             task_type=task_state.task_type,
                             domain=domain,
                             session_id=session_id)
                return {domain}
    except Exception as e:
        logger.debug("wm_domain_detect_failed", error=str(e))

    return set()


def _resolve_tools(tool_names: list[str]) -> list[StructuredTool]:
    """将工具名列表解析为实际的 StructuredTool 对象列表。

    从全局注册表中查找工具对象；若某个工具名未注册则跳过并记录警告。

    Args:
        tool_names: 工具名列表

    Returns:
        对应的 StructuredTool 对象列表
    """
    registry = get_registry()
    resolved: list[StructuredTool] = []
    for name in tool_names:
        tool_obj = registry.get(name)
        if tool_obj is not None:
            resolved.append(tool_obj)
        else:
            logger.warning("tool_not_found_in_registry", tool_name=name)
    return resolved


def select_tools(message: str, state: dict) -> list[StructuredTool]:
    """根据对话上下文动态选择与当前意图相关的工具子集。

    选择策略（按优先级叠加）：
        1. 分析用户最新消息中的领域关键词 → 命中领域
        2. 检查 Working Memory 任务状态 → 补充活跃任务领域
        3. 始终包含 ``transfer_to_human``（逃生通道）
        4. 若以上均未命中任何领域 → 回退到全量工具（safe fallback）

    Args:
        message: 用户最新消息内容
        state:   当前 AgentState（可包含 session_id 等信息）

    Returns:
        筛选后的工具列表，可直接传给 ``llm.bind_tools()``
    """
    global _total_selections, _fallback_count

    # ── Step 1: 关键词匹配 ──
    domains = _detect_domains_from_message(message)

    # ── Step 2: Working Memory 状态补充 ──
    wm_domains = _detect_domain_from_wm_state(state)
    domains |= wm_domains

    # ── Step 3: 始终包含 transfer_to_human（逃生通道）──
    domains.add("transfer")

    # ── Step 4: 汇总工具列表 ──
    if domains == {"transfer"}:
        # 仅命中 transfer（即关键词和 WM 均未识别到具体领域）→ 安全回退
        _record_stats(set(), fallback=True)
        logger.debug("dynamic_binding_fallback",
                     reason="no_domain_detected",
                     tool_count=len(ALL_TOOLS))
        return list(ALL_TOOLS)

    # 收集所有命中领域的工具名
    selected_names: list[str] = []
    for domain in domains:
        selected_names.extend(TOOL_DOMAINS.get(domain, []))

    # 去重（多领域可能通过不同路径命中同一工具）
    seen: set[str] = set()
    unique_names: list[str] = []
    for name in selected_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    tools = _resolve_tools(unique_names)

    _record_stats(domains, fallback=False)

    logger.debug("dynamic_binding_selected",
                 domains=sorted(domains),
                 tool_count=len(tools),
                 total_tools=len(ALL_TOOLS),
                 saved=len(ALL_TOOLS) - len(tools))

    return tools


# ============================================================
# 6. 统计函数
# ============================================================

def _record_stats(domains: set[str], fallback: bool) -> None:
    """记录领域选择统计（线程安全）。"""
    global _total_selections, _fallback_count

    with _stats_lock:
        _total_selections += 1
        if fallback:
            _fallback_count += 1
        for domain in domains:
            if domain in _domain_selection_counts:
                _domain_selection_counts[domain] += 1


def get_tool_stats() -> dict[str, Any]:
    """获取工具选择统计数据，用于监控和优化。

    Returns:
        包含以下字段的字典::

            {
                "total_selections": int,       # 总调用次数
                "fallback_count": int,          # 回退到全量工具的次数
                "fallback_rate": float,         # 回退率（0.0 ~ 1.0）
                "domain_counts": {              # 各领域被选中次数
                    "orders": 42,
                    "logistics": 15,
                    ...
                },
                "avg_tools_per_call": float,    # 平均每次选择的工具数
            }
    """
    with _stats_lock:
        total = _total_selections
        fallback = _fallback_count
        domain_counts = dict(_domain_selection_counts)

    # 计算平均每次选择的工具数
    total_domain_hits = sum(domain_counts.values())
    avg_tools = total_domain_hits / max(total, 1)

    return {
        "total_selections": total,
        "fallback_count": fallback,
        "fallback_rate": fallback / max(total, 1),
        "domain_counts": domain_counts,
        "avg_tools_per_call": round(avg_tools, 2),
    }


def reset_stats() -> None:
    """重置统计数据（通常在监控面板拉取后调用，或用于测试）。"""
    global _total_selections, _fallback_count

    with _stats_lock:
        _total_selections = 0
        _fallback_count = 0
        for domain in _domain_selection_counts:
            _domain_selection_counts[domain] = 0
    logger.info("dynamic_binding_stats_reset")
