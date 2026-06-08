package com.social.orderservice.domain.dto;

import lombok.Data;

/**
 * 发货DTO（卖家发货时填写）
 */
@Data
public class DeliverOrderDTO {

    /**
     * 快递单号（快递发货时填写）
     */
    private String trackingNumber;

    /**
     * 发货备注/自提地址（自提时填写自提地址，快递时可选填备注）
     */
    private String deliveryRemark;
}
