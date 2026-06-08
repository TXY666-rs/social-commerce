package com.social.couponservice.controller;

import com.social.couponservice.domain.vo.CouponVO;
import com.social.couponservice.domain.vo.UserCouponVO;
import com.social.couponservice.service.CouponService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/coupon")
public class UserCouponController {

    @Autowired
    private CouponService couponService;

    @GetMapping("/available")
    public Result<List<CouponVO>> available(HttpServletRequest request) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null) {
            return Result.error(401, "未登录");
        }
        List<CouponVO> list = couponService.getAvailableCoupons(Long.parseLong(userIdStr));
        return Result.success(list);
    }

    @PostMapping("/claim/{couponId}")
    public Result<String> claim(HttpServletRequest request, @PathVariable Long couponId) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null) {
            return Result.error(401, "未登录");
        }
        couponService.claimCoupon(Long.parseLong(userIdStr), couponId);
        return Result.success("领取成功");
    }

    @GetMapping("/my")
    public Result<List<UserCouponVO>> myCoupons(
            HttpServletRequest request,
            @RequestParam(required = false) Integer status) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null) {
            return Result.error(401, "未登录");
        }
        List<UserCouponVO> list = couponService.getUserCoupons(Long.parseLong(userIdStr), status);
        return Result.success(list);
    }

    @PostMapping("/use/{userCouponId}")
    public Result<String> use(HttpServletRequest request, @PathVariable Long userCouponId) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null) {
            return Result.error(401, "未登录");
        }
        couponService.useCoupon(Long.parseLong(userIdStr), userCouponId);
        return Result.success("使用成功");
    }
}
