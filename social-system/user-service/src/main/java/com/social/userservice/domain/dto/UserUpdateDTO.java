package com.social.userservice.domain.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;

/**
 * 用户更新请求DTO
 */
@Data
public class UserUpdateDTO {
    
    @Size(min = 2, max = 50, message = "昵称长度必须在2-50个字符之间")
    private String nickname;
    
    private String avatar;
    
    private Integer gender;
    
    private LocalDate birthday;
    
    @Size(max = 255, message = "个性签名不能超过255个字符")
    private String signature;
    
    private String email;
    
    private String phone;
}