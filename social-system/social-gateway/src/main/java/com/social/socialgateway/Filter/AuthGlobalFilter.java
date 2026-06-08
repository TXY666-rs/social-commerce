package com.social.socialgateway.Filter;

import com.social.auth.utils.JwtUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

@Component
public class AuthGlobalFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(AuthGlobalFilter.class);

    private static final String TRACE_ID_HEADER = "X-Trace-Id";

    @Autowired
    private JwtUtil jwtUtil;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {

        String path = exchange.getRequest().getPath().value();

        // 生成或透传 TraceId，用于分布式链路追踪
        String traceId = exchange.getRequest().getHeaders().getFirst(TRACE_ID_HEADER);
        if (traceId == null || traceId.isBlank()) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }
        final String tid = traceId;

        // 放行登录注册等公开接口
        if (path.contains("/login") || path.contains("/register")) {
            ServerHttpRequest request = exchange.getRequest().mutate()
                    .header(TRACE_ID_HEADER, tid)
                    .build();
            log.info("[TraceId:{}] {} {}", tid, exchange.getRequest().getMethod(), path);
            return chain.filter(exchange.mutate().request(request).build());
        }

        // 放行路由降级日志接口（AI Agent 内部调用，无需用户认证）
        if (path.contains("/route-fallback")) {
            ServerHttpRequest request = exchange.getRequest().mutate()
                    .header(TRACE_ID_HEADER, tid)
                    .build();
            return chain.filter(exchange.mutate().request(request).build());
        }

        // 放行健康检查和 Actuator 端点
        if (path.contains("/health") || path.startsWith("/actuator")) {
            ServerHttpRequest request = exchange.getRequest().mutate()
                    .header(TRACE_ID_HEADER, tid)
                    .build();
            return chain.filter(exchange.mutate().request(request).build());
        }

        String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
        if (authHeader == null || authHeader.isBlank()) {
            log.warn("[TraceId:{}] 请求缺少 Authorization, path={}", tid, path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = jwtUtil.extractToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            log.warn("[TraceId:{}] JWT 验证失败, path={}", tid, path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        try {
            Long userId = jwtUtil.getUserId(token);
            Long role = jwtUtil.getUserRole(token);
            String roleStr = (role != null && role == 1) ? "ADMIN" : "USER";
            ServerHttpRequest request = exchange.getRequest().mutate()
                    .header("X-User-Id", userId.toString())
                    .header("X-User-Role", roleStr)
                    .header(TRACE_ID_HEADER, tid)
                    .build();
            log.info("[TraceId:{}] userId={} role={} roleStr={} {} {}", tid, userId, role, roleStr, exchange.getRequest().getMethod(), path);
            return chain.filter(exchange.mutate().request(request).build());
        } catch (Exception e) {
            log.error("[TraceId:{}] JWT 解析异常: {}", tid, e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
    }

    @Override
    public int getOrder() {
        return 0;
    }
}
