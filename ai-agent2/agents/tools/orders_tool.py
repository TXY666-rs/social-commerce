from langchain_core.tools import tool
from middleware.context import _get_user_id
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool
from agents.tools.constants import ORDER_STATUS, NOT_LOGGED_IN_MSG
from mock_data import query_orders, cancel_order as _cancel_order_mock, change_address as _change_address_mock


# ============================================================
# 兼容性 helper（供 skill 层调用，签名与旧版 _xxx_api 一致）
# 重构后底层改为操作 mock_data
# ============================================================

def _fetch_orders(product_keyword: str = "") -> list[dict] | None:
    """查询用户订单列表（供 skill 复用）。失败返回 None"""
    user_id = _get_user_id()
    if not user_id:
        return None
    try:
        return query_orders(user_id, product_keyword)
    except Exception:
        return None


def _cancel_order_api(order_id: str) -> tuple[bool, str]:
    """取消订单 API（供 skill 复用）"""
    user_id = _get_user_id()
    if not user_id:
        return False, "用户未登录"
    return _cancel_order_mock(user_id, order_id)


def _change_address_api(order_id: str, new_address: str) -> tuple[bool, str]:
    """修改收货地址 API（供 skill 复用）"""
    user_id = _get_user_id()
    if not user_id:
        return False, "用户未登录"
    return _change_address_mock(user_id, order_id, new_address)


# ============================================================
# 订单工具 —— 操作本地 Mock 数据（重构后不再依赖 Java 后端）
# ============================================================

@register_tool()
@tool
@tool_result_cache(ttl=60)
@resilient_tool()
def get_my_orders(productKeyword: str = "") -> str:
    """查询当前用户的订单列表。

    Args:
        productKeyword: 商品关键词，可选，用于筛选特定商品的订单
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="查询订单")

    orders = query_orders(user_id, productKeyword)
    if not orders:
        return "您暂无订单记录。"
    lines = [f"共 {len(orders)} 个订单：\n"]
    internal_ids = []
    for i, item in enumerate(orders, 1):
        status = ORDER_STATUS.get(item.get("status", 0), "未知状态")
        line = (
            f"【{i}】{item.get('productName', '未知商品')}"
            f" ×{item.get('quantity', 1)}  ¥{item.get('totalPrice', 0)}  [{status}]"
        )
        # 订单号（供后续取消/退款/改地址等操作使用）
        line += f"\n   订单号: {item.get('id', '未知')}"
        # 时间信息（有则显示）
        time_parts = []
        if item.get("completeTime"):
            time_parts.append(f"确认收货: {item['completeTime']}")
        if item.get("deliveryTime"):
            time_parts.append(f"发货: {item['deliveryTime']}")
        if item.get("payTime"):
            time_parts.append(f"下单: {item['payTime']}")
        if time_parts:
            line += f"\n   {' | '.join(time_parts)}"
        lines.append(line)
        internal_ids.append({
            "index": i,
            "id": item.get("id"),
            "completeTime": item.get("completeTime", ""),
            "deliveryTime": item.get("deliveryTime", ""),
        })
    lines.append(f"\n<!-- internal_ids:{internal_ids} -->")
    return "\n".join(lines)


@register_tool()
@tool
@resilient_tool()
def cancel_order(order_id: str) -> str:
    """取消订单。根据订单ID取消用户的订单。只有待付款状态的订单可以取消。"""
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="取消订单")
    success, message = _cancel_order_mock(user_id, order_id)
    return message


@register_tool()
@tool
@resilient_tool()
def change_address(order_id: str, new_address: str) -> str:
    """修改收货地址。只有未发货的订单可以修改地址。

    Args:
        order_id: 订单ID（先通过 get_my_orders 获取）
        new_address: 新的收货地址
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="修改地址")
    success, message = _change_address_mock(user_id, order_id, new_address)
    return message
