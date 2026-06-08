package com.social.orderservice.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.social.orderservice.domain.po.Complaint;
import com.social.orderservice.domain.po.Order;
import com.social.orderservice.domain.po.Refund;
import com.social.orderservice.mapper.ComplaintMapper;
import com.social.orderservice.mapper.OrderMapper;
import com.social.orderservice.mapper.RefundMapper;
import com.social.orderservice.service.OrderService;
import com.social.socialcommon.result.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 售后控制器 — 退款 / 退货 / 投诉
 *
 * 订单状态流转：
 *  已支付(1) → [申请退款] → 退款中(5) → [审核通过] → 已退款(6) + 恢复库存/退券
 *  已支付(1) → [申请退货] → 退款中(5)
 */
@Slf4j
@RestController
public class AfterSaleController {

    @Autowired
    private RefundMapper refundMapper;

    @Autowired
    private ComplaintMapper complaintMapper;

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderService orderService;

    // ==================== 退款 ====================

    @PostMapping("/refund")
    @Transactional
    public Result<Map<String, Object>> requestRefund(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            String orderId = toString(body.get("orderId"));
            String reason = (String) body.getOrDefault("reason", "");

            Order order = orderMapper.selectById(orderId);
            if (order == null) return Result.error("订单不存在");
            if (!order.getUserId().equals(userId)) return Result.error("无权操作该订单");
            if (order.getStatus() != 0 && order.getStatus() != 1)
                return Result.error("仅待支付/已付款的订单可退款");

            // 订单状态 → 退款中
            order.setStatus(5);
            order.setUpdateTime(LocalDateTime.now());
            orderMapper.updateById(order);

            // 创建退款记录
            Refund refund = new Refund();
            refund.setUserId(userId);
            refund.setOrderId(orderId);
            refund.setType(0);
            refund.setReason(reason);
            refund.setAmount(order.getTotalPrice());
            refund.setStatus(0);  // 待审核
            refundMapper.insert(refund);

            log.info("退款申请: refundId={}, orderId={}, userId={}", refund.getId(), orderId, userId);
            return Result.success("退款申请已提交", Map.of("id", refund.getId()));
        } catch (Exception e) {
            log.error("退款申请失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/refund/{id}")
    public Result<Map<String, Object>> checkRefundStatus(@PathVariable Long id) {
        try {
            Refund refund = refundMapper.selectById(id);
            if (refund == null) return Result.error("退款单不存在");

            String[] refundStatusMap = {"待审核", "审核通过", "退款中", "已退款", "已拒绝", "已取消"};
            String refundStatusDesc = refundStatusMap[Math.min(refund.getStatus(), refundStatusMap.length - 1)];

            Order order = orderMapper.selectById(refund.getOrderId());
            String orderStatus = order != null ? getOrderStatusDesc(order.getStatus()) : "未知";

            return Result.success(Map.of(
                    "id", refund.getId(),
                    "orderId", refund.getOrderId(),
                    "orderStatus", orderStatus,
                    "amount", refund.getAmount(),
                    "status", refund.getStatus(),
                    "statusDesc", refundStatusDesc,
                    "remark", refund.getRemark() != null ? refund.getRemark() : ""
            ));
        } catch (Exception e) {
            log.error("查询退款进度失败", e);
            return Result.error(e.getMessage());
        }
    }

    /** 审核通过退款（模拟后台审核），恢复库存 + 退券 */
    @PutMapping("/refund/{id}/approve")
    @Transactional
    public Result<Map<String, Object>> approveRefund(@PathVariable Long id) {
        try {
            Refund refund = refundMapper.selectById(id);
            if (refund == null) return Result.error("退款单不存在");
            if (refund.getStatus() != 0) return Result.error("仅待审核状态可审核");

            Order order = orderMapper.selectById(refund.getOrderId());
            if (order == null) return Result.error("关联订单不存在");

            // 订单状态 → 已退款
            order.setStatus(6);
            order.setUpdateTime(LocalDateTime.now());
            orderMapper.updateById(order);

            // 执行恢复库存 + 退券（复用 cancelOrder 逻辑）
            orderService.processRefund(order);

            // 退款单状态 → 已退款
            refund.setStatus(3);
            refundMapper.updateById(refund);

            log.info("退款审核通过: refundId={}, orderId={}, amount={}", id, refund.getOrderId(), refund.getAmount());
            return Result.success("退款审核通过，已退款", Map.of(
                    "id", refund.getId(),
                    "orderId", refund.getOrderId(),
                    "amount", refund.getAmount()
            ));
        } catch (Exception e) {
            log.error("退款审核失败", e);
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/refund/{id}")
    @Transactional
    public Result<Boolean> cancelRefund(@PathVariable Long id, HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            Refund refund = refundMapper.selectById(id);
            if (refund == null) return Result.error("退款单不存在");
            if (!refund.getUserId().equals(userId)) return Result.error("无权操作该退款单");
            if (refund.getStatus() != 0 && refund.getStatus() != 1)
                return Result.error("仅待审核/审核通过的退款单可取消");

            Order order = orderMapper.selectById(refund.getOrderId());
            if (order != null && order.getStatus() == 5) {
                // 恢复订单状态为已支付
                order.setStatus(1);
                order.setUpdateTime(LocalDateTime.now());
                orderMapper.updateById(order);
            }

            refund.setStatus(5);  // 已取消
            refundMapper.updateById(refund);

            log.info("取消退款: refundId={}, orderId={}, userId={}", id, refund.getOrderId(), userId);
            return Result.success("退款申请已取消", true);
        } catch (Exception e) {
            log.error("取消退款失败", e);
            return Result.error(e.getMessage());
        }
    }

    /** 按订单ID查询退款记录（AI Agent 用） */
    @GetMapping("/refund/order/{orderId}")
    public Result<Map<String, Object>> getRefundByOrder(@PathVariable String orderId, HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            Refund refund = refundMapper.selectOne(
                    new LambdaQueryWrapper<Refund>()
                            .eq(Refund::getOrderId, orderId)
                            .eq(Refund::getUserId, userId)
                            .eq(Refund::getIsDeleted, 0)
                            .orderByDesc(Refund::getCreateTime)
                            .last("LIMIT 1")
            );
            if (refund == null) return Result.error("该订单无退款记录");

            String[] refundStatusMap = {"待审核", "审核通过", "退款中", "已退款", "已拒绝", "已取消"};
            String statusDesc = refundStatusMap[Math.min(refund.getStatus(), refundStatusMap.length - 1)];

            return Result.success(Map.of(
                    "id", refund.getId(),
                    "orderId", refund.getOrderId(),
                    "amount", refund.getAmount(),
                    "status", refund.getStatus(),
                    "statusDesc", statusDesc,
                    "reason", refund.getReason() != null ? refund.getReason() : "",
                    "remark", refund.getRemark() != null ? refund.getRemark() : ""
            ));
        } catch (Exception e) {
            log.error("按订单查询退款失败", e);
            return Result.error(e.getMessage());
        }
    }

    /** 按订单ID取消退款（AI Agent 用） */
    @DeleteMapping("/refund/order/{orderId}")
    @Transactional
    public Result<Boolean> cancelRefundByOrder(@PathVariable String orderId, HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            Refund refund = refundMapper.selectOne(
                    new LambdaQueryWrapper<Refund>()
                            .eq(Refund::getOrderId, orderId)
                            .eq(Refund::getUserId, userId)
                            .in(Refund::getStatus, 0, 1)  // 仅待审核/审核通过可取消
                            .eq(Refund::getIsDeleted, 0)
                            .last("LIMIT 1")
            );
            if (refund == null) return Result.error("未找到可取消的退款记录");

            // 恢复订单状态
            Order order = orderMapper.selectById(refund.getOrderId());
            if (order != null && order.getStatus() == 5) {
                order.setStatus(1);
                order.setUpdateTime(LocalDateTime.now());
                orderMapper.updateById(order);
            }

            refund.setStatus(5);  // 已取消
            refundMapper.updateById(refund);

            log.info("按订单取消退款: refundId={}, orderId={}, userId={}", refund.getId(), orderId, userId);
            return Result.success("退款申请已取消", true);
        } catch (Exception e) {
            log.error("按订单取消退款失败", e);
            return Result.error(e.getMessage());
        }
    }

    // ==================== 退货 ====================

    @PostMapping("/return")
    @Transactional
    public Result<Map<String, Object>> requestReturn(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            String orderId = toString(body.get("orderId"));
            String reason = (String) body.getOrDefault("reason", "");
            String returnType = (String) body.getOrDefault("type", "refund");
            int type = "exchange".equals(returnType) ? 2 : 1;

            Order order = orderMapper.selectById(orderId);
            if (order == null) return Result.error("订单不存在");
            if (!order.getUserId().equals(userId)) return Result.error("无权操作该订单");
            if (order.getStatus() != 1 && order.getStatus() != 2)
                return Result.error("仅已付款/已发货的订单可申请退货");

            // 退货退款 → 退款中，换货不改变状态
            if (type == 1) {
                order.setStatus(5);
                order.setUpdateTime(LocalDateTime.now());
                orderMapper.updateById(order);
            }

            Refund refund = new Refund();
            refund.setUserId(userId);
            refund.setOrderId(orderId);
            refund.setType(type);
            refund.setReason(reason);
            refund.setAmount(order.getTotalPrice());
            refund.setStatus(0);
            refundMapper.insert(refund);

            String typeDesc = type == 2 ? "换货" : "退货退款";
            log.info("{}申请: refundId={}, orderId={}, userId={}", typeDesc, refund.getId(), orderId, userId);
            return Result.success(typeDesc + "申请已提交", Map.of("id", refund.getId()));
        } catch (Exception e) {
            log.error("退货申请失败", e);
            return Result.error(e.getMessage());
        }
    }

    // ==================== 投诉 ====================

    @PostMapping("/complaint")
    public Result<Map<String, Object>> submitComplaint(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request) {
        try {
            Long userId = getUserId(request);
            String orderId = toString(body.get("orderId"));
            String detail = (String) body.getOrDefault("detail", "");
            String complaintType = (String) body.getOrDefault("type", "service");

            Complaint complaint = new Complaint();
            complaint.setUserId(userId);
            complaint.setOrderId(orderId);
            complaint.setType(complaintType);
            complaint.setDetail(detail);
            complaint.setStatus(0);
            complaintMapper.insert(complaint);

            log.info("投诉登记: complaintId={}, orderId={}, userId={}, type={}",
                    complaint.getId(), orderId, userId, complaintType);
            return Result.success("投诉已登记，人工客服将尽快联系", Map.of("id", complaint.getId()));
        } catch (Exception e) {
            log.error("投诉提交失败", e);
            return Result.error(e.getMessage());
        }
    }

    // ==================== 工具方法 ====================

    private Long getUserId(HttpServletRequest request) {
        String userIdStr = request.getHeader("X-User-Id");
        if (userIdStr == null || userIdStr.isEmpty()) {
            throw new RuntimeException("未提供有效令牌");
        }
        return Long.valueOf(userIdStr);
    }

    private String toString(Object obj) {
        if (obj == null) throw new IllegalArgumentException("orderId 不能为空");
        return obj.toString();
    }

    private static String getOrderStatusDesc(Integer status) {
        return switch (status != null ? status : -1) {
            case 0 -> "待支付";
            case 1 -> "已支付";
            case 2 -> "已发货";
            case 3 -> "已完成";
            case 4 -> "已取消";
            case 5 -> "退款中";
            case 6 -> "已退款";
            default -> "未知";
        };
    }
}
