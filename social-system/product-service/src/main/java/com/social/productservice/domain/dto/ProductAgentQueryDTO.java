package com.social.productservice.domain.dto;


import lombok.Data;

import java.math.BigDecimal;

@Data
public class ProductAgentQueryDTO {

    /**
     * 商品分类（筛选某一个分类）
     */
    private String category;

    /**
     * 最低价格
     */
    private BigDecimal min_price;

    /**
     * 最高价格
     */
    private BigDecimal max_price;


    /**
     * 搜索关键词
     */
    private String keyword;

    /**
     * 商品状态 (0:下架, 1:上架)
     */
    private Integer status;

    /**
     * 至多返回的条数
     */
    private Integer top_k;

}
