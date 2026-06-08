package com.social.product.service.api.feign;

import com.social.product.service.api.dto.ProductBriefDTO;
import com.social.socialcommon.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ProductClientFallbackFactory implements FallbackFactory<ProductClient> {

    @Override
    public ProductClient create(Throwable cause) {
        log.error("ProductClient 调用失败，启用 fallback", cause);
        return new ProductClient() {
            @Override
            public Result<List<ProductBriefDTO>> getProductBrief(List<Long> ids) {
                return Result.success(Collections.emptyList());
            }

            @Override
            public Result<Boolean> decreaseStock(Long id, Integer quantity) {
                return Result.error("商品服务暂不可用");
            }

            @Override
            public Result<Boolean> increaseStock(Long id, Integer quantity) {
                return Result.error("商品服务暂不可用");
            }

            @Override
            public Result<Map<String, Object>> getAdminProductPage(String category, String keyword, Integer status, Integer pageNum, Integer pageSize) {
                return Result.error("商品服务暂不可用");
            }

            @Override
            public Result<Map<String, Object>> getAdminProductDetail(Long id) {
                return Result.error("商品服务暂不可用");
            }

            @Override
            public Result<Boolean> adminToggleProductStatus(Long id, Integer status) {
                return Result.error("商品服务暂不可用");
            }
        };
    }
}
