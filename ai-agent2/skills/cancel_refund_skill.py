"""取消退款 Skill — 取消退款/退货申请

流程：
1. 用户说"取消退款" → 触发 Skill
2. 收集订单号（validator 校验订单是否存在）
3. 确认阶段：查询退款记录，展示退款信息，等待用户确认
4. 执行取消操作
"""
import structlog
from typing import Optional
from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.orders_tool import _fetch_orders
from agents.tools.after_sale_tool import (
    _get_refund_by_order_api,
    _cancel_refund_api,
    _cancel_refund_by_order_api,
)

logger = structlog.get_logger(__name__)


async def _validate_order_id(order_id: str, user_id: str) -> tuple[bool, str, str]:
    """验证订单是否存在且处于退款中状态，返回 (is_valid, order_id, error_msg)

    订单状态: 0:待支付 1:已支付 2:已发货 3:已完成 4:已取消 5:退款中 6:已退款
    只有 status=5（退款中）的订单可以取消退款
    """
    orders = _fetch_orders()
    if orders is None:
        return False, "", "查询订单时出现问题，请稍后重试。"

    target = next((o for o in orders if str(o.get("id", "")) == order_id), None)
    if not target:
        return False, "", f"未找到订单号 {order_id}，请确认后重新输入。"

    status = target.get("status", -1)
    if status != 5:
        return False, "", f"订单 {order_id} 当前不在退款中状态，无法取消退款。"

    return True, str(order_id), ""


class CancelRefundSkill(BaseSkill):
    name = "cancel_refund"
    description = "取消退款：查询退款中的订单→确认→取消退款申请"
    trigger_keywords = ["取消退款", "不退了", "不要退了", "撤回退款",
                        "撤销退款", "取消退款申请"]

    params = [
        ParamDef(
            name="order_id",
            ask_prompt="好的，我来帮您处理取消退款～\n请提供要取消退款的订单号（格式：order+13位数字，如 order2026060100003）。",
            extractor="regex",
            pattern=r"order\d{13}",
            validator=_validate_order_id,
            required=True,
        ),
    ]

    async def build_confirm_prompt(self, state: SkillState) -> Optional[str]:
        """确认阶段：查询退款记录，展示退款信息，等待用户确认

        注意区分两套状态码：
        - 订单状态 (order.status): 0待支付 1已支付 2已发货 3已完成 4已取消 5退款中 6已退款
        - 退款记录状态 (refund.status): 0待审核 1审核通过 2退款中 3已退款 4已拒绝 5已取消
        validator 已确保 order.status == 5，此处只需检查 refund.status
        """
        order_id = state.collected["order_id"]

        refund_data = _get_refund_by_order_api(order_id)
        if not refund_data:
            # 无退款记录或接口异常 → 直接完成
            state.context["needs_confirm"] = False
            return (
                f"订单 {order_id} 暂无退款申请，无需取消。\n"
                f"如需其他帮助请随时告诉我～"
            )

        refund_status = refund_data.get("status", -1)  # 退款记录状态，非订单状态
        amount = refund_data.get("amount", 0)

        # 退款记录状态 3:已退款 → 订单已变为 status=6，无法取消
        if refund_status == 3:
            state.context["needs_confirm"] = False
            return (
                f"订单 {order_id} 的退款已完成，无法取消了。\n"
                f'如需帮助请回复"转人工"联系客服。'
            )

        # 退款记录状态 5:已取消
        if refund_status == 5:
            state.context["needs_confirm"] = False
            return (
                f"订单 {order_id} 的退款申请已经取消过了，无需重复操作。\n"
                f"如需其他帮助请随时告诉我～"
            )

        # 退款记录状态 4:已拒绝
        if refund_status == 4:
            state.context["needs_confirm"] = False
            return (
                f"订单 {order_id} 的退款申请已被拒绝，无需取消。\n"
                f'如有疑问请回复"转人工"联系客服。'
            )

        # 退款记录状态 2:退款中 — 退款正在处理，可能来不及在线取消
        if refund_status >= 2:
            state.context["needs_confirm"] = False
            return (
                f"订单 {order_id} 的退款正在处理中，暂不支持在线取消。\n"
                f'请回复"转人工"联系客服处理。'
            )

        # 退款记录状态 0:待审核 / 1:审核通过 — 可以取消
        # 存储退款信息供 execute 使用
        state.context["refund_data"] = refund_data
        state.context["needs_confirm"] = True

        product_name = refund_data.get("productName", "")
        product_info = f"📦 商品：{product_name}\n" if product_name else ""
        amount_info = f"💰 退款金额：¥{amount}\n" if amount else ""
        return (
            f"帮您查到了这笔退款申请：\n\n"
            f"📋 订单号：{order_id}\n"
            f"{product_info}"
            f"{amount_info}\n"
            f"您确定要取消这笔退款申请吗？\n"
            f"取消后如需退款需要重新申请。\n\n"
            f'回复"确认"取消退款，或"取消"放弃。'
        )

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行取消退款"""
        order_id = state.collected["order_id"]
        refund_data = state.context.get("refund_data")

        # 如果确认阶段已获取到退款信息，直接用 refund_id 取消
        if refund_data:
            refund_id = refund_data.get("id")
            if refund_id:
                success, msg = _cancel_refund_api(refund_id)
                if success:
                    return (
                        f"已成功取消订单 {order_id} 的退款申请 ✅\n\n"
                        f"如需重新申请退款，随时告诉我～"
                    )
                return '取消退款时出了点问题，请稍后重试或回复"转人工"联系客服。'

        # 备用方案：按订单 ID 取消
        success, msg = _cancel_refund_by_order_api(order_id)
        if success:
            return (
                f"已成功取消订单 {order_id} 的退款申请 ✅\n\n"
                f"如需重新申请退款，随时告诉我～"
            )
        return '取消退款时出了点问题，请稍后重试或回复"转人工"联系客服。'
