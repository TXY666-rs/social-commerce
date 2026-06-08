"""订单修改 Skill — 取消订单/催发货/改地址

流程：
1. 收集订单号
2. 确认阶段：展示订单信息，等待用户确认
3. 根据子意图执行
"""
import structlog
from typing import Optional

from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.orders_tool import _fetch_orders, _cancel_order_api, _change_address_api
from agents.tools.after_sale_tool import _remind_delivery_api
from agents.tools.constants import ORDER_STATUS

logger = structlog.get_logger(__name__)


async def _validate_order_id(order_id: str, user_id: str) -> tuple[bool, str, str]:
    """验证订单是否存在，返回 (is_valid, order_id, error_msg)"""
    orders = _fetch_orders()
    if orders is None:
        return False, "", "查询订单时出现问题，请稍后重试。"

    target = next((o for o in orders if str(o.get("id", "")) == order_id), None)
    if not target:
        return False, "", f"未找到订单号 {order_id}，请确认后重新输入。"

    return True, str(order_id), ""


class ModifyOrderSkill(BaseSkill):
    name = "modify_order"
    description = "订单修改：取消订单、催发货、改地址"
    trigger_keywords = ["取消订单", "不想买了", "取消这个", "催发货", "催单", "怎么还没到",
                        "快递太慢", "改地址", "修改地址", "换地址"]

    params = [
        ParamDef(
            name="order_id",
            ask_prompt="好的，我来帮您处理订单修改（取消订单/催发货/改地址）～\n请提供您的订单号（格式：order+13位数字），我先查一下订单。",
            extractor="regex",
            pattern=r"order\d{13}",
            validator=_validate_order_id,
            required=True,
        ),
        ParamDef(
            name="new_address",
            ask_prompt="好的，请输入您的新收货地址（详细到门牌号）。",
            extractor="raw",
            required=False,  # 仅改地址时需要
            skip_on_trigger=True,
        ),
    ]

    def _detect_sub_intent(self, message: str) -> str:
        """检测子意图"""
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ["取消", "不想买", "不想要"]):
            return "cancel"
        if any(kw in msg_lower for kw in ["催", "慢", "还没到", "什么时候到"]):
            return "expedite"
        if any(kw in msg_lower for kw in ["改地址", "修改地址", "换地址", "地址错了"]):
            return "change_address"
        return "cancel"  # 默认取消

    async def build_confirm_prompt(self, state: SkillState) -> Optional[str]:
        """确认阶段：展示订单信息，等待用户确认"""
        order_id = state.collected["order_id"]

        # 检测子意图
        sub_intent = state.context.get("sub_intent", "")
        if not sub_intent:
            original_msg = state.context.get("original_message", "")
            sub_intent = self._detect_sub_intent(original_msg) if original_msg else "cancel"
        state.context["sub_intent"] = sub_intent

        # 改地址且未提供地址 → 跳过确认，让 execute 处理
        if sub_intent == "change_address" and not state.collected.get("new_address"):
            return None

        # 获取订单详情
        order_info = self._fetch_order_detail(order_id)
        if not order_info:
            state.context["needs_confirm"] = False
            return "查询订单详情失败，请稍后重试或联系人工客服。"

        state.context["order_info"] = order_info
        status = order_info.get("status", -1)
        product_name = order_info.get("productName", "未知商品")
        status_desc = ORDER_STATUS.get(status, "未知状态")

        # ── 取消订单 ──
        if sub_intent == "cancel":
            if status != 0:
                state.context["needs_confirm"] = False
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"📊 状态：{status_desc}\n\n"
                    f"只有待付款的订单可以取消哦，当前订单状态为「{status_desc}」，无法取消。\n"
                    f'如有疑问请回复"转人工"联系客服。'
                )
            state.context["needs_confirm"] = True
            return (
                f"帮您查到了这笔订单：\n\n"
                f"📦 商品：{product_name}\n"
                f"📋 订单号：{order_id}\n"
                f"📊 状态：{status_desc}\n\n"
                f"您确定要取消这笔订单吗？取消后无法恢复。\n\n"
                f'回复"确认"取消订单，或"取消"放弃。'
            )

        # ── 催发货 ──
        if sub_intent == "expedite":
            if status not in [1, 2]:
                state.context["needs_confirm"] = False
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"📊 状态：{status_desc}\n\n"
                    f"只有已付款/已发货的订单可以催促配送，当前状态为「{status_desc}」。\n"
                    f'如有疑问请回复"转人工"联系客服。'
                )
            state.context["needs_confirm"] = True
            return (
                f"帮您查到了这笔订单：\n\n"
                f"📦 商品：{product_name}\n"
                f"📋 订单号：{order_id}\n"
                f"📊 状态：{status_desc}\n\n"
                f"确认要催促这笔订单的物流吗？\n\n"
                f'回复"确认"提交催单，或"取消"放弃。'
            )

        # ── 改地址 ──
        if sub_intent == "change_address":
            new_address = state.collected.get("new_address", "")
            if status == 0:
                state.context["needs_confirm"] = False
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"📊 状态：{status_desc}\n\n"
                    f"订单尚未付款，您可以取消后重新下单，无需修改地址。\n"
                    f'回复"取消订单"即可取消。'
                )
            if status in (2, 3):
                # 已发货/已完成 → 转人工
                state.context["needs_confirm"] = False
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"📊 状态：{status_desc}\n\n"
                    f"订单已发货，修改地址需要联系人工客服处理。\n"
                    f"正在为您转接人工客服..."
                )
            if status == 1:
                state.context["needs_confirm"] = True
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"📍 新地址：{new_address}\n\n"
                    f"确认修改收货地址吗？\n\n"
                    f'回复"确认"修改，或"取消"放弃。'
                )

        # 默认跳过确认
        return None

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行订单修改"""
        order_id = state.collected["order_id"]
        sub_intent = state.context.get("sub_intent", "cancel")

        order_info = state.context.get("order_info")
        if not order_info:
            order_info = self._fetch_order_detail(order_id)
            if not order_info:
                return "查询订单详情失败，请稍后重试或联系人工客服。"

        status = order_info.get("status", -1)
        product_name = order_info.get("productName", "")

        if sub_intent == "cancel":
            return self._cancel_order(order_id, status, product_name)
        elif sub_intent == "expedite":
            return self._expedite_shipping(order_id, status, product_name)
        elif sub_intent == "change_address":
            new_address = state.collected.get("new_address", "")
            return self._change_address(order_id, status, product_name, new_address)

        return "抱歉，无法识别您的操作意图。"

    def _cancel_order(self, order_id: str, status: int, product_name: str) -> str:
        """取消订单"""
        if status != 0:
            status_desc = ORDER_STATUS.get(status, "未知状态")
            return f'订单当前状态为「{status_desc}」，只有待付款订单可以取消。如有疑问请回复"转人工"联系客服。'

        success, msg = _cancel_order_api(order_id)
        if success:
            return (
                f"订单已取消成功 ✅\n\n"
                f"📦 商品：{product_name}\n\n"
                f"如需重新下单或其他帮助，随时告诉我～"
            )
        return "取消订单时出了点问题，请稍后重试。"

    def _expedite_shipping(self, order_id: str, status: int, product_name: str) -> str:
        """催发货"""
        if status not in [1, 2]:
            status_desc = ORDER_STATUS.get(status, "未知状态")
            return f'订单当前状态为「{status_desc}」，只有已付款/已发货订单可以催促配送。如有疑问请回复"转人工"联系客服。'

        success, msg = _remind_delivery_api(order_id)
        if success:
            return (
                f"已为您催促物流配送 ✅\n\n"
                f"📦 商品：{product_name}\n"
                f"⏰ 预计 24 小时内更新物流状态\n\n"
                f"有其他需要随时告诉我～"
            )
        return "催单时出了点问题，请稍后重试。"

    def _change_address(self, order_id: str, status: int, product_name: str, new_address: str = "") -> str:
        """改地址"""
        if status == 0:
            return (
                f"订单「{product_name}」尚未付款，您可以取消后重新下单，无需修改地址。\n"
                f'回复"取消订单"即可取消。'
            )
        if status in (2, 3):
            return (
                f"订单「{product_name}」已发货，修改地址需要联系人工客服处理。\n"
                f"正在为您转接人工客服..."
            )
        if status == 1:
            if not new_address:
                return "好的，请提供您的新收货地址（详细到门牌号），我来帮您修改。"
            success, msg = _change_address_api(order_id, new_address)
            if success:
                return (
                    f"地址修改成功 ✅\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📍 新地址：{new_address}\n\n"
                    f"有其他需要随时告诉我～"
                )
            return (
                f"订单「{product_name}」已付款但未发货，修改地址需要联系人工客服处理。\n"
                f"正在为您转接人工客服..."
            )

        status_desc = ORDER_STATUS.get(status, "未知状态")
        return (
            f"订单当前状态为「{status_desc}」，暂不支持在线修改地址。\n"
            f'回复"转人工"联系客服处理。'
        )

    def _fetch_order_detail(self, order_id: str):
        """获取订单详情"""
        orders = _fetch_orders()
        if orders is None:
            return None
        return next((o for o in orders if str(o.get("id")) == order_id), None)
