package com.social.user.service.api.feign;

import com.social.socialcommon.result.Result;
import com.social.user.service.api.dto.UserBriefDTO;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@FeignClient(name = "user-service", path = "/api", fallbackFactory = UserClientFallbackFactory.class)
public interface UserClient {

    @GetMapping("/internal/user/{id}")
    Result<UserBriefDTO> getUserBrief(@PathVariable("id") Long id);

    @GetMapping("/internal/user/batch")
    Result<Map<Long, UserBriefDTO>> batchGetUserBrief(@RequestParam("ids") List<Long> ids);

    // ========== Admin 管理端接口 ==========

    @GetMapping("/internal/admin/users")
    Result<Map<String, Object>> getAdminUserPage(
            @RequestParam(value = "keyword", required = false) String keyword,
            @RequestParam(value = "status", required = false) Integer status,
            @RequestParam(value = "role", required = false) Integer role,
            @RequestParam("pageNum") Integer pageNum,
            @RequestParam("pageSize") Integer pageSize);

    @GetMapping("/internal/admin/users/{id}")
    Result<Map<String, Object>> getAdminUserDetail(@PathVariable("id") Long id);

    @PutMapping("/internal/admin/users/{id}/status")
    Result<Boolean> adminToggleUserStatus(@PathVariable("id") Long id,
                                           @RequestParam("status") Integer status);

    @PutMapping("/internal/admin/users/{id}/reset-password")
    Result<Boolean> adminResetPassword(@PathVariable("id") Long id,
                                        @RequestParam("newPassword") String newPassword);

    @GetMapping("/internal/admin/users/count")
    Result<Long> getAdminUserCount();
}
