"""Skill 管理器 — 激活/查询/退出/超时

职责：
- 管理 Skill 的生命周期（激活 → 执行 → 完成/退出）
- Redis 存储 Skill 状态
- 提供 Skill 查询接口
"""
import json
import time
from typing import Optional
import structlog
from services.redis_client import get_redis
from skills.base import BaseSkill, SkillState, SkillPhase

logger = structlog.get_logger(__name__)

SKILL_TTL = 1800  # 30分钟


class SkillManager:

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        """注册 Skill"""
        self._skills[skill.name] = skill
        logger.info("skill_registered", name=skill.name)

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def get_all_skills(self) -> dict[str, BaseSkill]:
        return self._skills.copy()

    # ── Redis 状态管理 ──

    def _key(self, session_id: str) -> str:
        return f"chat::ai::skill::{session_id}"

    def get_active_skill(self, session_id: str) -> Optional[tuple[BaseSkill, SkillState]]:
        """查询当前会话是否有活跃 Skill"""
        try:
            r = get_redis()
            raw = r.get(self._key(session_id))
            if not raw:
                return None
            data = json.loads(raw)
            # 确保 phase 字段正确反序列化为枚举
            if "phase" in data and isinstance(data["phase"], str):
                try:
                    data["phase"] = SkillPhase(data["phase"])
                except ValueError:
                    return None
            state = SkillState(**data)
            if state.phase in (SkillPhase.COMPLETED, SkillPhase.FAILED):
                return None
            skill = self._skills.get(state.skill_name)
            if not skill:
                return None
            return skill, state
        except Exception:
            return None

    def activate_skill(self, session_id: str, skill: BaseSkill) -> SkillState:
        """激活一个 Skill"""
        state = SkillState(
            skill_name=skill.name,
            pending_params=[p.name for p in skill.params if p.required],
        )
        self._save_state(session_id, state)
        logger.info("skill_activated", session_id=session_id, skill=skill.name)
        return state

    def update_state(self, session_id: str, state: SkillState):
        """更新 Skill 状态"""
        self._save_state(session_id, state)

    def clear_skill(self, session_id: str):
        """清除 Skill 状态"""
        try:
            r = get_redis()
            r.delete(self._key(session_id))
        except Exception:
            pass

    def _save_state(self, session_id: str, state: SkillState):
        try:
            r = get_redis()
            data = {
                "skill_name": state.skill_name,
                "phase": state.phase.value,
                "collected": state.collected,
                "pending_params": state.pending_params,
                "context": state.context,
                "turns": state.turns,
                "error": state.error,
            }
            r.setex(self._key(session_id), SKILL_TTL,
                    json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("skill_save_failed", error=str(e))


# 全局单例
skill_manager = SkillManager()
