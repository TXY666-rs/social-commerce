package com.social.couponservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import com.social.couponservice.domain.po.Coupon;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface CouponMapper extends BaseMapper<Coupon> {

    /**
     * 原子扣减优惠券库存（数据库层面保证 total_stock > 0）
     */
    @Update("UPDATE coupon SET total_stock = total_stock - 1, update_time = NOW() WHERE id = #{id} AND total_stock > 0")
    int decreaseStock(@Param("id") Long id);
}
