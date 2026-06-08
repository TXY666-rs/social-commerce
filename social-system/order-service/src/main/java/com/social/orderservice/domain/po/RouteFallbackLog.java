package com.social.orderservice.domain.po;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 路由降级日志实体
 * 记录 AI Agent 路由未命中时的降级情况
 */
@Data
@TableName("route_fallback_log")
public class RouteFallbackLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 原始用户消息 */
    private String message;

    /** 关键词命中的领域（NULL=未命中） */
    private String keywordResult;

    /** 关键词最高分 */
    private Integer keywordScore;

    /** LLM 返回的领域（NULL=失败） */
    private String llmResult;

    /** LLM 错误信息 */
    private String llmError;

    /** 用户选择的领域（回填） */
    private String userChoice;

    /** 创建时间 */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
