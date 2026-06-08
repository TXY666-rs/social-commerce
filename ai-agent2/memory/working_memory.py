"""Working Memory — 任务状态追踪

不同于 session_memory（存聊天记录）和 summarizer（存摘要），
Working Memory 追踪的是"当前任务做到哪了"——一个结构化的任务状态机。

设计思路：
    客服场景的任务通常是多步骤的（查订单 → 确认哪一单 → 申请退款 → 确认原因）。
    传统方式靠 LLM 自己从聊天历史中"回忆"，容易遗漏关键信息。
    Working Memory 把任务状态显式化，注入 System Prompt，让 LLM 始终知道当前进度。

状态模型：
    phase:      任务阶段（information_gathering / confirmation / execution / completed）
    task_type:  任务类型（refund / return / complaint / query_order / ...）
    collected:  已收集的信息（dict，如 {"order_id": 123, "reason": "质量问题"}）
    pending:    待收集的信息（list，如 ["receiver_address"]）
    turns:      当前任务已进行的轮数
"""

import json
import structlog
from dataclasses import dataclass, field
from services.redis_client import get_redis

logger = structlog.get_logger(__name__)

WM_TTL = 3600  # 1 小时（比 session 短，任务完成后不需要保留）


# ============================================================
# 任务阶段定义
# ============================================================

class Phase:
    """任务阶段枚举"""
    GATHERING = "information_gathering"    # 信息收集阶段
    CONFIRMATION = "confirmation"          # 用户确认阶段
    EXECUTION = "execution"                # 执行操作阶段
    COMPLETED = "completed"                # 任务完成


# 每种任务需要收集的信息模板
TASK_REQUIREMENTS = {
    "refund": ["order_id", "reason"],
    "return": ["order_id", "reason", "return_type"],
    "complaint": ["order_id", "detail", "complaint_type"],
    "query_order": [],                     # 查询不需要额外信息
    "query_logistics": [],
    "cancel_order": ["order_id"],
}


@dataclass
class TaskState:
    """单个任务的状态"""
    phase: str = Phase.GATHERING
    task_type: str = ""
    collected: dict = field(default_factory=dict)   # 已收集的信息
    pending: list = field(default_factory=list)      # 待收集的信息
    turns: int = 0                                   # 当前任务轮数
    error: str = ""                                  # 最近一次错误

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "task_type": self.task_type,
            "collected": self.collected,
            "pending": self.pending,
            "turns": self.turns,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskState":
        return cls(
            phase=data.get("phase", Phase.GATHERING),
            task_type=data.get("task_type", ""),
            collected=data.get("collected", {}),
            pending=data.get("pending", []),
            turns=data.get("turns", 0),
            error=data.get("error", ""),
        )


# ============================================================
# Working Memory 管理器
# ============================================================

class WorkingMemory:
    """管理单个会话的任务状态"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._state: TaskState | None = None

    def _key(self) -> str:
        return f"chat::ai::wm::{self.session_id}"

    def load(self) -> TaskState:
        """从 Redis 加载任务状态，不存在则返回空状态"""
        if self._state is not None:
            return self._state
        try:
            r = get_redis()
            raw = r.get(self._key())
            if raw:
                self._state = TaskState.from_dict(json.loads(raw))
                return self._state
        except Exception:
            pass
        self._state = TaskState()
        return self._state

    def save(self):
        """保存任务状态到 Redis"""
        if self._state is None:
            return
        try:
            r = get_redis()
            r.setex(self._key(), WM_TTL,
                    json.dumps(self._state.to_dict(), ensure_ascii=False))
        except Exception as e:
            logger.warning("wm_save_failed", error=str(e))

    def start_task(self, task_type: str):
        """开始一个新任务"""
        requirements = TASK_REQUIREMENTS.get(task_type, [])
        self._state = TaskState(
            phase=Phase.GATHERING,
            task_type=task_type,
            collected={},
            pending=list(requirements),
            turns=0,
        )
        self.save()
        logger.info("wm_task_started", task_type=task_type, pending=requirements)

    def collect(self, key: str, value):
        """收集一条信息"""
        state = self.load()
        state.collected[key] = value
        if key in state.pending:
            state.pending.remove(key)
        # 如果所有信息都收集完了，进入确认阶段
        if not state.pending and state.phase == Phase.GATHERING:
            state.phase = Phase.CONFIRMATION
        self.save()

    def advance_phase(self, new_phase: str):
        """推进任务阶段"""
        state = self.load()
        old_phase = state.phase
        state.phase = new_phase
        self.save()
        logger.info("wm_phase_advanced", session_id=self.session_id,
                     old=old_phase, new=new_phase)

    def mark_error(self, error: str):
        """记录错误"""
        state = self.load()
        state.error = error
        self.save()

    def complete(self):
        """标记任务完成"""
        state = self.load()
        state.phase = Phase.COMPLETED
        self.save()
        logger.info("wm_task_completed", session_id=self.session_id,
                     task_type=state.task_type, turns=state.turns)

    def reset(self):
        """重置任务状态（新任务开始时调用）"""
        self._state = TaskState()
        self.save()

    def increment_turn(self):
        """轮数 +1"""
        state = self.load()
        state.turns += 1
        self.save()

    def get_state(self) -> TaskState:
        return self.load()

    def build_context(self) -> str:
        """构建 Working Memory 上下文，注入 System Prompt。

        Returns:
            格式化的任务状态提示段落（空字符串 = 无活跃任务）
        """
        state = self.load()

        # 没有活跃任务
        if not state.task_type or state.phase == Phase.COMPLETED:
            return ""

        lines = ["【任务状态追踪】"]

        phase_desc = {
            Phase.GATHERING: "信息收集阶段 — 还需要向用户确认以下信息",
            Phase.CONFIRMATION: "确认阶段 — 已收集到足够信息，等待用户确认后执行",
            Phase.EXECUTION: "执行阶段 — 正在调用工具完成任务",
        }
        lines.append(f"当前任务: {state.task_type}")
        lines.append(f"当前阶段: {phase_desc.get(state.phase, state.phase)}")

        if state.collected:
            lines.append(f"已收集信息: {json.dumps(state.collected, ensure_ascii=False)}")

        if state.pending:
            lines.append(f"待收集信息: {', '.join(state.pending)}")
            lines.append("→ 请优先向用户询问以上缺失信息，不要跳过。")

        if state.error:
            lines.append(f"上次错误: {state.error}")
            lines.append("→ 请基于错误信息调整策略，不要重复相同的错误操作。")

        lines.append(f"已进行轮数: {state.turns}")
        if state.turns >= 5:
            lines.append("→ 对话轮数较多，建议加快解决节奏，避免用户失去耐心。")

        return "\n".join(lines)


# ============================================================
# 全局管理器（按 session_id 创建）
# ============================================================

_instances: dict[str, WorkingMemory] = {}


def get_working_memory(session_id: str) -> WorkingMemory:
    """获取或创建 WorkingMemory 实例"""
    if session_id not in _instances:
        _instances[session_id] = WorkingMemory(session_id)
    return _instances[session_id]
