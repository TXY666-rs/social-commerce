package com.social.memory.service.api.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class MemorySaveDTO {

    @NotBlank(message = "用户ID不能为空")
    private String userId;

    @NotBlank(message = "内容不能为空")
    private String content;

    /**
     * 角色：user / assistant
     */
    private String role = "user";

    /**
     * 会话ID
     */
    private String sessionId;
}
