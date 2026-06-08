package com.social.memory.service.api.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class MemoryVO {

    private Long id;

    private String userId;

    private String content;

    private String sessionId;

    private String role;

    private LocalDateTime createdAt;
}
