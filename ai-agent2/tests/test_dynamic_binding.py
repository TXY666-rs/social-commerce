"""agents/tools/dynamic_binding.py 单元测试

覆盖函数：
    - select_tools():       动态工具选择
    - get_tool_stats():     统计数据查询
    - reset_stats():        统计数据重置
    - _detect_domains_from_message():  关键词领域检测
    - _detect_domain_from_wm_state():  Working Memory 领域推断
    - _resolve_tools():     工具名解析
    - _record_stats():      统计记录

测试策略：
    - 使用 MagicMock 模拟 StructuredTool 对象
    - 使用 patch 隔离 registry 和 ALL_TOOLS，避免真实工具导入
    - 使用 patch 隔离 Working Memory 依赖
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# 测试辅助：构建模拟工具对象和注册表
# ============================================================

def _make_mock_tool(name: str) -> MagicMock:
    """创建一个模拟的 StructuredTool 对象"""
    tool = MagicMock()
    tool.name = name
    return tool


# 所有已注册的工具名（与 dynamic_binding.py 中 TOOL_DOMAINS 一致）
ALL_TOOL_NAMES = [
    "get_my_orders", "cancel_order", "remind_delivery",
    "track_logistics",
    "request_refund", "request_return", "check_refund_status",
    "cancel_refund", "submit_complaint",
    "transfer_to_human",
]

# 模拟的工具对象字典
MOCK_REGISTRY = {name: _make_mock_tool(name) for name in ALL_TOOL_NAMES}
MOCK_ALL_TOOLS = list(MOCK_REGISTRY.values())


# ============================================================
# Fixtures — 在每个测试前 patch 全局依赖
# ============================================================

@pytest.fixture(autouse=True)
def patch_tool_dependencies():
    """自动 patch agents.tools 依赖，避免导入真实的 LangChain 工具链"""
    with (
        patch("agents.tools.dynamic_binding.ALL_TOOLS", MOCK_ALL_TOOLS),
        patch("agents.tools.dynamic_binding.get_registry", return_value=MOCK_REGISTRY),
    ):
        yield


@pytest.fixture(autouse=True)
def reset_dynamic_stats():
    """每个测试前重置统计数据，避免测试间干扰"""
    from agents.tools.dynamic_binding import reset_stats
    reset_stats()
    yield
    reset_stats()


@pytest.fixture(autouse=True)
def patch_wm_state():
    """默认 patch _detect_domain_from_wm_state 返回空集合，避免 WM 依赖"""
    with patch(
        "agents.tools.dynamic_binding._detect_domain_from_wm_state",
        return_value=set(),
    ):
        yield


# ============================================================
# 导入被测模块（放在 fixtures 定义之后）
# ============================================================

from agents.tools.dynamic_binding import (
    select_tools,
    get_tool_stats,
    reset_stats,
    _detect_domains_from_message,
    _resolve_tools,
    TOOL_DOMAINS,
    DOMAIN_KEYWORDS,
    WM_TASK_TYPE_TO_DOMAIN,
)


# ============================================================
# 辅助函数
# ============================================================

def _get_selected_tool_names(tools: list) -> list[str]:
    """从模拟工具列表中提取工具名"""
    return [t.name for t in tools]


# ============================================================
# 1. _detect_domains_from_message() — 关键词领域检测
# ============================================================

class TestDetectDomainsFromMessage:
    """测试基于消息关键词的领域检测"""

    # ── 订单领域 ──

    def test_orders_keyword_order(self):
        """'订单' 关键词命中 orders 领域"""
        assert "orders" in _detect_domains_from_message("帮我查一下订单")

    def test_orders_keyword_cancel(self):
        """'取消订单' 关键词命中 orders 领域"""
        assert "orders" in _detect_domains_from_message("我要取消订单")

    def test_orders_keyword_urge_delivery(self):
        """'催发货' 关键词命中 orders 领域"""
        assert "orders" in _detect_domains_from_message("催发货，等了三天了")

    def test_orders_keyword_purchase(self):
        """'购买' 关键词命中 orders 领域"""
        assert "orders" in _detect_domains_from_message("我昨天购买了一件商品")

    # ── 物流领域 ──

    def test_logistics_keyword_express(self):
        """'快递' 关键词命中 logistics 领域"""
        assert "logistics" in _detect_domains_from_message("快递到哪了")

    def test_logistics_keyword_delivery(self):
        """'发货' 关键词命中 logistics 领域"""
        assert "logistics" in _detect_domains_from_message("什么时候发货")

    def test_logistics_keyword_shipping(self):
        """'配送' 关键词命中 logistics 领域"""
        assert "logistics" in _detect_domains_from_message("配送进度查一下")

    def test_logistics_keyword_signed(self):
        """'签收' 关键词命中 logistics 领域"""
        assert "logistics" in _detect_domains_from_message("显示已签收但没收到")

    # ── 售后领域 ──

    def test_after_sale_keyword_refund(self):
        """'退款' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("申请退款")

    def test_after_sale_keyword_return(self):
        """'退货' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("我要退货")

    def test_after_sale_keyword_complaint(self):
        """'投诉' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("我要投诉")

    def test_after_sale_keyword_quality(self):
        """'质量问题' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("商品有质量问题")

    def test_after_sale_keyword_damaged(self):
        """'破损' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("收到的时候已经破损了")

    def test_after_sale_keyword_cancel_refund(self):
        """'取消退款' 关键词命中 after_sale 领域"""
        assert "after_sale" in _detect_domains_from_message("我要取消退款申请")

    # ── 转人工领域 ──

    def test_transfer_keyword_human(self):
        """'人工' 关键词命中 transfer 领域"""
        assert "transfer" in _detect_domains_from_message("转人工")

    def test_transfer_keyword_customer_service(self):
        """'客服' 关键词命中 transfer 领域"""
        assert "transfer" in _detect_domains_from_message("找客服")

    def test_transfer_keyword_real_person(self):
        """'真人' 关键词命中 transfer 领域"""
        assert "transfer" in _detect_domains_from_message("我要找真人客服")

    # ── 多领域同时命中 ──

    def test_multi_domain_hit(self):
        """消息可同时命中多个领域"""
        # "订单" → orders, "退款" → after_sale
        domains = _detect_domains_from_message("我的订单要退款")
        assert "orders" in domains
        assert "after_sale" in domains

    # ── 无命中 ──

    def test_no_domain_hit(self):
        """无法识别的消息返回空集合"""
        domains = _detect_domains_from_message("今天天气怎么样")
        assert len(domains) == 0

    def test_empty_message(self):
        """空消息返回空集合"""
        assert _detect_domains_from_message("") == set()


# ============================================================
# 2. select_tools() — 动态工具选择
# ============================================================

class TestSelectTools:
    """测试动态工具选择逻辑"""

    # ── 订单消息 → 选择订单领域工具 ──

    def test_order_message_selects_order_tools(self):
        """订单相关消息选择 orders 领域工具"""
        tools = select_tools("帮我查一下订单", {})
        names = _get_selected_tool_names(tools)
        # orders 领域的工具应被选中
        assert "get_my_orders" in names
        # transfer_to_human 始终包含
        assert "transfer_to_human" in names

    def test_cancel_order_selects_order_tools(self):
        """取消订单消息选择 orders 领域工具"""
        tools = select_tools("我要取消订单", {})
        names = _get_selected_tool_names(tools)
        assert "cancel_order" in names
        assert "transfer_to_human" in names

    # ── 物流消息 → 选择物流工具 ──

    def test_logistics_message_selects_logistics_tools(self):
        """物流相关消息选择 logistics 领域工具"""
        tools = select_tools("快递到哪了", {})
        names = _get_selected_tool_names(tools)
        assert "track_logistics" in names
        assert "transfer_to_human" in names

    # ── 售后消息 → 选择售后工具 ──

    def test_after_sale_message_selects_after_sale_tools(self):
        """售后关键词选择 after_sale 领域工具"""
        tools = select_tools("申请退款", {})
        names = _get_selected_tool_names(tools)
        assert "request_refund" in names
        assert "request_return" in names
        assert "transfer_to_human" in names

    def test_complaint_selects_after_sale_tools(self):
        """投诉消息选择 after_sale 领域工具"""
        tools = select_tools("我要投诉", {})
        names = _get_selected_tool_names(tools)
        assert "submit_complaint" in names
        assert "transfer_to_human" in names

    # ── 无法识别消息 → 回退到全量工具（safe fallback）──

    def test_unknown_message_fallback_to_all_tools(self):
        """无法识别领域的消息回退到全量工具"""
        tools = select_tools("你好啊，今天天气不错", {})
        names = _get_selected_tool_names(tools)
        # 应包含所有工具
        for tool_name in ALL_TOOL_NAMES:
            assert tool_name in names, f"全量工具中缺少 {tool_name}"

    def test_empty_message_fallback(self):
        """空消息回退到全量工具"""
        tools = select_tools("", {})
        assert len(tools) == len(MOCK_ALL_TOOLS)

    # ── transfer_to_human 始终包含 ──

    def test_transfer_always_included_for_order(self):
        """订单消息中 transfer_to_human 始终包含"""
        tools = select_tools("查订单", {})
        names = _get_selected_tool_names(tools)
        assert "transfer_to_human" in names

    def test_transfer_always_included_for_logistics(self):
        """物流消息中 transfer_to_human 始终包含"""
        tools = select_tools("快递到了没", {})
        names = _get_selected_tool_names(tools)
        assert "transfer_to_human" in names

    def test_transfer_always_included_for_after_sale(self):
        """售后消息中 transfer_to_human 始终包含"""
        tools = select_tools("退货退款", {})
        names = _get_selected_tool_names(tools)
        assert "transfer_to_human" in names

    def test_transfer_always_included_for_fallback(self):
        """回退场景中 transfer_to_human 也包含"""
        tools = select_tools("随便聊聊", {})
        names = _get_selected_tool_names(tools)
        assert "transfer_to_human" in names

    # ── 多领域命中 ──

    def test_multi_domain_selects_combined_tools(self):
        """同时命中多个领域时，工具列表合并"""
        # "订单退款" → orders + after_sale
        tools = select_tools("我的订单要申请退款", {})
        names = _get_selected_tool_names(tools)
        # orders 领域工具
        assert "get_my_orders" in names
        # after_sale 领域工具
        assert "request_refund" in names
        # transfer_to_human 始终包含
        assert "transfer_to_human" in names

    # ── 工具去重 ──

    def test_no_duplicate_tools(self):
        """多领域命中时工具不重复"""
        tools = select_tools("我的订单要申请退款", {})
        names = _get_selected_tool_names(tools)
        assert len(names) == len(set(names)), "工具列表中有重复项"


# ============================================================
# 3. Working Memory 任务类型影响
# ============================================================

class TestWorkingMemoryInfluence:
    """测试 Working Memory 的 task_type 对工具选择的影响"""

    def test_wm_refund_task_adds_after_sale_domain(self):
        """WM 中 refund 任务类型添加 after_sale 领域"""
        # 覆盖默认的 patch，让 WM 返回 after_sale 领域
        with patch(
            "agents.tools.dynamic_binding._detect_domain_from_wm_state",
            return_value={"after_sale"},
        ):
            # 消息本身不命中任何领域，但 WM 提示 after_sale
            tools = select_tools("你好", {})
            names = _get_selected_tool_names(tools)
            assert "request_refund" in names
            assert "transfer_to_human" in names

    def test_wm_query_order_adds_orders_domain(self):
        """WM 中 query_order 任务类型添加 orders 领域"""
        with patch(
            "agents.tools.dynamic_binding._detect_domain_from_wm_state",
            return_value={"orders"},
        ):
            tools = select_tools("嗯", {})
            names = _get_selected_tool_names(tools)
            assert "get_my_orders" in names

    def test_wm_combined_with_message_keywords(self):
        """WM 领域与消息关键词领域合并"""
        with patch(
            "agents.tools.dynamic_binding._detect_domain_from_wm_state",
            return_value={"logistics"},
        ):
            # 消息命中 after_sale，WM 补充 logistics
            tools = select_tools("我要退款", {})
            names = _get_selected_tool_names(tools)
            # after_sale 工具（来自消息关键词）
            assert "request_refund" in names
            # logistics 工具（来自 WM）
            assert "track_logistics" in names

    def test_wm_empty_state_no_effect(self):
        """WM 返回空集合时不影响关键词检测结果"""
        # 默认 patch 返回空集合
        tools = select_tools("查快递", {})
        names = _get_selected_tool_names(tools)
        assert "track_logistics" in names


# ============================================================
# 4. get_tool_stats() — 统计数据
# ============================================================

class TestGetToolStats:
    """测试统计数据查询"""

    def test_stats_initial_values(self):
        """初始统计数据全为零"""
        stats = get_tool_stats()
        assert stats["total_selections"] == 0
        assert stats["fallback_count"] == 0
        assert stats["fallback_rate"] == 0.0
        assert stats["avg_tools_per_call"] == 0.0
        # 所有领域计数均为 0
        for domain, count in stats["domain_counts"].items():
            assert count == 0

    def test_stats_after_order_selection(self):
        """订单选择后统计数据更新"""
        select_tools("查订单", {})
        stats = get_tool_stats()
        assert stats["total_selections"] == 1
        assert stats["domain_counts"]["orders"] >= 1
        assert stats["domain_counts"]["transfer"] >= 1  # transfer 始终计入

    def test_stats_after_fallback(self):
        """回退场景统计正确"""
        select_tools("你好天气不错", {})
        stats = get_tool_stats()
        assert stats["total_selections"] == 1
        assert stats["fallback_count"] == 1
        assert stats["fallback_rate"] == 1.0

    def test_stats_multiple_calls(self):
        """多次调用后统计累加"""
        select_tools("查订单", {})
        select_tools("快递到了没", {})
        select_tools("你好", {})  # fallback
        stats = get_tool_stats()
        assert stats["total_selections"] == 3
        assert stats["fallback_count"] == 1

    def test_stats_fallback_rate_calculation(self):
        """回退率计算正确"""
        select_tools("查订单", {})     # 非回退
        select_tools("查快递", {})     # 非回退
        select_tools("你好", {})       # 回退
        select_tools("嗨", {})         # 回退
        stats = get_tool_stats()
        assert stats["total_selections"] == 4
        assert stats["fallback_count"] == 2
        assert abs(stats["fallback_rate"] - 0.5) < 0.01

    def test_stats_domain_counts(self):
        """各领域计数正确"""
        select_tools("查订单", {})       # orders + transfer
        select_tools("查订单", {})       # orders + transfer
        select_tools("快递到了没", {})   # logistics + transfer
        stats = get_tool_stats()
        assert stats["domain_counts"]["orders"] == 2
        assert stats["domain_counts"]["logistics"] == 1
        assert stats["domain_counts"]["transfer"] == 3


# ============================================================
# 5. reset_stats() — 统计重置
# ============================================================

class TestResetStats:
    """测试统计数据重置"""

    def test_reset_clears_all_stats(self):
        """reset_stats 将所有统计归零"""
        select_tools("查订单", {})
        select_tools("你好", {})
        reset_stats()
        stats = get_tool_stats()
        assert stats["total_selections"] == 0
        assert stats["fallback_count"] == 0
        for count in stats["domain_counts"].values():
            assert count == 0


# ============================================================
# 6. _resolve_tools() — 工具名解析
# ============================================================

class TestResolveTools:
    """测试工具名到 StructuredTool 的解析"""

    def test_resolve_known_tools(self):
        """已注册工具名正确解析"""
        tools = _resolve_tools(["get_my_orders", "cancel_order"])
        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "get_my_orders" in names
        assert "cancel_order" in names

    def test_resolve_unknown_tool_skipped(self):
        """未注册工具名被跳过（不报错）"""
        tools = _resolve_tools(["get_my_orders", "nonexistent_tool"])
        assert len(tools) == 1
        assert tools[0].name == "get_my_orders"

    def test_resolve_empty_list(self):
        """空列表返回空结果"""
        assert _resolve_tools([]) == []

    def test_resolve_all_unknown(self):
        """全部未知返回空列表"""
        assert _resolve_tools(["foo", "bar"]) == []


# ============================================================
# 7. TOOL_DOMAINS 和 DOMAIN_KEYWORDS 完整性校验
# ============================================================

class TestDomainConfiguration:
    """测试领域配置的完整性和一致性"""

    def test_all_domains_have_tools(self):
        """每个领域都有对应的工具列表"""
        for domain in DOMAIN_KEYWORDS:
            assert domain in TOOL_DOMAINS, f"领域 '{domain}' 缺少工具配置"

    def test_all_domains_have_keywords(self):
        """每个领域都有对应的关键词列表"""
        for domain in TOOL_DOMAINS:
            assert domain in DOMAIN_KEYWORDS, f"领域 '{domain}' 缺少关键词配置"

    def test_tool_names_in_registry(self):
        """TOOL_DOMAINS 中的所有工具名都在模拟注册表中"""
        for domain, tool_names in TOOL_DOMAINS.items():
            for name in tool_names:
                assert name in MOCK_REGISTRY, \
                    f"领域 '{domain}' 的工具 '{name}' 未注册"

    def test_wm_task_type_domains_valid(self):
        """WM_TASK_TYPE_TO_DOMAIN 中的所有领域都存在于 TOOL_DOMAINS"""
        for task_type, domain in WM_TASK_TYPE_TO_DOMAIN.items():
            assert domain in TOOL_DOMAINS, \
                f"WM 任务类型 '{task_type}' 映射到不存在的领域 '{domain}'"

    def test_transfer_tool_in_transfer_domain(self):
        """transfer_to_human 在 transfer 领域中"""
        assert "transfer_to_human" in TOOL_DOMAINS["transfer"]

    def test_all_four_domains_present(self):
        """确认共有 4 个领域"""
        expected_domains = {"orders", "logistics", "after_sale", "transfer"}
        assert set(TOOL_DOMAINS.keys()) == expected_domains
