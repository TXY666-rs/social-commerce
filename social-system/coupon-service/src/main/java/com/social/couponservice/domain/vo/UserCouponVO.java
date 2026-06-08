package com.social.couponservice.domain.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 用户优惠券（我的优惠券）VO
 */
@Data
public class UserCouponVO {
    private Long id;
    private Long userId;
    private Long couponId;
    private String couponName; // 优惠券名称（冗余方便展示）
    private Integer type; // 优惠类型
    private String typeName;
    private BigDecimal thresholdAmount;
    private BigDecimal discountAmount;
    private BigDecimal discountRate;
    private BigDecimal maxDiscount;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer status; // 0:未使用, 1:已使用, 2:已过期
    private String statusName;
    private LocalDateTime claimTime;
    private LocalDateTime useTime;
}
