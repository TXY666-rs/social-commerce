package com.social.orderservice.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.social.orderservice.domain.dto.OrderCreateDTO;
import com.social.orderservice.domain.dto.OrderQueryDTO;
import com.social.orderservice.domain.vo.OrderToolVO;
import com.social.orderservice.domain.vo.OrderVO;
import com.social.orderservice.service.OrderService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/order")
public class UserOrderController {

    @Autowired
    private OrderService orderService;

    /**
     * 查询订单，（tool）
     */
    @GetMapping("/tool/query")
    public Result<List<OrderToolVO>> getOrders(OrderQueryDTO orderQueryDTO) {
        if (orderQueryDTO.getUser_id().isEmpty())
            return Result.error("userId不能为空");
        try {
            List<OrderToolVO> orderToolVOList= orderService.getOrders(orderQueryDTO);
            return Result.success(orderToolVOList);
        }catch (Exception e){
            log.error("订单查询失败", e);
            return Result.error(e.getMessage());
        }
    }


    @PostMapping("/create")
    public Result<OrderVO> createOrder(
            @Valid @RequestBody OrderCreateDTO createDTO,
            HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            OrderVO order = orderService.createOrder(userId, createDTO);
            return Result.success("下单成功", order);
        } catch (Exception e) {
            log.error("创建订单失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<OrderVO> getOrderDetail(@PathVariable String id) {
        try {
            OrderVO order = orderService.getOrderDetail(id);
            return Result.success(order);
        } catch (Exception e) {
            log.error("获取订单详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/my")
    public Result<IPage<OrderVO>> getMyOrders(OrderQueryDTO queryDTO, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            IPage<OrderVO> page = orderService.getUserOrders(userId, queryDTO);
            return Result.success("查询成功", page);
        } catch (Exception e) {
            log.error("查询订单列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/cancel/{id}")
    public Result<Boolean> cancelOrder(@PathVariable String id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean cancelled = orderService.cancelOrder(id, userId);
            if (cancelled) {
                return Result.success("取消成功", true);
            } else {
                return Result.error("取消失败");
            }
        } catch (Exception e) {
            log.error("取消订单失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/pay/{id}")
    public Result<Boolean> payOrder(@PathVariable String id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean paid = orderService.payOrder(id, userId);
            if (paid) {
                return Result.success("支付成功", true);
            } else {
                return Result.error("支付失败");
            }
        } catch (Exception e) {
            log.error("支付订单失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/complete/{id}")
    public Result<Boolean> completeOrder(@PathVariable String id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean completed = orderService.completeOrder(id, userId);
            if (completed) {
                return Result.success("确认收货成功", true);
            } else {
                return Result.error("操作失败");
            }
        } catch (Exception e) {
            log.error("确认收货失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/{id}/remind")
    public Result<Boolean> remindDelivery(@PathVariable String id, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            boolean reminded = orderService.remindDelivery(id, userId);
            if (reminded) {
                return Result.success("已催促物流配送", true);
            } else {
                return Result.error("催单失败");
            }
        } catch (Exception e) {
            log.error("催单失败", e);
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/{id}/address")
    public Result<Boolean> updateOrderAddress(
            @PathVariable String id,
            @RequestBody Map<String, String> body,
            HttpServletRequest request) {
        try {
            Long userId = getUserIdFromRequest(request);
            String newAddress = body.get("address");
            if (newAddress == null || newAddress.isBlank()) {
                return Result.error("地址不能为空");
            }
            boolean updated = orderService.updateOrderAddress(id, userId, newAddress);
            if (updated) {
                return Result.success("收货地址修改成功", true);
            } else {
                return Result.error("修改地址失败");
            }
        } catch (Exception e) {
            log.error("修改收货地址失败", e);
            return Result.error(e.getMessage());
        }
    }

    private Long getUserIdFromRequest(HttpServletRequest request) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null || userIdStr.isEmpty()) {
            throw new RuntimeException("未提供有效令牌");
        }
        return Long.valueOf(userIdStr);
    }
}
