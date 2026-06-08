package com.social.couponservice.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.social.couponservice.domain.dto.CouponCreateDTO;
import com.social.couponservice.domain.po.Coupon;
import com.social.couponservice.domain.vo.CouponVO;
import com.social.couponservice.domain.vo.UserCouponVO;


import java.util.List;

/**
 * 优惠券服务接口
 */
public interface CouponService extends IService<Coupon> {

    /**
//     * 分页查询优惠券列表（管理员用）
     */
    List<CouponVO> getCouponList(String name, Integer status);

    /**
     * 获取优惠券详情
     */
    CouponVO getCouponDetail(Long id);

    /**
     * 创建优惠券（管理员）
     */
    Long createCoupon(CouponCreateDTO dto);

    /**
     * 更新优惠券（管理员）
     */
    void updateCoupon(Long id, CouponCreateDTO dto);

    /**
     * 删除优惠券（管理员）
     */
    void deleteCoupon(Long id);

    // ========== 用户端 ==========

    /**
     * 用户查看可领取的优惠券列表
     */
    List<CouponVO> getAvailableCoupons(Long userId);

    /**
     * 用户领取优惠券
     */
    void claimCoupon(Long userId, Long couponId);

    /**
     * 查看我的优惠券列表
     */
    List<UserCouponVO> getUserCoupons(Long userId, Integer status);

    /**
     * 使用优惠券
     */
    void useCoupon(Long userId, Long userCouponId);
}
