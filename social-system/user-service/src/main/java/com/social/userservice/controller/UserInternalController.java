package com.social.userservice.controller;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.social.socialcommon.result.Result;
import com.social.user.service.api.dto.UserBriefDTO;
import com.social.user.service.api.feign.UserClient;
import com.social.userservice.domain.po.User;
import com.social.userservice.domain.vo.UserVO;
import com.social.userservice.mapper.UserMapper;
import com.social.userservice.service.UserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
public class UserInternalController implements UserClient {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private UserService userService;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Override
    public Result<UserBriefDTO> getUserBrief(Long id) {
        User user = userMapper.selectById(id);
        if (user == null) {
            return Result.error("用户不存在");
        }
        UserBriefDTO userBriefDTO = BeanUtil.copyProperties(user, UserBriefDTO.class);
        return Result.success(userBriefDTO);
    }

    @Override
    public Result<Map<Long, UserBriefDTO>> batchGetUserBrief(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return Result.success(new HashMap<>());
        }
        List<User> users = userMapper.selectBatchIds(ids);
        Map<Long, UserBriefDTO> map = new HashMap<>();
        for (User user : users) {
            map.put(user.getId(), BeanUtil.copyProperties(user, UserBriefDTO.class));
        }
        // 补全未找到的 ID（可能已删除）
        for (Long id : ids) {
            map.putIfAbsent(id, null);
        }
        return Result.success(map);
    }

    // ========== Admin 管理端接口实现 ==========

    @Override
    public Result<Map<String, Object>> getAdminUserPage(String keyword, Integer status, Integer role, Integer pageNum, Integer pageSize) {
        try {
            Page<User> page = new Page<>(pageNum, pageSize);
            com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<User> wrapper =
                    new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();

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

    @Override
    public Result<Map<String, Object>> getAdminUserDetail(Long id) {
        try {
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

    @Override
    public Result<Boolean> adminToggleUserStatus(Long id, Integer status) {
        try {
            boolean updated = userService.toggleUserStatus(id, status);
            return Result.success(status == 0 ? "禁用成功" : "启用成功", updated);
        } catch (Exception e) {
            log.error("管理端切换用户状态失败", e);
            return Result.error(e.getMessage());
        }
    }

    @Override
    public Result<Boolean> adminResetPassword(Long id, String newPassword) {
        try {
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

    @Override
    public Result<Long> getAdminUserCount() {
        try {
            Long count = userMapper.selectCount(null);
            return Result.success(count);
        } catch (Exception e) {
            log.error("管理端获取用户总数失败", e);
            return Result.error(e.getMessage());
        }
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
