package com.social.product.service.api.feign;

import com.social.product.service.api.dto.ProductBriefDTO;
import com.social.socialcommon.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@FeignClient(name = "product-service", path = "/api", fallbackFactory = ProductClientFallbackFactory.class)
public interface ProductClient {

    @GetMapping("/internal/brief")
    Result<List<ProductBriefDTO>> getProductBrief(@RequestParam List<Long> ids);

    @PostMapping("/internal/stock/decrease")
    Result<Boolean> decreaseStock(
            @RequestParam("id") Long id,
            @RequestParam("quantity") Integer quantity);

    @PostMapping("/internal/stock/increase")
    Result<Boolean> increaseStock(
            @RequestParam("id") Long id,
            @RequestParam("quantity") Integer quantity);

    // ========== Admin 管理端接口（查看+上架/下架） ==========

    @GetMapping("/internal/admin/products")
    Result<Map<String, Object>> getAdminProductPage(
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "keyword", required = false) String keyword,
            @RequestParam(value = "status", required = false) Integer status,
            @RequestParam("pageNum") Integer pageNum,
            @RequestParam("pageSize") Integer pageSize);

    @GetMapping("/internal/admin/products/{id}")
    Result<Map<String, Object>> getAdminProductDetail(@PathVariable("id") Long id);

    @PutMapping("/internal/admin/products/{id}/status")
    Result<Boolean> adminToggleProductStatus(@PathVariable("id") Long id,
                                              @RequestParam("status") Integer status);
}
