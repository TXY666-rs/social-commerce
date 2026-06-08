package com.social.orderservice.domain.vo;



import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 订单视图对象
 */
@Data
public class OrderVO {

    /**
     * 订单ID
     */
    private String id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 商品ID
     */
    private Long productId;

    /**
     * 卖家ID
     */
    private Long sellerId;

    /**
     * 卖家昵称
     */
    private String sellerNickname;

    /**
     * 商品名称
     */
    private String productName;

    /**
     * 商品图片
     */
    private String productImage;

    /**
     * 商品单价
     */
    private BigDecimal productPrice;

    /**
     * 购买数量
     */
    private Integer quantity;

    /**
     * 总价（实付金额）
     */
    private BigDecimal totalPrice;

    /**
     * 原价
     */
    private BigDecimal originalPrice;

    /**
     * 优惠金额
     */
    private BigDecimal discountAmount;

    /**
     * 使用的用户优惠券ID
     */
    private Long userCouponId;

    /**
     * 订单状态 (0:待支付, 1:已支付, 2:已发货, 3:已完成, 4:已取消, 5:退款中, 6:已退款)
     */
    private Integer status;

    /**
     * 订单状态描述
     */
    private String statusDesc;

    /**
     * 收货人姓名
     */
    private String receiverName;

    /**
     * 收货人电话
     */
    private String receiverPhone;

    /**
     * 收货地址
     */
    private String receiverAddress;


    /**
     * 快递单号
     */
    private String trackingNumber;

    /**
     * 发货备注
     */
    private String deliveryRemark;

    /**
     * 支付时间
     */
    private LocalDateTime payTime;

    /**
     * 发货时间
     */
    private LocalDateTime deliveryTime;

    /**
     * 完成时间
     */
    private LocalDateTime completeTime;

    /**
     * 备注
     */
    private String remark;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
