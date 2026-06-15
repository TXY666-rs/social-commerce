"""Mock 数据层 —— 替代 Java 后端的本地业务数据

重构后 Agent 不再依赖 Java 微服务，所有业务数据（订单/退款/物流/投诉/商品/用户/地址）
存储在本地 Redis 中。启动时由 seed.py 自动预置演示数据。

这样面试官克隆项目后，无需启动任何 Java 服务即可体验完整的电商客服场景：
浏览商品、下单、查订单、退款、转人工等全链路功能。
"""

from mock_data.store import (
    ensure_seeded,
    # 订单
    query_orders,
    get_order_by_id,
    cancel_order,
    remind_delivery,
    change_address,
    create_order,
    pay_order,
    complete_order,
    # 退款
    submit_refund,
    get_refund_by_id,
    get_refund_by_order,
    cancel_refund,
    cancel_refund_by_order,
    # 投诉
    submit_complaint,
    # 商品
    query_products,
    get_product_by_id,
    get_products_by_category,
    query_my_products,
    create_product,
    # 用户
    get_user_by_id,
    find_user_by_credentials,
    register_user,
    update_user,
    # 地址
    query_addresses,
    create_address,
    update_address,
    delete_address,
)

__all__ = [
    "ensure_seeded",
    # 订单
    "query_orders", "get_order_by_id", "cancel_order", "remind_delivery", "change_address",
    "create_order", "pay_order", "complete_order",
    # 退款
    "submit_refund", "get_refund_by_id", "get_refund_by_order", "cancel_refund", "cancel_refund_by_order",
    # 投诉
    "submit_complaint",
    # 商品
    "query_products", "get_product_by_id", "get_products_by_category", "query_my_products", "create_product",
    # 用户
    "get_user_by_id", "find_user_by_credentials", "register_user", "update_user",
    # 地址
    "query_addresses", "create_address", "update_address", "delete_address",
]
