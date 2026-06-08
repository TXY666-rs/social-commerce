package com.social.orderservice.domain.po;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 订单实体类
 * 对应数据库中的 order 表
 */
@Data
@TableName("\"order\"")
public class Order {

    /**
     * 订单ID（格式: order + 8位日期 + 5位流水号，如 order2026052800001）
     */
    @TableId(type = IdType.INPUT)
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
     * 购买数量
     */
    private Integer quantity;

    /**
     * 总价（实付金额 = 原价 - 优惠金额）
     */
    private BigDecimal totalPrice;

    /**
     * 原价（商品单价 * 数量）
     */
    private BigDecimal originalPrice;

    /**
     * 优惠金额
     */
    private BigDecimal discountAmount;

    /**
     * 使用的用户优惠券ID（user_coupon 表的 ID）
     */
    private Long userCouponId;

    /**
     * 订单状态 (0:待支付, 1:已支付, 2:已发货, 3:已完成, 4:已取消, 5:退款中, 6:已退款)
     */
    private Integer status;

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
     * 快递单号（快递发货时填写）
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
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 是否删除
     */
    @TableLogic
    private Integer isDeleted;
}
