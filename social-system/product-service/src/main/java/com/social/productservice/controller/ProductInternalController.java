package com.social.productservice.controller;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.productservice.domain.dto.ProductQueryDTO;
import com.social.productservice.domain.po.Product;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;
import com.social.productservice.mapper.ProductMapper;
import com.social.product.service.api.dto.ProductBriefDTO;
import com.social.product.service.api.feign.ProductClient;
import com.social.productservice.service.ProductService;
import com.social.socialcommon.result.Result;
import com.social.socialcommon.utils.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
public class ProductInternalController implements ProductClient {

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private ProductService productService;
    @Qualifier("redisUtil")

    @Autowired
    private RedisUtil redisUtil;


    @Override
    @GetMapping("/internal/brief")
    public Result<List<ProductBriefDTO>> getProductBrief(List<Long>ids) {
        List<Product> products = productMapper.selectByIds(ids);
        if (products.isEmpty()) {
            return Result.error("商品不存在");
        }
        List<ProductBriefDTO> list = products.stream().map(product -> BeanUtil.copyProperties(product, ProductBriefDTO.class)).collect(Collectors.toList());
        return Result.success(list);
    }

    @Override
    @PostMapping("/internal/stock/decrease")
    public Result<Boolean> decreaseStock(Long id, Integer quantity) {
        // 直接扣MySQL（数据库层面保证 stock >= quantity，不会超卖）
        int rows = productMapper.decreaseStock(id, quantity);
        if (rows <= 0) {
            return Result.error("库存不足");
        }
        // 清除商品详情缓存，下次查询会从DB读取最新库存
        redisUtil.delete("product:detail:" + id);
        return Result.success(true);
    }

    @Override
    public Result<Boolean> increaseStock(Long id, Integer quantity) {
        int rows = productMapper.increaseStock(id, quantity);
        if (rows <= 0) {
            log.warn("库存恢复失败，商品可能不存在: productId={}", id);
            return Result.error("库存恢复失败");
        }
        // 清除商品详情缓存
        redisUtil.delete("product:detail:" + id);
        return Result.success(true);
    }

    // ========== Admin 管理端接口实现（查看+上架/下架） ==========

    @Override
    public Result<Map<String, Object>> getAdminProductPage(String category, String keyword, Integer status, Integer pageNum, Integer pageSize) {
        try {
            ProductQueryDTO queryDTO = new ProductQueryDTO();
            queryDTO.setCategory(category);
            queryDTO.setKeyword(keyword);
            queryDTO.setStatus(status);
            queryDTO.setPageNum(pageNum);
            queryDTO.setPageSize(pageSize);
            IPage<ProductListVO> productListVOList = productService.getProductPage(queryDTO);
            Map<String, Object> result = new HashMap<>();
            result.put("records", productListVOList);
            return Result.success(result);
        } catch (Exception e) {
            log.error("管理端查询商品列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Map<String, Object>> getAdminProductDetail(Long id) {
        try {
            ProductVO productVO = productService.getProductDetail(id);
            Map<String, Object> map = BeanUtil.beanToMap(productVO);
            return Result.success(map);
        } catch (Exception e) {
            log.error("管理端获取商品详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> adminToggleProductStatus(Long id, Integer status) {
        try {
            boolean updated = productService.toggleProductStatus(id, null, status);
            return Result.success(status == 1 ? "上架成功" : "下架成功", updated);
        } catch (Exception e) {
            log.error("管理端切换商品状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    private Map<String, Object> productVOToMap(ProductVO vo) {
        return BeanUtil.beanToMap(vo);
    }
}
