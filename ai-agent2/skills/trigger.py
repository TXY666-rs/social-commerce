"""Skill 触发检测 — 在路由之前执行

逻辑：
1. 先检查是否有活跃 Skill（直接接管）
2. 再用关键词匹配是否触发新 Skill
3. 都没有 → 返回 None，走正常路由
"""
import time
from typing import Optional
from skills.base import BaseSkill, SkillState, SkillPhase
from skills.manager import skill_manager
import structlog
from middleware.context import _get_user_id

logger = structlog.get_logger(__name__)


async def check_active_skill(message: str, session_id: str) -> tuple[Optional[str], Optional[str]]:
    """检查是否有活跃 Skill 并处理（会话连续性，最高优先级）

    Returns:
        (str, str): (Skill 生成的回复, skill_name)
        (None, None): 没有活跃 Skill，继续后续流程
    """
    active = skill_manager.get_active_skill(session_id)
    if active:
        skill, state = active
        logger.info("skill_active_found", session_id=session_id, skill=skill.name, phase=state.phase)
        reply = await _handle_active_skill(skill, state, message, session_id)
        return (reply, skill.name)
    return (None, None)


async def trigger_skill(message: str, session_id: str) -> tuple[Optional[str], Optional[str]]:
    """Skill 触发检测并处理（新 Skill 激活）

    Returns:
        (str, str): (Skill 生成的回复, skill_name)
        (None, None): 没有匹配的 Skill，走正常路由
    """
    triggered_skill = _detect_trigger(message)
    if triggered_skill:
        logger.info("skill_triggered", skill=triggered_skill.name, message=message[:50])
        state = skill_manager.activate_skill(session_id, triggered_skill)
        # 触发时检测上下文（如退款/退货类型区分）
        triggered_skill.detect_trigger_context(message, state)
        reply = await _handle_active_skill(triggered_skill, state, message, session_id)
        return (reply, triggered_skill.name)
    return (None, None)


async def try_skill(message: str, session_id: str) -> tuple[Optional[str], Optional[str]]:
    """兼容旧接口：活跃 Skill 检查 + 触发检测"""
    reply, skill_name = await check_active_skill(message, session_id)
    if reply:
        return (reply, skill_name)
    return await trigger_skill(message, session_id)


def _detect_trigger(message: str) -> Optional[BaseSkill]:
    """关键词触发检测 — 最长匹配优先

    解决关键词包含关系导致的误匹配问题，例如：
    - "我要取消退款" 应匹配 CancelRefundSkill("取消退款") 而非 ReturnItemSkill("退款")
    - "不要退了" 应匹配 CancelRefundSkill("不要退了") 而非 ReturnItemSkill("不要了")
    """
    msg_lower = message.lower()
    best_skill = None
    best_len = 0

    for skill in skill_manager.get_all_skills().values():
        for kw in skill.trigger_keywords:
            if kw in msg_lower and len(kw) > best_len:
                best_skill = skill
                best_len = len(kw)

    return best_skill


async def _handle_active_skill(skill: BaseSkill, state: SkillState,
                                message: str, session_id: str) -> str:
    """处理活跃 Skill 的用户消息"""
    user_id = _get_user_id(session_id)

    # ── 退出检测 ──
    if skill.is_exit_intent(message):
        skill_manager.clear_skill(session_id)
        return "好的，已取消当前操作。请问还有什么可以帮您？"

    state.turns += 1

    # ── 参数收集阶段 ──
    if state.phase == SkillPhase.COLLECTING:
        return await _collect_params(skill, state, message, session_id, user_id)

    # ── 确认阶段 ──
    if state.phase == SkillPhase.CONFIRMING:
        return await _handle_confirm(skill, state, message, session_id, user_id)

    # ── 执行阶段 ──
    if state.phase == SkillPhase.EXECUTING:
        return await _execute_skill(skill, state, session_id, user_id)

    return "抱歉，处理出现了问题，请稍后重试。"


async def _collect_params(skill: BaseSkill, state: SkillState,
                           message: str, session_id: str, user_id: str) -> str:
    """参数收集逻辑

    提取策略：
    1. 优先提取精确参数（regex/keyword）
    2. 仅当没有精确参数被提取时，才提取 raw 参数
       避免"order2026060100003"同时被 order_id(regex) 和 reason(raw) 提取
    """
    newly_collected = {}
    has_precise_extract = False  # 是否有精确提取（regex/keyword）

    # 第一轮：提取精确参数（regex/keyword）
    for param_def in skill.params:
        if param_def.name in state.pending_params and param_def.extractor != "raw":
            if state.turns == 1 and param_def.skip_on_trigger:
                continue
            value = skill.extract_param(param_def, message)
            if value:
                has_precise_extract = True

                if param_def.validator:
                    is_valid, validated_value, error_msg = await param_def.validator(value, user_id)
                    if not is_valid:
                        # 验证失败：保留在 pending_params 中，用户可重新输入
                        return error_msg
                    # 验证通过：保存到 collected
                    state.pending_params.remove(param_def.name)
                    state.collected[param_def.name] = validated_value
                    newly_collected[param_def.name] = validated_value
                else:
                    # 无验证器：直接保存
                    state.pending_params.remove(param_def.name)
                    state.collected[param_def.name] = value
                    newly_collected[param_def.name] = value

    # 第二轮：提取 raw 参数（仅当没有精确参数被提取时）
    for param_def in skill.params:
        if param_def.name in state.pending_params and param_def.extractor == "raw":
            if state.turns == 1 and param_def.skip_on_trigger:
                continue
            if has_precise_extract:
                continue  # 已有精确参数被提取，跳过 raw 参数
            value = skill.extract_param(param_def, message)
            if value:
                if param_def.validator:
                    is_valid, validated_value, error_msg = await param_def.validator(value, user_id)
                    if not is_valid:
                        return error_msg
                    state.pending_params.remove(param_def.name)
                    state.collected[param_def.name] = validated_value
                    newly_collected[param_def.name] = validated_value
                else:
                    state.pending_params.remove(param_def.name)
                    state.collected[param_def.name] = value
                    newly_collected[param_def.name] = value

    if newly_collected:
        logger.info("skill_params_collected", skill=skill.name,
                     collected=newly_collected, remaining=state.pending_params)

    # 还有未收集的参数 → 追问（使用动态话术，子类可根据上下文定制）
    if state.pending_params:
        next_param_name = state.pending_params[0]
        skill_manager.update_state(session_id, state)
        return skill.get_param_prompt(next_param_name, state)

    # 所有参数已收集 → 检查是否需要确认
    confirm_prompt = await skill.build_confirm_prompt(state)
    if confirm_prompt:
        if state.context.get("needs_confirm", True):
            # 需要用户确认 → 进入确认阶段
            state.phase = SkillPhase.CONFIRMING
            skill_manager.update_state(session_id, state)
            logger.info("skill_enter_confirming", skill=skill.name, session_id=session_id)
            return confirm_prompt
        else:
            # 不需要确认（拒绝/提示类消息）→ 直接完成
            state.phase = SkillPhase.COMPLETED
            skill_manager.update_state(session_id, state)
            skill_manager.clear_skill(session_id)
            logger.info("skill_auto_completed", skill=skill.name, session_id=session_id)
            return confirm_prompt

    # 不需要确认 → 直接执行
    state.phase = SkillPhase.EXECUTING
    skill_manager.update_state(session_id, state)
    return await _execute_skill(skill, state, session_id, user_id)


async def _handle_confirm(skill: BaseSkill, state: SkillState,
                          message: str, session_id: str, user_id: str) -> str:
    """处理确认阶段的用户回复"""
    # 检测确认意图
    if skill.is_confirm_intent(message):
        logger.info("skill_user_confirmed", skill=skill.name, session_id=session_id)
        state.phase = SkillPhase.EXECUTING
        skill_manager.update_state(session_id, state)
        return await _execute_skill(skill, state, session_id, user_id)

    # 检测拒绝意图
    if skill.is_deny_intent(message):
        logger.info("skill_user_denied", skill=skill.name, session_id=session_id)
        skill_manager.clear_skill(session_id)
        return "好的，已取消当前操作。请问还有什么可以帮您？"

    # 既不是确认也不是拒绝，提示用户
    return '请回复"确认"继续操作，或"取消"放弃。'


async def _execute_skill(skill: BaseSkill, state: SkillState,
                          session_id: str, user_id: str) -> str:
    """执行 Skill"""
    t0 = time.monotonic()
    try:
        reply = await skill.execute(state, user_id)
        duration = time.monotonic() - t0

        state.phase = SkillPhase.COMPLETED
        skill_manager.update_state(session_id, state)
        skill_manager.clear_skill(session_id)

        logger.info("skill_executed",
                     skill=skill.name,
                     session_id=session_id,
                     duration=f"{duration:.2f}s",
                     turns=state.turns)
        return reply
    except Exception as e:
        duration = time.monotonic() - t0

        state.phase = SkillPhase.FAILED
        state.error = str(e)
        skill_manager.update_state(session_id, state)

        logger.error("skill_execute_failed",
                     skill=skill.name,
                     session_id=session_id,
                     user_id=user_id,
                     error=str(e),
                     error_type=type(e).__name__,
                     phase=state.phase.value,
                     collected=state.collected,
                     duration=f"{duration:.2f}s",
                     turns=state.turns)
        return f"处理过程中出现了问题，请稍后重试。您也可以回复'转人工'获取帮助。"
