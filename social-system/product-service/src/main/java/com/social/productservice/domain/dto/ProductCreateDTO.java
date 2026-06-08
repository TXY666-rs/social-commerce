package com.social.productservice.domain.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * 创建商品DTO
 */
@Data
public class ProductCreateDTO {

    /**
     * 商品名称
     */
    @NotBlank(message = "商品名称不能为空")
    private String name;

    /**
     * 商品描述
     */
    private String description;

    /**
     * 价格
     */
    @NotNull(message = "价格不能为空")
    @Min(value = 0, message = "价格不能为负数")
    private BigDecimal price;

    /**
     * 库存
     */
    @NotNull(message = "库存不能为空")
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
}
