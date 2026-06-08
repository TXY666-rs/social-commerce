package com.social.orderservice.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.TimeUnit;

/**
 * 订单ID生成器
 * 格式: order + 8位日期 + 5位流水号
 * 示例: order2026052800001
 *
 * 使用 Redis INCR 保证并发安全，每日流水号自动重置
 */
@Slf4j
@Component
public class OrderIdGenerator {

    private static final String PREFIX = "order";
    private static final String REDIS_KEY_PREFIX = "order:seq:";
    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final int SEQ_LENGTH = 5;
    private static final long SEQ_EXPIRE_DAYS = 2;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    /**
     * 生成订单ID
     * @return 订单ID，格式: order2026052800001
     */
    public String generate() {
        String date = LocalDate.now().format(DATE_FORMAT);
        String redisKey = REDIS_KEY_PREFIX + date;

        // 使用 Redis INCR 原子递增，保证并发安全
        Long seq = stringRedisTemplate.opsForValue().increment(redisKey);

        // 设置 key 过期时间（首次创建时设置）
        if (seq != null && seq == 1) {
            stringRedisTemplate.expire(redisKey, SEQ_EXPIRE_DAYS, TimeUnit.DAYS);
        }

        // 格式化流水号为固定长度，补零
        String seqStr = String.format("%0" + SEQ_LENGTH + "d", seq);

        String orderId = PREFIX + date + seqStr;
        log.debug("生成订单ID: {}", orderId);
        return orderId;
    }
}
