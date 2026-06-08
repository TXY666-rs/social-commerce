package com.social.orderservice.service;

import com.social.orderservice.domain.dto.RouteFallbackLogDTO;

import java.util.List;
import java.util.Map;

/**
 * 路由降级日志 Service
 */
public interface RouteFallbackLogService {

    /**
     * 记录路由降级日志
     */
    void saveLog(RouteFallbackLogDTO dto);

    /**
     * 回填用户选择
     * @param id 日志 ID
     * @param userChoice 用户选择的领域
     */
    void updateUserChoice(Long id, String userChoice);

    /**
     * 统计今日降级次数
     */
    int countToday();

    /**
     * 获取用户选择分布（最近30天）
     */
    List<Map<String, Object>> getUserChoiceDistribution();
}
