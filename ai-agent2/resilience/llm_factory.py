"""LLM 工厂模块 — 集中管理 LLM 实例创建，支持多级降级和动态参数配置"""
from functools import lru_cache
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import StreamingStdOutCallbackHandler
from langchain_core.language_models import BaseChatModel
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# ============================================================
# 降级模型链（优先级从高到低）
# ============================================================
FALLBACK_MODELS = [
    settings.OPENAI_MODEL,           # qwen3-max（主力）
    "qwen-plus",                     # 降级1：qwen-plus（性价比高）
    "qwen-turbo",                    # 降级2：qwen-turbo（最快）
]

# 固定话术（所有 LLM 都不可用时的最后兜底）
FALLBACK_TEXT = (
    "抱歉，AI 服务暂时繁忙，请稍后再试。"
    "当前您可以通过以下方式自助处理：\n"
    "1. 在「我的订单」页面查看订单状态和物流\n"
    "2. 在「活动中心」领取优惠券\n"
    "3. 如需人工帮助，请在工作时间联系客服。"
)

# 当前生效的降级索引（0=主力, 1=降级1, 2=降级2, -1=已全部不可用）
_current_fallback_index: int = -1


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
        callbacks=[StreamingStdOutCallbackHandler()],
    )


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """获取当前可用 LLM 实例（线程安全），自动降级。

    降级链：qwen3-max → qwen-plus → qwen-turbo → 固定话术兜底
    每次调用 get_llm() 都会验证当前级别是否仍然可用。
    """
    global _current_fallback_index

    # 首次调用，从主力模型开始
    if _current_fallback_index == -1:
        _current_fallback_index = 0

    # 已经全部不可用
    if _current_fallback_index >= len(FALLBACK_MODELS):
        logger.warning("llm_all_unavailable", fallback_to="static_text")
        raise LLMFallbackException(FALLBACK_TEXT)

    model_name = FALLBACK_MODELS[_current_fallback_index]
    logger.info("llm_instance_created", model=model_name, fallback_level=_current_fallback_index)
    return _build_llm(model_name)


def mark_llm_failed() -> tuple[bool, str]:
    """标记当前模型失效，尝试下一级降级。

    Returns:
        (has_next_level: bool, fallback_message: str)
        - has_next_level=True: 已切换到下一级模型，可重试
        - has_next_level=False: 所有模型已失效，返回固定话术
    """
    global _current_fallback_index

    _current_fallback_index += 1
    if _current_fallback_index >= len(FALLBACK_MODELS):
        logger.error("llm_all_levels_exhausted", fallback_to="static_text")
        return False, FALLBACK_TEXT

    # 清除缓存，强制重建 LLM 实例
    get_llm.cache_clear()

    model_name = FALLBACK_MODELS[_current_fallback_index]
    logger.warning("llm_fallback_triggered",
                   new_model=model_name,
                   level=_current_fallback_index)
    return True, f"已切换至备用模型 {model_name}"


def reset_llm() -> None:
    """重置降级状态，恢复到主力模型（配置热更新时调用）"""
    global _current_fallback_index
    _current_fallback_index = 0
    get_llm.cache_clear()
    logger.info("llm_reset_to_primary", model=FALLBACK_MODELS[0])


class LLMFallbackException(Exception):
    """LLM 全部不可用时的异常，携带固定话术"""
    def __init__(self, fallback_text: str):
        super().__init__(fallback_text)
        self.fallback_text = fallback_text



