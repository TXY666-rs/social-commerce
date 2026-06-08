package com.social.socialcommon.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.core.incrementer.IKeyGenerator;
import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;
import com.baomidou.mybatisplus.extension.incrementer.H2KeyGenerator;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 数据源和MyBatis-Plus配置
 * 配置分页插件、SQL日志、多数据源等
 */
@Configuration
public class DataSourceConfig {

    @Value("${spring.profiles.active:dev}")
    private String activeProfile;

    /**
     * MyBatis-Plus插件配置
     * 包括分页插件、性能分析插件等
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        // 分页插件
        PaginationInnerInterceptor paginationInnerInterceptor = new PaginationInnerInterceptor();
        paginationInnerInterceptor.setDbType(DbType.POSTGRE_SQL);
        paginationInnerInterceptor.setMaxLimit(1000L); // 单页最大记录数
        paginationInnerInterceptor.setOverflow(true);  // 超过最大页数时是否显示第一页
        
        interceptor.addInnerInterceptor(paginationInnerInterceptor);
        
        return interceptor;
    }

    /**
     * 主键生成器（仅用于H2测试数据库）
     */
    @Bean
    @ConditionalOnProperty(name = "spring.datasource.url", havingValue = ".*h2.*", matchIfMissing = false)
    public IKeyGenerator keyGenerator() {
        return new H2KeyGenerator();
    }

    /**
     * 自定义ID生成器
     */
    @Bean
    public IdentifierGenerator idGenerator() {
        return new CustomIdGenerator();
    }

    /**
     * 自定义ID生成器
     * 可以在这里实现雪花算法等分布式ID生成
     */
    public static class CustomIdGenerator implements IdentifierGenerator {
        @Override
        public Number nextId(Object entity) {
            // 这里可以集成雪花算法等分布式ID生成算法
            // 暂时返回null，使用数据库自增
            return null;
        }

        @Override
        public String nextUUID(Object entity) {
            // 生成UUID
            return java.util.UUID.randomUUID().toString().replace("-", "");
        }
    }
}