package com.social.memoryservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.memoryservice.domain.po.ChatHistory;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ChatHistoryMapper extends BaseMapper<ChatHistory> {
}
