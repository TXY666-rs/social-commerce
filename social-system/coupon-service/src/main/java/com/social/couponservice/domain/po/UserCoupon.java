package com.social.couponservice.domain.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户优惠券（领取记录）
 */
@Data
@TableName("user_coupon")
public class UserCoupon implements Serializable {
    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 优惠券ID
     */
    private Long couponId;

    /**
     * 状态 (0:未使用, 1:已使用, 2:已过期)
     */
    private Integer status;

    /**
     * 领取时间
     */
    private LocalDateTime claimTime;

    /**
     * 使用时间
     */
    private LocalDateTime useTime;
}
