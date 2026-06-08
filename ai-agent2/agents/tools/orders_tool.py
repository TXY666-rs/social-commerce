from services.http_client import get_client
from langchain_core.tools import tool
from middleware.context import _auth_headers, _get_user_id
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool
from agents.tools.constants import ORDER_STATUS, NOT_LOGGED_IN_MSG


# ============================================================
# 内部 helper（返回结构化数据，供 skill 复用，带容错）
# ============================================================

@resilient_tool()
def _fetch_orders(product_keyword: str = "") -> list[dict] | None:
    """查询用户订单列表，返回原始订单字典列表。失败返回 None"""
    params = {"product_keyword": product_keyword}
    client = get_client()
    resp = client.get("/api/order/my", headers=_auth_headers(), params=params)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        return None
    return result.get("data", {}).get("records", [])


@resilient_tool()
def _cancel_order_api(order_id: str) -> tuple[bool, str]:
    """取消订单 API，返回 (success, message)"""
    client = get_client()
    resp = client.put(f"/api/order/cancel/{order_id}", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "订单取消成功。"
    return False, result.get("message", "取消订单失败")


@resilient_tool()
def _change_address_api(order_id: str, new_address: str) -> tuple[bool, str]:
    """修改收货地址 API，返回 (success, message)"""
    client = get_client()
    resp = client.put(
        f"/api/order/{order_id}/address",
        headers=_auth_headers(),
        json={"address": new_address},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return True, "收货地址修改成功。"
    return False, result.get("message", "修改地址失败")



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

    orders = _fetch_orders(productKeyword)
    if orders is None:
        return "查询订单失败，请稍后重试。"
    if not orders:
        return "您暂无订单记录。"
    lines = [f"共 {len(orders)} 个订单：\n"]
    internal_ids = []
    for i, item in enumerate(orders, 1):
        # Python 自己的 status_map（Java 侧无 statusDesc 字段）
        status = ORDER_STATUS.get(item.get("status", 0), "未知状态")
        line = (
            f"【{i}】{item.get('productName', '未知商品')}"
            f" ×{item.get('quantity', 1)}  ¥{item.get('totalPrice', 0)}  [{status}]"
        )
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
    success, message = _cancel_order_api(order_id)
    return message
