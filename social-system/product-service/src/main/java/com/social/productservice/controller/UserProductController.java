package com.social.productservice.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.productservice.domain.dto.ProductAgentQueryDTO;
import com.social.productservice.domain.dto.ProductCreateDTO;
import com.social.productservice.domain.dto.ProductQueryDTO;
import com.social.productservice.domain.dto.ProductUpdateDTO;
import com.social.productservice.domain.vo.AgentResponse;
import com.social.productservice.domain.vo.ProductListVO;
import com.social.productservice.domain.vo.ProductVO;
import com.social.productservice.service.ProductService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/product")
public class UserProductController {

    @Autowired
    private ProductService productService;


    /**
     * 供agent使用的查询接口
     */
    @GetMapping("/list/search")
    public Result<AgentResponse> getProductVOList(ProductAgentQueryDTO productAgentQueryDTO) {
        try {
            // 公开查询只显示上架商品
            productAgentQueryDTO.setStatus(1);
            AgentResponse agentResponse=productService.getProductVOList(productAgentQueryDTO);
            return Result.success("查询成功",agentResponse);
        } catch (Exception e) {
            log.error("查询商品列表失败", e);
            return Result.error(e.getMessage());
        }
    }


    @GetMapping("/categories")
    public Result<List<String>> getCategories() {
        try {
            List<String> categories = productService.getCategories();
            return Result.success(categories);
        } catch (Exception e) {
            log.error("获取分类列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/category/{category}")
    public Result<List<ProductListVO>> getProductsByCategory(@PathVariable String category) {
        try {
            List<ProductListVO> list = productService.getProductsByCategory(category);
            return Result.success("查询成功", list);
        } catch (Exception e) {
            log.error("根据分类查询商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/list")
    public Result<IPage<ProductListVO>> getProductList(ProductQueryDTO queryDTO) {
        try {
            queryDTO.setStatus(1);
            IPage<ProductListVO> page = productService.getProductPage(queryDTO);
            return Result.success("查询成功", page);
        } catch (Exception e) {
            log.error("查询商品列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<ProductVO> getProductDetail(@PathVariable Long id) {
        try {
            ProductVO product = productService.getProductDetail(id);
            return Result.success(product);
        } catch (Exception e) {
            log.error("获取商品详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/create")
    public Result<ProductVO> createProduct(
            @Valid @RequestBody ProductCreateDTO createDTO,
            HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            ProductVO product = productService.createProduct(userId, createDTO);
            return Result.success("商品发布成功", product);
        } catch (Exception e) {
            log.error("发布商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/update/{id}")
    public Result<ProductVO> updateProduct(
            @PathVariable Long id,
            @Valid @RequestBody ProductUpdateDTO updateDTO,
            HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            ProductVO product = productService.updateProduct(id, userId, updateDTO);
            return Result.success("商品更新成功", product);
        } catch (Exception e) {
            log.error("更新商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/delete/{id}")
    public Result<Boolean> deleteProduct(@PathVariable Long id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean deleted = productService.deleteProduct(id, userId);
            if (deleted) {
                return Result.success("删除成功", true);
            } else {
                return Result.error("删除失败");
            }
        } catch (Exception e) {
            log.error("删除商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/toggle-status/{id}")
    public Result<Boolean> toggleProductStatus(
            @PathVariable Long id,
            @RequestParam Integer status,
            HttpServletRequest request) {
        try {
            if (status != 0 && status != 1) {
                return Result.error("状态值无效，只能为0(下架)或1(上架)");
            }
            Long userId = getUserIdFromRequest(request);
            boolean updated = productService.toggleProductStatus(id, userId, status);
            if (updated) {
                String msg = status == 1 ? "上架成功" : "下架成功";
                return Result.success(msg, true);
            } else {
                return Result.error("操作失败");
            }
        } catch (Exception e) {
            log.error("上架/下架商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/my")
    public Result<IPage<ProductVO>> getMyProducts(ProductQueryDTO queryDTO, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            IPage<ProductVO> page = productService.getSellerProducts(userId, queryDTO);
            return Result.success("查询成功", page);
        } catch (Exception e) {
            log.error("查询我的商品失败", e);
            return Result.error(e.getMessage());
        }
    }

    private Long getUserIdFromRequest(HttpServletRequest request) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null) {
            throw new RuntimeException("未提供有效令牌");
        }
        return Long.parseLong(userIdStr);
    }
}
