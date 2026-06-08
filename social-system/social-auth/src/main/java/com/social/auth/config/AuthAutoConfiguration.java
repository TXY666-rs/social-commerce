package com.social.auth.config;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.ComponentScan;

/**
 * social-auth 模块自动配置
 * 通过 spring.factories / AutoConfiguration.imports 触发
 * 扫描 com.social.auth 包下的 @Component / @ConfigurationProperties
 */
@AutoConfiguration
@ComponentScan("com.social.auth")
public class AuthAutoConfiguration {
}
