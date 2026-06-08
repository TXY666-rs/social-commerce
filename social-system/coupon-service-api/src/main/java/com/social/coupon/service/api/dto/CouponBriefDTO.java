package com.social.coupon.service.api.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class CouponBriefDTO {

    private Long id;

    private String name;

    private Integer type;

    private BigDecimal discount;

    private BigDecimal minAmount;

    private Integer totalCount;

    private Integer claimedCount;

    private Integer usedCount;

    private Integer status;

    private LocalDateTime startTime;

    private LocalDateTime endTime;
}
