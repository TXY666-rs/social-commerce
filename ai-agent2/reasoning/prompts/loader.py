"""Prompt YAML 加载器 — 从 YAML 文件加载 Prompt 配置

加载顺序：
    1. base.yaml — 公共组件（persona, policies, tone, self_correction）
    2. {domain}.yaml — 领域配置（order, after_sale）

缓存策略：
    - 文件级缓存：首次加载后缓存到 _cache，后续直接读缓存
    - 热更新：调用 reload_prompts() 清空缓存，下次加载时重新读文件

使用方式：
    from agents.prompts.loader import load_base, load_domain
    base = load_base()
    order = load_domain("order")
"""

import os
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# YAML 文件目录
_YAML_DIR = Path(__file__).parent / "yaml"

# 缓存：文件路径 → 解析后的 dict
_cache: dict[str, dict] = {}

# POLICIES 需要从 policies/ 动态构建，不放在 YAML 中
_policies_text: Optional[str] = None


def _load_yaml(filename: str) -> dict:
    """加载单个 YAML 文件（带缓存）"""
    filepath = _YAML_DIR / filename
    cache_key = str(filepath)

    if cache_key in _cache:
        return _cache[cache_key]

    if not filepath.exists():
        logger.warning("prompt_yaml_not_found", path=str(filepath))
        return {}

    try:
        import yaml
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _cache[cache_key] = data
        logger.debug("prompt_yaml_loaded", file=filename, keys=list(data.keys()))
        return data
    except Exception as e:
        logger.error("prompt_yaml_load_failed", file=filename, error=str(e))
        return {}


def load_base() -> dict:
    """加载公共 Prompt 组件

    Returns:
        dict: {"persona": str, "policies": str, "tone": str, "self_correction": str}
    """
    data = _load_yaml("base.yaml")

    # POLICIES 从 policies/ 动态构建（YAML 中不存储）
    global _policies_text
    if _policies_text is None:
        try:
            from reasoning.prompts.policies import build_policy_prompt
            _policies_text = build_policy_prompt()
        except Exception:
            _policies_text = ""
            logger.warning("policies_build_failed")

    data["policies"] = _policies_text
    return data


def load_domain(domain: str) -> dict:
    """加载领域 Prompt 配置

    Args:
        domain: 领域名称，如 "order", "after_sale"

    Returns:
        dict: 领域配置，包含 tools_hints, flow, cross_domain 等
    """
    return _load_yaml(f"{domain}.yaml")


def reload_prompts():
    """清空缓存，强制下次加载时重新读文件（热更新用）"""
    global _policies_text
    _cache.clear()
    _policies_text = None
    logger.info("prompts_cache_cleared")
