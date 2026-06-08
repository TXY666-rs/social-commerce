package com.social.memory.service.api.feign;

import com.social.memory.service.api.dto.*;
import com.social.socialcommon.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@FeignClient(name = "memory-service", path = "/api/memory")
public interface MemoryClient {

    /**
     * 保存对话记录
     */
    @PostMapping("/save")
    Result<MemorySaveResult> saveMemory(@RequestBody MemorySaveDTO saveDTO);

    /**
     * 批量保存
     */
    @PostMapping("/batch_save")
    Result<List<MemorySaveResult>> batchSaveMemory(@RequestBody List<MemorySaveDTO> saveDTOList);

    /**
     * 关键词搜索历史
     */
    @GetMapping("/keyword")
    Result<List<MemoryVO>> searchByKeyword(
            @RequestParam("userId") String userId,
            @RequestParam("keyword") String keyword,
            @RequestParam(value = "limit", defaultValue = "10") Integer limit);

    /**
     * 查询用户最近的历史记录
     */
    @GetMapping("/recent/{userId}")
    Result<List<MemoryVO>> getRecentHistory(
            @PathVariable("userId") String userId,
            @RequestParam(value = "limit", defaultValue = "20") Integer limit);

    /**
     * 查询指定会话的历史
     */
    @GetMapping("/session/{sessionId}")
    Result<List<MemoryVO>> getSessionHistory(@PathVariable("sessionId") String sessionId);
}
