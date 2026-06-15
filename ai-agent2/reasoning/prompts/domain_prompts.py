"""统一 System Prompt 构建器 — 从 YAML 配置文件加载

结构：PERSONA(公共) + [sentiment] + [summary] + [dialog] + POLICIES(公共) + 全量TOOLS说明 + TONE(公共)

设计要点：
    - Prompt 内容从 reasoning/prompts/yaml/*.yaml 加载，支持热更新
    - 合并所有领域工具说明为一个统一 Prompt（单 Agent 架构）
    - 固定前缀最大化 KV-cache 命中
"""

from reasoning.prompts.loader import load_base, load_domain, reload_prompts

# ============================================================
# 从 YAML 加载公共组件
# ============================================================

_base = load_base()
PERSONA = _base.get("persona", "")
POLICIES = _base.get("policies", "")
TONE = _base.get("tone", "")
SELF_CORRECTION = _base.get("self_correction", "")


def _refresh_base():
    """刷新公共组件（热更新后调用）"""
    global PERSONA, POLICIES, TONE, SELF_CORRECTION
    _base = load_base()
    PERSONA = _base.get("persona", "")
    POLICIES = _base.get("policies", "")
    TONE = _base.get("tone", "")
    SELF_CORRECTION = _base.get("self_correction", "")


# ============================================================
# 从 YAML 加载并合并全量工具说明
# ============================================================

# 合并时包含的字段（排除 cross_domain — 那是旧的多 Agent 跨域切换指引）
_UNIFIED_KEYS = {"tools_hints", "flow", "data_integrity", "confirmation",
                 "emotion_priority", "sales_guide"}


def _build_unified_tool_hints() -> str:
    """合并所有领域的工具说明文本（排除 cross_domain 跨域切换指引）"""
    all_parts = []
    for domain in ["order", "after_sale"]:
        data = load_domain(domain)
        domain_parts = []
        for key in _UNIFIED_KEYS:
            if key in data and data[key]:
                domain_parts.append(data[key].strip())
        if domain_parts:
            all_parts.append("\n\n".join(domain_parts))
    return "\n\n---\n\n".join(all_parts)


# 合并后的全量工具说明（模块加载时构建一次）
UNIFIED_TOOL_HINTS = _build_unified_tool_hints()


# ============================================================
# 统一拼接器
# ============================================================

def _join(summary: str, dialog_context: str = "", sentiment_context: str = "") -> str:
    """拼接统一 System Prompt

    固定前缀(PERSONA+POLICIES+TONE+SELF_CORRECTION)放在最前，最大化 KV-cache 命中。
    可变内容(sentiment/summary/dialog)按影响范围排序：情感 > 历史 > 进度。
    """
    parts = [PERSONA, POLICIES, TONE, SELF_CORRECTION]
    if sentiment_context:
        parts.append(sentiment_context)
    if summary:
        parts.append(f"【上次对话回顾】{summary}\n注意：你可以根据这个回顾主动询问用户上次问题的进展。")
    if dialog_context:
        parts.append(dialog_context)
    parts.append(UNIFIED_TOOL_HINTS)
    return "\n\n---\n\n".join(parts)


# ============================================================
# 统一构建器 — 供 nodes.py 调用
# ============================================================

def build_unified_prompt(summary: str = "", dialog_context: str = "", sentiment_context: str = "") -> str:
    """构建统一 System Prompt（单 Agent 架构，全量工具）"""
    return _join(summary, dialog_context, sentiment_context)



