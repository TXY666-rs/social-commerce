"""Skill 注册表 — 自动注册 + 初始化"""
from skills.manager import skill_manager
from skills.trigger import try_skill, check_active_skill, trigger_skill
from skills.return_item_skill import ReturnItemSkill
from skills.track_order_skill import TrackOrderSkill
from skills.modify_order_skill import ModifyOrderSkill
from skills.cancel_refund_skill import CancelRefundSkill
from skills.refund_status_skill import RefundStatusSkill
from skills.complaint_skill import ComplaintSkill
from skills.transfer_to_human_skill import TransferToHumanSkill

# ── 注册所有 Skill ──
skill_manager.register(ReturnItemSkill())
skill_manager.register(TrackOrderSkill())
skill_manager.register(ModifyOrderSkill())
skill_manager.register(CancelRefundSkill())
skill_manager.register(RefundStatusSkill())
skill_manager.register(ComplaintSkill())
skill_manager.register(TransferToHumanSkill())

__all__ = ["skill_manager", "try_skill", "check_active_skill", "trigger_skill"]
