"""工具自动注册表 — @register_tool 装饰器

单 Agent 架构下，所有工具统一注册到扁平列表，由 React Agent 全量绑定。

使用方式：
    @register_tool()
    @tool
    @tool_result_cache(ttl=60)
    @resilient_tool()
    def get_my_orders(...) -> str:
        ...
"""

from langchain_core.tools import StructuredTool

# 注册表：tool_name → StructuredTool（扁平，无领域分组）
_REGISTRY: dict[str, StructuredTool] = {}


def register_tool():
    """装饰器：将 langchain StructuredTool 注册到全局工具列表。

    单 Agent 架构下不再区分领域，所有工具统一暴露给 React Agent。
    """
    def decorator(tool_obj: StructuredTool) -> StructuredTool:
        name = tool_obj.name
        if name not in _REGISTRY:
            _REGISTRY[name] = tool_obj
        return tool_obj
    return decorator


def get_all_tools() -> list[StructuredTool]:
    """获取所有已注册工具"""
    return list(_REGISTRY.values())


def get_registry() -> dict[str, StructuredTool]:
    """获取原始注册表（供调试用）"""
    return _REGISTRY.copy()
