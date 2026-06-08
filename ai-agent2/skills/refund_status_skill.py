"""退款进度查询 Skill — 查询退款/退货处理进度

流程：
1. 用户说"退款到哪了" → 触发 Skill
2. 查询用户所有订单
3. 筛选出有退款申请的订单
4. 展示退款进度
"""
import structlog
from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.after_sale_tool import _get_refund_by_order_api
from agents.tools.orders_tool import _fetch_orders
from agents.tools.constants import AFTER_SALE_STATUS

logger = structlog.get_logger(__name__)


class RefundStatusSkill(BaseSkill):
    name = "refund_status"
    description = "查询退款进度：查询订单→筛选退款中→展示进度"
    trigger_keywords = ["退款进度", "退款到哪了", "退款状态", "退款多久", "退到哪了",
                        "退款处理", "退款什么时候", "退钱到哪了", "钱退到哪了",
                        "退货进度", "退货到哪了", "退货状态"]

    params = [
        ParamDef(
            name="order_id",
            ask_prompt="请提供要查询退款进度的订单号，如 order2026060100003",
            extractor="regex",
            pattern=r"order\d{13}",
            required=False,
            skip_on_trigger=True,
        ),
    ]

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行退款进度查询"""
        order_id = state.collected.get("order_id")

        if order_id:
            return await self._query_by_order(order_id)
        else:
            return await self._query_all_refunds()

    async def _query_by_order(self, order_id: str) -> str:
        """按订单号查询退款进度"""
        data = _get_refund_by_order_api(order_id)
        if data is None:
            return await self._query_all_refunds()
        if not data:
            return (
                f"订单 {order_id} 暂无退款申请记录。\n"
                "如需申请退款，请告诉我。"
            )
        return self._format_refund_detail(data)

    async def _query_all_refunds(self) -> str:
        """查询所有退款中的订单"""
        orders = _fetch_orders()
        if orders is None:
            return "查询订单时出现问题，请稍后重试。"
        refund_orders = [
            o for o in orders
            if o.get("status") in (5, 6)
        ]

        if not refund_orders:
            return "好的，帮您查了一下，您目前没有退款中的订单。如需申请退款请告诉我～"

        lines = ["好的，帮您查到了以下退款订单：\n"]
        for i, order in enumerate(refund_orders, 1):
            product_name = order.get("productName", "未知商品")
            status = order.get("status", 0)
            status_desc = {5: "退款中", 6: "已退款"}.get(status, "未知")
            lines.append(f"【{i}】{product_name} — {status_desc}")
            if order.get("id"):
                lines.append(f"   订单号: {order['id']}")
            if order.get("completeTime"):
                lines.append(f"   确认收货: {order['completeTime']}")

        lines.append("\n回复订单号可查看具体退款详情。")
        return "\n".join(lines)

    def _format_refund_detail(self, data: dict) -> str:
        """格式化退款详情"""
        status = data.get("status", -1)
        status_desc = AFTER_SALE_STATUS.get(status, "未知状态")
        amount = data.get("amount", 0)
        remark = data.get("remark", "")

        lines = [
            f"退款状态：{status_desc}",
            f"💰 退款金额：¥{amount}",
        ]

        if remark:
            lines.append(f"📝 备注：{remark}")

        # 根据状态给出提示
        if status == 0:
            lines.append("\n退款申请正在审核中，预计 1-3 个工作日处理，请耐心等待～")
        elif status == 1:
            lines.append("\n退款已审核通过，预计 1-3 个工作日到账。")
        elif status == 2:
            lines.append("\n退款处理中，预计 1-3 个工作日到账。")
        elif status == 3:
            lines.append("\n退款已完成，款项已退回原支付方式。有其他需要随时告诉我～")
        elif status == 4:
            lines.append('\n退款申请被拒绝，如有疑问请回复"转人工"联系客服。')
        elif status == 5:
            lines.append("\n退款已取消。如需重新申请请告诉我。")

        return "\n".join(lines)
