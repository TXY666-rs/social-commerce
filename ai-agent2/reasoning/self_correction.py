"""Self-Correction（自纠错）— 工具输出守卫 + 纠错上下文注入

这是 reasoning 模块的唯一入口，在 graph.py 的 guard 节点中调用。

执行流程（对每个 ToolMessage）：
    ① 安全过滤：检测 SQL 异常栈 / IP / 凭证泄露 → 替换为安全话术
    ② 纠错检测：检测 未登录 / 未找到 / 操作失败 / 资源不足 / 空结果
    ③ 纠错注入：构建纠错上下文（问题类型 + 建议 + 限制）注入 ToolMessage

设计要点：
    - 标准 ReAct 是单向流（LLM→Tool→LLM），LLM 犯错后会在错误基础上继续
    - Self-Correction 在工具执行后注入纠错提示，强制 LLM 换策略
    - 与重试的区别：重试是"同样的调用再试一次"，自纠错是"换一种方式再试"
    - 纠错成本控制：最多纠错 1 次，避免无限循环
"""

import structlog
from langchain_core.messages import AIMessage

logger = structlog.get_logger(__name__)

# 最大纠错次数（避免无限循环）
MAX_CORRECTIONS = 1


# ============================================================
# 纠错判断
# ============================================================

# 工具输出中的"需要纠错"信号
CORRECTION_SIGNALS = {
    "authentication": {
        "patterns": ["未登录", "请先登录", "token.*无效", "认证失败", "权限不足"],
        "hint": "用户登录态异常 — 请告知用户需要重新登录，不要继续调用其他工具。",
    },
    "not_found": {
        "patterns": ["未找到", "不存在", "没有.*记录", "查询.*为空"],
        "hint": "未找到目标数据 — 请询问用户更多定位信息（如订单号），或建议用户在「我的订单」页面查看。",
    },
    "operation_failed": {
        "patterns": ["失败", "错误", "异常", "不可用", "暂时无法"],
        "hint": "操作执行失败 — 请向用户说明原因，提供替代方案（如转人工、换一种方式）。",
    },
    "resource_unavailable": {
        "patterns": ["库存不足", "已售罄", "超出限制", "余额不足"],
        "hint": "资源不足 — 请告知用户具体原因，不要重复调用同一工具。",
    },
    "empty_result": {
        "patterns": ["^\\s*$", "^null$"],
        "hint": "工具返回为空 — 请告知用户暂无相关数据，不要编造内容。",
    },
}


def detect_correction_needed(tool_output: str) -> tuple[bool, str, str]:
    """检测工具输出是否需要纠错。

    Returns:
        (needs_correction, signal_type, hint)
        - needs_correction: 是否需要纠错
        - signal_type: 检测到的信号类型
        - hint: 纠错提示
    """
    import re
    if not tool_output:
        return False, "", ""

    for signal_type, config in CORRECTION_SIGNALS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, tool_output):
                logger.debug("correction_signal_detected",
                             signal=signal_type, pattern=pattern,
                             output_preview=tool_output[:80])
                return True, signal_type, config["hint"]

    return False, "", ""


# ============================================================
# 安全过滤（防止信息泄露）
# ============================================================

LEAK_PATTERNS = [
    (r"(?i)(\b\w+Exception\b|\b\w+Error\b|Caused\s+by:|Stack\s*trace|at\s+com\.\w+|\.java:\d+)", "报错信息"),
    (r"(?i)(connection\s*(refused|timeout|reset|failed)|database\s*error)", "数据库连接信息"),
    (r"(?i)(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)", "IP地址"),
    (r"(?i)(secret|password|token|api[_\s]*key)\s*[:=]", "凭证信息"),
]

SAFE_FALLBACK = "系统处理您的请求时出现了问题，请稍后重试或联系人工客服。"


def check_safety(content: str) -> tuple[bool, str]:
    """检查内容是否包含敏感信息泄露。

    Returns:
        (is_safe, safe_content)
        - is_safe: True = 安全, False = 检测到泄露
        - safe_content: 如果不安全，返回替换后的内容
    """
    import re
    for pattern, label in LEAK_PATTERNS:
        if re.search(pattern, content):
            logger.warning("safety_leak_detected", label=label, preview=content[:120])
            return False, SAFE_FALLBACK

    # PII 检测（手机号、身份证、邮箱）
    try:
        from core.security import detect_pii, mask_pii
        pii_found = detect_pii(content)
        if pii_found:
            logger.warning("pii_detected_in_tool_output", pii_types=list(pii_found.keys()))
            return False, mask_pii(content)
    except Exception:
        pass

    return True, content


# ============================================================
# 纠错上下文构建
# ============================================================

def build_correction_context(
    tool_name: str,
    tool_output: str,
    signal_type: str,
    hint: str,
    correction_count: int,
) -> str:
    """构建纠错上下文，注入到 ToolMessage 中。

    Args:
        tool_name: 工具名
        tool_output: 原始工具输出
        signal_type: 检测到的信号类型
        hint: 纠错提示
        correction_count: 已纠错次数

    Returns:
        纠错上下文字符串
    """
    lines = [
        f"[系统纠错提示 — 第{correction_count}次]",
        f"工具 {tool_name} 的返回结果存在问题：",
        f"- 问题类型: {signal_type}",
        f"- 建议: {hint}",
    ]

    if correction_count >= MAX_CORRECTIONS:
        lines.append("- ⚠ 已达到最大纠错次数，请直接用自然语言回复用户，不要再调用工具。")

    return "\n".join(lines)


# ============================================================
# 完整的 Guard + Self-Correction 流程
# ============================================================

def apply_guard_and_correct(tool_message) -> tuple:
    """对工具输出执行 安全检查 + 纠错检测。

    这是 reasoning 模块的核心函数，替代原来的简单 apply_guard。

    Returns:
        (corrected_message, needs_correction, correction_context)
        - corrected_message: 处理后的消息（可能被安全过滤替换）
        - needs_correction: 是否需要自纠错
        - correction_context: 纠错上下文（空字符串 = 不需要纠错）
    """
    from langchain_core.messages import ToolMessage
    content = tool_message.content
    tool_name = getattr(tool_message, "name", "unknown")

    # 1. 安全过滤
    is_safe, safe_content = check_safety(content)
    if not is_safe:
        corrected = ToolMessage(content=safe_content, tool_call_id=tool_message.tool_call_id, name=tool_name)
        return corrected, False, ""

    # 2. 纠错检测
    needs_correction, signal_type, hint = detect_correction_needed(content)

    if needs_correction:
        correction_ctx = build_correction_context(
            tool_name, content, signal_type, hint, 1
        )
        # 注入纠错上下文到消息内容前
        corrected = ToolMessage(
            content=correction_ctx + "\n\n" + content,
            tool_call_id=tool_message.tool_call_id,
            name=tool_name,
        )
        return corrected, True, correction_ctx

    return tool_message, False, ""
