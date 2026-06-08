package com.social.auth.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置类
 * 读取 application.yml 中 jwt.* 前缀的配置
 */
@Data
@Component
@ConfigurationProperties(prefix = "jwt")
public class JwtConfig {

    /**
     * 签名密钥
     */
    private String secret;

    /**
     * 令牌有效期（毫秒）
     */
    private long expiration;

    /**
     * 请求头名称
     */
    private String header = "Authorization";

    /**
     * 令牌前缀（如 "Bearer "）
     */
    private String tokenPrefix = "Bearer ";
}
