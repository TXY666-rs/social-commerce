package com.social.productservice.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.productservice.domain.dto.ProductAgentQueryDTO;
import com.social.productservice.domain.dto.ProductCreateDTO;
import com.social.productservice.domain.dto.ProductQueryDTO;
import com.social.productservice.domain.dto.ProductUpdateDTO;
import com.social.productservice.domain.po.Category;
import com.social.productservice.domain.vo.AgentResponse;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;

import java.util.List;

/**
 * 商品服务接口
 */
public interface ProductService {

    /**
     * 创建商品
     */
    ProductVO createProduct(Long sellerId, ProductCreateDTO createDTO);

    /**
     * 更新商品
     */
    ProductVO updateProduct(Long productId, Long sellerId, ProductUpdateDTO updateDTO);

    /**
     * 删除商品
     */
    boolean deleteProduct(Long productId, Long sellerId);

    /**
     * 获取商品详情
     */
    ProductVO getProductDetail(Long productId) throws InterruptedException;

    /**
     * 分页查询商品列表
     */
    IPage<ProductListVO> getProductPage(ProductQueryDTO queryDTO) throws InterruptedException;

    /**
     * 获取卖家商品列表
     */
    IPage<ProductVO> getSellerProducts(Long sellerId, ProductQueryDTO queryDTO);

    /**
     * 上架/下架商品
     */
    boolean toggleProductStatus(Long productId, Long sellerId, Integer status);

    /**
     * 获取商品分类列表
     */
    List<String> getCategories();

    /**
     * 根据分类查询商品列表（带Redis缓存）
     */
    List<ProductListVO> getProductsByCategory(String category) throws InterruptedException;

    // ========== 分类管理 ==========

    /**
     * 获取所有分类（管理端）
     */
    List<Category> getAllCategories();

    /**
     * 添加分类
     */
    void addCategory(String name, Integer sortOrder);

    /**
     * 更新分类
     */
    void updateCategory(Long id, String name, Integer sortOrder, Integer status);

    /**
     * 删除分类
     */
    void deleteCategory(Long id);

    /**
     * AI Agent：查询商品列表
     */
    AgentResponse getProductVOList(ProductAgentQueryDTO productAgentQueryDTO);
}
