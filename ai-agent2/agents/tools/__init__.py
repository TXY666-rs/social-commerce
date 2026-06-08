"""Agent 工具集 — 自动注册 + 统一导出

工具通过 @register_tool() 装饰器自动注册到全局列表。
单 Agent 架构下，所有工具统一通过 ALL_TOOLS 暴露给 React Agent。
"""

# ── 导入工具模块（触发 @register_tool 注册） ──
import agents.tools.orders_tool        # noqa: F401  注册: get_my_orders, cancel_order
import agents.tools.goods_tool         # noqa: F401  注册: search_products
import agents.tools.logistics_tool     # noqa: F401  注册: track_logistics
import agents.tools.coupon_tool        # noqa: F401  注册: get_available_coupons, get_my_coupons, claim_coupon
import agents.tools.after_sale_tool    # noqa: F401  注册: request_refund, request_return, ...
import agents.tools.transfer_tool      # noqa: F401  注册: transfer_to_human

from agents.tools.registry import get_all_tools

# ── 全量工具（单 Agent 架构下所有工具统一暴露） ──
ALL_TOOLS = get_all_tools()

__all__ = ["ALL_TOOLS", "get_all_tools"]
