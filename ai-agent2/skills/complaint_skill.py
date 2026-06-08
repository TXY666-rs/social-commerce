"""投诉 Skill — 提交投诉转人工处理

流程：
1. 用户说"投诉" → 触发 Skill
2. 收集投诉描述和订单号（可选）
3. 确认阶段：展示投诉信息，等待用户确认
4. 提交投诉
"""
import structlog
from typing import Optional
from skills.base import BaseSkill, ParamDef, SkillState
from agents.tools.after_sale_tool import _submit_complaint_api

logger = structlog.get_logger(__name__)


# 投诉类型检测关键词
_COMPLAINT_TYPE_KEYWORDS = {
    "delivery": ["快递", "物流", "发货", "配送", "运输", "签收", "包裹", "没到", "丢了"],
    "product": ["商品", "质量", "假货", "坏了", "破损", "不一样", "描述不符", "瑕疵", "有问题"],
    "service": ["态度", "客服", "服务", "回复", "不理", "推诿", "敷衍"],
}


def _detect_complaint_type(detail: str) -> str:
    """根据投诉描述自动检测投诉类型

    Returns:
        "delivery" / "product" / "service"
    """
    detail_lower = detail.lower()
    scores = {ctype: 0 for ctype in _COMPLAINT_TYPE_KEYWORDS}
    for ctype, keywords in _COMPLAINT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in detail_lower:
                scores[ctype] += 1

    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else "service"


class ComplaintSkill(BaseSkill):
    name = "complaint"
    description = "投诉：收集投诉描述+订单号→确认→提交投诉"
    trigger_keywords = ["投诉", "举报", "差评", "不满意", "服务态度", "有问题"]

    _TYPE_NAMES = {"service": "服务问题", "delivery": "物流问题", "product": "商品问题"}

    params = [
        ParamDef(
            name="detail",
            ask_prompt="非常理解您的心情，遇到问题确实让人不舒服。我来帮您登记投诉。\n请问您要投诉什么问题？请详细描述一下，我来帮您处理。",
            extractor="raw",
            required=True,
            skip_on_trigger=True,
        ),
        ParamDef(
            name="order_id",
            ask_prompt='好的，请问涉及哪个订单？请提供订单号（格式：order+13位数字）。\n如果与具体订单无关，回复"无"跳过。',
            extractor="regex",
            pattern=r"order\d{13}",
            required=False,
        ),
    ]

    async def build_confirm_prompt(self, state: SkillState) -> Optional[str]:
        """确认阶段：展示投诉信息，等待用户确认"""
        detail = state.collected["detail"]
        order_id = state.collected.get("order_id", "")
        complaint_type = _detect_complaint_type(detail)
        type_name = self._TYPE_NAMES.get(complaint_type, "服务问题")

        state.context["complaint_type"] = complaint_type
        state.context["needs_confirm"] = True

        order_line = f"📋 关联订单：{order_id}\n" if order_id else ""
        return (
            f"好的，确认一下投诉信息：\n\n"
            f"📝 投诉内容：{detail[:200]}\n"
            f"🏷️ 投诉类型：{type_name}\n"
            f"{order_line}\n"
            f"确认提交投诉吗？提交后会有专人跟进处理。\n\n"
            f'回复"确认"提交，或"取消"放弃。'
        )

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行投诉提交"""
        detail = state.collected["detail"]
        order_id = state.collected.get("order_id", "")
        complaint_type = state.context.get("complaint_type", _detect_complaint_type(detail))

        success, msg = _submit_complaint_api(order_id, detail, complaint_type)

        if success:
            type_name = self._TYPE_NAMES.get(complaint_type, "服务问题")
            lines = [
                "投诉已登记成功 ✅\n",
                f"🏷️ 投诉类型：{type_name}",
                f"📝 投诉内容：{detail[:100]}",
            ]
            if order_id:
                lines.append(f"📋 关联订单：{order_id}")
            lines.append(
                "\n人工客服将尽快与您联系处理。\n"
                f'您也可以回复"转人工"直接与客服沟通。有其他需要随时告诉我～'
            )
            return "\n".join(lines)
        return '提交投诉时出了点问题，请稍后重试或回复"转人工"直接联系客服。'
