package com.social.userservice.service;


import com.social.userservice.domain.dto.UserLoginDTO;
import com.social.userservice.domain.dto.UserRegisterDTO;
import com.social.userservice.domain.dto.UserUpdateDTO;
import com.social.userservice.domain.po.User;
import com.social.userservice.domain.vo.UserTokenVO;
import com.social.userservice.domain.vo.UserVO;

import java.util.List;

/**
 * 用户服务接口
 */
public interface UserService {
    
    /**
     * 用户注册
     */
    Long register(UserRegisterDTO registerDTO);
    
    /**
     * 用户登录
     */
    UserTokenVO login(UserLoginDTO loginDTO);
    
    /**
     * 用户退出
     */
    void logout(String token);
    
    /**
     * 获取当前用户信息
     */
    UserVO getCurrentUser(String token);
    
    /**
     * 更新用户信息
     */
    void updateUser(Long userId, UserUpdateDTO updateDTO);
    
    /**
     * 根据ID查询用户
     */
    UserVO getUserById(Long id);
    
    /**
     * 根据用户名查询用户
     */
    UserVO getUserByUsername(String username);
    
    /**
     * 查询所有用户
     */
    List<UserVO> getAllUsers();
    
    /**
     * 删除用户
     */
    boolean deleteUser(Long id);
    
    /**
     * 禁用/启用用户
     */
    boolean toggleUserStatus(Long id, Integer status);
    
    /**
     * 验证用户是否存在
     */
    boolean existsUsername(String username);
    
    /**
     * 验证邮箱是否存在
     */
    boolean existsEmail(String email);
    
    /**
     * 验证手机号是否存在
     */
    boolean existsPhone(String phone);
    
    /**
     * 根据ID获取用户实体
     */
    User getUserEntityById(Long id);
    
    /**
     * 按用户名模糊搜索用户
     */
    List<UserVO> searchUsers(String keyword);

}