package com.social.userservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.social.userservice.domain.po.User;
import org.apache.ibatis.annotations.Mapper;

/**
 * 用户Mapper接口
 */
@Mapper
public interface UserMapper extends BaseMapper<User> {
    
    /**
     * 根据用户名查询用户
     */
    User findByUsername(String username);
    
    /**
     * 根据邮箱查询用户
     */
    User findByEmail(String email);
    
    /**
     * 根据手机号查询用户
     */
    User findByPhone(String phone);
    
    /**
     * 更新最后登录信息
     */
    int updateLoginInfo(Long userId, String loginIp);
}