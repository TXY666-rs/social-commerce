package com.social.orderservice.mapper;


import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.orderservice.domain.po.Order;
import com.social.orderservice.domain.vo.OrderVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 订单Mapper接口
 */
@Mapper
public interface OrderMapper extends BaseMapper<Order> {

    /**
     * 分页查询用户订单
     */
    IPage<Order> selectUserOrderPage(Page<Order> page,
                                     @Param("userId") Long userId,
                                     @Param("status") Integer status);

    /**
     * 分页查询卖家订单
     */
    IPage<Order> selectSellerOrderPage(Page<Order> page,
                                        @Param("sellerId") Long sellerId,
                                        @Param("status") Integer status);

    List<OrderVO> selectByUserId(Long userId);
}
