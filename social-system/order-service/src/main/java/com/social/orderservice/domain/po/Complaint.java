package com.social.orderservice.domain.po;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 投诉实体类
 * 对应数据库中的 complaint 表
 */
@Data
@TableName("complaint")
public class Complaint {

    /**
     * 投诉ID（数据库自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 关联订单ID
     */
    private String orderId;

    /**
     * 投诉类型 (service:服务问题, delivery:物流问题, product:商品问题)
     */
    private String type;

    /**
     * 投诉详细描述
     */
    private String detail;

    /**
     * 处理状态 (0:待处理, 1:处理中, 2:已处理)
     */
    private Integer status;

    /**
     * 处理备注
     */
    private String handlerNote;

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
