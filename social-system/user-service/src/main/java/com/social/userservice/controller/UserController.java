package com.social.userservice.controller;

import com.social.socialcommon.result.Result;
import com.social.socialcommon.result.ResultCode;
import com.social.auth.utils.JwtUtil;
import com.social.userservice.domain.dto.UserLoginDTO;
import com.social.userservice.domain.dto.UserRegisterDTO;
import com.social.userservice.domain.dto.UserUpdateDTO;
import com.social.userservice.domain.vo.UserTokenVO;
import com.social.userservice.domain.vo.UserVO;
import com.social.userservice.service.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 用户控制器
 */
@RestController
@RequestMapping("/user")
public class UserController {
    
    @Autowired
    private UserService userService;
    
    @Autowired
    private JwtUtil jwtUtil;


    /**
     * 用户注册
     */
    @PostMapping("/register")
    public Result<Long> register(@Valid @RequestBody UserRegisterDTO registerDTO) {
        try {
            Long userId = userService.register(registerDTO);
            return Result.success("注册成功", userId);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 用户登录
     */
    @PostMapping("/login")
    public Result<UserTokenVO> login(@Valid @RequestBody UserLoginDTO loginDTO) {
        try {
            UserTokenVO tokenVO = userService.login(loginDTO);
            return Result.success("登录成功", tokenVO);
        } catch (Exception e) {
            return Result.error(ResultCode.LOGIN_FAILED.getCode(), e.getMessage());
        }
    }
    
    /**
     * 用户退出
     */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader(value = "Authorization", required = false) String authHeader) {
        try {
            if (authHeader != null) {
                String token = jwtUtil.extractToken(authHeader);
                userService.logout(token);
            }
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 获取当前用户信息
     */
    @GetMapping("/me")
    public Result<UserVO> getCurrentUser(@RequestHeader("Authorization") String authHeader) {
        try {
            String token = jwtUtil.extractToken(authHeader);
            if (token == null) {
                return Result.unauthorized("未提供有效令牌");
            }
            
            UserVO userVO = userService.getCurrentUser(token);
            return Result.success(userVO);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 更新用户信息
     */
    @PutMapping("/update")
    public Result<Boolean> updateUser(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody UserUpdateDTO updateDTO) {
        try {
            String token = jwtUtil.extractToken(authHeader);
            if (token == null) {
                return Result.unauthorized("未提供有效令牌");
            }
            
            Long userId = jwtUtil.getUserId(token);
            userService.updateUser(userId, updateDTO);
            return Result.success("更新成功",true);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 根据ID查询用户
     */
    @GetMapping("/{id}")
    public Result<UserVO> getUserById(@PathVariable Long id) {
        try {
            UserVO userVO = userService.getUserById(id);
            if (userVO != null) {
                return Result.success(userVO);
            } else {
                return Result.notFound("用户不存在");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 根据用户名查询用户
     */
    @GetMapping("/username/{username}")
    public Result<UserVO> getUserByUsername(@PathVariable String username) {
        try {
            UserVO userVO = userService.getUserByUsername(username);
            if (userVO != null) {
                return Result.success(userVO);
            } else {
                return Result.notFound("用户不存在");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 查询所有用户（需要管理员权限）
     */
    @GetMapping("/all")
    public Result<List<UserVO>> getAllUsers() {
        try {
            List<UserVO> users = userService.getAllUsers();
            return Result.success(users);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 删除用户（需要管理员权限）
     */
    @DeleteMapping("/{id}")
    public Result<Boolean> deleteUser(@PathVariable Long id) {
        try {
            boolean deleted = userService.deleteUser(id);
            if (deleted) {
                return Result.success("删除成功", true);
            } else {
                return Result.error("删除失败");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 禁用/启用用户（需要管理员权限）
     */
    @PutMapping("/status/{id}")
    public Result<Boolean> toggleUserStatus(@PathVariable Long id, @RequestParam Integer status) {
        try {
            if (status != 0 && status != 1) {
                return Result.error("状态值无效");
            }
            
            boolean updated = userService.toggleUserStatus(id, status);
            if (updated) {
                String message = status == 0 ? "禁用成功" : "启用成功";
                return Result.success(message, true);
            } else {
                return Result.error("操作失败");
            }
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 检查用户名是否可用
     */
    @GetMapping("/check/username/{username}")
    public Result<Boolean> checkUsername(@PathVariable String username) {
        try {
            boolean exists = userService.existsUsername(username);
            // 返回用户名是否已存在（true=已存在，false=不存在/可用）
            return Result.success("查询成功", exists);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 检查邮箱是否可用
     */
    @GetMapping("/check/email/{email}")
    public Result<Boolean> checkEmail(@PathVariable String email) {
        try {
            boolean exists = userService.existsEmail(email);
            // 返回邮箱是否已存在（true=已存在，false=不存在/可用）
            return Result.success("查询成功", exists);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 检查手机号是否可用
     */
    @GetMapping("/check/phone/{phone}")
    public Result<Boolean> checkPhone(@PathVariable String phone) {
        try {
            boolean exists = userService.existsPhone(phone);
            // 返回手机号是否已存在（true=已存在，false=不存在/可用）
            return Result.success("查询成功", exists);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 搜索用户（按用户名/昵称模糊搜索）
     */
    @GetMapping("/search")
    public Result<List<UserVO>> searchUsers(@RequestParam(required = false) String keyword) {
        try {
            List<UserVO> users = userService.searchUsers(keyword);
            return Result.success(users);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}