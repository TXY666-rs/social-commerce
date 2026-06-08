package com.social.productservice.domain.po;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 商品实体类
 * 对应数据库中的 product 表
 */
@Data
@TableName("product")
public class Product {

    /**
     * 商品ID
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 商品名称
     */
    private String name;

    /**
     * 商品描述
     */
    private String description;

    /**
     * 价格
     */
    private BigDecimal price;

    /**
     * 库存
     */
    private Integer stock;

    /**
     * 商品分类
     */
    private String category;

    /**
     * 商品图片URL
     */
    private String image;

    /**
     * 卖家ID
     */
    private Long sellerId;

    /**
     * 配送方式 (逗号分隔, 1:快递发货, 2:上门自提)
     */
    private String deliveryType;

    /**
     * 状态 (0:下架, 1:上架)
     */
    private Integer status;

    /**
     * 浏览次数
     */
    private Integer viewCount;


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
