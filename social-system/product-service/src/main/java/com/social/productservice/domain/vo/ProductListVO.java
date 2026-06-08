package com.social.productservice.domain.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ProductListVO {

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
     * 商品分类列表
     */
    private List<String> categories;


    /**
     * 商品图片URL（原始值，逗号分隔）
     */
    private String image;

    /**
     * 商品图片完整URL列表（已拼接前缀，前端展示用）
     */
    private List<String> images;

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


}
