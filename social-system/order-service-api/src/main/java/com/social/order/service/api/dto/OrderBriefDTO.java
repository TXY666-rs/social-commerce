package com.social.order.service.api.dto;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class OrderBriefDTO {

    private String id;

    private Long userId;

    private Long sellerId;

    private Long productId;

    private Integer quantity;

    private BigDecimal totalPrice;

    private Integer status;

    private String trackingNumber;
}
