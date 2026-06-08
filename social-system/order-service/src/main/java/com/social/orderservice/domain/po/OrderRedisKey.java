package com.social.orderservice.domain.po;

public class OrderRedisKey {

    public static final String ORDER_DETAIL = "order:detail:";
    public static final String ORDER_USER_LIST = "order:user:list:";
    public static final String ORDER_SELLER_LIST = "order:seller:list:";

    public static final long DETAIL_TTL = 5;   // 订单详情 5 分钟
    public static final long LIST_TTL = 3;      // 订单列表 3 分钟

    public static final String ORDER_DETAIL_LOCK = "order:detail:lock:";
}
