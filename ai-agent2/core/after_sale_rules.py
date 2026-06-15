"""售后规则统一模块 — 集中管理退货/退款时效判断

解决问题：
    原来 7天无理由退货 / 15天质量问题的判断逻辑在 after_sale_tool.py 和
    return_item_skill.py 中各实现了一套，质量关键词列表有差异，拒绝行为也不同。
    同一个请求走 Tool 路径和 Skill 路径可能得到矛盾的回答。

使用方式：
    from core.after_sale_rules import check_refund_eligibility, RefundEligibility

    result = check_refund_eligibility(complete_time, reason)
    if not result.eligible:
        return result.message  # 统一的拒绝话术
"""

from dataclasses import dataclass
from datetime import date, datetime
import structlog

logger = structlog.get_logger(__name__)


# ============================================================
# 质量关键词（统一维护，避免多处不一致）
# ============================================================

QUALITY_ISSUE_KEYWORDS = [
    "质量", "坏", "破", "损", "不工作", "漏", "故障", "问题", "瑕疵",
    "坏了", "碎了", "裂了", "断了", "掉了", "不亮", "不转",
    "有洞", "有洞", "有污渍", "掉色", "起球", "开线",
]

# 退货时效（天）
NO_REASON_RETURN_DAYS = 7       # 无理由退货期
QUALITY_ISSUE_RETURN_DAYS = 15  # 质量问题退货期


@dataclass
class RefundEligibility:
    """退货资格检查结果"""
    eligible: bool              # 是否可以退货
    message: str                # 结果说明（eligible=True 时为通过说明，False 时为拒绝话术）
    days_passed: int | None     # 距确认收货天数
    block_reason: str | None    # 阻止原因标签（供 LLM 理解）


def _parse_days_since_complete(complete_time: str) -> int | None:
    """解析确认收货时间，返回距今天数。解析失败返回 None"""
    if not complete_time:
        return None
    try:
        complete_str = complete_time.strip()[:10]
        complete_date = datetime.strptime(complete_str, "%Y-%m-%d").date()
        return (date.today() - complete_date).days
    except ValueError:
        return None


def is_quality_issue(reason: str) -> bool:
    """判断退货原因是否属于质量问题"""
    if not reason:
        return False
    reason_lower = reason.lower()
    return any(kw in reason_lower for kw in QUALITY_ISSUE_KEYWORDS)


def check_refund_eligibility(complete_time: str, reason: str = "") -> RefundEligibility:
    """检查退货/退款资格（统一入口）

    规则：
        1. 未确认收货（complete_time 为空）→ 允许，提示"由后台审核"
        2. 确认收货 ≤ 7天 → 允许（无理由退货期）
        3. 确认收货 7-15天 → 仅质量问题允许
        4. 确认收货 > 15天 → 不允许，建议转人工

    Args:
        complete_time: 确认收货时间字符串（如 "2026-05-23T14:30:00"）
        reason: 退货原因（用于判断质量问题）

    Returns:
        RefundEligibility 结果
    """
    days_passed = _parse_days_since_complete(complete_time)

    # 未确认收货
    if days_passed is None:
        return RefundEligibility(
            eligible=True,
            message="订单尚未确认收货，已提交退款由后台审核",
            days_passed=None,
            block_reason=None,
        )

    # ≤ 7天：无理由退货期
    if days_passed <= NO_REASON_RETURN_DAYS:
        return RefundEligibility(
            eligible=True,
            message=f"确认收货距今 {days_passed} 天，在 7 天无理由退货期内",
            days_passed=days_passed,
            block_reason=None,
        )

    # 7-15天：仅质量问题
    if days_passed <= QUALITY_ISSUE_RETURN_DAYS:
        if is_quality_issue(reason):
            return RefundEligibility(
                eligible=True,
                message=f"确认收货距今 {days_passed} 天，超过无理由退货期但属于质量问题",
                days_passed=days_passed,
                block_reason=None,
            )
        return RefundEligibility(
            eligible=False,
            message=(
                f"确认收货距今 {days_passed} 天，已超过 7 天无理由退货期。\n"
                "仅在商品存在质量问题时可在 15 天内申请退货。\n"
                "如果是其他原因，建议提交投诉或转人工客服处理。"
            ),
            days_passed=days_passed,
            block_reason="超7天无理由,非质量问题",
        )

    # > 15天：不允许
    return RefundEligibility(
        eligible=False,
        message=(
            f"确认收货距今 {days_passed} 天，已超过 15 天退货时效。\n"
            "无法在线申请退货退款。建议转人工客服协商处理。"
        ),
        days_passed=days_passed,
        block_reason=f"超期{days_passed}天",
    )
