package com.social.couponservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.couponservice.domain.po.UserCoupon;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserCouponMapper extends BaseMapper<UserCoupon> {

    /**
     * 统计用户已领取某优惠券的数量
     */
    @Select("SELECT COUNT(*) FROM user_coupon WHERE user_id = #{userId} AND coupon_id = #{couponId}")
    int countUserClaims(@Param("userId") Long userId, @Param("couponId") Long couponId);
}
