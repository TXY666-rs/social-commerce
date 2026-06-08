package com.social.memoryservice.mapper;

import com.social.memoryservice.domain.po.ChatHistory;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface MemoryMapper {

    /**
     * 查询用户最近的对话历史
     */
    List<ChatHistory> getRecentHistory(
            @Param("userId") String userId,
            @Param("limit") Integer limit
    );

    /**
     * 查询指定会话的历史
     */
    List<ChatHistory> getSessionHistory(
            @Param("sessionId") String sessionId
    );

    /**
     * 关键词搜索历史记录
     */
    List<ChatHistory> searchByKeyword(
            @Param("userId") String userId,
            @Param("keyword") String keyword,
            @Param("limit") Integer limit
    );
}
