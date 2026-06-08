package com.social.orderservice.service.impl;

import com.social.orderservice.domain.dto.RouteFallbackLogDTO;
import com.social.orderservice.domain.po.RouteFallbackLog;
import com.social.orderservice.mapper.RouteFallbackLogMapper;
import com.social.orderservice.service.RouteFallbackLogService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class RouteFallbackLogServiceImpl implements RouteFallbackLogService {

    @Autowired
    private RouteFallbackLogMapper routeFallbackLogMapper;

    @Override
    public void saveLog(RouteFallbackLogDTO dto) {
        RouteFallbackLog entity = new RouteFallbackLog();
        entity.setMessage(dto.getMessage());
        entity.setKeywordResult(dto.getKeywordResult());
        entity.setKeywordScore(dto.getKeywordScore());
        entity.setLlmResult(dto.getLlmResult());
        entity.setLlmError(dto.getLlmError());
        entity.setUserChoice(dto.getUserChoice());
        routeFallbackLogMapper.insert(entity);
        log.info("路由降级日志已保存, id={}, message={}", entity.getId(),
                dto.getMessage() != null ? dto.getMessage().substring(0, Math.min(dto.getMessage().length(), 50)) : "");
    }

    @Override
    public void updateUserChoice(Long id, String userChoice) {
        RouteFallbackLog entity = routeFallbackLogMapper.selectById(id);
        if (entity != null) {
            entity.setUserChoice(userChoice);
            routeFallbackLogMapper.updateById(entity);
            log.info("路由降级日志已回填用户选择, id={}, choice={}", id, userChoice);
        }
    }

    @Override
    public int countToday() {
        return routeFallbackLogMapper.countToday();
    }

    @Override
    public List<Map<String, Object>> getUserChoiceDistribution() {
        return routeFallbackLogMapper.getUserChoiceDistribution();
    }
}
