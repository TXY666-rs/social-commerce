package com.social.couponservice.controller;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.coupon.service.api.feign.CouponClient;
import com.social.couponservice.domain.dto.CouponCreateDTO;
import com.social.couponservice.domain.po.Coupon;
import com.social.couponservice.domain.po.UserCoupon;
import com.social.couponservice.mapper.CouponMapper;
import com.social.couponservice.mapper.UserCouponMapper;
import com.social.couponservice.service.CouponService;
import com.social.socialcommon.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
public class CouponInternalController implements CouponClient {

    @Autowired
    private CouponMapper couponMapper;

    @Autowired
    private CouponService couponService;

    // ========== Admin 管理端接口实现 ==========

    @Override
    public Result<Map<String, Object>> getAdminCouponPage(String name, Integer status, Integer type, Integer pageNum, Integer pageSize) {
        try {
            LambdaQueryWrapper<Coupon> wrapper = new LambdaQueryWrapper<>();
            if (name != null && !name.isEmpty()) {
                wrapper.like(Coupon::getName, name);
            }
            if (status != null) {
                wrapper.eq(Coupon::getStatus, status);
            }
            if (type != null) {
                wrapper.eq(Coupon::getType, type);
            }
            wrapper.orderByDesc(Coupon::getCreateTime);

            Page<Coupon> page = new Page<>(pageNum, pageSize);
            Page<Coupon> couponPage = couponMapper.selectPage(page, wrapper);

            List<Map<String, Object>> records = couponPage.getRecords().stream()
                    .map(this::couponToMap)
                    .collect(Collectors.toList());

            Map<String, Object> result = new HashMap<>();
            result.put("records", records);
            result.put("total", couponPage.getTotal());
            result.put("pages", couponPage.getPages());
            result.put("current", couponPage.getCurrent());
            result.put("size", couponPage.getSize());

            return Result.success(result);
        } catch (Exception e) {
            log.error("管理端查询优惠券列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Map<String, Object>> getAdminCouponDetail(Long id) {
        try {
            Coupon coupon = couponMapper.selectById(id);
            if (coupon == null) {
                return Result.error("优惠券不存在");
            }
            Map<String, Object> map = couponToMap(coupon);
            return Result.success(map);
        } catch (Exception e) {
            log.error("管理端获取优惠券详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Long> adminCreateCoupon(Map<String, Object> couponDTO) {
        try {
            CouponCreateDTO createDTO = BeanUtil.mapToBean(couponDTO, CouponCreateDTO.class, false);
            Long couponId = couponService.createCoupon(createDTO);
            return Result.success("创建成功", couponId);
        } catch (Exception e) {
            log.error("管理端创建优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> adminUpdateCoupon(Long id, Map<String, Object> couponDTO) {
        try {
            CouponCreateDTO updateDTO = BeanUtil.mapToBean(couponDTO, CouponCreateDTO.class, false);
            couponService.updateCoupon(id, updateDTO);
            return Result.success("更新成功", true);
        } catch (Exception e) {
            log.error("管理端更新优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> adminDeleteCoupon(Long id) {
        try {
            couponService.deleteCoupon(id);
            return Result.success("删除成功", true);
        } catch (Exception e) {
            log.error("管理端删除优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> adminToggleCouponStatus(Long id, Integer status) {
        try {
            Coupon coupon = couponMapper.selectById(id);
            if (coupon == null) {
                return Result.error("优惠券不存在");
            }
            coupon.setStatus(status);
            couponMapper.updateById(coupon);
            return Result.success(status == 1 ? "启用成功" : "停用成功", true);
        } catch (Exception e) {
            log.error("管理端切换优惠券状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    // ========== 订单服务调用：折扣计算与核销 ==========

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Override
    public Result<BigDecimal> calculateDiscount(Long userId, Long userCouponId, BigDecimal orderAmount) {
        try {
            UserCoupon userCoupon = userCouponMapper.selectById(userCouponId);
            if (userCoupon == null || !userCoupon.getUserId().equals(userId)) {
                return Result.error("优惠券不存在或不属于当前用户");
            }
            if (userCoupon.getStatus() != 0) {
                return Result.error("优惠券已使用或已过期");
            }

            Coupon coupon = couponMapper.selectById(userCoupon.getCouponId());
            if (coupon == null || coupon.getStatus() != 1) {
                return Result.error("优惠券已停用");
            }
            if (LocalDateTime.now().isAfter(coupon.getEndTime())) {
                return Result.error("优惠券已过期");
            }

            BigDecimal discount = doCalculateDiscount(coupon, orderAmount);
            return Result.success(discount);
        } catch (Exception e) {
            log.error("计算优惠券折扣失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> useCoupon(Long userId, Long userCouponId) {
        try {
            couponService.useCoupon(userId, userCouponId);
            return Result.success(true);
        } catch (Exception e) {
            log.error("核销优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> restoreCoupon(Long userId, Long userCouponId) {
        try {
            UserCoupon uc = userCouponMapper.selectById(userCouponId);
            if (uc == null || !uc.getUserId().equals(userId)) {
                return Result.error("优惠券不存在");
            }
            if (uc.getStatus() != 1) {
                return Result.success(true); // 已经是未使用状态，直接返回成功
            }
            uc.setStatus(0); // 恢复为未使用
            uc.setUseTime(null);
            userCouponMapper.updateById(uc);
            log.info("[优惠券] 用户 {} 的优惠券 {} 已退回", userId, userCouponId);
            return Result.success(true);
        } catch (Exception e) {
            log.error("退回优惠券失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 根据优惠券类型计算折扣金额
     * type=1: 满减（满thresholdAmount减discountAmount）
     * type=2: 折扣（discountRate折，如8.5=85折，即打8.5折，实付85%，优惠15%）
     * type=3: 固定减免（直接减discountAmount）
     */
    private BigDecimal doCalculateDiscount(Coupon coupon, BigDecimal orderAmount) {
        switch (coupon.getType()) {
            case 1: // 满减
                if (orderAmount.compareTo(coupon.getThresholdAmount()) >= 0) {
                    return coupon.getDiscountAmount();
                }
                return BigDecimal.ZERO;
            case 2: // 折扣
                // discountRate=8.5 表示 85折，优惠比例 = 1 - 8.5/10 = 0.15
                BigDecimal rate = coupon.getDiscountRate().divide(BigDecimal.TEN, 4, RoundingMode.HALF_UP);
                BigDecimal discount = orderAmount.multiply(BigDecimal.ONE.subtract(rate));
                if (coupon.getMaxDiscount() != null && discount.compareTo(coupon.getMaxDiscount()) > 0) {
                    return coupon.getMaxDiscount();
                }
                return discount.setScale(2, RoundingMode.HALF_UP);
            case 3: // 固定减免
                return coupon.getDiscountAmount();
            default:
                return BigDecimal.ZERO;
        }
    }

    private Map<String, Object> couponToMap(Coupon coupon) {
        return BeanUtil.beanToMap(coupon);
    }
}
