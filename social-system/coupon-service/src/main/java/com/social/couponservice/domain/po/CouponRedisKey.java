package com.social.couponservice.domain.po;

public class CouponRedisKey {

    public static final String COUPON_DETAIL = "coupon:detail:";
    public static final String COUPON_AVAILABLE_LIST = "coupon:available:list";

    public static final long DETAIL_TTL = 30;    // 优惠券详情 30 分钟
    public static final long AVAILABLE_TTL = 10;  // 可领取列表 10 分钟

    public static final String COUPON_DETAIL_LOCK = "coupon:detail:lock:";
    public static final String COUPON_AVAILABLE_LOCK = "coupon:available:lock:";
}
