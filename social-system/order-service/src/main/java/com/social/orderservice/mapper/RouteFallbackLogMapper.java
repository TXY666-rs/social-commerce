package com.social.orderservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.orderservice.domain.po.RouteFallbackLog;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

/**
 * 路由降级日志 Mapper
 */
@Mapper
public interface RouteFallbackLogMapper extends BaseMapper<RouteFallbackLog> {

    /**
     * 统计用户选择分布
     */
    @Select("SELECT user_choice, COUNT(*) as count FROM route_fallback_log " +
            "WHERE created_at >= NOW() - INTERVAL '30 days' " +
            "GROUP BY user_choice ORDER BY count DESC")
    List<Map<String, Object>> getUserChoiceDistribution();

    /**
     * 统计今日降级次数
     */
    @Select("SELECT COUNT(*) FROM route_fallback_log WHERE created_at >= CURRENT_DATE")
    int countToday();
}
