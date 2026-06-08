package com.social.socialcommon.utils;


import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.lang.TypeReference;
import cn.hutool.json.JSONUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.metadata.IPage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;
import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Redis工具类
 * 支持字符串操作和JSON对象缓存
 */
@Slf4j
@Component
public class RedisUtil {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private static final ScheduledExecutorService SCHEDULER =
            Executors.newScheduledThreadPool(2, r -> {
                Thread t = new Thread(r, "redis-delay-delete");
                t.setDaemon(true);
                return t;
            });

    /**
     * 延迟删除缓存（用于延迟双删策略）
     * @param key 缓存 key
     * @param delayMs 延迟毫秒数（建议 500-1000ms）
     */
    public void deleteAsync(String key, long delayMs) {
        SCHEDULER.schedule(() -> {
            try {
                delete(key);
                log.debug("延迟删除缓存成功: {}", key);
            } catch (Exception e) {
                log.warn("延迟删除缓存失败: {}", key, e);
            }
        }, delayMs, TimeUnit.MILLISECONDS);
    }

    /**
     * 延迟按模式删除缓存（用于延迟双删策略）
     * @param pattern key 模式
     * @param delayMs 延迟毫秒数（建议 500-1000ms）
     */
    public void deleteByPatternAsync(String pattern, long delayMs) {
        SCHEDULER.schedule(() -> {
            try {
                deleteByPattern(pattern);
                log.debug("延迟按模式删除缓存成功: {}", pattern);
            } catch (Exception e) {
                log.warn("延迟按模式删除缓存失败: {}", pattern, e);
            }
        }, delayMs, TimeUnit.MILLISECONDS);
    }

    // ========== 通用操作 ==========

    /**
     * 设置过期时间
     */
    public Boolean expire(String key, long timeout, TimeUnit unit) {
        return stringRedisTemplate.expire(key, timeout, unit);
    }

    /**
     * 获取过期时间
     */
    public Long getExpire(String key, TimeUnit unit) {
        return stringRedisTemplate.getExpire(key, unit);
    }

    /**
     * 判断key是否存在
     */
    public Boolean hasKey(String key) {
        return stringRedisTemplate.hasKey(key);
    }

    /**
     * 删除缓存
     */
    public Boolean delete(String key) {
        return stringRedisTemplate.delete(key);
    }

    /**
     * 批量删除缓存
     */
    public Long delete(Collection<String> keys) {
        return stringRedisTemplate.delete(keys);
    }

    /**
     * 按模式删除缓存（使用 SCAN 替代 KEYS，避免阻塞 Redis）
     */
    public Long deleteByPattern(String pattern) {
        long deleted = 0;
        try {
            Cursor<byte[]> cursor = stringRedisTemplate.getConnectionFactory()
                .getConnection()
                .scan(ScanOptions.scanOptions()
                    .match(pattern)
                    .count(100)
                    .build());
            while (cursor.hasNext()) {
                byte[] key = cursor.next();
                stringRedisTemplate.delete(new String(key, StandardCharsets.UTF_8));
                deleted++;
            }
        } catch (Exception e) {
            log.error("deleteByPattern 失败: pattern={}, error={}", pattern, e.getMessage());
        }
        return deleted;
    }

    // ========== 字符串操作 ==========

    /**
     * 设置缓存
     */
    public void set(String key, String value) {
        stringRedisTemplate.opsForValue().set(key, value);
    }

    /**
     * 设置缓存并指定过期时间
     */
    public void set(String key, String value, long timeout, TimeUnit unit) {
        stringRedisTemplate.opsForValue().set(key, value, timeout, unit);
    }

    /**
     * 获取缓存
     */
    public String get(String key) {
        return stringRedisTemplate.opsForValue().get(key);
    }

    // ========== Hash操作 ==========


    /**
     * Hash获取
     */
    public <T> T hGet(String key, String hashKey, Class<T> clazz) {
        Object value = stringRedisTemplate.opsForHash().get(key, hashKey);
        if (value == null) {
            return null;
        }
        try {
            return JSON.parseObject(value.toString(), clazz);
        } catch (Exception e) {
            log.warn("Hash反序列化缓存失败, key={}, hashKey={}", key, hashKey);
            return null;
        }
    }

    /**
     * Hash删除
     */
    public Long hDelete(String key, String... hashKeys) {
        return stringRedisTemplate.opsForHash().delete(key, (Object[]) hashKeys);
    }

    // ========== Token操作 ==========

    /**
     * 存储token到Redis
     */
    public void storeToken(String userId, String token) {
        String key = "user:token:" + userId;
        set(key, token, 30, TimeUnit.MINUTES);
    }

    /**
     * 验证用户的token与传入的token是否一致
     */
    public boolean validateToken(String userId, String token) {
        String key = "user:token:" + userId;
        String storedToken = get(key);
        return storedToken != null && storedToken.equals(token);
    }

    /**
     * 删除token
     */
    public void deleteToken(String userId) {
        String key = "user:token:" + userId;
        delete(key);
    }

    /**
     * 获取锁
     */
    public boolean tryLock(String key, long timeout, TimeUnit unit) {
        return stringRedisTemplate.opsForValue().setIfAbsent(key,"1", timeout, unit);
    }

    /**
     * lua脚本
     *
     */
    public boolean decreaseStock(String lua ,String productId,Integer amount){
        Long isSuccess = stringRedisTemplate.execute(
                new DefaultRedisScript<>(lua, Long.class),
                Collections.singletonList("stock:" + productId),
                String.valueOf(amount)
        );
        return isSuccess>0;
    }

}
