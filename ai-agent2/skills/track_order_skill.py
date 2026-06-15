"""订单查询 Skill — 查订单+物流

流程：
1. 查询订单列表（可按关键词筛选）
2. 展示订单信息
3. 如需查物流，调用物流接口
"""
import structlog

from skills.base import BaseSkill,SkillState
from agents.tools.orders_tool import _fetch_orders
from agents.tools.logistics_tool import _track_logistics_api
from agents.tools.constants import ORDER_STATUS, NOT_LOGGED_IN_MSG

logger = structlog.get_logger(__name__)


class TrackOrderSkill(BaseSkill):
    name = "track_order"
    description = "订单查询：查订单列表、查物流状态"
    trigger_keywords = ["查订单", "订单", "我的订单", "订单查询", "订单列表",
                        "物流", "快递", "到哪了", "发货了吗", "查物流"]

    params = []  # 无需收集参数，直接查询

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行订单查询"""
        if not user_id:
            return NOT_LOGGED_IN_MSG.format(action="查询订单")

        # ── 1. 查询订单列表 ──
        orders = _fetch_orders()
        if orders is None:
            return "查询订单时出现问题，请稍后重试。"
        if not orders:
            return "好的，帮您查了一下，您目前还没有订单记录哦。有什么想买的可以告诉我～"

        # ── 2. 展示订单列表 ──
        lines = [f"好的，帮您查到了 {len(orders)} 个订单：\n"]
        for i, item in enumerate(orders, 1):
            status = ORDER_STATUS.get(item.get("status", 0), "未知状态")
            line = (
                f"【{i}】{item.get('productName', '未知商品')}"
                f" ×{item.get('quantity', 1)}  ¥{item.get('totalPrice', 0)}  [{status}]"
            )
            # 订单号（供后续取消/退款/改地址等操作使用）
            line += f"\n   订单号: {item.get('id', '未知')}"
            # 时间信息
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

        # ── 3. 查询最新订单的物流信息 ──
        latest_order = orders[0]
        order_id = latest_order.get("id")
        if order_id:
            logistics_info = self._get_logistics(order_id)
            if logistics_info:
                lines.append(f"\n【最新订单物流】{logistics_info}")

        return "\n".join(lines)

    def _get_logistics(self, order_id: int) -> str:
        """查询物流信息"""
        data_list = _track_logistics_api(order_id=str(order_id))
        if not data_list:
            return "暂无物流信息"
        data = data_list[0] if isinstance(data_list, list) and data_list else {}
        if not data:
            return "暂无物流信息"
        lines = []
        if data.get("logisticsNo"):
            lines.append(f"快递单号: {data['logisticsNo']}")
        if data.get("logisticsCompany"):
            lines.append(f"物流公司: {data['logisticsCompany']}")
        if data.get("statusDesc"):
            lines.append(f"状态: {data['statusDesc']}")
        if data.get("lastUpdateTime"):
            lines.append(f"最新更新: {data['lastUpdateTime']}")
        return "\n".join(lines) if lines else "暂无物流信息"
