package com.social.memoryservice.controller;

import com.social.memory.service.api.dto.*;
import com.social.memoryservice.service.MemoryService;
import com.social.socialcommon.result.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/memory")
public class MemoryController {

    @Autowired
    private MemoryService memoryService;

    /**
     * 保存对话记录
     */
    @PostMapping("/save")
    public Result<MemorySaveResult> saveMemory(@Valid @RequestBody MemorySaveDTO saveDTO) {
        return memoryService.saveMemory(saveDTO);
    }

    /**
     * 批量保存
     */
    @PostMapping("/batch_save")
    public Result<List<MemorySaveResult>> batchSaveMemory(@Valid @RequestBody List<MemorySaveDTO> saveDTOList) {
        if (saveDTOList.size() > 20) {
            return Result.error("批量保存最多支持20条");
        }
        return memoryService.batchSaveMemory(saveDTOList);
    }

    /**
     * 关键词搜索历史
     */
    @GetMapping("/keyword")
    public Result<List<MemoryVO>> searchByKeyword(
            @RequestParam("userId") String userId,
            @RequestParam("keyword") String keyword,
            @RequestParam(value = "limit", defaultValue = "10") Integer limit) {
        return memoryService.searchByKeyword(userId, keyword, limit);
    }

    /**
     * 查询用户最近的历史记录
     */
    @GetMapping("/recent/{userId}")
    public Result<List<MemoryVO>> getRecentHistory(
            @PathVariable("userId") String userId,
            @RequestParam(value = "limit", defaultValue = "20") Integer limit) {
        return memoryService.getRecentHistory(userId, limit);
    }

    /**
     * 查询指定会话的历史
     */
    @GetMapping("/session/{sessionId}")
    public Result<List<MemoryVO>> getSessionHistory(@PathVariable("sessionId") String sessionId) {
        return memoryService.getSessionHistory(sessionId);
    }

    /**
     * 健康检查
     */
    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("Memory service is running");
    }
}
