package com.social.productservice.domain.vo;

import lombok.Data;

import java.math.BigDecimal;
@Data
public class ToAgentProductVO {


    /**
     * 商品id
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

}
