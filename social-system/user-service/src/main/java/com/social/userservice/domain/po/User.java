package com.social.userservice.domain.po;

import com.baomidou.mybatisplus.annotation.TableName;
import com.social.socialcommon.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 用户实体类
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("\"user\"")
public class User extends BaseEntity {
    
    /**
     * 用户名
     */
    private String username;
    
    /**
     * 昵称
     */
    private String nickname;
    
    /**
     * 密码
     */
    private String password;
    
    /**
     * 邮箱
     */
    private String email;
    
    /**
     * 手机号
     */
    private String phone;
    
    /**
     * 头像URL
     */
    private String avatar;
    
    /**
     * 性别 (0:未知, 1:男, 2:女)
     */
    private Integer gender;
    
    /**
     * 生日
     */
    private LocalDate birthday;

    /**
     * 状态 (0:禁用, 1:正常)
     */
    private Integer status;
    
    /**
     * 最后登录时间
     */
    private LocalDateTime lastLoginTime;
    
    /**
     * 最后登录IP
     */
    private String lastLoginIp;

    /**
     * 用户角色 (0:普通用户, 1:管理员)
     */
    private Integer role;
}