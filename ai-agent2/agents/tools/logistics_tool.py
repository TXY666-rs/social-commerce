from langchain_core.tools import tool
from middleware.context import _get_user_id
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool
from agents.tools.constants import ORDER_STATUS, NOT_LOGGED_IN_MSG
from mock_data import query_orders


# ============================================================
# 兼容性 helper（供 skill 层调用）
# ============================================================

def _track_logistics_api(order_id: str = "", product_keyword: str = "") -> list[dict] | None:
    """查询物流 API（供 skill 复用）。失败返回 None"""
    user_id = _get_user_id()
    if not user_id:
        return None
    try:
        orders = query_orders(user_id, product_keyword)
        if order_id:
            orders = [o for o in orders if str(o.get("id")) == str(order_id)]
        return orders
    except Exception:
        return None


# ============================================================
# 物流工具 —— 操作本地 Mock 数据（重构后不再依赖 Java 后端）
# ============================================================

@register_tool()
@tool
@tool_result_cache(ttl=30)
@resilient_tool()
def track_logistics(order_id: str = "", product_keyword: str = "") -> str:
    """查询物流信息。根据订单ID或商品关键词查询物流状态、快递单号等。当用户询问发货了吗、到哪了、物流信息时使用此工具。

    Args:
        order_id: 订单ID，可选
        product_keyword: 商品关键词，可选，用于筛选特定商品的订单物流
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="查询物流")

    # 从 mock 数据查询该用户的订单，按 order_id / product_keyword 筛选
    orders = query_orders(user_id, product_keyword)
    if order_id:
        orders = [o for o in orders if str(o.get("id")) == str(order_id)]
    if not orders:
        return "未找到相关订单的物流信息。"

    lines = []
    internal_ids = []
    for o in orders:
        status = o.get("status", -1)
        status_desc = ORDER_STATUS.get(status, "未知")
        line = f"订单 {o.get('productName', '未知商品')} — {status_desc}"

        # 物流信息按订单状态展示
        if o.get("trackingNumber"):
            line += f"\n   快递单号: {o['trackingNumber']}"
            if o.get("carrier"):
                line += f"\n   快递公司: {o['carrier']}"
        elif status == 2:
            # 已发货但无单号：可能是刚发货数据尚未同步，明确告知
            line += "\n   物流单号: 【暂未生成，数据同步中】"
            line += "\n   快递公司: 【暂未分配】"

        if o.get("deliveryTime"):
            line += f"\n   发货时间: {o['deliveryTime']}"
        elif status == 2:
            line += f"\n   发货时间: 【暂未记录】"

        if o.get("payTime"):
            line += f"\n   付款时间: {o['payTime']}"
        if o.get("completeTime"):
            line += f"\n   完成时间: {o['completeTime']}"
        if o.get("remark"):
            line += f"\n   备注: {o['remark']}"
        lines.append(line)
        internal_ids.append({"id": o.get("id")})
    lines.append(f"\n<!-- internal_ids:{internal_ids} -->")
    return "\n\n".join(lines)
