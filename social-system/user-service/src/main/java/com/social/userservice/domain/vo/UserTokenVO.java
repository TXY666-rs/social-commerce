package com.social.userservice.domain.vo;

import lombok.Data;

/**
 * 用户登录令牌返回对象
 */
@Data
public class UserTokenVO {
    
    private String token;
    
    private String tokenPrefix;
    
    private Long userId;
    
    private String username;
    
    private String nickname;
    
    private String avatar;
    
    private Long expiresIn;
}