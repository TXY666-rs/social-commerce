"""LLM 工厂模块 — 集中管理 LLM 实例创建，支持多级降级和动态参数配置

特性：
    - 3 个模型均可通过 .env 配置（LLM_MODEL_1 / LLM_MODEL_2 / LLM_MODEL_3）
    - 自动降级：当前模型不可用时自动切换到下一级
    - 自动恢复探测：降级 5 分钟后自动尝试恢复主力模型（带 health-check）
    - 请求级模型追踪：每次调用记录实际使用的模型名
    - 管理端可见：get_llm_status() 返回当前状态供 Dashboard 展示
"""

import time
import threading
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# 线程安全锁 — 保护降级索引 / 实例缓存的并发读写
_llm_lock = threading.Lock()

# Thread-local 存储 — 记录当前请求使用的模型信息
_request_context = threading.local()

# 健康探测：距离上次降级超过此时间后自动尝试恢复主力模型
_PROBE_INTERVAL_SECONDS = 300

# ============================================================
# 状态变量（由 _llm_lock 保护）
# ============================================================
_last_fallback_time: float = 0.0
_current_fallback_index: int = 0      # 0 = 主力模型
_cached_llm: BaseChatModel | None = None


def get_model_chain() -> list[str]:
    """获取当前配置的模型链（过滤空值）"""
    models = [
        settings.LLM_MODEL_1,
        settings.LLM_MODEL_2,
        settings.LLM_MODEL_3,
    ]
    return [m for m in models if m]


# ============================================================
# 固定话术
# ============================================================

FALLBACK_TEXT = (
    "抱歉，AI 服务暂时繁忙，请稍后再试。"
    "当前您可以通过以下方式自助处理：\n"
    "1. 在「我的订单」页面查看订单状态和物流\n"
    "2. 如需人工帮助，请在工作时间联系客服。"
)


def _build_llm(model_name: str) -> ChatOpenAI:
    """构建指定模型的 LLM 实例"""
    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_REQUEST_TIMEOUT,
        streaming=True,
        stream_usage=True,
        callbacks=[],
    )


def get_llm() -> BaseChatModel:
    """获取当前可用 LLM 实例（线程安全），支持自动恢复探测。

    自动恢复：降级超过 5 分钟后，下次调用自动尝试恢复主力模型。
    恢复逻辑：向目标模型发送 health-check 请求，通过则恢复，不通过则保持降级。
    """
    global _current_fallback_index, _last_fallback_time, _cached_llm

    with _llm_lock:
        models = get_model_chain()
        if not models:
            raise LLMFallbackException(FALLBACK_TEXT)

        now = time.monotonic()

        # ── 自动恢复探测 ──
        if (_current_fallback_index > 0
                and now - _last_fallback_time >= _PROBE_INTERVAL_SECONDS):
            probe_target = max(0, _current_fallback_index - 1)
            probe_model = models[probe_target]
            logger.info("llm_recovery_probe",
                        trying_model=probe_model,
                        current_level=_current_fallback_index,
                        target_level=probe_target)
            if _health_check(probe_model):
                _current_fallback_index = probe_target
                _cached_llm = None          # 使缓存失效，触发重建
                _last_fallback_time = now
                logger.info("llm_recovery_success",
                            model=probe_model, level=probe_target)
            else:
                # 探测失败，重置计时器，等待下一个周期再试
                _last_fallback_time = now
                logger.warning("llm_recovery_failed",
                               model=probe_model,
                               next_probe_in=f"{_PROBE_INTERVAL_SECONDS}s")

        # ── 检查是否已耗尽所有模型 ──
        if _current_fallback_index >= len(models):
            logger.warning("llm_all_unavailable", fallback_to="static_text")
            raise LLMFallbackException(FALLBACK_TEXT)

        # ── 缓存命中：直接返回已有实例 ──
        if _cached_llm is not None:
            return _cached_llm

        # ── 构建新实例 ──
        model_name = models[_current_fallback_index]
        _cached_llm = _build_llm(model_name)
        logger.info("llm_instance_created",
                     model=model_name,
                     fallback_level=_current_fallback_index)

        # 记录到 thread-local（供 execution 层读取）
        _request_context.model_name = model_name

        return _cached_llm


def mark_llm_failed() -> tuple[bool, str]:
    """标记当前模型失效，尝试下一级降级（线程安全）。

    Returns:
        (has_next_level: bool, fallback_message: str)
    """
    global _current_fallback_index, _last_fallback_time, _cached_llm

    with _llm_lock:
        models = get_model_chain()
        _current_fallback_index += 1
        _last_fallback_time = time.monotonic()
        _cached_llm = None                  # 使缓存失效

        if _current_fallback_index >= len(models):
            logger.error("llm_all_levels_exhausted", fallback_to="static_text")
            return False, FALLBACK_TEXT

        model_name = models[_current_fallback_index]
        logger.warning("llm_fallback_triggered",
                        new_model=model_name,
                        level=_current_fallback_index)
        return True, f"已切换至备用模型 {model_name}"


def reset_llm() -> None:
    """重置降级状态，恢复到主力模型（线程安全）"""
    global _current_fallback_index, _last_fallback_time, _cached_llm
    with _llm_lock:
        _current_fallback_index = 0
        _last_fallback_time = 0.0
        _cached_llm = None
        models = get_model_chain()
        primary = models[0] if models else "unknown"
        logger.info("llm_reset_to_primary", model=primary)


# ============================================================
# 对外查询接口（Dashboard / Admin / 请求追踪）
# ============================================================

def get_current_model_name() -> str:
    """获取当前活跃的模型名称"""
    models = get_model_chain()
    if not models:
        return "none"
    idx = min(_current_fallback_index, len(models) - 1)
    return models[idx]


def get_request_model_info() -> str:
    """获取当前请求（thread-local）使用的模型名称。

    Skill 路由的请求不经过 LLM，返回空字符串。
    """
    return getattr(_request_context, "model_name", "")


def get_llm_status() -> dict:
    """获取 LLM 状态信息（供管理端 Dashboard 展示）

    Returns:
        {
            "current_model": "qwen3-max",
            "fallback_level": 0,
            "total_models": 3,
            "is_healthy": True,
            "last_fallback_time": 1718000000.0,
            "seconds_since_fallback": 120.5,
            "models": [
                {"name": "qwen3-max",   "level": 0, "active": True},
                {"name": "qwen-plus",   "level": 1, "active": False},
                {"name": "qwen-turbo",  "level": 2, "active": False},
            ]
        }
    """
    models = get_model_chain()
    now = time.monotonic()
    elapsed = now - _last_fallback_time if _last_fallback_time > 0 else None

    model_list = []
    for i, m in enumerate(models):
        model_list.append({
            "name": m,
            "level": i,
            "active": i == _current_fallback_index,
        })

    return {
        "current_model": get_current_model_name(),
        "fallback_level": _current_fallback_index,
        "total_models": len(models),
        "is_healthy": _current_fallback_index == 0,
        "last_fallback_time": _last_fallback_time if _last_fallback_time > 0 else None,
        "seconds_since_fallback": round(elapsed, 1) if elapsed is not None else None,
        "models": model_list,
    }


# ============================================================
# Health-Check 探针
# ============================================================

def _health_check(model_name: str) -> bool:
    """向目标模型发送极简请求，验证可用性。

    使用独立的短超时 ChatOpenAI 实例，不影响主实例配置。
    """
    try:
        probe = ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0,
            max_tokens=5,
            timeout=10,
            streaming=False,
            callbacks=[],
        )
        probe.invoke([{"role": "user", "content": "ping"}])
        return True
    except Exception as e:
        logger.debug("llm_health_check_failed",
                      model=model_name, error=str(e)[:120])
        return False


# ============================================================
# 异常
# ============================================================

class LLMFallbackException(Exception):
    """LLM 全部不可用时的异常，携带固定话术"""
    def __init__(self, fallback_text: str):
        super().__init__(fallback_text)
        self.fallback_text = fallback_text
