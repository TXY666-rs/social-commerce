package com.social.userservice.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.social.auth.config.JwtConfig;
import com.social.auth.utils.JwtUtil;
import com.social.socialcommon.utils.RedisUtil;
import com.social.userservice.domain.dto.UserLoginDTO;
import com.social.userservice.domain.dto.UserRegisterDTO;
import com.social.userservice.domain.dto.UserUpdateDTO;
import com.social.userservice.domain.po.User;
import com.social.userservice.domain.vo.UserTokenVO;
import com.social.userservice.domain.vo.UserVO;
import com.social.userservice.mapper.UserMapper;
import com.social.userservice.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 用户服务实现类
 */
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {
    
    @Autowired
    private UserMapper userMapper;
    
    @Autowired
    private JwtUtil jwtUtil;
    
    @Autowired
    private RedisUtil redisUtil;
    
    @Autowired
    private JwtConfig jwtConfig;
    
    @Autowired
    private BCryptPasswordEncoder passwordEncoder;
    
    @Autowired
    private HttpServletRequest request;
    
    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long register(UserRegisterDTO registerDTO) {
        // 检查用户名是否存在
        if (existsUsername(registerDTO.getUsername())) {
            throw new RuntimeException("用户名已存在");
        }
        
        // 检查邮箱是否存在
        if (StringUtils.hasText(registerDTO.getEmail()) && existsEmail(registerDTO.getEmail())) {
            throw new RuntimeException("邮箱已被注册");
        }
        
        // 检查手机号是否存在
        if (StringUtils.hasText(registerDTO.getPhone()) && existsPhone(registerDTO.getPhone())) {
            throw new RuntimeException("手机号已被注册");
        }
        
        // 创建用户
        User user = new User();
        BeanUtils.copyProperties(registerDTO, user);
        
        // 加密密码
        user.setPassword(passwordEncoder.encode(registerDTO.getPassword()));
        
        // 设置默认值
        user.setStatus(1); // 正常状态
        user.setAvatar("https://avatars.githubusercontent.com/u/default"); // 默认头像
        user.setGender(registerDTO.getGender() != null ? registerDTO.getGender() : 0);
        
        // 保存用户
        userMapper.insert(user);
        
        return user.getId();
    }
    
    @Override
    public UserTokenVO login(UserLoginDTO loginDTO) {
        // 查询用户
        User user = userMapper.findByUsername(loginDTO.getUsername());
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        // 检查用户状态
        if (user.getStatus() != 1) {
            throw new RuntimeException("用户已被禁用");
        }
        
        // 验证密码
        if (!passwordEncoder.matches(loginDTO.getPassword(), user.getPassword())) {
            throw new RuntimeException("用户名或密码错误");
        }
        
        // 生成JWT令牌
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", user.getId());
        claims.put("username", user.getUsername());
        claims.put("role", user.getRole());
        String token = jwtUtil.generateToken(claims);
        
        // 存储令牌到Redis
        redisUtil.storeToken(user.getId().toString(), token);

        // 更新最后登录信息
        String ip = getClientIp();
        userMapper.updateLoginInfo(user.getId(), ip);
        
        // 构建返回结果
        UserTokenVO tokenVO = BeanUtil.copyProperties(user, UserTokenVO.class);
        tokenVO.setToken(token);
        tokenVO.setTokenPrefix(jwtConfig.getTokenPrefix());
        tokenVO.setExpiresIn(jwtConfig.getExpiration() / 1000); // 转换为秒
        
        return tokenVO;
    }
    
    @Override
    public void logout(String token) {
        if (StringUtils.hasText(token)) {
            try {
                Long userId = jwtUtil.getUserId(token);
                redisUtil.deleteToken(userId.toString());
            } catch (Exception e) {
                // 令牌无效，忽略
            }
        }
    }
    
    @Override
    public UserVO getCurrentUser(String token) {
        if (StrUtil.isEmpty(token)) {
            throw new RuntimeException("未提供认证令牌");
        }
        // 验证令牌
        if (!jwtUtil.validateToken(token)) {
            throw new RuntimeException("认证令牌无效");
        }
        
        // 获取用户ID
        Long userId = jwtUtil.getUserId(token);

        // 验证Redis中的令牌
        if (!redisUtil.validateToken(userId.toString(), token)) {
            throw new RuntimeException("认证令牌已失效");
        }
        
        // 查询用户信息
        User user = getUserEntityById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        
        return convertToVO(user);
    }
    
    @Override
    public void updateUser(Long userId, UserUpdateDTO updateDTO) {
        User user = getUserEntityById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        LambdaUpdateWrapper<User> wrapper = Wrappers.lambdaUpdate();
        wrapper
                .eq(User::getId, userId)
                .set(User::getAvatar, updateDTO.getAvatar())
                .set(User::getEmail, updateDTO.getEmail())
                .set(User::getPhone, updateDTO.getPhone())
                .set(User::getGender, updateDTO.getGender())
                .set(User::getBirthday, updateDTO.getBirthday());
        userMapper.update(null, wrapper);
    }
    
    @Override
    public UserVO getUserById(Long id) {
        User user = getUserEntityById(id);
        return user != null ? convertToVO(user) : null;
    }
    
    @Override
    public UserVO getUserByUsername(String username) {
        User user = userMapper.findByUsername(username);
        return user != null ? convertToVO(user) : null;
    }
    
    @Override
    public List<UserVO> getAllUsers() {
        LambdaQueryWrapper<User> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(User::getIsDeleted, 0)
                   .orderByDesc(User::getCreateTime);
        
        List<User> users = list(queryWrapper);
        return users.stream()
                   .map(this::convertToVO)
                   .collect(Collectors.toList());
    }
    
    @Override
    public boolean deleteUser(Long id) {
        User user = getUserEntityById(id);
        if (user == null) {
            return false;
        }
        
        user.setIsDeleted(1);
        return updateById(user);
    }
    
    @Override
    public boolean toggleUserStatus(Long id, Integer status) {
        User user = getUserEntityById(id);
        if (user == null) {
            return false;
        }
        
        user.setStatus(status);
        user.setUpdateTime(LocalDateTime.now());
        return updateById(user);
    }
    
    @Override
    public boolean existsUsername(String username) {
        return userMapper.findByUsername(username) != null;
    }
    
    @Override
    public boolean existsEmail(String email) {
        return StringUtils.hasText(email) && userMapper.findByEmail(email) != null;
    }
    
    @Override
    public boolean existsPhone(String phone) {
        return StringUtils.hasText(phone) && userMapper.findByPhone(phone) != null;
    }
    
    @Override
    public User getUserEntityById(Long id) {
        return getById(id);
    }
    
    @Override
    public List<UserVO> searchUsers(String keyword) {
        LambdaQueryWrapper<User> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(User::getIsDeleted, 0);
        if (StringUtils.hasText(keyword)) {
            queryWrapper.and(w -> w
                    .like(User::getUsername, keyword)
                    .or()
                    .like(User::getNickname, keyword)
            );
        }
        queryWrapper.orderByDesc(User::getCreateTime);
        
        List<User> users = page(new Page<>(1, 20), queryWrapper).getRecords();
        return users.stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());
    }



    /**
     * 将User实体转换为UserVO
     */
    private UserVO convertToVO(User user) {
        if (user == null) {
            return null;
        }
        
        UserVO userVO = new UserVO();
        BeanUtils.copyProperties(user, userVO);
        return userVO;
    }
    
    /**
     * 获取客户端IP地址
     */
    private String getClientIp() {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        
        // 对于多个代理的情况，第一个IP为客户端真实IP
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        
        return ip;
    }
}