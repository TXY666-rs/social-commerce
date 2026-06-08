"""转人工 Skill — 引导用户转接人工客服

流程：
1. 用户说"转人工" → 触发 Skill
2. 收集转接原因（可选）
3. 复用 transfer_tool.do_transfer_to_human() 写入 Redis 转接队列
4. 返回转接确认 + 排队提示
"""
import structlog
from skills.base import BaseSkill, ParamDef, SkillState
from middleware.context import _get_user_id
from agents.tools.transfer_tool import do_transfer_to_human

logger = structlog.get_logger(__name__)


class TransferToHumanSkill(BaseSkill):
    name = "transfer_to_human"
    description = "转人工：收集原因→写入转接队列→返回排队提示"
    trigger_keywords = ["转人工", "人工客服", "人工", "真人", "找人", "转接人工",
                        "叫人来", "换个真人"]

    params = [
        ParamDef(
            name="reason",
            ask_prompt='好的，马上帮您转接～\n请问您想转人工的原因是什么？（如：问题没解决、需要专属服务等）\n直接回复原因即可，或回复"跳过"跳过。',
            extractor="raw",
            required=False,
            skip_on_trigger=True,
        ),
    ]

    async def execute(self, state: SkillState, user_id: str) -> str:
        """执行转人工流程 — 委托给 transfer_tool.do_transfer_to_human"""
        reason = state.collected.get("reason", "")
        if not reason or reason.strip().lower() in ("跳过", "skip", "没事", "不用"):
            reason = "用户主动要求转人工"

        actual_user_id = _get_user_id() or user_id or "anonymous"

        try:
            success, transfer_id, error_msg = do_transfer_to_human(actual_user_id, reason)
            return (
                f"正在为您转接人工客服 🙋\n\n"
                f"📋 转接单号：{transfer_id}\n"
                f"📝 转接原因：{reason}\n\n"
                f"当前排队中，请稍候...人工客服接入后会主动联系您。\n"
                f"在等待期间，您也可以继续向我提问，我会尽力帮助您～"
            )
        except Exception as e:
            logger.error("transfer_skill_failed", error=str(e))
            return (
                "转接人工客服时出现异常，请稍后重试。\n"
                "您也可以拨打客服热线 400-xxx-xxxx。"
            )
