package com.social.orderservice.domain.dto;

import lombok.Data;

/**
 * 路由降级日志请求 DTO
 */
@Data
public class RouteFallbackLogDTO {

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
}
