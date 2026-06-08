package com.social.product.service.api.dto;


import lombok.Data;

import java.math.BigDecimal;

@Data
public class ProductBriefDTO {

    /*
    * 商品id
    * */
    private Long id;

    /*
     * 商品名称
     * */
    private String name;

    /*
     * 商品售价
     * */
    private BigDecimal price;

    /*
     * 卖家id
     * */
    private Long sellerId;

    /*
     * 商品状态
     * */
    private Integer status;

    /*
     * 商品库存
     * */
    private Integer stock;

    /*
     * 商品图片URL（逗号分隔）
     * */
    private String image;
}
