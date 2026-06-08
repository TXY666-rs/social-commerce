package com.social.productservice.domain.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 商品视图对象
 */
@Data
public class ProductVO {

    /**
     * 商品ID
     */
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
     * 商品分类（逗号分隔，兼容旧接口）
     */
    private String category;

    /**
     * 商品分类列表
     */
    private List<String> categories;

    /**
     * 配送方式 (逗号分隔, 1:快递发货, 2:上门自提)
     */
    private String deliveryType;

    /**
     * 配送方式列表
     */
    private List<Integer> deliveryTypes;

    /**
     * 商品图片URL（原始值，逗号分隔）
     */
    private String image;

    /**
     * 商品图片完整URL列表（已拼接前缀，前端展示用）
     */
    private List<String> images;

    /**
     * 卖家ID
     */
    private Long sellerId;

    /**
     * 卖家昵称
     */
    private String sellerNickname;

    /**
     * 状态 (0:下架, 1:上架)
     */
    private Integer status;

    /**
     * 浏览次数
     */
    private Integer viewCount;

    /**
     * 销售数量
     */
    private Integer saleCount;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;
}
