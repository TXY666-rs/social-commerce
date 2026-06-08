package com.social.coupon.service.api.feign;

import com.social.socialcommon.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.Map;

@FeignClient(name = "coupon-service", path = "/api", fallbackFactory = CouponClientFallbackFactory.class)
public interface CouponClient {

    // ========== Admin 管理端接口（完整CRUD+状态切换） ==========

    @GetMapping("/internal/admin/coupons")
    Result<Map<String, Object>> getAdminCouponPage(
            @RequestParam(value = "name", required = false) String name,
            @RequestParam(value = "status", required = false) Integer status,
            @RequestParam(value = "type", required = false) Integer type,
            @RequestParam("pageNum") Integer pageNum,
            @RequestParam("pageSize") Integer pageSize);

    @GetMapping("/internal/admin/coupons/{id}")
    Result<Map<String, Object>> getAdminCouponDetail(@PathVariable("id") Long id);

    @PostMapping("/internal/admin/coupons")
    Result<Long> adminCreateCoupon(@RequestBody Map<String, Object> couponDTO);

    @PutMapping("/internal/admin/coupons/{id}")
    Result<Boolean> adminUpdateCoupon(@PathVariable("id") Long id,
                                      @RequestBody Map<String, Object> couponDTO);

    @DeleteMapping("/internal/admin/coupons/{id}")
    Result<Boolean> adminDeleteCoupon(@PathVariable("id") Long id);

    @PutMapping("/internal/admin/coupons/{id}/status")
    Result<Boolean> adminToggleCouponStatus(@PathVariable("id") Long id,
                                             @RequestParam("status") Integer status);

    // ========== 订单服务调用：折扣计算与核销 ==========

    /**
     * 计算优惠券折扣金额
     */
    @GetMapping("/internal/coupon/calculate")
    Result<BigDecimal> calculateDiscount(
            @RequestParam("userId") Long userId,
            @RequestParam("userCouponId") Long userCouponId,
            @RequestParam("orderAmount") BigDecimal orderAmount);

    /**
     * 核销优惠券（标记为已使用）
     */
    @PostMapping("/internal/coupon/use")
    Result<Boolean> useCoupon(
            @RequestParam("userId") Long userId,
            @RequestParam("userCouponId") Long userCouponId);

    /**
     * 退回优惠券（取消订单时恢复为未使用）
     */
    @PostMapping("/internal/coupon/restore")
    Result<Boolean> restoreCoupon(
            @RequestParam("userId") Long userId,
            @RequestParam("userCouponId") Long userCouponId);
}
