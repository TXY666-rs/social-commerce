package com.social.memoryservice.service;

import com.social.memory.service.api.dto.*;
import com.social.memory.service.api.feign.MemoryClient;
import com.social.memoryservice.domain.po.ChatHistory;
import com.social.memoryservice.mapper.ChatHistoryMapper;
import com.social.memoryservice.mapper.MemoryMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
public class MemoryService implements MemoryClient {

    @Autowired
    private MemoryMapper memoryMapper;

    @Autowired
    private ChatHistoryMapper chatHistoryMapper;

    @Override
    public com.social.socialcommon.result.Result<MemorySaveResult> saveMemory(MemorySaveDTO saveDTO) {
        try {
            ChatHistory record = new ChatHistory();
            record.setUserId(saveDTO.getUserId());
            record.setSessionId(saveDTO.getSessionId());
            record.setRole(saveDTO.getRole());
            record.setContent(saveDTO.getContent());
            chatHistoryMapper.insert(record);

            MemorySaveResult result = new MemorySaveResult();
            result.setMemoryId(record.getId());
            result.setSuccess(true);
            return com.social.socialcommon.result.Result.success("保存成功", result);
        } catch (Exception e) {
            log.error("Failed to save chat history", e);
            MemorySaveResult result = new MemorySaveResult();
            result.setSuccess(false);
            result.setErrorMessage(e.getMessage());
            return com.social.socialcommon.result.Result.error("保存失败: " + e.getMessage());
        }
    }

    @Override
    public com.social.socialcommon.result.Result<List<MemorySaveResult>> batchSaveMemory(List<MemorySaveDTO> saveDTOList) {
        List<MemorySaveResult> results = saveDTOList.stream()
                .map(dto -> saveMemory(dto).getData())
                .collect(Collectors.toList());
        return com.social.socialcommon.result.Result.success("批量保存完成", results);
    }

    @Override
    public com.social.socialcommon.result.Result<List<MemoryVO>> searchByKeyword(
            String userId, String keyword, Integer limit) {
        try {
            List<ChatHistory> records = memoryMapper.searchByKeyword(userId, keyword, limit);
            List<MemoryVO> voList = records.stream()
                    .map(this::convertToVO)
                    .collect(Collectors.toList());
            return com.social.socialcommon.result.Result.success("检索成功", voList);
        } catch (Exception e) {
            log.error("Failed to search by keyword", e);
            return com.social.socialcommon.result.Result.error("检索失败: " + e.getMessage());
        }
    }

    @Override
    public com.social.socialcommon.result.Result<List<MemoryVO>> getRecentHistory(String userId, Integer limit) {
        try {
            List<ChatHistory> records = memoryMapper.getRecentHistory(userId, limit);
            List<MemoryVO> voList = records.stream()
                    .map(this::convertToVO)
                    .collect(Collectors.toList());
            return com.social.socialcommon.result.Result.success("查询成功", voList);
        } catch (Exception e) {
            log.error("Failed to get recent history", e);
            return com.social.socialcommon.result.Result.error("查询失败: " + e.getMessage());
        }
    }

    @Override
    public com.social.socialcommon.result.Result<List<MemoryVO>> getSessionHistory(String sessionId) {
        try {
            List<ChatHistory> records = memoryMapper.getSessionHistory(sessionId);
            List<MemoryVO> voList = records.stream()
                    .map(this::convertToVO)
                    .collect(Collectors.toList());
            return com.social.socialcommon.result.Result.success("查询成功", voList);
        } catch (Exception e) {
            log.error("Failed to get session history", e);
            return com.social.socialcommon.result.Result.error("查询失败: " + e.getMessage());
        }
    }

    private MemoryVO convertToVO(ChatHistory record) {
        MemoryVO vo = new MemoryVO();
        vo.setId(record.getId());
        vo.setUserId(record.getUserId());
        vo.setContent(record.getContent());
        vo.setSessionId(record.getSessionId());
        vo.setRole(record.getRole());
        vo.setCreatedAt(record.getCreatedAt());
        return vo;
    }
}
