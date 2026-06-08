package com.social.coupon.service.api.feign;

import com.social.socialcommon.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.openfeign.FallbackFactory;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Map;

@Slf4j
@Component
public class CouponClientFallbackFactory implements FallbackFactory<CouponClient> {

    @Override
    public CouponClient create(Throwable cause) {
        log.error("CouponClient 调用失败，启用 fallback", cause);
        return new CouponClient() {
            @Override
            public Result<Map<String, Object>> getAdminCouponPage(String name, Integer status, Integer type, Integer pageNum, Integer pageSize) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Map<String, Object>> getAdminCouponDetail(Long id) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Long> adminCreateCoupon(Map<String, Object> couponDTO) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Boolean> adminUpdateCoupon(Long id, Map<String, Object> couponDTO) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Boolean> adminDeleteCoupon(Long id) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Boolean> adminToggleCouponStatus(Long id, Integer status) {
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<BigDecimal> calculateDiscount(Long userId, Long userCouponId, BigDecimal orderAmount) {
                log.warn("calculateDiscount fallback: 折扣计算失败，返回 0");
                return Result.success(BigDecimal.ZERO);
            }

            @Override
            public Result<Boolean> useCoupon(Long userId, Long userCouponId) {
                log.warn("useCoupon fallback: 优惠券核销失败");
                return Result.error("优惠券服务暂不可用");
            }

            @Override
            public Result<Boolean> restoreCoupon(Long userId, Long userCouponId) {
                log.warn("restoreCoupon fallback: 优惠券退回失败");
                return Result.error("优惠券服务暂不可用");
            }
        };
    }
}
