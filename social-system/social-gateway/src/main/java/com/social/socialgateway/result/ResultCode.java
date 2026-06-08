package com.social.socialgateway.result;

import lombok.Getter;

/**
 * 响应状态码枚举
 */
@Getter
public enum ResultCode {
    
    /**
     * 成功
     */
    SUCCESS(200, "成功"),
    
    /**
     * 失败
     */
    ERROR(500, "服务器内部错误"),
    
    /**
     * 参数验证失败
     */
    VALIDATE_FAILED(400, "参数验证失败"),
    
    /**
     * 未认证
     */
    UNAUTHORIZED(401, "未认证"),
    
    /**
     * 拒绝访问
     */
    FORBIDDEN(403, "拒绝访问"),
    
    /**
     * 未找到
     */
    NOT_FOUND(404, "未找到"),
    
    /**
     * 方法不允许
     */
    METHOD_NOT_ALLOWED(405, "方法不允许"),
    
    /**
     * 请求超时
     */
    REQUEST_TIMEOUT(408, "请求超时"),
    
    /**
     * 未登录
     */
    NOT_LOGIN(1001, "未登录"),
    
    /**
     * 用户名或密码错误
     */
    LOGIN_FAILED(1002, "用户名或密码错误"),
    
    /**
     * 用户已存在
     */
    USER_EXISTS(1003, "用户已存在"),
    
    /**
     * 用户不存在
     */
    USER_NOT_EXISTS(1004, "用户不存在"),
    
    /**
     * 商品不存在
     */
    PRODUCT_NOT_EXISTS(2001, "商品不存在"),
    
    /**
     * 库存不足
     */
    PRODUCT_STOCK_INSUFFICIENT(2002, "库存不足"),
    
    /**
     * 订单不存在
     */
    ORDER_NOT_EXISTS(3001, "订单不存在"),
    
    /**
     * 支付失败
     */
    PAY_FAILED(3002, "支付失败");
    
    private final Integer code;
    private final String message;
    
    ResultCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}