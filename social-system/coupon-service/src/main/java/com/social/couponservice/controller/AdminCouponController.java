package com.social.couponservice.controller;

import com.social.couponservice.domain.dto.CouponCreateDTO;
import com.social.couponservice.domain.vo.CouponVO;
import com.social.couponservice.service.CouponService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/admin/coupon")
public class AdminCouponController {

    @Autowired
    private CouponService couponService;

    @GetMapping("/list")
    public Result<List<CouponVO>> list(
            HttpServletRequest request,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Integer status) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            List<CouponVO> list = couponService.getCouponList(name, status);
            return Result.success(list);
        } catch (Exception e) {
            log.error("管理端查询优惠券列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<CouponVO> detail(@PathVariable Long id, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            CouponVO vo = couponService.getCouponDetail(id);
            return Result.success(vo);
        } catch (Exception e) {
            log.error("管理端获取优惠券详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/create")
    public Result<Long> create(@Valid @RequestBody CouponCreateDTO dto, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            Long id = couponService.createCoupon(dto);
            return Result.success("创建成功", id);
        } catch (Exception e) {
            log.error("管理端创建优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public Result<String> update(@PathVariable Long id,
                                 @Valid @RequestBody CouponCreateDTO dto,
                                 HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            couponService.updateCoupon(id, dto);
            return Result.success("更新成功");
        } catch (Exception e) {
            log.error("管理端更新优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public Result<String> delete(@PathVariable Long id, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            couponService.deleteCoupon(id);
            return Result.success("删除成功");
        } catch (Exception e) {
            log.error("管理端删除优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    private boolean isAdmin(HttpServletRequest request) {
        String role = request.getHeader("X-User-Role");
        return "ADMIN".equals(role);
    }
}
