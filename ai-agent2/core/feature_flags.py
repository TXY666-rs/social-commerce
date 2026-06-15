"""功能开关（Feature Flags） — 无需代码部署即可动态启停功能

设计动机：
    智能客服系统包含大量可选功能模块（情绪检测、工作记忆、动态工具绑定、
    PII 脱敏等）。在生产环境中，需要一种轻量级机制来：

    1. **灰度发布** — 新功能上线时先关闭，验证稳定后再开启
    2. **紧急回滚** — 某个功能出现异常时立即关闭，无需重新部署
    3. **测试隔离** — 单元测试中临时关闭某些功能以验证降级路径
    4. **精细控制** — 按需关闭低优先级功能以降低系统负载

设计原则：
    - **进程内存储** — 使用模块级字典存储，零延迟读取（不依赖 Redis）
    - **线程安全** — 所有读写操作通过 ``threading.Lock`` 保护
    - **默认值不可变** — 默认配置定义在常量 ``_DEFAULT_FLAGS`` 中，
      ``reset_flags()`` 可恢复到初始状态
    - **访问未知开关时返回 False** — 避免因拼写错误而静默放过
    - **上下文管理器** — ``temporarily_disable`` 用于测试场景，
      保证退出时恢复原值（即使发生异常）

默认开关一览：
    ========================  ======  ================================
    开关名                    默认值   说明
    ========================  ======  ================================
    sentiment_detection       True    情绪检测
    working_memory            True    工作记忆
    conversation_summary      True    对话摘要
    token_budget              True    Token 预算管理
    self_correction_guard     True    自纠错 Guard
    dynamic_tool_binding      False   动态工具绑定（默认关闭，需手动开启）
    skill_enabled             True    Skill 系统
    faq_fast_path             True    FAQ 快速路径
    transfer_to_human         True    转人工
    security_check            True    安全检查
    prompt_injection_detection True   注入检测
    pii_masking               True    PII 脱敏
    output_compression        True    输出压缩
    ========================  ======  ================================

使用示例::

    from core.feature_flags import is_enabled, set_flag, temporarily_disable

    # 判断是否启用动态工具绑定
    if is_enabled("dynamic_tool_binding"):
        tools = select_tools(message, state)
    else:
        tools = ALL_TOOLS

    # 紧急关闭情绪检测
    set_flag("sentiment_detection", False)

    # 测试时临时关闭某个功能
    with temporarily_disable("working_memory"):
        result = process_without_wm(...)
    # 退出上下文后自动恢复
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Generator

import structlog

logger = structlog.get_logger(__name__)


# ============================================================
# 1. 默认开关配置（不可变常量）
# ============================================================

_DEFAULT_FLAGS: dict[str, bool] = {
    # ── 核心对话功能 ──
    "sentiment_detection":        True,   # 情绪检测：关键词匹配 + 累计升级
    "working_memory":             True,   # 工作记忆：任务状态追踪状态机
    "conversation_summary":       True,   # 对话摘要：长对话压缩
    "token_budget":               True,   # Token 预算管理：防止上下文溢出
    "self_correction_guard":      True,   # 自纠错 Guard：工具输出校验 + 纠错
    "dynamic_tool_binding":       False,  # 动态工具绑定：默认关闭，需验证后开启
    "skill_enabled":              True,   # Skill 系统：高级多步任务编排
    "faq_fast_path":              True,   # FAQ 快速路径：问候语 / 功能介绍匹配
    "transfer_to_human":          True,   # 转人工：Human-in-the-Loop
    # ── 安全与合规 ──
    "security_check":             True,   # 安全检查：输出合规过滤
    "prompt_injection_detection": True,   # 注入检测：Prompt 注入攻击防护
    "pii_masking":                True,   # PII 脱敏：手机号 / 身份证 / 邮箱
    # ── 性能优化 ──
    "output_compression":         True,   # 输出压缩：减少工具返回的 token 消耗
}


# ============================================================
# 2. 运行时状态（线程安全）
# ============================================================

_lock = threading.Lock()
_flags: dict[str, bool] = dict(_DEFAULT_FLAGS)


# ============================================================
# 3. 公共 API
# ============================================================

def is_enabled(flag: str) -> bool:
    """查询指定功能开关是否启用。

    若开关名不存在（拼写错误或未注册），返回 ``False``，
    并在首次遇到时记录警告日志，便于排查。

    Args:
        flag: 功能开关名称（如 ``"sentiment_detection"``）

    Returns:
        ``True`` 表示启用，``False`` 表示关闭或不存在
    """
    with _lock:
        if flag not in _flags:
            # 未知开关名：可能是拼写错误，记录警告帮助排查
            logger.warning("feature_flag_unknown", flag=flag)
            return False
        return _flags[flag]


def set_flag(flag: str, enabled: bool) -> None:
    """设置功能开关的状态。

    若开关名不存在于默认配置中，记录警告但仍允许设置，
    以支持运行时动态注册新开关。

    Args:
        flag:    功能开关名称
        enabled: ``True`` 启用，``False`` 关闭
    """
    with _lock:
        if flag not in _DEFAULT_FLAGS:
            logger.warning("feature_flag_unknown_set",
                           flag=flag,
                           enabled=enabled)
        old_value = _flags.get(flag)
        _flags[flag] = enabled

    # 仅在状态实际发生变化时记录
    if old_value != enabled:
        logger.info("feature_flag_changed",
                    flag=flag,
                    old=old_value,
                    new=enabled)


def get_all_flags() -> dict[str, bool]:
    """获取所有功能开关的当前状态（快照副本）。

    返回的是字典副本，外部修改不会影响内部状态。

    Returns:
        ``{flag_name: enabled}`` 字典
    """
    with _lock:
        return dict(_flags)


def reset_flags() -> None:
    """将所有功能开关重置为默认值。

    通常在以下场景调用：
    - 应用重启后的初始化
    - 测试用例的 tearDown
    - 管理员手动触发"恢复默认配置"
    """
    with _lock:
        _flags.clear()
        _flags.update(_DEFAULT_FLAGS)
    logger.info("feature_flags_reset",
                flag_count=len(_DEFAULT_FLAGS),
                defaults=dict(_DEFAULT_FLAGS))


def get_default_flags() -> dict[str, bool]:
    """获取默认开关配置（只读副本）。

    与 ``get_all_flags()`` 的区别：本函数返回的是编译时定义的默认值，
    而非运行时可能被修改过的当前值。

    Returns:
        默认 ``{flag_name: enabled}`` 字典
    """
    return dict(_DEFAULT_FLAGS)


# ============================================================
# 4. 上下文管理器（测试 / 临时降级场景）
# ============================================================

@contextmanager
def temporarily_disable(flag: str) -> Generator[None, None, None]:
    """上下文管理器：在作用域内临时关闭指定功能开关，退出时自动恢复原值。

    主要用于：
    - **单元测试** — 验证功能关闭时的降级路径是否正确
    - **紧急降级** — 在请求级别临时绕过某个有问题的功能

    即使代码块内发生异常，也会保证恢复原始状态（通过 ``finally``）。

    Args:
        flag: 要临时关闭的功能开关名称

    Raises:
        不抛出自身异常，但若 flag 不存在会在 ``set_flag`` 中记录警告

    使用示例::

        from core.feature_flags import is_enabled, temporarily_disable

        assert is_enabled("working_memory") is True

        with temporarily_disable("working_memory"):
            # 在此块内 working_memory 为 False
            assert is_enabled("working_memory") is False
            result = process_message_without_wm(...)

        # 退出后自动恢复
        assert is_enabled("working_memory") is True
    """
    # 保存原值
    with _lock:
        original_value = _flags.get(flag, True)
        _flags[flag] = False

    logger.debug("feature_flag_temporarily_disabled",
                 flag=flag,
                 original=original_value)
    try:
        yield
    finally:
        # 无论是否发生异常，均恢复原值
        with _lock:
            _flags[flag] = original_value
        logger.debug("feature_flag_restored",
                     flag=flag,
                     restored_to=original_value)


@contextmanager
def temporarily_enable(flag: str) -> Generator[None, None, None]:
    """上下文管理器：在作用域内临时启用指定功能开关，退出时自动恢复原值。

    与 ``temporarily_disable`` 对称，用于在测试中临时开启默认关闭的功能。

    Args:
        flag: 要临时启用的功能开关名称

    使用示例::

        with temporarily_enable("dynamic_tool_binding"):
            assert is_enabled("dynamic_tool_binding") is True
            tools = select_tools(message, state)
    """
    with _lock:
        original_value = _flags.get(flag, False)
        _flags[flag] = True

    logger.debug("feature_flag_temporarily_enabled",
                 flag=flag,
                 original=original_value)
    try:
        yield
    finally:
        with _lock:
            _flags[flag] = original_value
        logger.debug("feature_flag_restored",
                     flag=flag,
                     restored_to=original_value)
