package com.social.socialcommon.result;

import lombok.Data;

import java.io.Serializable;

/**
 * 统一响应结果
 */
@Data
public class Result<T> implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    /**
     * 状态码
     */
    private Integer code;
    
    /**
     * 消息
     */
    private String message;
    
    /**
     * 数据
     */
    private T data;
    
    /**
     * 时间戳
     */
    private Long timestamp;
    
    /**
     * 成功结果
     */
    public static <T> Result<T> success() {
        return success(null);
    }
    
    /**
     * 成功结果
     */
    public static <T> Result<T> success(T data) {
        return success("操作成功", data);
    }
    
    /**
     * 成功结果
     */
    public static <T> Result<T> success(String message, T data) {
        Result<T> result = new Result<>();
        result.setCode(ResultCode.SUCCESS.getCode());
        result.setMessage(message);
        result.setData(data);
        result.setTimestamp(System.currentTimeMillis());
        return result;
    }
    
    /**
     * 失败结果
     */
    public static <T> Result<T> error() {
        return error("操作失败");
    }
    
    /**
     * 失败结果
     */
    public static <T> Result<T> error(String message) {
        return error(ResultCode.ERROR.getCode(), message);
    }
    
    /**
     * 失败结果
     */
    public static <T> Result<T> error(Integer code, String message) {
        Result<T> result = new Result<>();
        result.setCode(code);
        result.setMessage(message);
        result.setTimestamp(System.currentTimeMillis());
        return result;
    }
    
    /**
     * 未认证
     */
    public static <T> Result<T> unauthorized(String message) {
        return error(ResultCode.UNAUTHORIZED.getCode(), message);
    }
    
    /**
     * 拒绝访问
     */
    public static <T> Result<T> forbidden(String message) {
        return error(ResultCode.FORBIDDEN.getCode(), message);
    }
    
    /**
     * 未找到
     */
    public static <T> Result<T> notFound(String message) {
        return error(ResultCode.NOT_FOUND.getCode(), message);
    }
    
    /**
     * 验证失败
     */
    public static <T> Result<T> validateFailed(String message) {
        return error(ResultCode.VALIDATE_FAILED.getCode(), message);
    }
}