package com.social.couponservice.domain.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 优惠券 VO
 */
@Data
public class CouponVO {
    /**
     * 优惠券id
     */
    private Long id;

    /**
     * 优惠券名称
     */
    private String name;

    /**
     * 优惠类型 (1:满减, 2:折扣, 3:固定金额减免)
     */
    private Integer type;

    /**
     * 阈值金额（满减时表示满多少钱可用）
     */
    private BigDecimal thresholdAmount;

    /**
     * 减免金额（满减或固定减免时的金额）
     */
    private BigDecimal discountAmount;

    /**
     * 折扣值（折扣类型，如8.5表示85折）
     */
    private BigDecimal discountRate;

    /**
     * 最大优惠金额上限
     */
    private BigDecimal maxDiscount;

    /**
     * 优惠券总量
     */
    private Integer totalStock;

    /**
     * 每人限领数量
     */
    private Integer perUserLimit;

    /**
     * 有效开始时间
     */
    private LocalDateTime startTime;

    /**
     * 有效结束时间
     */
    private LocalDateTime endTime;

    /**
     * 状态 (0:停用, 1:启用)
     */
    private Integer status;

    /**
     * 描述
     */
    private String description;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;


    /** 前端额外字段：当前用户是否已领取 */
    private Boolean claimedByMe = false;
    /** 当前用户已领取数量 */
    private Integer myClaimedCount = 0;
}
