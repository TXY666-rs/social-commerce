package com.social.productservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.productservice.domain.po.Product;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;
import com.social.productservice.domain.vo.ToAgentProductVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;

/**
 * 商品Mapper接口
 */
@Mapper
public interface ProductMapper extends BaseMapper<Product> {

    /**
     * 根据分类查询上架商品列表
     */
    List<ProductListVO> selectByCategory(@Param("category") String category);

    /**
     * 分页查询上架商品（带分类筛选和关键词搜索）
     */
    IPage<ProductListVO> selectProductPage(Page<ProductListVO> page,
                                           @Param("category") String category,
                                           @Param("keyword") String keyword,
                                           @Param("status") Integer status);



    /**
     * 增加浏览次数
     */
    int incrementViewCount(@Param("id") Long id);

    /**
     * 增加销售数量
     */
    int increaseStock(@Param("id") Long id, @Param("quantity") Integer quantity);

    /**
     * 扣减库存
     */
    int decreaseStock(@Param("id") Long id, @Param("quantity") Integer quantity);

    /**
     * 分页查询卖家商品（带分类筛选和关键词搜索）
     */
    IPage<Product> selectSellerProductPage(Page<Product> page,
                                            @Param("sellerId") Long sellerId,
                                            @Param("category") String category,
                                            @Param("keyword") String keyword,
                                            @Param("status") Integer status);

    List<ToAgentProductVO> selectByScalarQuery(@Param("category") String category,
                                               @Param("keyword") String keyword,
                                               @Param("topK") Integer topK,
                                               @Param("minPrice") BigDecimal minPrice,
                                               @Param("status") Integer status,
                                               @Param("maxPrice") BigDecimal maxPrice);
}
