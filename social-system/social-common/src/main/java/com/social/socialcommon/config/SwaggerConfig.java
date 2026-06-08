package com.social.socialcommon.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;



/**
 * Swagger/OpenAPI配置类
 * 自动生成API文档，支持JWT认证
 */
@Configuration
public class SwaggerConfig {

    /**
     * 配置OpenAPI
     */
    @Bean
    public OpenAPI socialSystemOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("简易社交系统 API文档")
                        .description("简易社交系统 REST API接口文档，包含用户管理、商品管理、订单管理、聊天功能等")
                        .version("v1.0.0")
                        .contact(new Contact()
                                .name("Social System Team")
                                .email("support@social.com")
                                .url("https://www.example.com"))
                        .license(new License()
                                .name("MIT License")
                                .url("https://opensource.org/licenses/MIT")))
                .addSecurityItem(new SecurityRequirement().addList("JWT"))
                .components(new io.swagger.v3.oas.models.Components()
                        .addSecuritySchemes("JWT",
                                new SecurityScheme()
                                        .name("JWT")
                                        .type(SecurityScheme.Type.HTTP)
                                        .scheme("bearer")
                                        .bearerFormat("JWT")));
    }

    /**
     * 用户相关的API分组

    @Bean
    public GroupedOpenApi userApiGroup() {
        return GroupedOpenApi.builder()
                .group("用户管理")
                .pathsToMatch("/api/user/**")
                .pathsToExclude("/api/user/auth/login", "/api/user/auth/register")
                .build();
    }*/

    /**
     * 认证相关的API分组（公开接口）

    @Bean
    public GroupedOpenApi authApiGroup() {
        return GroupedOpenApi.builder()
                .group("用户认证")
                .pathsToMatch("/api/user/auth/**")
                .build();
    }*/

    /**
     * 商品相关的API分组

    @Bean
    public GroupedOpenApi productApiGroup() {
        return GroupedOpenApi.builder()
                .group("商品管理")
                .pathsToMatch("/api/product/**")
                .build();
    }*/

    /**
     * 订单相关的API分组

    @Bean
    public GroupedOpenApi orderApiGroup() {
        return GroupedOpenApi.builder()
                .group("订单管理")
                .pathsToMatch("/api/order/**")
                .build();
    }*/

    /**
     * 聊天相关的API分组

    @Bean
    public GroupedOpenApi chatApiGroup() {
        return GroupedOpenApi.builder()
                .group("聊天功能")
                .pathsToMatch("/api/chat/**")
                .build();
    }*/

    /**
     * 所有API分组（默认）

    @Bean
    public GroupedOpenApi allApiGroup() {
        return GroupedOpenApi.builder()
                .group("全部API")
                .pathsToMatch("/api/**")
                .build();
    }*/
}