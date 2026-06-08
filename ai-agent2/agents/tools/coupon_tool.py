from services.http_client import get_client
from langchain_core.tools import tool
from middleware.context import _auth_headers, _get_user_id
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool
from agents.tools.constants import COUPON_STATUS, NOT_LOGGED_IN_MSG


# 优惠券类型映射（模块级常量，避免每次调用重建）
COUPON_TYPE_MAP = {1: "满减券", 2: "折扣券", 3: "立减券"}


def _format_coupon(c: dict, index: int = 0) -> str:
    """格式化单条优惠券信息"""
    ctype = COUPON_TYPE_MAP.get(c.get("type", 1), "优惠券")
    prefix = f"{index}. " if index > 0 else ""

    if c.get("type") == 2:
        # 折扣券：显示"打x折"
        discount_text = f"打{c.get('discountRate', 10)}折"
        if c.get("maxDiscount"):
            discount_text += f"，最高减{c['maxDiscount']}元"
    elif c.get("type") == 1:
        # 满减券
        discount_text = f"满{c.get('thresholdAmount', 0)}减{c.get('discountAmount', 0)}"
    else:
        # 立减券
        discount_text = f"立减{c.get('discountAmount', 0)}元"

    desc = c.get("description", "")
    return (
        f"{prefix}【{ctype}】{c.get('name', '')}"
        f"\n   优惠: {discount_text}"
        f"\n   有效期: {c.get('startTime', '')} ~ {c.get('endTime', '')}"
        f"{f'\n   {desc}' if desc else ''}"
    )


@register_tool()
@tool
@tool_result_cache(ttl=120)
@resilient_tool()
def get_available_coupons() -> str:
    """查看可领取的优惠券列表。当用户询问有什么优惠券、促销活动、折扣时使用此工具。返回的是优惠券模板，领取后需用'我的优惠券'查看领取后的券ID。"""
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="查看优惠券")

    client = get_client()
    resp = client.get("/api/coupon/available", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        return result.get("message", "获取优惠券失败")
    coupons = result.get("data", [])
    if not coupons:
        return "当前没有可领取的优惠券。"
    lines = ["当前可领取的优惠券："]
    for i, c in enumerate(coupons, 1):
        lines.append(_format_coupon(c, i))
        lines.append(f"   优惠券ID: {c.get('id', '')}")
    return "\n".join(lines)


@register_tool()
@tool
@tool_result_cache(ttl=60)
@resilient_tool()
def get_my_coupons(status: int = -1) -> str:
    """查看当前用户已领取的优惠券。下单前用此工具获取可用优惠券的ID（user_coupon_id）。返回的优惠券ID可直接用于下单。

    Args:
        status: 筛选状态，-1=全部，0=未使用，1=已使用，2=已过期，默认-1
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="查看优惠券")

    params = {}
    if status >= 0:
        params["status"] = status
    client = get_client()
    resp = client.get("/api/coupon/my", headers=_auth_headers(), params=params)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        return result.get("message", "获取优惠券失败")
    coupons = result.get("data", [])
    if not coupons:
        return "您还没有优惠券，可以先领取后再使用。"
    lines = ["您的优惠券："]
    for i, c in enumerate(coupons, 1):
        s = COUPON_STATUS.get(c.get("status", 0), "未知")
        lines.append(_format_coupon(c, i))
        lines.append(f"   状态: {s}")
        lines.append(f"   优惠券ID: {c.get('id', '')}")
    return "\n".join(lines)


@register_tool()
@tool
@resilient_tool()
def claim_coupon(coupon_id: int) -> str:
    """领取优惠券。根据优惠券模板ID领取一张优惠券。领取后用'我的优惠券'查看已领取的券ID用于下单。

    Args:
        coupon_id: 优惠券模板ID（从'可领取优惠券'列表中获取的ID）
    """
    user_id = _get_user_id()
    if not user_id:
        return NOT_LOGGED_IN_MSG.format(action="领取优惠券")

    client = get_client()
    resp = client.post(f"/api/coupon/claim/{coupon_id}", headers=_auth_headers())
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        return "优惠券领取成功！请用'我的优惠券'查看已领取的优惠券ID，下单时可使用。"
    return result.get("message", "领取优惠券失败")
