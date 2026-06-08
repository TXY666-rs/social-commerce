"""Token Budget Management — 单会话 Token 预算管理

设计思路：
    每个会话有一个 Token 预算上限。当累计消耗接近上限时，
    触发上下文压缩（丢弃早期消息、压缩工具输出），避免超出预算。

    这不是限制用户使用，而是：
    1. 防止单个会话消耗过多 LLM 资源（成本控制）
    2. 避免上下文窗口溢出导致 LLM 报错（稳定性）
    3. 在预算紧张时优先保留重要信息（智能裁剪）

预算策略：
    - 正常消耗（< 70%）：不做任何干预
    - 接近上限（70-90%）：压缩早期消息，保留最近 6 轮
    - 接近上限（> 90%）：激进压缩，只保留最近 3 轮 + 摘要

面试要点：
    - 为什么需要预算管理？LLM API 按 token 计费，无限制使用成本不可控
    - 与上下文截断的区别？截断是固定窗口，预算管理是动态的（根据消耗速率调整）
    - 压缩策略：渐进式压缩，不是一刀切
"""

import structlog

logger = structlog.get_logger(__name__)


# ============================================================
# 预算配置
# ============================================================

# 每个会话的 Token 预算上限
DEFAULT_BUDGET = 100_000  # 10 万 token（约 50 轮对话）

# 压缩阈值（占预算的比例）
WARN_THRESHOLD = 0.7     # 70% — 开始压缩早期消息
CRITICAL_THRESHOLD = 0.9  # 90% — 激进压缩

# 压缩后保留的轮数
NORMAL_KEEP_TURNS = 20   # 正常保留轮数
WARN_KEEP_TURNS = 6      # 警告级别保留轮数
CRITICAL_KEEP_TURNS = 3  # 临界级别保留轮数


class TokenBudget:
    """单个会话的 Token 预算管理器"""

    def __init__(self, session_id: str, budget: int = DEFAULT_BUDGET):
        self.session_id = session_id
        self.budget = budget
        self._consumed = 0         # 已消耗的 token 数
        self._input_tokens = 0     # 累计输入 token
        self._output_tokens = 0    # 累计输出 token
        self._rounds = 0           # LLM 调用轮数

    @property
    def consumed(self) -> int:
        return self._consumed

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self._consumed)

    @property
    def usage_ratio(self) -> float:
        """已消耗占预算的比例（0.0 ~ 1.0）"""
        return self._consumed / self.budget if self.budget > 0 else 0.0

    @property
    def level(self) -> str:
        """当前预算级别"""
        ratio = self.usage_ratio
        if ratio >= CRITICAL_THRESHOLD:
            return "critical"
        elif ratio >= WARN_THRESHOLD:
            return "warn"
        return "normal"

    def record(self, input_tokens: int, output_tokens: int):
        """记录一次 LLM 调用的 token 消耗"""
        total = input_tokens + output_tokens
        self._consumed += total
        self._input_tokens += input_tokens
        self._output_tokens += output_tokens
        self._rounds += 1

        level = self.level
        if level == "critical":
            logger.warning("token_budget_critical",
                           session_id=self.session_id,
                           consumed=self._consumed,
                           budget=self.budget,
                           ratio=f"{self.usage_ratio:.1%}")
        elif level == "warn":
            logger.info("token_budget_warn",
                        session_id=self.session_id,
                        consumed=self._consumed,
                        budget=self.budget,
                        ratio=f"{self.usage_ratio:.1%}")

    def get_keep_turns(self) -> int:
        """根据预算级别返回应保留的对话轮数"""
        level = self.level
        if level == "critical":
            return CRITICAL_KEEP_TURNS
        elif level == "warn":
            return WARN_KEEP_TURNS
        return NORMAL_KEEP_TURNS

    def should_compress(self) -> bool:
        """是否需要压缩上下文"""
        return self.usage_ratio >= WARN_THRESHOLD

    def build_budget_context(self) -> str:
        """构建预算状态上下文（注入 System Prompt）"""
        level = self.level
        if level == "normal":
            return ""

        lines = ["【资源提示】"]
        if level == "critical":
            lines.append("Token 预算即将耗尽，请尽量简洁回复，减少不必要的工具调用。")
            lines.append("优先使用已有信息回答，避免重复查询。")
        elif level == "warn":
            lines.append("Token 预算消耗较多，建议适当精简回复。")

        lines.append(f"（已消耗: {self._consumed:,} / {self.budget:,}）")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取预算统计信息"""
        return {
            "session_id": self.session_id,
            "budget": self.budget,
            "consumed": self._consumed,
            "remaining": self.remaining,
            "usage_ratio": f"{self.usage_ratio:.1%}",
            "level": self.level,
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "rounds": self._rounds,
        }


# ============================================================
# 全局管理器
# ============================================================

_budgets: dict[str, TokenBudget] = {}


def get_token_budget(session_id: str, budget: int = DEFAULT_BUDGET) -> TokenBudget:
    """获取或创建指定会话的 Token 预算管理器"""
    if session_id not in _budgets:
        _budgets[session_id] = TokenBudget(session_id, budget)
    return _budgets[session_id]


def get_all_budgets() -> dict[str, dict]:
    """获取所有会话的预算统计（供管理 API 使用）"""
    return {sid: b.get_stats() for sid, b in _budgets.items()}
