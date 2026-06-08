package com.social.orderservice.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.coupon.service.api.feign.CouponClient;
import com.social.orderservice.domain.dto.DeliverOrderDTO;
import com.social.orderservice.domain.dto.OrderCreateDTO;
import com.social.orderservice.domain.dto.OrderQueryDTO;
import com.social.orderservice.domain.po.Order;
import com.social.orderservice.domain.vo.OrderToolVO;
import com.social.orderservice.domain.vo.OrderVO;
import com.social.orderservice.mapper.OrderMapper;
import com.social.orderservice.service.OrderService;
import com.social.orderservice.util.OrderIdGenerator;
import com.social.product.service.api.dto.ProductBriefDTO;
import com.social.product.service.api.feign.ProductClient;
import com.social.socialcommon.result.Result;
import com.social.user.service.api.dto.UserBriefDTO;
import com.social.user.service.api.feign.UserClient;
import com.alibaba.fastjson2.JSON;
import com.social.orderservice.domain.po.OrderRedisKey;
import com.social.socialcommon.utils.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class OrderServiceImpl implements OrderService {

    private static final Map<Integer, String> STATUS_DESC = Map.of(
            0, "待支付", 1, "已支付", 2, "已发货", 3, "已完成", 4, "已取消",
            5, "退款中", 6, "已退款"
    );

    @Autowired
    private ProductClient productClient;

    @Autowired
    private UserClient userClient;

    @Autowired
    private CouponClient couponClient;

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private RedisUtil redisUtil;

    @Autowired
    private OrderIdGenerator orderIdGenerator;

    // ==================== 业务方法 ====================

    @Override
    @Transactional
    public OrderVO createOrder(Long userId, OrderCreateDTO createDTO) {
        ProductBriefDTO product = getProductBrief(createDTO.getProductId());
        if (product.getStatus() != 1) {
            throw new RuntimeException("商品已下架");
        }
        if (product.getStock() < createDTO.getQuantity()) {
            throw new RuntimeException("库存不足");
        }
        if (product.getSellerId().equals(userId)) {
            throw new RuntimeException("不能购买自己的商品");
        }

        Result<Boolean> decreaseResult = productClient.decreaseStock(createDTO.getProductId(), createDTO.getQuantity());
        if (decreaseResult.getData() == null || !decreaseResult.getData()) {
            throw new RuntimeException(decreaseResult.getMessage() != null ? decreaseResult.getMessage() : "库存扣减失败");
        }

        // 计算原价
        BigDecimal originalPrice = product.getPrice().multiply(BigDecimal.valueOf(createDTO.getQuantity()));
        BigDecimal discountAmount = BigDecimal.ZERO;

        // 如果传了优惠券，计算折扣
        if (createDTO.getUserCouponId() != null && createDTO.getUserCouponId() > 0) {
            Result<BigDecimal> discountResult = couponClient.calculateDiscount(userId, createDTO.getUserCouponId(), originalPrice);
            if (discountResult.getData() != null && discountResult.getData().compareTo(BigDecimal.ZERO) > 0) {
                discountAmount = discountResult.getData();
            } else {
                log.warn("优惠券计算返回折扣为0或失败: {}", discountResult.getMessage());
            }
        }

        Order order = BeanUtil.copyProperties(createDTO, Order.class);
        order.setId(orderIdGenerator.generate());
        order.setUserId(userId);
        order.setSellerId(product.getSellerId());
        order.setOriginalPrice(originalPrice);
        order.setDiscountAmount(discountAmount);
        order.setTotalPrice(originalPrice.subtract(discountAmount));
        if (createDTO.getUserCouponId() != null && createDTO.getUserCouponId() > 0) {
            order.setUserCouponId(createDTO.getUserCouponId());
        }
        order.setStatus(0); // 待支付
        order.setCreateTime(LocalDateTime.now());
        order.setUpdateTime(LocalDateTime.now());
        order.setIsDeleted(0);
        orderMapper.insert(order);
        log.info("订单创建成功，订单ID: {}, 用户: {}, 总价: {}",
                order.getId(), userId, order.getTotalPrice());
        return convertToOrderVO(order);
    }

    @Override
    public OrderVO getOrderDetail(String orderId) {
        String cacheKey = OrderRedisKey.ORDER_DETAIL + orderId;
        String cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return JSON.parseObject(cached, OrderVO.class);
        }

        String lockKey = OrderRedisKey.ORDER_DETAIL_LOCK + orderId;
        if (redisUtil.tryLock(lockKey, 10, TimeUnit.SECONDS)) {
            try {
                // double-check
                cached = redisUtil.get(cacheKey);
                if (cached != null) {
                    return JSON.parseObject(cached, OrderVO.class);
                }
                OrderVO vo = convertToOrderVO(getOrderOrThrow(orderId));
                redisUtil.set(cacheKey, JSON.toJSONString(vo), OrderRedisKey.DETAIL_TTL, TimeUnit.MINUTES);
                return vo;
            } finally {
                redisUtil.delete(lockKey);
            }
        }
        return convertToOrderVO(getOrderOrThrow(orderId));
    }

    @Override
    public IPage<OrderVO> getUserOrders(Long userId, OrderQueryDTO queryDTO) {
        return queryOrderPage(queryDTO,
                () -> orderMapper.selectUserOrderPage(buildPage(queryDTO), userId, parseStatus(queryDTO)));
    }


    @Override
    @Transactional
    public boolean cancelOrder(String orderId, Long userId) {
        Order order = getOrderOrThrow(orderId);
        checkBuyerPermission(order, userId);
        checkCancellable(order);
        return doCancelOrder(order, orderId);
    }

    @Override
    @Transactional
    public boolean sellerCancelOrder(String orderId, Long userId) {
        Order order = getOrderOrThrow(orderId);
        checkSellerPermission(order, userId);
        checkCancellable(order);
        return doCancelOrder(order, orderId);
    }

    @Override
    @Transactional
    public boolean payOrder(String orderId, Long userId) {
        Order order = getOrderOrThrow(orderId);
        checkBuyerPermission(order, userId);
        if (order.getStatus() != 0) {
            throw new RuntimeException("订单状态不正确");
        }
        // 延迟双删：先删缓存
        evictOrderCache(orderId);
        order.setStatus(1);
        order.setPayTime(LocalDateTime.now());
        int rows = orderMapper.updateById(order);
        if (rows > 0 && order.getUserCouponId() != null && order.getUserCouponId() > 0) {
            try {
                couponClient.useCoupon(userId, order.getUserCouponId());
                log.info("优惠券核销成功, orderId={}, userCouponId={}", orderId, order.getUserCouponId());
            } catch (Exception e) {
                log.error("优惠券核销失败, orderId={}, userCouponId={}", orderId, order.getUserCouponId(), e);
            }
        }
        return rows > 0;
    }

    @Override
    @Transactional
    public boolean deliverOrder(String orderId, Long userId, DeliverOrderDTO deliverDTO) {
        Order order = getOrderOrThrow(orderId);
        checkSellerPermission(order, userId);
        if (order.getStatus() != 1) {
            throw new RuntimeException("订单状态不正确");
        }
        // 延迟双删：先删缓存
        evictOrderCache(orderId);
        order.setStatus(2);
        order.setDeliveryTime(LocalDateTime.now());
        order.setTrackingNumber(deliverDTO.getTrackingNumber());
        order.setDeliveryRemark(deliverDTO.getDeliveryRemark());
        return orderMapper.updateById(order) > 0;
    }

    @Override
    @Transactional
    public boolean completeOrder(String orderId, Long userId) {
        Order order = getOrderOrThrow(orderId);
        checkBuyerPermission(order, userId);
        if (order.getStatus() != 2) {
            throw new RuntimeException("订单状态不正确");
        }
        // 延迟双删：先删缓存
        evictOrderCache(orderId);
        order.setStatus(3);
        order.setCompleteTime(LocalDateTime.now());
        return orderMapper.updateById(order) > 0;
    }

    /**
     * 催促物流配送 — 仅校验订单归属和状态，记录催单日志
     */
    @Override
    public boolean remindDelivery(String orderId, Long userId) {
        Order order = getOrderOrThrow(orderId);
        checkBuyerPermission(order, userId);
        if (order.getStatus() != 2) {
            throw new RuntimeException("订单不是已发货状态，无法催单");
        }
        log.info("用户催单: orderId={}, userId={}, trackingNumber={}", orderId, userId, order.getTrackingNumber());
        return true;
    }

    /**
     * 修改订单收货地址 — 仅待支付/已支付/已发货状态可修改
     */
    @Override
    public boolean updateOrderAddress(String orderId, Long userId, String newAddress) {
        Order order = getOrderOrThrow(orderId);
        checkBuyerPermission(order, userId);
        if (order.getStatus() > 2) {
            throw new RuntimeException("订单已完成或已取消，无法修改地址");
        }
        order.setReceiverAddress(newAddress);
        order.setUpdateTime(LocalDateTime.now());
        return orderMapper.updateById(order) > 0;
    }

    /**
     * 退款审核通过后的资源回收：恢复库存 + 退还优惠券
     */
    @Override
    public void processRefund(Order order) {
        productClient.increaseStock(order.getProductId(), order.getQuantity());
        log.info("退款恢复库存: orderId={}, productId={}, quantity={}",
                order.getId(), order.getProductId(), order.getQuantity());

        if (order.getUserCouponId() != null && order.getUserCouponId() > 0) {
            try {
                couponClient.restoreCoupon(order.getUserId(), order.getUserCouponId());
                log.info("退款退券成功: orderId={}, userCouponId={}", order.getId(), order.getUserCouponId());
            } catch (Exception e) {
                log.error("退款退券失败: orderId={}, userCouponId={}", order.getId(), order.getUserCouponId(), e);
            }
        }
    }

    @Override
    public List<OrderToolVO> getOrders(OrderQueryDTO orderQueryDTO) {
        List<OrderVO> orderVOList = orderMapper.selectByUserId(Long.parseLong(orderQueryDTO.getUser_id()));
        List<Long> productIds = orderVOList.stream().map(OrderVO::getProductId).toList();
        Map<Long, ProductBriefDTO> productMap = batchGetProductBriefMap(productIds);

        return orderVOList.stream().map(orderVO -> {
            OrderToolVO toolVO = new OrderToolVO();
            BeanUtil.copyProperties(orderVO, toolVO);
            ProductBriefDTO product = productMap.get(toolVO.getProductId());
            if (product != null) {
                toolVO.setProductName(product.getName());
            }
            return toolVO;
        }).toList();
    }

    // ==================== 私有辅助方法 ====================

    /**
     * 查询订单，不存在则抛异常
     */
    private Order getOrderOrThrow(String orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new RuntimeException("订单不存在");
        }
        return order;
    }

    /**
     * 获取商品简要信息，不存在则抛异常
     */
    private ProductBriefDTO getProductBrief(Long productId) {
        Result<List<ProductBriefDTO>> result = productClient.getProductBrief(List.of(productId));
        if (result == null || result.getData() == null || result.getData().isEmpty()) {
            throw new RuntimeException("商品不存在");
        }
        ProductBriefDTO product = result.getData().get(0);
        if (product == null) throw new RuntimeException("商品不存在");
        return product;
    }

    /**
     * 批量获取商品信息，返回 productId -> ProductBriefDTO 映射
     */
    private Map<Long, ProductBriefDTO> batchGetProductBriefMap(List<Long> productIds) {
        if (productIds == null || productIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return productClient.getProductBrief(productIds).getData().stream()
                .collect(Collectors.toMap(ProductBriefDTO::getId, p -> p));
    }

    /**
     * 校验买家权限
     */
    private void checkBuyerPermission(Order order, Long userId) {
        if (!order.getUserId().equals(userId)) {
            throw new RuntimeException("无权操作该订单");
        }
    }

    /**
     * 校验卖家权限（sellerId 为空时回退到商品服务查询）
     */
    private void checkSellerPermission(Order order, Long userId) {
        if (order.getSellerId() == null) {
            Result<List<ProductBriefDTO>> result = productClient.getProductBrief(List.of(order.getProductId()));
            if (result == null || result.getData() == null || result.getData().isEmpty()) {
                throw new RuntimeException("商品不存在");
            }
            ProductBriefDTO product = result.getData().get(0);
            if (product == null || !product.getSellerId().equals(userId)) {
                throw new RuntimeException("无权操作该订单");
            }
        } else if (!order.getSellerId().equals(userId)) {
            throw new RuntimeException("无权操作该订单");
        }
    }

    /**
     * 校验订单是否可取消
     */
    private void checkCancellable(Order order) {
        if (order.getStatus() != 0 && order.getStatus() != 1) {
            throw new RuntimeException("当前订单状态不可取消");
        }
    }

    /**
     * 延迟双删：立即删除 + 延迟 500ms 再删一次
     */
    private void evictOrderCache(String orderId) {
        String key = OrderRedisKey.ORDER_DETAIL + orderId;
        redisUtil.delete(key);
        redisUtil.deleteAsync(key, 500);
    }

    /**
     * 执行取消订单的核心逻辑（恢复库存、退款、退券）
     */
    private boolean doCancelOrder(Order order, String orderId) {
        boolean needRefund = order.getStatus() == 1;
        // 延迟双删：先删缓存
        evictOrderCache(orderId);
        order.setStatus(4);
        int rows = orderMapper.updateById(order);

        if (rows > 0) {
            productClient.increaseStock(order.getProductId(), order.getQuantity());
            if (needRefund) {
                log.info("订单 {} 退款成功，退款金额: {}", orderId, order.getTotalPrice());
                // TODO: 对接真实支付平台退款接口
            }
            // 退券：将优惠券状态恢复为未使用
            if (order.getUserCouponId() != null && order.getUserCouponId() > 0) {
                try {
                    couponClient.restoreCoupon(order.getUserId(), order.getUserCouponId());
                    log.info("优惠券退回成功, orderId={}, userCouponId={}", orderId, order.getUserCouponId());
                } catch (Exception e) {
                    log.error("优惠券退回失败, orderId={}, userCouponId={}", orderId, order.getUserCouponId(), e);
                }
            }
        }
        return rows > 0;
    }

    /**
     * 通用分页查询：查数据库 -> 批量填充商品和用户信息 -> 返回
     */
    private IPage<OrderVO> queryOrderPage(OrderQueryDTO queryDTO, PageQueryFunction queryFunction) {
        IPage<Order> orderPage = queryFunction.execute();
        List<Order> orders = orderPage.getRecords();

        List<Long> productIds = orders.stream().map(Order::getProductId).filter(Objects::nonNull).distinct().toList();
        List<Long> sellerIds = orders.stream().map(Order::getSellerId).filter(Objects::nonNull).distinct().toList();

        Map<Long, ProductBriefDTO> productMap = batchGetProductBriefMap(productIds);
        Map<Long, UserBriefDTO> userMap = batchGetUserBriefMap(sellerIds);

        List<OrderVO> voList = orders.stream()
                .map(order -> buildOrderVO(order, productMap, userMap))
                .toList();

        Page<OrderVO> resultPage = new Page<>(orderPage.getCurrent(), orderPage.getSize(), orderPage.getTotal());
        resultPage.setRecords(voList);
        return resultPage;
    }

    /**
     * 批量获取用户信息，返回 userId -> UserBriefDTO 映射
     */
    private Map<Long, UserBriefDTO> batchGetUserBriefMap(List<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        Result<Map<Long, UserBriefDTO>> result = userClient.batchGetUserBrief(userIds);
        if (result != null && result.getData() != null) {
            return result.getData();
        }
        return Collections.emptyMap();
    }

    /**
     * 从预加载的 Map 中构建 OrderVO（无额外 RPC 调用）
     */
    private OrderVO buildOrderVO(Order order, Map<Long, ProductBriefDTO> productMap, Map<Long, UserBriefDTO> userMap) {
        OrderVO vo = new OrderVO();
        BeanUtils.copyProperties(order, vo);
        vo.setStatusDesc(STATUS_DESC.getOrDefault(order.getStatus(), "未知"));

        ProductBriefDTO product = productMap.get(order.getProductId());
        if (product != null) {
            vo.setProductName(product.getName());
            vo.setProductImage(product.getImage());
            vo.setProductPrice(product.getPrice());
        }

        UserBriefDTO seller = userMap.get(order.getSellerId());
        if (seller != null) {
            vo.setSellerNickname(seller.getUsername());
        }

        return vo;
    }

    /**
     * 单个订单转 VO（用于创建、详情等单条场景）
     */
    private OrderVO convertToOrderVO(Order order) {
        OrderVO vo = new OrderVO();
        BeanUtils.copyProperties(order, vo);
        vo.setStatusDesc(STATUS_DESC.getOrDefault(order.getStatus(), "未知"));
        if (order.getProductId() != null) {
            Result<List<ProductBriefDTO>> result = productClient.getProductBrief(List.of(order.getProductId()));
            if (result != null && result.getData() != null && !result.getData().isEmpty()) {
                ProductBriefDTO product = result.getData().get(0);
                if (product != null) {
                    vo.setProductName(product.getName());
                    vo.setProductImage(product.getImage());
                    vo.setProductPrice(product.getPrice());
                }
            }
        }

        if (order.getSellerId() != null) {
            UserBriefDTO seller = userClient.getUserBrief(order.getSellerId()).getData();
            if (seller != null) {
                vo.setSellerNickname(seller.getUsername());
            }
        }

        return vo;
    }

    private Page<Order> buildPage(OrderQueryDTO queryDTO) {
        return new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
    }

    private Integer parseStatus(OrderQueryDTO queryDTO) {
        return queryDTO.getStatus() != null ? Integer.parseInt(queryDTO.getStatus()) : null;
    }

    @FunctionalInterface
    private interface PageQueryFunction {
        IPage<Order> execute();
    }
}
