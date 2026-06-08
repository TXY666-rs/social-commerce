package com.social.productservice.domain.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * 更新商品DTO
 */
@Data
public class ProductUpdateDTO {

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
    @Min(value = 0, message = "价格不能为负数")
    private BigDecimal price;

    /**
     * 库存
     */
    @Min(value = 0, message = "库存不能为负数")
    private Integer stock;

    /**
     * 商品分类（多选）
     */
    private List<String> categories;

    /**
     * 配送方式 (1:快递发货, 2:上门自提，可多选)
     */
    private List<Integer> deliveryTypes;

    /**
     * 商品图片URL
     */
    private String image;

    /**
     * 状态 (0:下架, 1:上架)
     */
    private Integer status;
}
