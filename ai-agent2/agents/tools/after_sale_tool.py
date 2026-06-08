"""售后工具 — 退款/退货/投诉/催单（含重试机制）

对应 Java 后端接口：
  POST   /api/refund          → request_refund
  POST   /api/return           → request_return
  GET    /api/refund/{id}      → check_refund_status
  GET    /api/refund/order/{orderId} → get_refund_by_order
  POST   /api/complaint        → submit_complaint
  DELETE /api/refund/{id}      → cancel_refund
  DELETE /api/refund/order/{orderId} → cancel_refund_by_order
  POST   /api/order/{id}/remind → remind_delivery
"""
from services.http_client import get_client
from langchain_core.tools import tool
from middleware.context import _auth_headers, _get_user_id
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool
from agents.tools.constants import AFTER_SALE_STATUS, NOT_LOGGED_IN_MSG
from datetime import date, datetime

# 质量问题关键词（模块级常量，避免每次调用重建）
QUALITY_ISSUE_KEYWORDS = ["质量", "坏", "破", "损", "不工作", "漏", "故障", "问题", "瑕疵"]


# ============================================================
# 内部 helper（返回结构化数据，供 skill 复用，带容错）
# ============================================================

@resilient_tool()
def _submit_refund_api(order_id: str, reason: str) -> tuple[bool, str, str]:
    """提交退款 API，返回 (success, message, refund_id)"""
    client = get_client()
    resp = client.post(
        "/api/refund",
        headers=_auth_headers(),
        json={"orderId": order_id, "reason": reason},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        refund_id = result.get("data", {}).get("id", "")
        return True, "退款申请已提交", refund_id
    return False, result.get("message", "退款申请失败"), ""


@resilient_tool()
def _submit_return_api(order_id: str, reason: str) -> tuple[bool, str, str]:
    """提交退货退款 API，返回 (success, message, return_id)"""
    client = get_client()
    resp = client.post(
        "/api/return",
        headers=_auth_headers(),
        json={"orderId": order_id, "reason": reason, "type": "refund"},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return_id = result.get("data", {}).get("id", "")
        return True, "退货退款申请已提交", return_id
    return False, result.get("message", "退货申请失败"), ""


@resilient_tool()
def _cancel_refund_api(refund_id: str) -> tuple[bool, str]:
    """按退款ID取消退款，返回 (success, message)"""
    client = get_client()
    resp = client.delete(f"/api/refund/{refund_id}", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "退款申请已取消。"
    return False, result.get("message", "取消退款申请失败")


@resilient_tool()
def _get_refund_by_order_api(order_id: str) -> dict | None:
    """按订单ID查询退款记录，返回退款字典。失败/无记录返回 None"""
    client = get_client()
    resp = client.get(f"/api/refund/order/{order_id}", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return result.get("data")
    return None


@resilient_tool()
def _cancel_refund_by_order_api(order_id: str) -> tuple[bool, str]:
    """按订单ID取消退款，返回 (success, message)"""
    client = get_client()
    resp = client.delete(f"/api/refund/order/{order_id}", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "退款申请已取消。"
    return False, result.get("message", "取消退款失败")


@resilient_tool()
def _submit_complaint_api(order_id: str, detail: str, complaint_type: str) -> tuple[bool, str]:
    """提交投诉 API，返回 (success, message)"""
    client = get_client()
    resp = client.post(
        "/api/complaint",
        headers=_auth_headers(),
        json={"orderId": order_id, "detail": detail, "type": complaint_type},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "投诉已登记"
    return False, result.get("message", "投诉提交失败")


@resilient_tool()
def _remind_delivery_api(order_id: str) -> tuple[bool, str]:
    """催发货 API，返回 (success, message)"""
    client = get_client()
    resp = client.post(f"/api/order/{order_id}/remind", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "已为您催促物流配送"
    return False, result.get("message", "催单失败")


def _parse_days_since_complete(complete_time: str) -> tuple[str, int] | None:
    """解析确认收货时间，返回 (日期字符串, 距今天数)。解析失败返回 None"""
    if not complete_time:
        return None
    try:
        complete_str = complete_time.strip()[:10]
        complete_date = datetime.strptime(complete_str, "%Y-%m-%d").date()
        days_passed = (date.today() - complete_date).days
        return complete_str, days_passed
    except ValueError:
        return None


@register_tool()
@tool
@resilient_tool()
def request_refund(order_id: str, reason: str, complete_time: str = "") -> str:
    """发起退款申请。如果提供了确认收货时间（completeTime），系统会自动判断退货时效。
    应在调用 get_my_orders 后再调用此工具，get_my_orders 返回的 internal_ids 中包含 completeTime。

    Args:
        order_id: 要退款的订单ID（从 get_my_orders 的 internal_ids 中获取）
        reason: 退款原因，如"商品质量问题"、"与描述不符"、"不想要了"
        complete_time: 确认收货时间，如"2026-05-23T14:30:00"，从 internal_ids.completeTime 获取。为空则跳过时间判断
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="申请退款")

    # ── 确认收货时间判断（≤7天/7-15天/>15天）──
    parsed = _parse_days_since_complete(complete_time)
    if parsed:
        complete_str, days_passed = parsed

        if days_passed > 15:
            return (
                f"【系统判断】确认收货时间 {complete_str}，距今 {days_passed} 天，已超过15天退货时效。\n"
                "无法在线申请退货退款。建议引导用户提交投诉转人工客服协商处理。\n"
                f"<!-- blocked:超期{days_passed}天 -->"
            )
        elif days_passed > 7:
            is_quality = any(kw in reason for kw in QUALITY_ISSUE_KEYWORDS)
            if not is_quality:
                return (
                    f"【系统判断】确认收货时间 {complete_str}，距今 {days_passed} 天，超过7天无理由退货期。\n"
                    "仅在商品存在质量问题时可在15天内申请退货。请确认：您遇到的属于质量问题吗？\n"
                    "如果是质量问题，请描述具体问题后重试；如果是其他原因，建议提交投诉转人工处理。\n"
                    f"<!-- blocked:超7天无理由,需确认质量 -->"
                )

    client = get_client()
    success, msg, refund_id = _submit_refund_api(order_id, reason)
    if not success:
        return msg
    if parsed:
        _, days_passed = parsed
        days_info = f"- 确认收货距今: {days_passed} 天\n"
    else:
        days_info = "- 注意：订单尚未确认收货，已提交退款由后台审核\n"
    return (
        "退款申请已提交！\n"
        f"{days_info}"
        f"- 原因: {reason}\n"
        "- 预计 1-3 个工作日处理\n"
        f"<!-- internal_refund_id:{refund_id} internal_order_id:{order_id} -->"
    )


@register_tool()
@tool
@resilient_tool()
def request_return(order_id: str, reason: str) -> str:
    """发起退货退款申请。用户收到商品后不满意，申请退货退款。

    Args:
        order_id: 要退货的订单ID（先通过 get_my_orders 获取）
        reason: 退货原因，如"尺码不合适"、"颜色不喜欢"、"质量问题"
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="申请退货")

    success, msg, return_id = _submit_return_api(order_id, reason)
    if not success:
        return msg
    return (
        "退货退款申请已提交！\n"
        f"- 原因: {reason}\n"
        "- 请保持商品原包装完好，等待审核。\n"
        f"<!-- internal_return_id:{return_id} internal_order_id:{order_id} -->"
    )


@register_tool()
@tool
@tool_result_cache(ttl=30)
@resilient_tool()
def check_refund_status(refund_id: str) -> str:
    """查询退款/退货进度。用户询问"退款到哪了"时调用。

    Args:
        refund_id: 退款单号（从 request_refund 或 request_return 返回的ID）
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="查询退款进度")

    client = get_client()
    resp = client.get(
        f"/api/refund/{refund_id}",
        headers=_auth_headers(),
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        return result.get("message", "查询退款进度失败")
    data = result.get("data", {})
    status = AFTER_SALE_STATUS.get(data.get("status", 0), "未知状态")
    lines = [
        f"退款当前状态：{status}",
        f"- 退款金额: ¥{data.get('amount', 0)}",
    ]
    if data.get("remark"):
        lines.append(f"- 备注: {data.get('remark')}")
    return "\n".join(lines)


@register_tool()
@tool
@resilient_tool()
def submit_complaint(order_id: str, detail: str, complaint_type: str = "service") -> str:
    """提交投诉。用户对商品/服务/物流不满意时，记录投诉并转人工处理。

    Args:
        order_id: 投诉关联的订单ID（先通过 get_my_orders 获取）
        detail: 投诉详细描述
        complaint_type: 投诉类型，"service"=服务问题，"delivery"=物流问题，"product"=商品问题
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="提交投诉")

    success, msg = _submit_complaint_api(order_id, detail, complaint_type)
    if success:
        return (
            "投诉已登记，人工客服将尽快与您联系。"
            f"\n- 类型: {complaint_type}"
            f"\n- 描述: {detail}"
        )
    return msg


@register_tool()
@tool
@resilient_tool()
def cancel_refund(refund_id: str) -> str:
    """取消退款/退货申请。用户改变主意不想退了时调用。

    Args:
        refund_id: 退款单号（从 request_refund 或 request_return 返回的ID）
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="取消退款")

    success, msg = _cancel_refund_api(refund_id)
    return msg


@register_tool()
@tool
@resilient_tool()
def remind_delivery(order_id: str) -> str:
    """催促物流配送。用户觉得快递太慢时调用，通知物流方加快处理。

    Args:
        order_id: 要催单的订单ID（先通过 get_my_orders 获取已发货的订单）
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="催促配送")

    success, msg = _remind_delivery_api(order_id)
    if success:
        return "已为您催促物流配送，预计 24 小时内更新物流状态，请留意查看。"
    return msg
