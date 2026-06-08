"""Skill 基类 — 有状态的会话级任务流程

核心设计：
- 每个 Skill 是一个状态机：collecting → executing → completed
- Skill 激活后"接管"会话，后续消息直接交给 Skill，跳过路由
- 参数收集阶段用正则/关键词提取，不依赖 LLM
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import re
import structlog

logger = structlog.get_logger(__name__)


class SkillPhase(str, Enum):
    COLLECTING = "collecting"    # 收集参数阶段
    CONFIRMING = "confirming"    # 确认阶段（等待用户确认后再执行）
    EXECUTING = "executing"      # 执行操作阶段
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败


@dataclass
class ParamDef:
    """参数定义"""
    name: str
    ask_prompt: str                          # 追问话术
    extractor: str = "raw"                   # 提取策略: regex/keyword/raw
    pattern: str = ""                        # regex 模式
    keywords: dict[str, list[str]] = field(default_factory=dict)  # keyword 分类映射
    validator: Optional[Callable] = None     # 验证函数 (value, user_id) -> (is_valid, value, error_msg)
    required: bool = True
    skip_on_trigger: bool = False            # 触发消息中是否跳过（避免把触发语句误认为参数值）


@dataclass
class SkillState:
    """Skill 运行时状态"""
    skill_name: str
    phase: SkillPhase = SkillPhase.COLLECTING
    collected: dict[str, Any] = field(default_factory=dict)
    pending_params: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)  
    turns: int = 0
    error: str = ""


class BaseSkill(ABC):
    """Skill 基类"""

    name: str = ""
    description: str = ""
    trigger_keywords: list[str] = []         # 触发关键词
    params: list[ParamDef] = []              # 需要收集的参数定义
    timeout: int = 1800                      # 超时时间

    @abstractmethod
    async def execute(self, state: SkillState, user_id: str) -> str:
        """所有参数收集完成后的执行逻辑，返回最终回复"""
        ...

    def detect_trigger_context(self, message: str, state: SkillState) -> None:
        """触发时检测上下文信息（子类可重写）

        在 Skill 被关键词触发后立即调用，用于从触发消息中提取
        意图类型等上下文信息，存入 state.context。
        例如：ReturnItemSkill 区分"退款"和"退货退款"。
        """
        pass

    def build_prompt_hint(self, state: SkillState) -> str:
        """构建注入 System Prompt 的 Skill 上下文（可选）"""
        return ""

    async def build_confirm_prompt(self, state: SkillState) -> Optional[str]:
        """构建确认话术。

        Returns:
            None: 不需要确认，直接执行
            str: 展示给用户的消息
                - state.context["needs_confirm"] = True  → 进入确认阶段等待用户确认
                - state.context["needs_confirm"] = False → 直接完成（用于拒绝/提示类消息）

        子类重写此方法以提供确认步骤。
        """
        return None

    # ── 确认/拒绝意图检测 ──

    _CONFIRM_KEYWORDS = ["确认", "好的", "可以", "是的", "嗯", "确定", "ok",
                         "好", "行", "没问题", "提交", "同意"]

    _DENY_KEYWORDS = ["算了", "不退了", "不要了", "不用了", "退出",
                      "不买了", "不提交", "放弃", "不了"]

    def is_confirm_intent(self, message: str) -> bool:
        """检测用户是否确认"""
        msg = message.strip().lower()
        return any(kw in msg for kw in self._CONFIRM_KEYWORDS)

    def is_deny_intent(self, message: str) -> bool:
        """检测用户是否拒绝"""
        msg = message.strip().lower()
        return any(kw in msg for kw in self._DENY_KEYWORDS)

    # ── 参数提取 ──

    def extract_param(self, param_def: ParamDef, user_message: str) -> Optional[str]:
        """从用户消息中提取参数值"""
        if param_def.extractor == "regex":
            return self._extract_regex(param_def, user_message)
        elif param_def.extractor == "keyword":
            return self._extract_keyword(param_def, user_message)
        elif param_def.extractor == "raw":
            return user_message.strip()
        return None

    def _extract_regex(self, param_def: ParamDef, msg: str) -> Optional[str]:
        match = re.search(param_def.pattern, msg)
        return match.group(0) if match else None

    def _extract_keyword(self, param_def: ParamDef, msg: str) -> Optional[str]:
        msg_lower = msg.lower()
        for category, keywords in param_def.keywords.items():
            for kw in keywords:
                if kw in msg_lower:
                    return category
        return None

    def get_param_prompt(self, param_name: str, state: SkillState) -> str:
        """获取参数的追问话术（子类可重写以实现动态话术）

        默认返回 ParamDef 中定义的 ask_prompt。
        子类可根据 state.context 中的信息返回不同的话术。
        """
        for p in self.params:
            if p.name == param_name:
                return p.ask_prompt
        return ""

    def is_exit_intent(self, message: str) -> bool:
        """检测用户是否想退出当前 Skill"""
        exit_keywords = ["算了", "不退了", "不要了", "不用了", "退出", "不买了"]
        return any(kw in message for kw in exit_keywords)
