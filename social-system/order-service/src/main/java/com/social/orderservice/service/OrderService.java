package com.social.orderservice.service;


import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.orderservice.domain.dto.DeliverOrderDTO;
import com.social.orderservice.domain.dto.OrderCreateDTO;
import com.social.orderservice.domain.dto.OrderQueryDTO;
import com.social.orderservice.domain.po.Order;
import com.social.orderservice.domain.vo.OrderToolVO;
import com.social.orderservice.domain.vo.OrderVO;

import java.util.List;

public interface OrderService {

    /**
     * 创建订单
     */
    OrderVO createOrder(Long userId, OrderCreateDTO createDTO);

    /**
     * 获取订单详情
     */
    OrderVO getOrderDetail(String orderId);

    /**
     * 获取用户订单列表
     */
    IPage<OrderVO> getUserOrders(Long userId, OrderQueryDTO queryDTO);


    /**
     * 买家取消订单（待支付/已支付未发货可取消，已支付时退款）
     */
    boolean cancelOrder(String orderId, Long userId);

    /**
     * 卖家取消订单（待支付/已支付未发货可取消，已支付时退款）
     */
    boolean sellerCancelOrder(String orderId, Long userId);

    /**
     * 支付订单
     */
    boolean payOrder(String orderId, Long userId);

    /**
     * 发货（卖家操作）
     */
    boolean deliverOrder(String orderId, Long sellerId, DeliverOrderDTO deliverDTO);

    /**
     * 确认收货
     */
    boolean completeOrder(String orderId, Long userId);

    /**
     * 催促物流配送
     */
    boolean remindDelivery(String orderId, Long userId);

    /**
     * 修改订单收货地址
     */
    boolean updateOrderAddress(String orderId, Long userId, String newAddress);

    /**
     * 退款审核通过后执行：恢复库存 + 退还优惠券
     */
    void processRefund(Order order);

    /**
     * AI Agent：查询订单
     */
    List<OrderToolVO> getOrders(OrderQueryDTO orderQueryDTO);
}
