package com.social.orderservice.controller;

import com.social.orderservice.domain.dto.RouteFallbackLogDTO;
import com.social.orderservice.service.RouteFallbackLogService;
import com.social.socialcommon.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 路由降级日志 Controller
 * 供 AI Agent 异步调用，记录路由降级情况
 */
@Slf4j
@RestController
@RequestMapping("/route-fallback")
public class RouteFallbackLogController {

    @Autowired
    private RouteFallbackLogService routeFallbackLogService;

    /**
     * 记录路由降级日志
     */
    @PostMapping("/log")
    public Result<Boolean> saveLog(@RequestBody RouteFallbackLogDTO dto) {
        try {
            routeFallbackLogService.saveLog(dto);
            return Result.success("保存成功", true);
        } catch (Exception e) {
            log.error("保存路由降级日志失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 回填用户选择
     */
    @PutMapping("/log/{id}/choice")
    public Result<Boolean> updateUserChoice(@PathVariable Long id, @RequestParam String userChoice) {
        try {
            routeFallbackLogService.updateUserChoice(id, userChoice);
            return Result.success("回填成功", true);
        } catch (Exception e) {
            log.error("回填用户选择失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取今日降级次数
     */
    @GetMapping("/stats/today")
    public Result<Integer> getTodayCount() {
        try {
            return Result.success(routeFallbackLogService.countToday());
        } catch (Exception e) {
            log.error("查询今日降级次数失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取用户选择分布（最近30天）
     */
    @GetMapping("/stats/distribution")
    public Result<List<Map<String, Object>>> getUserChoiceDistribution() {
        try {
            return Result.success(routeFallbackLogService.getUserChoiceDistribution());
        } catch (Exception e) {
            log.error("查询用户选择分布失败", e);
            return Result.error(e.getMessage());
        }
    }
}
