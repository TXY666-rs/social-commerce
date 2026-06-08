package com.social.userservice.controller;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.socialcommon.result.Result;
import com.social.userservice.domain.po.User;
import com.social.userservice.domain.vo.UserVO;
import com.social.userservice.mapper.UserMapper;
import com.social.userservice.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/admin/users")
public class AdminUserController {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private UserService userService;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    /**
     * 分页查询用户列表
     */
    @GetMapping
    public Result<Map<String, Object>> getAdminUserPage(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) Integer role,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            Page<User> page = new Page<>(pageNum, pageSize);
            LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();

            if (keyword != null && !keyword.isEmpty()) {
                wrapper.and(w -> w.like(User::getUsername, keyword)
                        .or().like(User::getNickname, keyword)
                        .or().like(User::getEmail, keyword));
            }
            if (status != null) {
                wrapper.eq(User::getStatus, status);
            }
            if (role != null) {
                wrapper.eq(User::getRole, role);
            }
            wrapper.orderByDesc(User::getCreateTime);

            IPage<User> userPage = userMapper.selectPage(page, wrapper);

            List<Map<String, Object>> records = userPage.getRecords().stream()
                    .map(this::userToMap)
                    .collect(Collectors.toList());

            Map<String, Object> result = new HashMap<>();
            result.put("records", records);
            result.put("total", userPage.getTotal());
            result.put("pages", userPage.getPages());
            result.put("current", userPage.getCurrent());
            result.put("size", userPage.getSize());

            return Result.success(result);
        } catch (Exception e) {
            log.error("管理端查询用户列表失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 获取用户详情
     */
    @GetMapping("/{id}")
    public Result<Map<String, Object>> getAdminUserDetail(@PathVariable Long id, HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            UserVO userVO = userService.getUserById(id);
            if (userVO == null) {
                return Result.notFound("用户不存在");
            }
            Map<String, Object> map = BeanUtil.beanToMap(userVO);
            return Result.success(map);
        } catch (Exception e) {
            log.error("管理端获取用户详情失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 禁用/启用用户
     */
    @PutMapping("/{id}/status")
    public Result<Boolean> adminToggleUserStatus(
            @PathVariable Long id,
            @RequestParam Integer status,
            HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            boolean updated = userService.toggleUserStatus(id, status);
            return Result.success(status == 0 ? "禁用成功" : "启用成功", updated);
        } catch (Exception e) {
            log.error("管理端切换用户状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    /**
     * 重置密码
     */
    @PutMapping("/{id}/reset-password")
    public Result<Boolean> adminResetPassword(
            @PathVariable Long id,
            @RequestParam String newPassword,
            HttpServletRequest request) {
        try {
            if (!isAdmin(request)) {
                return Result.error("无管理员权限");
            }
            User user = userMapper.selectById(id);
            if (user == null) {
                return Result.notFound("用户不存在");
            }
            user.setPassword(passwordEncoder.encode(newPassword));
            userMapper.updateById(user);
            return Result.success("重置密码成功", true);
        } catch (Exception e) {
            log.error("管理端重置密码失败", e);
            return Result.error(e.getMessage());
        }
    }

    private boolean isAdmin(HttpServletRequest request) {
        String role = request.getHeader("X-User-Role");
        return "ADMIN".equals(role);
    }

    private Map<String, Object> userToMap(User user) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", user.getId());
        map.put("username", user.getUsername());
        map.put("nickname", user.getNickname());
        map.put("email", user.getEmail());
        map.put("phone", user.getPhone());
        map.put("avatar", user.getAvatar());
        map.put("role", user.getRole());
        map.put("status", user.getStatus());
        map.put("createTime", user.getCreateTime());
        return map;
    }
}
