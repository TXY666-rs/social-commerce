package com.social.productservice.domain.dto;

import lombok.Data;

/**
 * 商品查询DTO
 */
@Data
public class ProductQueryDTO {

    /**
     * 商品分类（筛选某一个分类）
     */
    private String category;

    /**
     * 搜索关键词
     */
    private String keyword;

    /**
     * 商品状态 (0:下架, 1:上架)
     */
    private Integer status;

    /**
     * 页码
     */
    private Integer pageNum = 1;

    /**
     * 每页数量
     */
    private Integer pageSize = 12;
}
