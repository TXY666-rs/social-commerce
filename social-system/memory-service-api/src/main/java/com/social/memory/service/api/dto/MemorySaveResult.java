package com.social.memory.service.api.dto;

import lombok.Data;

@Data
public class MemorySaveResult {

    private Long memoryId;

    private Boolean success = true;

    private String errorMessage;
}
