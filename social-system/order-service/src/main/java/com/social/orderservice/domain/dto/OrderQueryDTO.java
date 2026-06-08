package com.social.orderservice.domain.dto;

import io.swagger.v3.oas.models.security.SecurityScheme;
import lombok.Data;

/**
 * 订单查询DTO
 */
@Data
public class OrderQueryDTO {

    /**
     * userId
     */
    private String user_id;

    /**
     * orderId
     */
    private String order_id;

    /**
     * productKeyword
     */
    private String product_keyword;

    /**
     * 订单状态 (0:待支付, 1:已支付, 2:已发货, 3:已完成, 4:已取消, 5:退款中, 6:已退款)
     */
    private String status;

    /**
     * 页码
     */
    private Integer pageNum = 1;

    /**
     * 每页数量
     */
    private Integer pageSize = 10;
}
