"""退款/退货退款 Skill — 根据用户意图自适应话术

流程：
1. 触发时检测意图类型（退款 / 退货退款）
2. 收集订单号 + 原因
3. 确认阶段：展示订单信息 + 退款/退货条件，等待用户确认
4. 检查发货状态
   - 未发货 → 自动退款
   - 已发货 → 检查退货期
5. 提交退款/退货退款申请

设计要点：
- 用户说"退款" → 全程用"退款"话术，不提"退货"
- 用户说"退货" → 全程用"退货退款"话术
- 执行阶段根据实际发货状态自动选择 API（不受话术影响）
"""
from datetime import date, datetime
from typing import Optional
import structlog
from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.orders_tool import _fetch_orders
from agents.tools.after_sale_tool import _submit_refund_api, _submit_return_api

logger = structlog.get_logger(__name__)

# ── 退货原因映射 ──
REASON_MAP = {
    "1": "质量问题",
    "2": "发错货",
    "3": "不喜欢/不合适",
    "4": "其他原因",
}

# 明确表达"退货"意图的关键词（其余触发词默认视为仅退款）
_RETURN_KEYWORDS = ["退货", "退掉", "不要了", "寄回", "退回"]


def _normalize_reason(reason: str) -> str:
    """将数字原因转换为文字"""
    return REASON_MAP.get(reason.strip(), reason)


async def _validate_order_id(order_id: str, user_id: str) -> tuple[bool, str, str]:
    """验证订单是否存在，返回 (is_valid, order_id, error_msg)"""
    orders = _fetch_orders()
    if orders is None:
        return False, "", "查询订单时出现问题，请稍后重试。"

    target = next((o for o in orders if str(o.get("id", "")) == order_id), None)
    if not target:
        return False, "", f"未找到订单号 {order_id}，请确认后重新输入。"

    status = target.get("status", -1)
    if status == 4:
        return False, "", "该订单已取消，无法申请退款。"
    if status == 5:
        return False, "", "该订单已有退款/退货申请在处理中。"
    if status == 6:
        return False, "", "该订单已退款完成。"

    return True, str(order_id), ""


class ReturnItemSkill(BaseSkill):
    name = "return_item"
    description = "退款/退货退款：查订单→确认→检查条件→提交申请"
    trigger_keywords = ["退货", "退掉", "不要了", "退款", "退钱", "申请退", "我想退"]

    params = [
        ParamDef(
            name="order_id",
            ask_prompt="",  # 由 get_param_prompt 动态生成
            extractor="regex",
            pattern=r"order\d{13}",
            validator=_validate_order_id,
            required=True,
        ),
        ParamDef(
            name="reason",
            ask_prompt="",  # 由 get_param_prompt 动态生成
            extractor="raw",
            required=True,
            skip_on_trigger=True,
        ),
    ]

    # ── 触发时检测退款类型 ──

    def detect_trigger_context(self, message: str, state: SkillState) -> None:
        """根据触发关键词判断退款类型

        - 明确提到"退货/退掉/不要了" → return_refund（退货退款）
        - 其余（退款/退钱/申请退/我想退） → refund_only（仅退款）
        """
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in _RETURN_KEYWORDS):
            state.context["refund_type"] = "return_refund"
        else:
            state.context["refund_type"] = "refund_only"
        logger.info("refund_type_detected",
                     skill=self.name,
                     refund_type=state.context["refund_type"],
                     message=message[:50])

    # ── 动态话术 ──

    def get_param_prompt(self, param_name: str, state: SkillState) -> str:
        """根据 refund_type 返回不同的追问话术"""
        refund_type = state.context.get("refund_type", "refund_only")

        if param_name == "order_id":
            if refund_type == "return_refund":
                return ("好的，我来帮您处理退货退款～\n"
                        "请提供您的订单号（格式：order+13位数字，如 order2026060100003），"
                        "我先帮您查一下订单。")
            return ("好的，我来帮您处理退款～\n"
                    "请提供您的订单号（格式：order+13位数字，如 order2026060100003），"
                    "我先帮您查一下订单。")

        if param_name == "reason":
            if refund_type == "return_refund":
                return ("好的，请问退货的原因是什么呢？\n"
                        "1. 质量问题\n2. 发错货\n3. 不喜欢/不合适\n4. 其他原因\n"
                        "回复数字或直接描述都行～")
            return ("好的，请问退款的原因是什么呢？\n"
                    "1. 质量问题\n2. 发错货\n3. 不喜欢/不合适\n4. 其他原因\n"
                    "回复数字或直接描述都行～")

        return ""

    # ── 确认阶段 ──

    async def build_confirm_prompt(self, state: SkillState) -> Optional[str]:
        """确认阶段：展示订单信息 + 退款/退货条件，等待用户确认"""
        order_id = state.collected["order_id"]
        reason = _normalize_reason(state.collected["reason"])
        refund_type = state.context.get("refund_type", "refund_only")

        # 根据类型决定话术标签
        is_return = (refund_type == "return_refund")
        action_label = "退货退款" if is_return else "退款"
        action_short = "退货" if is_return else "退款"

        # 获取订单详情
        order_info = self._fetch_order_detail(order_id)
        if not order_info:
            state.context["needs_confirm"] = False
            return "查询订单详情失败，请稍后重试或联系人工客服。"

        state.context["order_info"] = order_info
        product_name = order_info.get("productName", "未知商品")
        total_price = order_info.get("totalPrice", 0)

        # ── 未发货 → 直接退款（无论用户说的是退款还是退货） ──
        delivery_time = order_info.get("deliveryTime", "")
        if not delivery_time:
            state.context["needs_confirm"] = True
            # 未发货时统一走退款，提示用户无需退货流程
            if is_return:
                return (
                    f"帮您查到了这笔订单：\n\n"
                    f"📦 商品：{product_name}\n"
                    f"📋 订单号：{order_id}\n"
                    f"💰 金额：¥{total_price}\n"
                    f"📝 原因：{reason}\n\n"
                    f"该订单尚未发货，不需要走退货流程，可以直接退款。\n"
                    f'请确认是否提交退款申请？回复"确认"提交，或"取消"放弃。'
                )
            return (
                f"帮您查到了这笔订单：\n\n"
                f"📦 商品：{product_name}\n"
                f"📋 订单号：{order_id}\n"
                f"💰 金额：¥{total_price}\n"
                f"📝 原因：{reason}\n\n"
                f"该订单尚未发货，可以直接退款。\n"
                f'请确认是否提交退款申请？回复"确认"提交，或"取消"放弃。'
            )

        # ── 已发货 → 检查退货期 ──
        complete_time = order_info.get("completeTime", "")
        if complete_time:
            try:
                complete_str = complete_time.strip()[:10]
                complete_date = datetime.strptime(complete_str, "%Y-%m-%d").date()
                days_passed = (date.today() - complete_date).days

                # 超过15天 → 拒绝
                if days_passed > 15:
                    state.context["needs_confirm"] = False
                    return (
                        f"帮您查到了这笔订单：\n\n"
                        f"📦 商品：{product_name}\n"
                        f"📋 订单号：{order_id}\n"
                        f"💰 金额：¥{total_price}\n"
                        f"⏰ 确认收货已{days_passed}天\n\n"
                        f"很抱歉，订单确认收货超过15天后已无法在线申请{action_label}了。\n"
                        f"建议您可以提交投诉，人工客服会帮您协商处理。\n"
                        f'回复"投诉"即可提交，或回复"转人工"直接联系客服。'
                    )

                # 7-15天 → 仅支持质量问题
                if days_passed > 7:
                    quality_keywords = ["质量", "坏", "破", "损", "故障", "问题", "瑕疵", "质量问题"]
                    is_quality = any(kw in reason for kw in quality_keywords)
                    if not is_quality:
                        state.context["needs_confirm"] = False
                        return (
                            f"帮您查到了这笔订单：\n\n"
                            f"📦 商品：{product_name}\n"
                            f"📋 订单号：{order_id}\n"
                            f"💰 金额：¥{total_price}\n"
                            f"⏰ 确认收货已{days_passed}天\n\n"
                            f"您的订单已超过7天无理由退货期，目前仅支持质量问题{action_short}。\n"
                            f"您的原因是「{reason}」，不属于质量问题范围。\n"
                            f"如果商品确实有质量问题，请描述具体情况后重试；否则建议联系人工客服协商。\n"
                            f'回复"转人工"即可联系客服。'
                        )

                    # 质量问题 → 确认
                    state.context["needs_confirm"] = True
                    return (
                        f"帮您查到了这笔订单：\n\n"
                        f"📦 商品：{product_name}\n"
                        f"📋 订单号：{order_id}\n"
                        f"💰 金额：¥{total_price}\n"
                        f"📝 原因：{reason}\n"
                        f"⏰ 确认收货已{days_passed}天\n\n"
                        f"已超过7天无理由退货期，但质量问题15天内仍可{action_short}。\n"
                        f'请确认是否提交{action_label}申请？回复"确认"提交，或"取消"放弃。'
                    )
            except ValueError:
                pass

        # ── 7天内 → 正常退款/退货 ──
        state.context["needs_confirm"] = True
        days_info = ""
        if complete_time:
            try:
                complete_str = complete_time.strip()[:10]
                complete_date = datetime.strptime(complete_str, "%Y-%m-%d").date()
                days_passed = (date.today() - complete_date).days
                days_info = f"⏰ 确认收货已{days_passed}天，符合7天无理由{action_short}条件\n\n"
            except ValueError:
                pass

        return (
            f"帮您查到了这笔订单：\n\n"
            f"📦 商品：{product_name}\n"
            f"📋 订单号：{order_id}\n"
            f"💰 金额：¥{total_price}\n"
            f"📝 原因：{reason}\n"
            f"{days_info}"
            f'请确认是否提交{action_label}申请？回复"确认"提交，或"取消"放弃。'
        )

    # ── 执行阶段 ──

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行退款/退货退款（根据发货状态自动选择 API）"""
        order_id = state.collected["order_id"]
        reason = _normalize_reason(state.collected["reason"])

        order_info = state.context.get("order_info")
        if not order_info:
            order_info = self._fetch_order_detail(order_id)
            if not order_info:
                return "查询订单详情失败，请稍后重试或联系人工客服。"

        # 未发货 → 退款
        delivery_time = order_info.get("deliveryTime", "")
        if not delivery_time:
            return self._submit_refund(order_id, reason, order_info)

        # 已发货 → 退货退款
        return self._submit_return(order_id, reason, order_info)

    def _submit_refund(self, order_id: str, reason: str, order_info: dict) -> str:
        """提交退款申请（未发货）"""
        success, msg, refund_id = _submit_refund_api(order_id, reason)
        if success:
            product_name = order_info.get("productName", "")
            return (
                f"退款申请已提交成功！✅\n\n"
                f"📦 商品：{product_name}\n"
                f"📝 原因：{reason}\n"
                f"⏰ 预计 1-3 个工作日处理\n\n"
                f"您可以在订单页查看退款进度，有其他需要随时告诉我～"
            )
        return '提交退款申请时出了点问题，请稍后重试或回复"转人工"联系客服。'

    def _submit_return(self, order_id: str, reason: str, order_info: dict) -> str:
        """提交退货退款申请（已发货）"""
        success, msg, return_id = _submit_return_api(order_id, reason)
        if success:
            product_name = order_info.get("productName", "")
            return (
                f"退货申请已提交成功！✅\n\n"
                f"📦 商品：{product_name}\n"
                f"📝 原因：{reason}\n\n"
                f"💡 温馨提示：请保持商品原包装完好，等待审核通过后寄回。\n"
                f"⏰ 预计 1-3 个工作日处理\n\n"
                f"您可以在订单页查看退款进度，有其他需要随时告诉我～"
            )
        return '提交退货申请时出了点问题，请稍后重试或回复"转人工"联系客服。'

    def _fetch_order_detail(self, order_id: str) -> Optional[dict]:
        """获取订单详情"""
        orders = _fetch_orders()
        if orders is None:
            return None
        return next((o for o in orders if str(o.get("id")) == order_id), None)
