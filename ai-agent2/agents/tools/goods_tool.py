from services.http_client import get_client
from langchain_core.tools import tool
from middleware.context import _auth_headers
from resilience.decorators import resilient_tool
from cost.cache import tool_result_cache
from agents.tools.registry import register_tool


def _do_search(keyword: str, category: str, min_price: float, max_price: float) -> tuple[list, int]:
    """执行一次商品搜索，返回 (products, total)"""
    params = {"keyword": keyword, "top_k": 10}
    if category:
        params["category"] = category
    if min_price > 0:
        params["min_price"] = min_price
    if max_price > 0:
        params["max_price"] = max_price
    client = get_client()
    resp = client.get("/api/product/list/search", headers=_auth_headers(), params=params)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 200:
        return [], 0
    data = result.get("data", {})
    return data.get("agentProductVOList", []), data.get("total", 0)




@register_tool()
@tool
@tool_result_cache(ttl=60)
@resilient_tool()
def search_products(keyword: str, category: str = "", min_price: float = 0, max_price: float = 0) -> str:
    """搜索商品。根据关键词、分类、价格范围搜索商品列表。当用户想要查找或推荐商品时使用此工具。

    关键词选择指南：
    - 优先使用商品名称的核心词，如用户说"裙子"用"裙"搜索，说"裤子"用"裤"搜索
    - 使用商品可能包含的通用词根，而非完整口语词
    - 如果用户提到了具体品类如"连衣裙"、"半身裙"，直接用该具体词搜索

    Args:
        keyword: 搜索关键词，应为商品名称的核心词根
        category: 商品分类，可选
        min_price: 最低价格，可选，0表示不限
        max_price: 最高价格，可选，0表示不限
    """
    # 第一次搜索：使用原始关键词
    products, total = _do_search(keyword, category, min_price, max_price)

    if not products:
        return f"未找到与'{keyword}'相关的商品。"
    lines = [f"共找到 {total} 件相关商品："]
    internal_ids = []
    for i, p in enumerate(products, 1):
        lines.append(
            f"{i}. {p.get('name', '')} — ¥{p.get('price', 0)}，库存{p.get('stock', 0)}件"
            f"\n   {p.get('description', '')[:60]}"
        )
        internal_ids.append({"index": i, "id": p.get("id")})
    lines.append(f"\n<!-- internal_ids:{internal_ids} -->")
    return "\n".join(lines)
